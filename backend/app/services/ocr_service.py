"""
OCR extraction service built on EasyOCR (pure-pip, no external binary
install required - unlike Tesseract which needs a separate system package).
The reader is loaded lazily and cached because model loading is slow.
"""
import threading
from typing import TypedDict

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
    results = reader.readtext(image_bytes)

    lines: list[OcrLine] = []
    for bbox, text, confidence in results:
        ys = [pt[1] for pt in bbox]
        height_px = max(ys) - min(ys)
        lines.append(
            {
                "text": text,
                "confidence": float(confidence),
                "bbox": [[float(x), float(y)] for x, y in bbox],
                "height_px": float(height_px),
            }
        )
    return lines


def full_text(lines: list[OcrLine]) -> str:
    return "\n".join(l["text"] for l in lines)
