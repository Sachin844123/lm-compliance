from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
def stats(
    db: Session = Depends(get_db),
    _user: schemas.UserOut = Depends(get_current_user),
):
    scans = db.query(models.Scan).all()
    total = len(scans)
    compliant = sum(1 for s in scans if s.status == models.ScanStatus.compliant)
    non_compliant = sum(1 for s in scans if s.status == models.ScanStatus.non_compliant)
    processing = sum(1 for s in scans if s.status == models.ScanStatus.processing)

    violation_counter: Counter[tuple[str, str]] = Counter()
    declarations = (
        db.query(models.Declaration).filter(models.Declaration.compliant.is_(False)).all()
    )
    for d in declarations:
        violation_counter[(d.rule_ref, d.label)] += 1

    breakdown = [
        schemas.RuleBreakdown(rule_ref=ref, label=label, violation_count=count)
        for (ref, label), count in sorted(
            violation_counter.items(), key=lambda kv: kv[1], reverse=True
        )
    ]

    recent = (
        db.query(models.Scan).order_by(models.Scan.created_at.desc()).limit(8).all()
    )

    return schemas.DashboardStats(
        total_scans=total,
        compliant_count=compliant,
        non_compliant_count=non_compliant,
        processing_count=processing,
        compliance_rate=round(100 * compliant / total, 1) if total else 0.0,
        violation_breakdown=breakdown,
        recent_scans=recent,
    )
