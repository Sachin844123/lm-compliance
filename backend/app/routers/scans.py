import json
import mimetypes
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, Response
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_role
from ..services import (
    ocr_service,
    rule_engine,
    report_generator,
    storage_service,
    image_preprocessing,
    groq_service,
)

router = APIRouter(prefix="/scans", tags=["scans"])

BLUR_WARNING_THRESHOLD = 60.0
MIN_RECOMMENDED_SHORT_SIDE = 900


def _guess_mime(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "image/jpeg"


@router.post("/", response_model=schemas.ScanDetailOut)
def create_scan(
    front_image: UploadFile = File(
        ..., description="Front-of-pack photo, used to auto-identify the product"
    ),
    image: UploadFile = File(..., description="Photo of the declarations panel to check for compliance"),
    product_name: Optional[str] = Form(None, description="Override the auto-identified product name"),
    brand_name: Optional[str] = Form(None, description="Override the auto-identified brand"),
    category: Optional[str] = Form(None, description="Override the auto-identified category"),
    calibration_mm_per_px: Optional[float] = Form(None),
    pdp_area_cm2: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user),
):
    image_bytes = image.file.read()
    mime = _guess_mime(image.filename or "image.jpg")
    front_bytes = front_image.file.read()
    front_mime = _guess_mime(front_image.filename or "image.jpg")

    # Auto-identify the product from its front-of-pack photo so nothing has
    # to be typed in manually. Groq's vision model does this reliably; if
    # it's not configured, fall back to a same-request OCR heuristic (the
    # most prominent text on a package front is almost always the product/
    # brand name) so the app still works with zero external setup.
    try:
        identified = groq_service.identify_product(front_bytes, front_mime) if groq_service.is_enabled() else {}
    except Exception:
        identified = {}
    final_product_name = product_name or identified.get("product_name")
    final_brand_name = brand_name or identified.get("brand_name")
    final_category = category or identified.get("category")
    if not final_product_name:
        try:
            front_lines = ocr_service.extract_lines(front_bytes)
            final_product_name = ocr_service.guess_product_name(front_lines)
        except Exception:
            final_product_name = None
        final_product_name = final_product_name or "Unidentified product"

    ext = Path(image.filename or "image.jpg").suffix or ".jpg"
    key = f"{uuid.uuid4().hex}{ext}"
    storage_service.save_file(image_bytes, key, mime)

    front_ext = Path(front_image.filename or "image.jpg").suffix or ".jpg"
    front_key = f"{uuid.uuid4().hex}{front_ext}"
    storage_service.save_file(front_bytes, front_key, front_mime)

    scan = models.Scan(
        product_name=final_product_name,
        brand_name=final_brand_name,
        category=final_category,
        image_path=key,
        front_image_path=front_key,
        calibration_mm_per_px=calibration_mm_per_px,
        pdp_area_cm2=pdp_area_cm2,
        status=models.ScanStatus.processing,
        created_by_id=current_user.id,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        lines = ocr_service.extract_lines(image_bytes)
        result = rule_engine.evaluate_scan(
            lines, pdp_area_cm2, calibration_mm_per_px, final_product_name, image_bytes, mime
        )

        scan.raw_text = result["raw_text"]
        scan.overall_score = result["score"]
        scan.status = (
            models.ScanStatus.compliant
            if result["overall_compliant"]
            else models.ScanStatus.non_compliant
        )
        ai_summary = result["ai_summary"]
        quality_warnings = []
        try:
            if image_preprocessing.blur_score(image_bytes) < BLUR_WARNING_THRESHOLD:
                quality_warnings.append(
                    "This photo appears blurry or out of focus, which can cause "
                    "OCR to misread or miss declarations - consider retaking it "
                    "with steadier hands and better lighting."
                )
            if image_preprocessing.short_side_px(image_bytes) < MIN_RECOMMENDED_SHORT_SIDE:
                quality_warnings.append(
                    "This photo's resolution is low, which limits how much fine "
                    "print (net quantity, MRP, dates) OCR can reliably read - "
                    "consider retaking it closer up so the label fills the frame."
                )
        except Exception:
            pass
        if quality_warnings:
            warning_text = " ".join(quality_warnings)
            ai_summary = f"{warning_text}\n\n{ai_summary}" if ai_summary else warning_text
        scan.notes = ai_summary

        for d in result["declarations"]:
            db.add(
                models.Declaration(
                    scan_id=scan.id,
                    key=d["key"],
                    label=d["label"],
                    rule_ref=d["rule_ref"],
                    found=d["found"],
                    matched_text=d["matched_text"],
                    bbox=json.dumps(d["bbox"]) if d["bbox"] else None,
                    font_height_mm=d["font_height_mm"],
                    min_required_mm=d["min_required_mm"],
                    compliant=d["compliant"],
                    severity=d["severity"],
                    issue=d["issue"],
                )
            )
        db.commit()
    except Exception as exc:
        scan.status = models.ScanStatus.error
        scan.notes = f"Processing failed: {exc}"
        db.commit()

    db.refresh(scan)
    return scan


@router.get("/", response_model=schemas.ScanListResponse)
def list_scans(
    db: Session = Depends(get_db),
    _user: schemas.UserOut = Depends(get_current_user),
    status: Optional[models.ScanStatus] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
):
    q = db.query(models.Scan)
    if status:
        q = q.filter(models.Scan.status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(models.Scan.product_name.ilike(like))
    total = q.count()
    items = q.order_by(models.Scan.created_at.desc()).offset(offset).limit(limit).all()
    return schemas.ScanListResponse(total=total, items=items)


@router.get("/{scan_id}", response_model=schemas.ScanDetailOut)
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _user: schemas.UserOut = Depends(get_current_user),
):
    scan = (
        db.query(models.Scan)
        .options(joinedload(models.Scan.declarations))
        .filter(models.Scan.id == scan_id)
        .first()
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/image")
def get_scan_image(
    scan_id: int,
    db: Session = Depends(get_db),
    _user: schemas.UserOut = Depends(get_current_user),
):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    try:
        data = storage_service.get_file(scan.image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type=_guess_mime(scan.image_path))


@router.get("/{scan_id}/front-image")
def get_scan_front_image(
    scan_id: int,
    db: Session = Depends(get_db),
    _user: schemas.UserOut = Depends(get_current_user),
):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan or not scan.front_image_path:
        raise HTTPException(status_code=404, detail="Front-of-pack image not found")
    try:
        data = storage_service.get_file(scan.front_image_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Front-of-pack image not found")
    return Response(content=data, media_type=_guess_mime(scan.front_image_path))


@router.get("/{scan_id}/report")
def get_scan_report(
    scan_id: int,
    db: Session = Depends(get_db),
    _user: schemas.UserOut = Depends(get_current_user),
):
    scan = (
        db.query(models.Scan)
        .options(joinedload(models.Scan.declarations))
        .filter(models.Scan.id == scan_id)
        .first()
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    try:
        image_bytes = storage_service.get_file(scan.image_path)
    except FileNotFoundError:
        image_bytes = None

    pdf_bytes = report_generator.build_report(scan, image_bytes)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="compliance_report_{scan.id}.pdf"'},
    )


@router.delete("/{scan_id}", status_code=204)
def delete_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _admin: schemas.UserOut = Depends(require_role(models.UserRole.admin, models.UserRole.inspector)),
):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    storage_service.delete_file(scan.image_path)
    if scan.front_image_path:
        storage_service.delete_file(scan.front_image_path)
    db.delete(scan)
    db.commit()
    return None
