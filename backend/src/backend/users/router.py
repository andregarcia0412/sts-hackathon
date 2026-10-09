from fastapi import APIRouter

from backend.auth.dependencies import CurrentUser
from backend.users.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead(id=str(user.id), email=user.email, name=user.name)
