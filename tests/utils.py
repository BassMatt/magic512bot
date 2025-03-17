import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def track_tasks():
    """Context manager to track and cleanup tasks created during a test."""
    before = set(asyncio.all_tasks())
    try:
        yield
    finally:
        after = set(asyncio.all_tasks())
        new_tasks = after - before
        if new_tasks:
            logger.warning(f"Cleaning up {len(new_tasks)} tasks")
            for task in new_tasks:
                if not task.done() and not task.cancelled():
                    task.cancel()
            try:
                async with asyncio.timeout(1.0):
                    await asyncio.gather(*new_tasks, return_exceptions=True)
            except TimeoutError:
                logger.error("Task cleanup timed out")


@asynccontextmanager
async def debug_tasks():
    """Context manager to debug task creation and cleanup."""
    before = set(asyncio.all_tasks())
    try:
        yield
    finally:
        after = set(asyncio.all_tasks())
        new_tasks = after - before
        if new_tasks:
            logger.warning(f"New tasks created during test: {len(new_tasks)}")
            for task in new_tasks:
                logger.warning(f"Task: {task.get_name()} - {task.get_coro().__name__}")
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=1.0)
                    except (TimeoutError, asyncio.CancelledError):
                        logger.error(f"Failed to cancel task: {task.get_name()}")
