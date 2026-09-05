"""
OCR extraction service built on EasyOCR (pure-pip, no external binary
install required - unlike Tesseract which needs a separate system package).
The reader is loaded lazily and cached because model loading is slow.
"""
import threading
from typing import TypedDict

from . import image_preprocessing

_reader = None
_reader_lock = threading.Lock()


class OcrLine(TypedDict):
    text: str
    confidence: float
    bbox: list[list[float]]  # 4 (x, y) points
    height_px: float


def _get_reader():
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:
                import easyocr

                _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def extract_lines(image_bytes: bytes) -> list[OcrLine]:
    reader = _get_reader()
    processed, scale_factor = image_preprocessing.normalize_for_ocr(image_bytes)
    results = reader.readtext(
        processed,
        # Defaults are tuned for scene text, not the small/dense print on
        # nutrition tables and net-quantity declarations - these loosen
        # detection to catch faint/small text at the cost of a few more
        # false positives, which the rule engine's regex matching filters
        # out anyway.
        mag_ratio=1.5,
        text_threshold=0.6,
        low_text=0.3,
        contrast_ths=0.05,
        adjust_contrast=0.7,
        paragraph=False,
    )

    lines: list[OcrLine] = []
    for bbox, text, confidence in results:
        # bbox/height are in the (possibly upscaled) preprocessed image's
        # pixel space; scale back down to the original photo's pixel space
        # so a calibration_mm_per_px computed against the original photo
        # still gives correct font-size-in-mm measurements.
        scaled_bbox = [[x / scale_factor, y / scale_factor] for x, y in bbox]
        ys = [pt[1] for pt in scaled_bbox]
        height_px = max(ys) - min(ys)
        lines.append(
            {
                "text": text,
                "confidence": float(confidence),
                "bbox": [[float(x), float(y)] for x, y in scaled_bbox],
                "height_px": float(height_px),
            }
        )
    return lines


def full_text(lines: list[OcrLine]) -> str:
    return "\n".join(l["text"] for l in lines)


def guess_product_name(lines: list[OcrLine]) -> str | None:
    """
    Naive fallback for when Groq isn't configured to identify the product
    from its front-of-pack photo: brand/product names are almost always the
    most prominent (tallest) text on the front of a package, so pick the
    tallest OCR line that looks like real text rather than noise.
    """
    candidates = [l for l in lines if len(l["text"].strip()) >= 3]
    if not candidates:
        return None
    return max(candidates, key=lambda l: l["height_px"])["text"].strip()
