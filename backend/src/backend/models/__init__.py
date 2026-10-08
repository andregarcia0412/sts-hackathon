from beanie import Document

from backend.users.models import User

# Register every Beanie Document here so init_beanie picks it up.
DOCUMENT_MODELS: list[type[Document]] = [User]
