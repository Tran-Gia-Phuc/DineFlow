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

# ── Queue key ─────────────────────────────────────────────────
# Redis List dùng làm queue
# LPUSH để thêm job vào đầu queue
# BRPOP để lấy job từ cuối queue (FIFO)
QUEUE_KEY = "dineflow:job_queue"


async def enqueue_job(job_id: str) -> None:
    """
    Đẩy job_id vào Redis queue để worker xử lý.

    LPUSH = Left Push — thêm vào đầu list
    Worker dùng BRPOP (Right Pop) → FIFO queue
    """
    redis = await get_redis()
    await redis.lpush(QUEUE_KEY, job_id)
    logger.info(f"Enqueued job: {job_id}")


async def _process_one_job(job_id: str) -> None:
    """
    Xử lý 1 job từ queue.
    Import executor ở đây để tránh circular import.
    """
    # Import ở đây thay vì đầu file — tránh circular import
    # worker → executor → tools → config (ok)
    # executor → worker (circular nếu import ở đầu file)
    from agent.executor import run_agent
    from storage.chat_history import load_history, save_message
    from agent.memory import count_tokens

    logger.info(f"Processing job: {job_id}")

    # Load job từ Redis
    job = await get_job(job_id)
    if not job:
        logger.warning(f"Job {job_id} không còn trong Redis (đã hết TTL?)")
        return

    # Đánh dấu đang xử lý
    await update_job_status(job_id, JobStatus.PROCESSING)

    try:
        session_id = job["session_id"]
        message    = job["message"]

        # Load history từ DB
        history = await load_history(session_id)

        # Chạy agent
        response_text = await run_agent(
            message=message,
            session_id=session_id,
            raw_history=history,
        )

        # Lưu vào DB
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

        # Cập nhật job COMPLETED
        await update_job_status(
            job_id,
            JobStatus.COMPLETED,
            result=response_text,
        )
        logger.info(f"Job {job_id} completed")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        await update_job_status(
            job_id,
            JobStatus.FAILED,
            error=str(e),
        )


async def run_worker(
    concurrency: int = 3,
    poll_timeout: int = 5,
) -> None:
    """
    Vòng lặp worker — chạy mãi mãi, poll Redis queue.

    Args:
        concurrency:  số job chạy đồng thời tối đa
        poll_timeout: giây chờ nếu queue rỗng (BRPOP timeout)

    Luồng:
    1. BRPOP chờ job_id từ queue (block tối đa poll_timeout giây)
    2. Nếu có job → tạo asyncio task xử lý
    3. Giới hạn concurrency bằng asyncio.Semaphore
    4. Lặp lại
    """
    logger.info(f"Worker started — concurrency={concurrency}")

    redis = await get_redis()

    # Semaphore giới hạn số job chạy đồng thời
    # Semaphore(3) → tối đa 3 job chạy song song
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_with_semaphore(job_id: str) -> None:
        """Wrapper chạy job trong semaphore."""
        async with semaphore:
            await _process_one_job(job_id)

    while True:
        try:
            # BRPOP: block đến khi có item hoặc timeout
            # Trả về tuple ("key", "value") hoặc None nếu timeout
            result = await redis.brpop(QUEUE_KEY, timeout=poll_timeout)

            if result is None:
                # Queue rỗng — tiếp tục chờ
                continue

            _, job_id = result   # bỏ qua key, lấy job_id
            logger.debug(f"Dequeued job: {job_id}")

            # Tạo task chạy song song — không await ở đây
            # để worker tiếp tục poll job tiếp theo
            asyncio.create_task(_run_with_semaphore(job_id))

        except asyncio.CancelledError:
            # Worker bị cancel (server shutdown) → dừng gracefully
            logger.info("Worker cancelled — shutting down")
            break

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            # Không crash worker — chờ 1 giây rồi tiếp tục
            await asyncio.sleep(1)