from prefect import flow, task
from prefect.futures import wait


@task
async def process_chunk(chunk: range) -> int:
    # Process a chunk of data
    return sum(chunk)


@flow(name="Concurrent Flow")
def concurrent_flow() -> int:
    # Create chunks of data
    data: list[range] = [range(i, i + 10) for i in range(10)]
    results = []
    for chunk in data:
        results.append(process_chunk.submit(chunk))

    wait(results)
    return sum([result.result() for result in results])


if __name__ == "__main__":
    result = concurrent_flow()
    print(result)
