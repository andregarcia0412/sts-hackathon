from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentError(ValueError):
    pass


def extract_text(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as error:
        raise DocumentError(f"PDF inválido: {error}") from error
    text = "\n\n".join(page.strip() for page in pages if page.strip())
    if not text:
        raise DocumentError("PDF sem texto extraível")
    return text
