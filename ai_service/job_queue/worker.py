import asyncio
import logging

import httpx

from config import settings
from storage.job_tracker import (
    get_redis,
    get_job,
    update_job_status,
    JobStatus,
)

logger = logging.getLogger(__name__)

QUEUE_KEY = "dineflow:job_queue"
ODOO_SAVE_URL = f"{settings.odoo_base_url}/dineflow/chat/save_result"

async def _save_result_to_odoo(session_id: str, message: str, response: str, job_id: str = "") -> None:
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "session_id": session_id,
            "job_id":     job_id,
            "message":    message,
            "response":   response,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                ODOO_SAVE_URL,
                json=payload,
                headers={
                    "Content-Type":   "application/json",
                    "X-Internal-Key": settings.odoo_internal_key,
                },
            )
            resp.raise_for_status()
            result = resp.json().get("result", {})
            if result.get("error"):
                logger.error(f"Odoo save_result lỗi: {result['error']}")
            else:
                logger.info(f"Đã lưu result về Odoo — session={session_id}")
    except Exception as e:
        logger.error(f"_save_result_to_odoo thất bại: {e}", exc_info=True)


async def enqueue_job(job_id: str) -> None:
    redis = await get_redis()
    await redis.lpush(QUEUE_KEY, job_id)
    logger.info(f"Enqueued job: {job_id}")


async def _process_one_job(job_id: str) -> None:
    from agent.executor import run_agent
    from storage.chat_history import load_history, save_message
    from agent.memory import count_tokens
    from streaming.sse_manager import sse_manager

    logger.info(f"Processing job: {job_id}")

    job = await get_job(job_id)
    if not job:
        logger.warning(f"Job {job_id} không còn trong Redis (đã hết TTL?)")
        return

    await update_job_status(job_id, JobStatus.PROCESSING)

    session_id = job["session_id"]
    message = job["message"]

    try:
        history = await load_history(session_id)
        sse_queue = sse_manager.get_queue(session_id)

        response_text, token_report = await run_agent(
            message=message,
            session_id=session_id,
            raw_history=history,
            sse_queue=sse_queue,
        )

        # Lưu vào PostgreSQL riêng của ai_service
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

        # Lưu về Odoo DB để /dineflow/chat/result đọc được
        await _save_result_to_odoo(
            session_id=session_id,
            message=message,
            response=response_text,
            job_id=job_id, 
        )

        await update_job_status(job_id, JobStatus.COMPLETED, result=response_text)
        logger.info(f"Job {job_id} completed")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        sse_queue = sse_manager.get_queue(session_id)
        if sse_queue:
            sse_manager.emit_sync(
                session_id,
                {
                    "type": "error",
                    "message": f"❌ Lỗi xử lý: {str(e)[:100]}",
                },
            )
        await update_job_status(job_id, JobStatus.FAILED, error=str(e))


async def run_worker(concurrency: int = 3, poll_timeout: int = 5) -> None:
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
