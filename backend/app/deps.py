from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from . import models, schemas
from .services import supabase_auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> schemas.UserOut:
    user = supabase_auth_service.verify_token(token)
    if user is None or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.UserOut(**user)


def require_role(*roles: models.UserRole):
    def checker(user: schemas.UserOut = Depends(get_current_user)) -> schemas.UserOut:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return checker
