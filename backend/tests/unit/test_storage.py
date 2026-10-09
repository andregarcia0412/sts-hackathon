import hashlib

from backend.storage import read_file, store_file


async def test_store_and_read_roundtrip_with_hash(db):
    stored = await store_file("evidencias/metodo.md", b"# metodo", {"project_id": "p1"})
    assert stored.sha256 == hashlib.sha256(b"# metodo").hexdigest()
    assert stored.size_bytes == 8
    assert await read_file(stored.gridfs_id) == b"# metodo"


async def test_storing_twice_never_overwrites(db):
    first = await store_file("a.md", b"v1", {})
    second = await store_file("a.md", b"v2", {})
    assert first.gridfs_id != second.gridfs_id
    assert await read_file(first.gridfs_id) == b"v1"
