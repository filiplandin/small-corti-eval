import asyncio


async def map_limited(fn, items, limit):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be an integer >= 1")
    values = list(items)
    semaphore = asyncio.Semaphore(limit)

    async def run(value):
        async with semaphore:
            return await fn(value)

    tasks = [asyncio.create_task(run(value)) for value in values]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
