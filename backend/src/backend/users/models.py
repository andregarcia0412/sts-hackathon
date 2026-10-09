from typing import Annotated

from beanie import Document, Indexed
from pydantic import EmailStr


class User(Document):
    email: Annotated[EmailStr, Indexed(unique=True)]
    name: str = ""
    password_hash: str

    class Settings:
        name = "users"
