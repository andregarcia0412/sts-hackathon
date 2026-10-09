import asyncio

from backend.analyses.jobs import JobRunner


async def test_runner_limits_concurrency_and_survives_failures():
    runner = JobRunner(concurrency=2)
    running, peak, done = 0, 0, []

    async def job(n):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        if n == 3:
            raise RuntimeError("boom")
        done.append(n)

    for n in range(6):
        await runner.submit(lambda n=n: job(n))
    await runner.wait_all()
    assert peak == 2
    assert sorted(done) == [0, 1, 2, 4, 5]
