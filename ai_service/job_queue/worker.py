import asyncio
import json
import logging
from datetime import datetime

from redis.asyncio import Redis

from config import settings
from storage.job_tracker import (
    get_redis,
    get_job,
    update_job_status,
    JobStatus,
)

logger = logging.getLogger(__name__)

QUEUE_KEY = "dineflow:job_queue"


async def enqueue_job(job_id: str) -> None:
    redis = await get_redis()
    await redis.lpush(QUEUE_KEY, job_id)
    logger.info(f"Enqueued job: {job_id}")


async def _process_one_job(job_id: str) -> None:
    from agent.executor import run_agent
    from storage.chat_history import load_history, save_message
    from agent.memory import count_tokens
    from streaming.sse_manager import sse_manager  # ← thêm

    logger.info(f"Processing job: {job_id}")

    job = await get_job(job_id)
    if not job:
        logger.warning(f"Job {job_id} không còn trong Redis (đã hết TTL?)")
        return

    await update_job_status(job_id, JobStatus.PROCESSING)

    try:
        session_id = job["session_id"]
        message    = job["message"]

        history = await load_history(session_id)

        # Lấy SSE queue đã tạo sẵn từ POST /chat/async
        sse_queue = sse_manager.get_queue(session_id)

        # run_agent giờ trả tuple (response, token_report)
        response_text, token_report = await run_agent(
            message=message,
            session_id=session_id,
            raw_history=history,
            sse_queue=sse_queue,  # ← truyền vào đây
        )

        await save_message(
            session_id=session_id,
            role="user",
            content=message,
            token_count=count_tokens(message),
        )
        await save_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
            token_count=count_tokens(response_text),
        )

        await update_job_status(
            job_id,
            JobStatus.COMPLETED,
            result=response_text,
        )
        logger.info(f"Job {job_id} completed")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)

        # Emit error event ra SSE client nếu có queue
        sse_queue = sse_manager.get_queue(session_id)
        if sse_queue:
            sse_manager.emit_sync(session_id, {
                "type": "error",
                "message": f"❌ Lỗi xử lý: {str(e)[:100]}",
            })

        await update_job_status(
            job_id,
            JobStatus.FAILED,
            error=str(e),
        )


async def run_worker(
    concurrency: int = 3,
    poll_timeout: int = 5,
) -> None:
    logger.info(f"Worker started — concurrency={concurrency}")

    redis = await get_redis()
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_with_semaphore(job_id: str) -> None:
        async with semaphore:
            await _process_one_job(job_id)

    while True:
        try:
            result = await redis.brpop(QUEUE_KEY, timeout=poll_timeout)

            if result is None:
                continue

            _, job_id = result
            logger.debug(f"Dequeued job: {job_id}")

            asyncio.create_task(_run_with_semaphore(job_id))

        except asyncio.CancelledError:
            logger.info("Worker cancelled — shutting down")
            break

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            await asyncio.sleep(1)