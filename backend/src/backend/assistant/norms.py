"""Normative base for the chatbot: PDFs cut by article/§ with metadata, searched with BM25 (no embeddings)."""

import asyncio
import hashlib
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from collections.abc import Callable

from beanie import Document
from pydantic import BaseModel
from pypdf import PdfReader

MAX_CHUNK_CHARS = 2000
MARKER_RE = re.compile(
    r"^\s*(?P<art>Art\.?\s*\d+[ºo°]?(?:-[A-Z])?)"
    r"|^\s*(?P<par>§\s*\d+[ºo°]?|Parágrafo único)"
    r"|^\s*(?P<num>\d{1,2}\.\d{1,3})\s+(?=[A-ZÀ-Ú])",
    re.MULTILINE,
)
STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas", "um", "uma", "que",
    "para", "por", "com", "se", "ao", "aos", "ou", "the", "of", "and", "to", "in", "is", "for", "on", "it", "be",
    "what", "qual", "quais", "como", "sobre", "diz", "e", "sao", "ser", "foi",
}


class NormChunk(BaseModel):
    id: str
    norm: str
    label: str
    page: int
    text: str

    @property
    def caption(self) -> str:
        if self.label.startswith("p. "):
            return f"{self.norm} — {self.label}"
        return f"{self.norm} — {self.label} (p. {self.page})"

    @property
    def search_text(self) -> str:
        return f"{self.norm} {self.label}\n{self.text}"


class NormChunkDocument(Document):
    chunk: NormChunk

    class Settings:
        name = "norm_chunks"


def norm_title(file_name: str) -> str:
    stem = Path(file_name).stem
    return re.sub(r"\s+-\s+[^-]+$", "", stem).strip()


def _label(match: re.Match) -> str:
    if match.group("art"):
        number = re.search(r"\d+[ºo°]?(?:-[A-Z])?", match.group("art")).group(0)
        return f"Art. {number}"
    if match.group("par"):
        return " ".join(match.group("par").split())
    return f"§{match.group('num')}"


def _make(norm: str, label: str, page: int, text: str) -> list[NormChunk]:
    text = text.strip()
    pieces = [text[i : i + MAX_CHUNK_CHARS] for i in range(0, len(text), MAX_CHUNK_CHARS)] or []
    return [
        NormChunk(id=hashlib.sha1(f"{norm}|{label}|{page}|{n}|{piece[:60]}".encode()).hexdigest()[:12],
                  norm=norm, label=label, page=page, text=piece)
        for n, piece in enumerate(pieces)
    ]


def chunk_pages(norm: str, pages: list[str]) -> list[NormChunk]:
    chunks: list[NormChunk] = []
    for number, page in enumerate(pages, start=1):
        matches = list(MARKER_RE.finditer(page))
        preamble = page[: matches[0].start()] if matches else page
        if preamble.strip():
            chunks += _make(norm, f"p. {number}", number, preamble)
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(page)
            chunks += _make(norm, _label(match), number, page[match.start() : end])
    return chunks


def tokenize(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(ch for ch in plain if not unicodedata.combining(ch))
    return [t for t in re.findall(r"\w{2,}", plain) if t not in STOPWORDS]


class BM25Index[T]:
    def __init__(self, chunks: list[T], k1: float = 1.5, b: float = 0.75,
                 key: Callable[[T], str] = lambda item: item.text) -> None:
        self.chunks = chunks
        self.k1, self.b = k1, b
        self._docs = [Counter(tokenize(key(c))) for c in chunks]
        self._lengths = [sum(d.values()) for d in self._docs]
        self._avg = (sum(self._lengths) / len(self._lengths)) if self._lengths else 0
        df = Counter(term for doc in self._docs for term in doc)
        n = len(chunks)
        self._idf = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def search(self, query: str, k: int = 5) -> list[T]:
        terms = tokenize(query)
        scored = []
        for index, doc in enumerate(self._docs):
            score = 0.0
            for term in terms:
                if term in doc:
                    tf = doc[term]
                    norm = 1 - self.b + self.b * self._lengths[index] / (self._avg or 1)
                    score += self._idf[term] * tf * (self.k1 + 1) / (tf + self.k1 * norm)
            if score > 0:
                scored.append((score, index))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [self.chunks[i] for _, i in scored[:k]]


def read_pdf_pages(path: Path) -> list[str]:
    return [page.extract_text() or "" for page in PdfReader(path).pages]


async def ingest_norms(folder: Path) -> list[NormChunk]:
    """Parses every PDF of the folder and replaces the stored chunks (idempotent)."""
    chunks: list[NormChunk] = []
    for pdf in sorted(folder.glob("*.pdf")):
        pages = await asyncio.to_thread(read_pdf_pages, pdf)
        chunks += chunk_pages(norm_title(pdf.name), pages)
    await NormChunkDocument.find_all().delete()
    if chunks:
        await NormChunkDocument.insert_many([NormChunkDocument(chunk=c) for c in chunks])
    return chunks


async def load_norm_index() -> BM25Index:
    return norm_index([doc.chunk for doc in await NormChunkDocument.find_all().to_list()])


def norm_index(chunks: list[NormChunk]) -> BM25Index:
    return BM25Index(chunks, key=lambda chunk: chunk.search_text)
