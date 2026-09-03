from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from .. import models, schemas
from ..deps import get_current_user, require_role
from ..services import supabase_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/users", response_model=schemas.UserOut)
def create_user(
    payload: schemas.UserCreate,
    _admin: schemas.UserOut = Depends(require_role(models.UserRole.admin)),
):
    if supabase_auth_service.find_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        user = supabase_auth_service.create_user(
            payload.email, payload.password, payload.full_name, payload.role.value
        )
    except supabase_auth_service.SupabaseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return schemas.UserOut(**user)


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(_admin: schemas.UserOut = Depends(require_role(models.UserRole.admin))):
    try:
        users = supabase_auth_service.list_users()
    except supabase_auth_service.SupabaseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return [schemas.UserOut(**u) for u in users]


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        result = supabase_auth_service.login(form_data.username, form_data.password)
    except supabase_auth_service.SupabaseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return schemas.Token(access_token=result["access_token"], user=schemas.UserOut(**result["user"]))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: schemas.UserOut = Depends(get_current_user)):
    return current_user
