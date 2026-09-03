import asyncio


async def map_limited(fn, items, limit):
    return await asyncio.gather(*(fn(item) for item in items))
