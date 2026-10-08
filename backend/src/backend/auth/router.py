from fastapi import APIRouter, HTTPException, status

from backend.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from backend.auth.security import (
    InvalidToken,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.users.service import (
    EmailAlreadyRegistered,
    create_user,
    get_user_by_email,
    get_user_by_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified when the email is unknown so login takes the same time either way.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def _token_pair(user_id: str) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest) -> TokenPair:
    try:
        user = await create_user(body.email, body.password)
    except EmailAlreadyRegistered:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    return _token_pair(str(user.id))


@router.post("/login")
async def login(body: LoginRequest) -> TokenPair:
    user = await get_user_by_email(body.email)
    if user is None:
        verify_password(body.password, _DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return _token_pair(str(user.id))


@router.post("/refresh")
async def refresh(body: RefreshRequest) -> TokenPair:
    try:
        user_id = decode_token(body.refresh_token, "refresh")
    except InvalidToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return _token_pair(str(user.id))
