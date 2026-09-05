import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .models import UserRole, ScanStatus


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.inspector


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Declarations ----------

class DeclarationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str
    rule_ref: str
    found: bool
    matched_text: Optional[str] = None
    bbox: Optional[str] = None
    font_height_mm: Optional[float] = None
    min_required_mm: Optional[float] = None
    compliant: bool
    severity: str
    issue: Optional[str] = None


# ---------- Scans ----------

class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: Optional[str] = None
    brand_name: Optional[str] = None
    category: Optional[str] = None
    image_path: str
    front_image_path: Optional[str] = None
    status: ScanStatus
    overall_score: float
    created_at: datetime.datetime
    created_by_id: Optional[str] = None


class ScanDetailOut(ScanOut):
    declarations: list[DeclarationOut] = []
    notes: Optional[str] = None
    calibration_mm_per_px: Optional[float] = None
    pdp_area_cm2: Optional[float] = None


class ScanListResponse(BaseModel):
    total: int
    items: list[ScanOut]


# ---------- Dashboard ----------

class RuleBreakdown(BaseModel):
    rule_ref: str
    label: str
    violation_count: int


class DashboardStats(BaseModel):
    total_scans: int
    compliant_count: int
    non_compliant_count: int
    processing_count: int
    compliance_rate: float
    violation_breakdown: list[RuleBreakdown]
    recent_scans: list[ScanOut]
