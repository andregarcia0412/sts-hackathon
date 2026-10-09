"""Immutable storage of the original package files (GridFS). Files are never overwritten (principle 10)."""

import hashlib
from collections.abc import Mapping
from typing import Any

from bson import ObjectId
from gridfs import AsyncGridFSBucket
from pydantic import BaseModel

from backend.users.models import User

BUCKET = "originals"


class StoredFile(BaseModel):
    gridfs_id: str
    sha256: str
    size_bytes: int


def _bucket() -> AsyncGridFSBucket:
    # Same database Beanie was initialised with (the app's or the test one).
    return AsyncGridFSBucket(User.get_pymongo_collection().database, bucket_name=BUCKET)


async def store_file(name: str, data: bytes, metadata: Mapping[str, Any]) -> StoredFile:
    digest = hashlib.sha256(data).hexdigest()
    file_id = await _bucket().upload_from_stream(name, data, metadata={**metadata, "sha256": digest})
    return StoredFile(gridfs_id=str(file_id), sha256=digest, size_bytes=len(data))


async def read_file(gridfs_id: str) -> bytes:
    stream = await _bucket().open_download_stream(ObjectId(gridfs_id))
    return await stream.read()
