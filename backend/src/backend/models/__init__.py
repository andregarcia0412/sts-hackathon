from beanie import Document

# Register every Beanie Document here so init_beanie picks it up.
DOCUMENT_MODELS: list[type[Document]] = []
