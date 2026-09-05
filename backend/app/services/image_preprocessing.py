"""
Image preprocessing to make real-world phone photos of product labels
readable by OCR. Phone photos routinely arrive rotated (EXIF orientation),
undersized for small print (nutrition tables, net-quantity text), and low
contrast (glossy/foil packaging, uneven lighting) - all of which badly
degrade EasyOCR's accuracy if the raw bytes are handed to it directly.
"""
import io

import cv2
import numpy as np
from PIL import Image, ImageOps

# EasyOCR (and most OCR engines) read small print far more reliably above
# roughly this many pixels on the short side. Phone photos are usually well
# above this, but downscaled/thumbnail uploads are not.
MIN_SHORT_SIDE = 1400
MAX_SHORT_SIDE = 2600  # avoid pointlessly blowing up an already-huge photo


def _pil_to_cv2(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _cv2_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def _enhance_contrast(arr: np.ndarray) -> np.ndarray:
    """CLAHE (adaptive histogram equalization) on the luminance channel only,
    so colour isn't distorted - helps text on glossy/foil or unevenly lit
    packaging stand out without blowing out highlights."""
    lab = cv2.cvtColor(arr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def _sharpen(arr: np.ndarray) -> np.ndarray:
    """Mild unsharp mask - counteracts the softness upscaling introduces."""
    blurred = cv2.GaussianBlur(arr, (0, 0), sigmaX=2)
    return cv2.addWeighted(arr, 1.5, blurred, -0.5, 0)


def _denoise(arr: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(arr, None, h=5, hColor=5, templateWindowSize=7, searchWindowSize=21)


def normalize_for_ocr(image_bytes: bytes) -> tuple[bytes, float]:
    """
    Returns (PNG bytes ready for OCR, scale_factor) where scale_factor is how
    much larger the returned image is than the EXIF-corrected original - the
    caller must divide any measured pixel size (e.g. bounding-box height) by
    this before applying a calibration computed against the original photo,
    or font-size-in-mm measurements will be silently inflated.

    Preprocessing: EXIF-corrected orientation, upscaled if the short side is
    too small for reliable small-print detection, denoised,
    contrast-enhanced, and sharpened. Falls back to the original bytes
    (orientation-corrected only) if any enhancement step fails, so a
    preprocessing bug never breaks scanning outright.
    """
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)  # phones store rotation in EXIF, not pixels
    img = img.convert("RGB")

    # Upscaling is plain PIL and essentially never fails - do it outside the
    # try/except below so scale_factor is always correct even if the
    # OpenCV enhancement steps (which operate on the already-resized image)
    # fail on some unusual input.
    scale_factor = 1.0
    short_side = min(img.size)
    if short_side < MIN_SHORT_SIDE:
        scale_factor = min(MIN_SHORT_SIDE / short_side, MAX_SHORT_SIDE / short_side)
        new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
        img = img.resize(new_size, Image.LANCZOS)

    try:
        arr = _pil_to_cv2(img)
        arr = _denoise(arr)
        arr = _enhance_contrast(arr)
        arr = _sharpen(arr)
        img = _cv2_to_pil(arr)
    except Exception:
        # Preprocessing is a best-effort quality boost, not a correctness
        # requirement - if OpenCV chokes on an unusual image, OCR the
        # resized-but-unenhanced image rather than fail the whole scan.
        pass

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), scale_factor


def blur_score(image_bytes: bytes) -> float:
    """Variance of the Laplacian - a low score means the photo is likely too
    blurry for reliable OCR. Used to surface a hint to the user, not to
    block scanning."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img).convert("L")
    arr = np.array(img)
    return float(cv2.Laplacian(arr, cv2.CV_64F).var())


def short_side_px(image_bytes: bytes) -> int:
    """The photo's shorter dimension in pixels, pre-upscaling. Upscaling
    (done in normalize_for_ocr) helps EasyOCR but can't invent detail a
    low-resolution source photo never captured - this is used to warn the
    user separately from the blur check."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    return min(img.size)
