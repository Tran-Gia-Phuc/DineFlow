import json
import logging
from datetime import datetime
from enum import Enum
from redis.asyncio import Redis

from config import settings

logger = logging.getLogger(__name__)


# ── Job Status ────────────────────────────────────────────────
class JobStatus(str, Enum):
    """
    Vòng đời của 1 job:
    PENDING → PROCESSING → COMPLETED
                        → FAILED
    """
    PENDING    = "PENDING"     # vừa tạo, chưa xử lý
    PROCESSING = "PROCESSING"  # đang chạy agent
    COMPLETED  = "COMPLETED"   # xong, có kết quả
    FAILED     = "FAILED"      # lỗi


# ── Redis client ──────────────────────────────────────────────
# Singleton — khởi tạo 1 lần khi module được import
_redis: Redis | None = None


async def get_redis() -> Redis:
    """
    Lấy Redis client, tạo mới nếu chưa có.
    Dùng connection pool mặc định của redis-py.
    """
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,  # tự decode bytes → str
        )
        logger.info(f"Redis connected: {settings.redis_url}")
    return _redis


async def close_redis() -> None:
    """Đóng kết nối Redis — gọi trong lifespan shutdown."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis disconnected")


# ── Key helper ────────────────────────────────────────────────
def _job_key(job_id: str) -> str:
    """
    Redis key format: "job:{job_id}"
    Prefix "job:" giúp phân biệt với các key khác trong Redis.
    """
    return f"job:{job_id}"


# ── CRUD ──────────────────────────────────────────────────────

async def create_job(job_id: str, session_id: str, message: str) -> dict:
    """
    Tạo job mới với trạng thái PENDING.

    Args:
        job_id:     ID duy nhất của job (UUID)
        session_id: ID phiên chat
        message:    câu hỏi của user

    Returns:
        dict job vừa tạo
    """
    redis = await get_redis()

    job = {
        "job_id":     job_id,
        "session_id": session_id,
        "message":    message,
        "status":     JobStatus.PENDING,
        "result":     None,
        "error":      None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    await redis.setex(
        _job_key(job_id),
        settings.job_ttl_seconds,  # tự xóa sau 1 giờ
        json.dumps(job, ensure_ascii=False),
    )

    logger.info(f"Job created: {job_id} session={session_id}")
    return job


async def update_job_status(
    job_id: str,
    status: JobStatus,
    result: str | None = None,
    error: str | None = None,
) -> None:
    """
    Cập nhật trạng thái job.

    Args:
        job_id:  ID job cần cập nhật
        status:  trạng thái mới
        result:  kết quả nếu COMPLETED
        error:   thông báo lỗi nếu FAILED
    """
    redis = await get_redis()
    key = _job_key(job_id)

    # Load job hiện tại
    raw = await redis.get(key)
    if not raw:
        logger.warning(f"Job not found: {job_id}")
        return

    job = json.loads(raw)
    job["status"]     = status
    job["updated_at"] = datetime.utcnow().isoformat()

    if result is not None:
        job["result"] = result
    if error is not None:
        job["error"] = error

    # Lưu lại với TTL cũ (reset TTL)
    await redis.setex(
        key,
        settings.job_ttl_seconds,
        json.dumps(job, ensure_ascii=False),
    )

    logger.info(f"Job {job_id} → {status}")


async def get_job(job_id: str) -> dict | None:
    """
    Lấy thông tin job theo ID.

    Returns:
        dict job hoặc None nếu không tìm thấy / đã hết TTL
    """
    redis = await get_redis()
    raw = await redis.get(_job_key(job_id))

    if not raw:
        return None

    return json.loads(raw)