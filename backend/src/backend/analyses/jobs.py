import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)
Job = Callable[[], Awaitable[object]]


class JobRunner:
    """Background execution with a concurrency limit (API rate limits, Ollama GPU)."""

    def __init__(self, concurrency: int) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)
        self._tasks: set[asyncio.Task] = set()

    async def submit(self, job: Job) -> None:
        task = asyncio.create_task(self._run(job))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, job: Job) -> None:
        async with self._semaphore:
            try:
                await job()
            except Exception:  # the job records its own failure; this only protects the loop
                logger.exception("background job failed")

    async def wait_all(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)


class InlineRunner:
    """Runs the job before returning (tests and the CLI)."""

    async def submit(self, job: Job) -> None:
        await job()

    async def wait_all(self) -> None:
        return None
