"""
Optional AI-assist layer using Groq's LLM API.

The deterministic rule engine (rule_engine.py) is the sole authority on
compliant/non-compliant verdicts - that keeps the checker auditable and
reproducible for enforcement use. Groq is used only in a supporting role,
and only ever to *add* information, never to overturn a verdict the rule
engine already reached:

  1. `analyze_image` sends the label photo itself to a Groq vision model as
     an independent second look - it can read declarations OCR garbled or
     split across lines, and can visually flag legibility issues (tiny
     font, low contrast) that a pixel-height measurement might miss.
  2. If the vision call is unavailable/fails, `generate_summary` still
     produces a plain-language report summary from a text-only model.

If GROQ_API_KEY is not configured, every function no-ops and the app keeps
working on rule-engine output alone.
"""
import base64
import json
import logging

from ..config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if not settings.groq_api_key:
        return None
    if _client is None:
        from groq import Groq

        _client = Groq(api_key=settings.groq_api_key)
    return _client


def is_enabled() -> bool:
    return bool(settings.groq_api_key)


def _fallback_summary(product_name: str, declarations: list[dict]) -> str:
    violations = [d for d in declarations if not d["compliant"]]
    if not violations:
        return f"{product_name} appears to comply with all checked Legal Metrology declarations."
    issues = "; ".join(f"{d['label']} ({d['issue']})" for d in violations)
    return f"{product_name} has {len(violations)} potential issue(s): {issues}."


def analyze_image(image_bytes: bytes, mime: str, product_name: str, declarations: list[dict]) -> dict:
    """
    Send the label photo to a Groq vision model as an independent check.
    Returns {"recovered": {label: snippet}, "visual_notes": str, "summary": str}
    - any field can be empty/missing if the call fails, in which case the
    caller should fall back to generate_summary() for the summary text.
    """
    client = _get_client()
    if client is None:
        return {}

    try:
        b64 = base64.b64encode(image_bytes).decode("ascii")

        missing_labels = [d["label"] for d in declarations if not d["found"]]
        prompt = (
            "You are assisting a Legal Metrology compliance inspector reviewing "
            f"a label photo for the product '{product_name}', sold as a packaged "
            "commodity in India. An automated OCR + rule-based check already "
            "ran; here are its results as JSON (do not contradict a declaration "
            "already marked compliant):\n"
            f"{json.dumps(declarations)}\n\n"
            "Look at the attached label image yourself and:\n"
            "1. For each of these declarations the automated check could NOT "
            f"find: {json.dumps(missing_labels)} - check if it is actually "
            "visible in the photo (OCR sometimes misses stylised or tiny "
            "text). Only report it if you can actually read it in the image.\n"
            "2. Note any visible legibility problems - e.g. a declaration "
            "printed in a font that looks disproportionately small, low "
            "contrast against the background, or partly obscured.\n"
            "3. Write a concise 2-4 sentence plain-language compliance summary "
            "for the inspector, referencing rule numbers where given.\n\n"
            "Respond ONLY with a JSON object of the form "
            '{"recovered": {"<declaration label>": "<exact text you read, '
            'or omit if not found>"}, "visual_notes": "<string, empty if none>", '
            '"summary": "<string>"}'
        )

        resp = client.chat.completions.create(
            model=settings.groq_vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return {
            "recovered": {
                k: v
                for k, v in (data.get("recovered") or {}).items()
                if isinstance(v, str) and v.strip()
            },
            "visual_notes": data.get("visual_notes") or "",
            "summary": data.get("summary") or "",
        }
    except Exception:
        logger.exception("Groq analyze_image failed")
        return {}


def generate_summary(product_name: str, declarations: list[dict]) -> str:
    """Text-only fallback summary, used when the vision call is unavailable."""
    client = _get_client()
    if client is None:
        return _fallback_summary(product_name, declarations)

    prompt = (
        "Write a concise (2-4 sentence) plain-language compliance summary for "
        "an enforcement inspector, based on this automated Legal Metrology "
        "label check. Be factual and neutral, reference rule numbers where "
        f"given.\n\nProduct: {product_name}\n\n"
        f"Declaration results (JSON): {json.dumps(declarations)}"
    )

    try:
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        logger.exception("Groq generate_summary failed")
        return _fallback_summary(product_name, declarations)
