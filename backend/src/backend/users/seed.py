import logging

from backend.config import settings
from backend.users.service import EmailAlreadyRegistered, create_user, get_user_by_email

logger = logging.getLogger(__name__)

SEED_USER_COUNT = 5


async def seed_users() -> None:
    """Create the default users if they don't exist yet (idempotent)."""
    created = 0
    for n in range(1, SEED_USER_COUNT + 1):
        email = settings.seed_email_pattern.format(n=n)
        if await get_user_by_email(email) is not None:
            continue
        try:
            await create_user(email, settings.seed_password, name=f"Analista {n}")
            created += 1
        except EmailAlreadyRegistered:
            pass
    logger.info("Seed users: %d created, %d already existed", created, SEED_USER_COUNT - created)
