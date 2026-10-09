"""One search session per analysis (spec 10): NOV, CRI and INC plan their searches independently and repeat each
other (~14% near-identical queries in the same front, ~11% repeated URLs). The session reuses the result of a
near-identical query of the same front and reads each URL once. It does not replace the Mongo cache (across
analyses); concurrent criteria wait for the first call instead of repeating it."""

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Any

SIMILAR = 0.6  # Jaccard of the query words


def query_words(query: str) -> set[str]:
    return set(re.findall(r"\w+", query.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def _quiet(future: asyncio.Future) -> None:
    if not future.cancelled():
        future.exception()  # retrieved: a failure shared by several waiters is reported by each of them


class SearchSession:
    def __init__(self) -> None:
        self._queries: dict[str, list[tuple[set[str], str, asyncio.Future]]] = {}
        self._pages: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def search(self, front: str, query: str, run: Callable[[], Awaitable[Any]]) -> tuple[Any, str | None]:
        """(result, query it was reused from — None when this call ran the search)."""
        words = query_words(query)
        async with self._lock:
            match = next(((q, f) for w, q, f in self._queries.get(front, []) if jaccard(words, w) >= SIMILAR), None)
            if match is None:
                future = asyncio.get_running_loop().create_future()
                future.add_done_callback(_quiet)
                self._queries.setdefault(front, []).append((words, query, future))
        if match is not None:
            return await asyncio.shield(match[1]), match[0]
        return await self._resolve(future, run), None

    async def page(self, url: str, run: Callable[[], Awaitable[Any]]) -> Any:
        async with self._lock:
            future = self._pages.get(url)
            owner = future is None
            if owner:
                future = asyncio.get_running_loop().create_future()
                future.add_done_callback(_quiet)
                self._pages[url] = future
        if not owner:
            return await asyncio.shield(future)
        return await self._resolve(future, run)

    @staticmethod
    async def _resolve(future: asyncio.Future, run: Callable[[], Awaitable[Any]]) -> Any:
        try:
            result = await run()
        except BaseException as error:
            future.set_exception(error)
            raise
        future.set_result(result)
        return result
