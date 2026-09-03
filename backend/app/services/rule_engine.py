import re

from . import groq_service
from .ocr_service import OcrLine, full_text
from .rules_data import (
    MANDATORY_DECLARATIONS,
    min_required_mm_for_net_quantity,
    MRP_MIN_HEIGHT_MM,
)


def _build_candidates(lines: list[OcrLine]) -> list[OcrLine]:
    """
    OCR frequently splits one printed declaration (e.g. "MRP Rs." / "189.00
    (incl. of all taxes)") across two or three separate detected lines. Single
    lines are tried first (best bbox accuracy for font-size checks); sliding
    windows of adjacent lines are added as a fallback so a declaration split
    across lines can still be matched.
    """
    candidates: list[OcrLine] = list(lines)
    for window in (2, 3):
        for i in range(len(lines) - window + 1):
            group = lines[i : i + window]
            candidates.append(
                {
                    "text": " ".join(l["text"] for l in group),
                    "confidence": min(l["confidence"] for l in group),
                    "bbox": group[0]["bbox"],
                    "height_px": max(l["height_px"] for l in group),
                }
            )
    return candidates


def _find_match(lines: list[OcrLine], patterns: list[str]) -> OcrLine | None:
    for line in _build_candidates(lines):
        for pattern in patterns:
            if re.search(pattern, line["text"], flags=re.IGNORECASE):
                return line
    return None


def evaluate_scan(
    lines: list[OcrLine],
    pdp_area_cm2: float | None,
    calibration_mm_per_px: float | None,
    product_name: str,
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> dict:
    raw_text = full_text(lines)
    results = []
    missing_labels_to_defs = {}

    for decl in MANDATORY_DECLARATIONS:
        match = _find_match(lines, decl["patterns"])
        entry = {
            "key": decl["key"],
            "label": decl["label"],
            "rule_ref": decl["rule_ref"],
            "found": match is not None,
            "matched_text": match["text"] if match else None,
            "bbox": match["bbox"] if match else None,
            "font_height_mm": None,
            "min_required_mm": None,
            "compliant": False,
            "severity": "minor" if decl.get("optional") else "major",
            "issue": None,
        }

        if decl.get("requires_font_check") and match is not None:
            if decl["key"] == "net_quantity":
                min_mm = min_required_mm_for_net_quantity(pdp_area_cm2)
            else:
                min_mm = MRP_MIN_HEIGHT_MM
            entry["min_required_mm"] = min_mm

            if calibration_mm_per_px:
                font_mm = round(match["height_px"] * calibration_mm_per_px, 2)
                entry["font_height_mm"] = font_mm
                if font_mm < min_mm:
                    entry["issue"] = (
                        f"Font height {font_mm}mm is below the minimum "
                        f"{min_mm}mm required by {decl['rule_ref']}"
                    )
                else:
                    entry["compliant"] = True
            else:
                # No physical calibration provided - presence is verified but
                # size compliance is indeterminate rather than failed.
                entry["compliant"] = True
                entry["issue"] = (
                    "Declaration found, but font-size could not be verified - "
                    "no physical scale calibration was supplied for this scan."
                )
                entry["severity"] = "minor"
        elif match is not None:
            entry["compliant"] = True
            if decl.get("fallback_note"):
                entry["issue"] = decl["fallback_note"]
        else:
            entry["issue"] = f"Declaration not detected on the label ({decl['rule_ref']})."
            if not decl.get("optional"):
                missing_labels_to_defs[decl["label"]] = entry

        results.append(entry)

    # AI-assist pass: send the label photo itself to Groq's vision model as
    # an independent second look, in case OCR noise or split lines caused a
    # false negative. This can only move a result from "missing" to "found"
    # for human review - it never overrides a match the rule engine already
    # made or downgrades a compliant verdict.
    vision_result = {}
    if groq_service.is_enabled() and image_bytes:
        vision_result = groq_service.analyze_image(image_bytes, image_mime, product_name, results)

    for label, snippet in vision_result.get("recovered", {}).items():
        if label in missing_labels_to_defs:
            entry = missing_labels_to_defs[label]
            entry["found"] = True
            entry["compliant"] = True
            entry["matched_text"] = snippet
            entry["issue"] = (
                "Detected by Groq's vision review of the label photo (not "
                "the primary rule engine) - please verify manually."
            )
            entry["severity"] = "minor"

    ai_summary = vision_result.get("summary") or None
    if groq_service.is_enabled() and not ai_summary:
        ai_summary = groq_service.generate_summary(product_name, results)

    visual_notes = vision_result.get("visual_notes")
    if visual_notes:
        ai_summary = f"{ai_summary}\n\nVisual note: {visual_notes}" if ai_summary else f"Visual note: {visual_notes}"

    required = [r for r in results if r["severity"] == "major"]
    compliant_count = sum(1 for r in required if r["compliant"])
    score = round(100 * compliant_count / len(required), 1) if required else 100.0
    overall_compliant = all(r["compliant"] for r in required)

    return {
        "raw_text": raw_text,
        "declarations": results,
        "overall_compliant": overall_compliant,
        "score": score,
        "ai_summary": ai_summary,
    }
