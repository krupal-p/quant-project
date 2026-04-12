import asyncio

from prefect import flow, task


@task
async def process_chunk(chunk: range) -> int:
    # Process a chunk of data
    return sum(chunk)


@flow(name="Parallel Processing")
async def parallel_flow() -> int:
    # Create chunks of data
    data: list[range] = [range(i, i + 10) for i in range(10)]

    results: list[int] = await asyncio.gather(*[process_chunk(chunk) for chunk in data])

    return sum(results)


if __name__ == "__main__":
    result: int = asyncio.run(parallel_flow())
