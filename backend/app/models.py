import enum
import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Float,
    Text,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from .database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    inspector = "inspector"
    viewer = "viewer"


class ScanStatus(str, enum.Enum):
    compliant = "compliant"
    non_compliant = "non_compliant"
    processing = "processing"
    error = "error"


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    # Auto-identified from front_image_path (Groq vision, or an OCR-based
    # heuristic fallback) - no longer manually typed by the inspector.
    product_name = Column(String, nullable=True)
    brand_name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    image_path = Column(String, nullable=False)
    front_image_path = Column(String, nullable=True)

    calibration_mm_per_px = Column(Float, nullable=True)
    pdp_area_cm2 = Column(Float, nullable=True)

    status = Column(SAEnum(ScanStatus), default=ScanStatus.processing, nullable=False)
    overall_score = Column(Float, default=0.0)
    raw_text = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)

    # References a Supabase Auth user id (UUID) - auth now lives in Supabase,
    # so this is a plain string, not a local foreign key.
    created_by_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    declarations = relationship("Declaration", back_populates="scan", cascade="all, delete-orphan")


class Declaration(Base):
    __tablename__ = "declarations"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)

    key = Column(String, nullable=False)
    label = Column(String, nullable=False)
    rule_ref = Column(String, nullable=False)

    found = Column(Boolean, default=False)
    matched_text = Column(Text, nullable=True)
    bbox = Column(String, nullable=True)  # JSON-encoded polygon

    font_height_mm = Column(Float, nullable=True)
    min_required_mm = Column(Float, nullable=True)

    compliant = Column(Boolean, default=False)
    severity = Column(String, default="major")  # major | minor
    issue = Column(String, nullable=True)

    scan = relationship("Scan", back_populates="declarations")
