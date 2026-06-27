from src.execution.async_bridge import AsyncRunner


def test_runner_executes_coroutine_from_sync():
    r = AsyncRunner()
    try:
        async def add(a, b):
            return a + b

        assert r.run(add(2, 3)) == 5
    finally:
        r.close()
