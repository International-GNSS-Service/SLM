import asyncio


class AsyncCoroutinePool:

    max_coroutines_: int = 5
    queue_: asyncio.Queue

    def __init__(self, max_coroutines: int = max_coroutines_):
        self.max_coroutines = 2 if max_coroutines < 2 else max_coroutines + 1
        self.queue_ = asyncio.Queue()

    async def run_task(name, queue):
        while True:
            # Get a "work item" out of the queue.
            task = await queue.get()

            # Sleep for the "sleep_for" seconds.
            await task()

            # Notify the queue that the "work item" has been processed.
            queue.task_done()

            print(f'{name} has slept for {sleep_for:.2f} seconds')