import sys
import time

from sqlalchemy.exc import OperationalError

if sys.platform == "win32":
    # EasyOCR's first-run model download prints a progress bar using Unicode
    # block characters; Windows' default console codepage (cp1252) can't
    # encode them, which crashes the OCR call. Force UTF-8 on the standard
    # streams so this - and any other library that prints Unicode - works
    # regardless of the terminal's active codepage.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth, scans, dashboard
from .services import storage_service, supabase_auth_service

def _create_all_with_retry(attempts: int = 3, delay_seconds: float = 2.0) -> None:
    """
    Supabase's connection pooler occasionally drops a brand-new connection
    outright (a transient network blip, not a stale-connection problem
    pool_pre_ping solves) - this is the very first query the app makes, so
    there's no pooled connection to retry with. A couple of short retries
    turns an occasional dropped connection here into a slightly slower
    startup instead of a crashed process.
    """
    for attempt in range(1, attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if attempt == attempts:
                raise
            print(f"Database connection attempt {attempt} failed, retrying in {delay_seconds}s...")
            time.sleep(delay_seconds)


_create_all_with_retry()

app = FastAPI(
    title="Legal Metrology Compliance Checker",
    description="Automated screening of packaged commodity labels against the "
    "Legal Metrology (Packaged Commodities) Rules, 2011.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(scans.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def ensure_storage_bucket():
    storage_service.ensure_bucket()


@app.on_event("startup")
def seed_default_admin():
    if not settings.auth_enabled:
        print(
            "WARNING: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY "
            "are not fully configured - authentication will not work."
        )
        return
    if supabase_auth_service.find_user_by_email(settings.default_admin_email):
        return
    supabase_auth_service.create_user(
        settings.default_admin_email,
        settings.default_admin_password,
        settings.default_admin_name,
        "admin",
    )
    print(f"Seeded default admin in Supabase: {settings.default_admin_email}")


@app.get("/")
def root():
    return {
        "service": "Legal Metrology Compliance Checker API",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
