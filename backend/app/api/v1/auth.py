from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserPublic,
)
from app.services import auth_service
from app.services.auth_service import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    LdapDisabledError,
    UserInactiveError,
)

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


def _access_token_ttl_seconds() -> int:
    return settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        user, access_token, refresh_token = await auth_service.login(
            db, payload.username, payload.password, payload.use_ldap, request
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль"
        ) from exc
    except UserInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Учётная запись заблокирована"
        ) from exc
    except LdapDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP-аутентификация не настроена",
        ) from exc

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_access_token_ttl_seconds(),
        user=UserPublic.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        user, access_token, refresh_token = await auth_service.refresh(
            db, payload.refresh_token, request
        )
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный refresh-токен"
        ) from exc

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_access_token_ttl_seconds(),
        user=UserPublic.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await auth_service.logout(db, payload.refresh_token, user, request)


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
