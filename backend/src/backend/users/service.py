from beanie import PydanticObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from backend.auth.security import hash_password
from backend.users.models import User


class EmailAlreadyRegistered(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_user_by_email(email: str) -> User | None:
    return await User.find_one(User.email == normalize_email(email))


async def get_user_by_id(user_id: str) -> User | None:
    try:
        object_id = PydanticObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    return await User.get(object_id)


async def create_user(email: str, password: str) -> User:
    email = normalize_email(email)
    if await User.find_one(User.email == email) is not None:
        raise EmailAlreadyRegistered(email)
    user = User(email=email, password_hash=hash_password(password))
    try:
        await user.insert()
    except DuplicateKeyError as exc:
        raise EmailAlreadyRegistered(email) from exc
    return user
