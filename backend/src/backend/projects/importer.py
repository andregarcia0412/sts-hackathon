"""Turns uploads (files, .zip) and package folders into (relative path, bytes) pairs."""

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_TOTAL_BYTES = 200 * 1024 * 1024
MAX_FILES = 500
PROJECT_CODE_RE = re.compile(r"PRJ\d+", re.IGNORECASE)
INVENTORY_HEADER = "id_evidencia;"
SKIPPED_PARTS = {"__MACOSX", ".DS_Store", "Thumbs.db"}


class ImportError_(ValueError):  # noqa: N801  (avoids shadowing the builtin ImportError)
    pass


@dataclass(frozen=True)
class IncomingFile:
    path: str  # relative POSIX path inside the project (e.g. evidencias/metodo.md)
    data: bytes
    top_folder: str | None = None


def _is_skipped(parts: tuple[str, ...]) -> bool:
    return any(part in SKIPPED_PARTS or part.startswith(".") for part in parts)


def files_from_zip(data: bytes) -> list[IncomingFile]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ImportError_("invalid .zip file") from error
    entries = [info for info in archive.infolist() if not info.is_dir()]
    if len(entries) > MAX_FILES:
        raise ImportError_(f"zip has more than {MAX_FILES} files")
    if sum(info.file_size for info in entries) > MAX_TOTAL_BYTES:
        raise ImportError_("zip is too large once extracted")
    kept: list[tuple[PurePosixPath, bytes]] = []
    for info in entries:
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ImportError_(f"unsafe path in zip: {info.filename}")
        if _is_skipped(path.parts):
            continue
        kept.append((path, archive.read(info)))
    tops = {path.parts[0] for path, _ in kept if len(path.parts) > 1}
    single_top = next(iter(tops)) if len(tops) == 1 and all(len(p.parts) > 1 for p, _ in kept) else None
    return [
        IncomingFile(
            path=str(PurePosixPath(*path.parts[1:])) if single_top else str(path),
            data=content,
            top_folder=single_top,
        )
        for path, content in kept
    ]


def files_from_directory(root: Path) -> list[IncomingFile]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not _is_skipped(relative.parts):
            files.append(IncomingFile(path=relative.as_posix(), data=path.read_bytes(), top_folder=root.name))
    if len(files) > MAX_FILES:
        raise ImportError_(f"folder has more than {MAX_FILES} files")
    return files


def _has_inventory(folder: Path) -> bool:
    """A project folder is recognised by content: a CSV whose header is the evidence inventory."""
    for csv_file in folder.glob("*.csv"):
        try:
            head = csv_file.read_text(encoding="utf-8-sig", errors="ignore")[:200]
        except OSError:
            continue
        if head.lstrip().startswith(INVENTORY_HEADER):
            return True
    return False


def find_project_dirs(root: Path) -> list[Path]:
    """Every project folder under `root` (or `root` itself), in sorted order."""
    candidates = [root, *sorted(p for p in root.rglob("*") if p.is_dir() and not _is_skipped(p.relative_to(root).parts))]
    return [folder for folder in candidates if _has_inventory(folder)]


def project_code_from(*names: str | None) -> str | None:
    for name in names:
        if name and (match := PROJECT_CODE_RE.search(name)):
            return match.group(0).upper()
    return None
