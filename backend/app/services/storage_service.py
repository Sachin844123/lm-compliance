"""
File storage abstraction for uploaded label images.

If SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are configured, files are
stored in Supabase Storage (needed for real deployment - most hosting
platforms have an ephemeral filesystem, so local disk storage doesn't
survive restarts/redeploys or scale past a single instance). Otherwise
files are stored on local disk under backend/uploads/, so the app still
runs with zero external setup for local development.

Either way, callers work with a plain string "key" (e.g. a UUID + original
extension) - where that key actually lives is an implementation detail
hidden behind save_file/get_file/delete_file.
"""
import logging
from pathlib import Path

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def is_remote() -> bool:
    return settings.storage_enabled


def _storage_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


def ensure_bucket() -> None:
    """Create the storage bucket if it doesn't already exist. Safe to call
    on every startup - a 409/"already exists" response is treated as success."""
    if not is_remote():
        return
    try:
        resp = httpx.post(
            f"{settings.supabase_url}/storage/v1/bucket",
            headers=_storage_headers(),
            json={"id": settings.supabase_storage_bucket, "name": settings.supabase_storage_bucket, "public": False},
            timeout=15,
        )
        if resp.status_code not in (200, 201) and "already exists" not in resp.text.lower():
            logger.warning("Could not ensure Supabase bucket exists: %s %s", resp.status_code, resp.text)
    except Exception:
        logger.exception("Failed to reach Supabase Storage while ensuring bucket exists")


def save_file(data: bytes, key: str, content_type: str) -> str:
    """Persist `data` under `key` and return the key to store in the DB."""
    if is_remote():
        resp = httpx.post(
            f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{key}",
            headers={**_storage_headers(), "Content-Type": content_type},
            content=data,
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Supabase Storage upload failed: {resp.status_code} {resp.text}")
    else:
        (settings.upload_dir / key).write_bytes(data)
    return key


def get_file(key: str) -> bytes:
    if is_remote():
        resp = httpx.get(
            f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{key}",
            headers=_storage_headers(),
            timeout=30,
        )
        if resp.status_code != 200:
            raise FileNotFoundError(f"Supabase Storage object not found: {key}")
        return resp.content
    else:
        path = settings.upload_dir / key
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {key}")
        return path.read_bytes()


def delete_file(key: str) -> None:
    try:
        if is_remote():
            httpx.delete(
                f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{key}",
                headers=_storage_headers(),
                timeout=15,
            )
        else:
            path = settings.upload_dir / key
            if path.exists():
                path.unlink()
    except Exception:
        logger.exception("Failed to delete stored file %s", key)
