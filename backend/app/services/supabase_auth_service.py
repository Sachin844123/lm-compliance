"""
Auth backed by Supabase Auth (GoTrue) instead of local password hashing +
self-issued JWTs. The backend proxies to Supabase's Auth REST API so the
frontend's request/response shapes never change - it still calls our
/auth/login, /auth/me, /auth/users exactly as before.

- Login verifies the user's password against Supabase and returns Supabase's
  own access token; our backend later validates that same token by asking
  Supabase who it belongs to (GET /auth/v1/user), rather than verifying a
  JWT signature locally.
- Role is stored in `app_metadata` (settable only via the service role key,
  never by the user themselves) so a user can't self-elevate by editing
  their own profile.
"""
import httpx

from ..config import settings


class SupabaseAuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


def _anon_headers() -> dict:
    return {"apikey": settings.supabase_anon_key, "Content-Type": "application/json"}


def _admin_headers() -> dict:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def _user_to_dict(user: dict) -> dict:
    user_metadata = user.get("user_metadata") or {}
    app_metadata = user.get("app_metadata") or {}
    return {
        "id": user["id"],
        "email": user.get("email") or "",
        "full_name": user_metadata.get("full_name") or user.get("email", ""),
        "role": app_metadata.get("role") or "viewer",
        "is_active": not bool(user.get("banned_until")),
    }


def login(email: str, password: str) -> dict:
    """Returns {"access_token": str, "user": {...}} or raises SupabaseAuthError."""
    resp = httpx.post(
        f"{settings.supabase_url}/auth/v1/token?grant_type=password",
        headers=_anon_headers(),
        json={"email": email, "password": password},
        timeout=15,
    )
    if resp.status_code != 200:
        raise SupabaseAuthError("Incorrect email or password", status_code=401)
    data = resp.json()
    return {"access_token": data["access_token"], "user": _user_to_dict(data["user"])}


def verify_token(access_token: str) -> dict | None:
    """Returns the user dict for a valid Supabase session token, else None."""
    resp = httpx.get(
        f"{settings.supabase_url}/auth/v1/user",
        headers={**_anon_headers(), "Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if resp.status_code != 200:
        return None
    return _user_to_dict(resp.json())


def list_users() -> list[dict]:
    resp = httpx.get(
        f"{settings.supabase_url}/auth/v1/admin/users",
        headers=_admin_headers(),
        timeout=15,
    )
    if resp.status_code != 200:
        raise SupabaseAuthError(f"Failed to list users: {resp.text}", status_code=502)
    return [_user_to_dict(u) for u in resp.json().get("users", [])]


def create_user(email: str, password: str, full_name: str, role: str) -> dict:
    resp = httpx.post(
        f"{settings.supabase_url}/auth/v1/admin/users",
        headers=_admin_headers(),
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name},
            "app_metadata": {"role": role},
        },
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        raise SupabaseAuthError(f"Failed to create user: {resp.text}", status_code=400)
    return _user_to_dict(resp.json())


def find_user_by_email(email: str) -> dict | None:
    for user in list_users():
        if user["email"].lower() == email.lower():
            return user
    return None
