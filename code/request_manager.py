import asyncio
import logging
from typing import Any, Callable
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = logging.getLogger(__name__)

class AsyncRequestManager:
    """
    Manages operational scaling for API calls: limits concurrency using an asyncio.Semaphore
    and handles exponential backoff/retries via tenacity to combat 429 Rate Limits and 500 Network Errors.
    """
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        return await func(*args, **kwargs)

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executes the provided async function enforcing the semaphore boundary and exponential backoff retry logic.
        """
        async with self.semaphore:
            # We strictly assume func is an async coroutine 
            return await self._execute_with_retry(func, *args, **kwargs)
