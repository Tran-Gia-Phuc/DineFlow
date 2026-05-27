from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import List, Any
import httpx
import logging

from config import settings
from middleware.auth import verify_api_key

from pipeline.selector import select_pipeline, get_simple_response, Pipeline
from llm.fallback import get_llm_with_fallback

# ── Logger ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Schema ────────────────────────────────────────────────────
# Pydantic tự validate + trả 422 nếu thiếu field bắt buộc
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    history: List[Any] = []

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message không được để trống")
        return v.strip()


class ChatResponse(BaseModel):
    success: bool
    response: str
    session_id: str


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("Starting DineFlow AI Service...")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.odoo_base_url}/web/health")
            if resp.status_code == 200:
                logger.info(f"Odoo connected: {settings.odoo_base_url}")
            else:
                logger.warning(f"Odoo trả về status {resp.status_code}")
    except Exception as e:
        logger.warning(f"Không kết nối được Odoo lúc startup: {e}")

    if settings.has_groq:
        logger.info(f"Groq: {len(settings.groq_api_keys_list)} key(s) loaded")
    else:
        logger.warning("Không có GROQ_API_KEYS — LLM sẽ không hoạt động")

    if settings.has_gemini:
        logger.info("Gemini fallback: enabled")

    logger.info("AI Service ready ✓")

    yield

    # SHUTDOWN
    logger.info("Shutting down AI Service...")
    # TODO bước 15-16: đóng DB pool, Redis pool ở đây


# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI Service cho DineFlow — thay thế n8n",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.odoo_base_url,    # http://odoo:8069 (trong docker network)
        "http://localhost:31204",   # Odoo từ ngoài docker
        "http://localhost:8069",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Global error handler ──────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "Lỗi hệ thống, vui lòng thử lại",
        },
    )


# ── Routes ────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Kiểm tra service còn sống — Docker, Jenkins, load balancer gọi cái này."""
    return {
        "success": True,
        "service": settings.app_name,
        "status": "ok",
        "groq_keys": len(settings.groq_api_keys_list),
        "gemini": settings.has_gemini,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    api_key: str = Depends(verify_api_key),   # ← auth tách riêng, tái dùng được
):
    """
    Endpoint chính — nhận message từ Odoo, trả về response AI.

    Request:  { "message": "...", "session_id": "...", "history": [...] }
    Response: { "success": true, "response": "...", "session_id": "..." }
    """
    logger.info(f"[{body.session_id}] User: {body.message[:80]}")

    # TODO bước 13: thay dòng dưới bằng agent_executor.run(body)
    response_text = f"[AI Service nhận được]: {body.message}"

    logger.info(f"[{body.session_id}] Response: {response_text[:80]}")

    return ChatResponse(
        success=True,
        response=response_text,
        session_id=body.session_id,
    )
    
    import uuid
from storage.job_tracker import (
    create_job, get_job, update_job_status,
    JobStatus, get_redis, close_redis
)

# ── Lifespan — thêm Redis shutdown ───────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    ...
    await init_db()
    await get_redis()   # khởi tạo Redis connection sớm
    logger.info("AI Service ready ✓")
    yield
    await close_redis()  # đóng Redis khi shutdown
    logger.info("Shutting down AI Service...")


# ── Endpoint mới: gửi job async ──────────────────────────────
@app.post("/chat/async")
async def chat_async(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
    """
    Gửi request xử lý ngầm, trả job_id ngay lập tức.
    Odoo poll /chat/async/{job_id} để lấy kết quả.
    """
    job_id = str(uuid.uuid4())

    # Tạo job PENDING
    await create_job(
        job_id=job_id,
        session_id=body.session_id,
        message=body.message,
    )

    # Chạy agent ngầm — không block response
    background_tasks.add_task(
        _process_job,
        job_id=job_id,
        body=body,
    )

    return {
        "success":    True,
        "job_id":     job_id,
        "status":     JobStatus.PENDING,
        "message":    "Đang xử lý, poll /chat/async/{job_id} để lấy kết quả",
    }


async def _process_job(job_id: str, body: ChatRequest) -> None:
    """Chạy agent và cập nhật job status."""
    try:
        await update_job_status(job_id, JobStatus.PROCESSING)

        history = await load_history(body.session_id)
        response_text = await run_agent(
            message=body.message,
            session_id=body.session_id,
            raw_history=history,
        )

        await save_message(body.session_id, "user", body.message,
                           count_tokens(body.message))
        await save_message(body.session_id, "assistant", response_text,
                           count_tokens(response_text))

        await update_job_status(job_id, JobStatus.COMPLETED, result=response_text)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        await update_job_status(job_id, JobStatus.FAILED, error=str(e))


# ── Endpoint poll kết quả ─────────────────────────────────────
@app.get("/chat/async/{job_id}")
async def get_job_result(
    job_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Odoo gọi endpoint này để kiểm tra job đã xong chưa."""
    job = await get_job(job_id)

    if not job:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": f"Job {job_id} không tìm thấy"}
        )

    return {
        "success":  True,
        "job_id":   job_id,
        "status":   job["status"],
        "result":   job.get("result"),
        "error":    job.get("error"),
    }
    
    import asyncio
from job_queue.worker import run_worker, enqueue_job

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    ...
    await init_db()
    await get_redis()

    # Khởi động worker trong background
    worker_task = asyncio.create_task(run_worker(concurrency=3))
    logger.info("Worker started")

    yield

    # SHUTDOWN — cancel worker gracefully
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await close_redis()
    logger.info("Shutting down AI Service...")


# Sửa /chat/async — dùng enqueue thay vì BackgroundTasks
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    api_key: str = Depends(verify_api_key),
):
    pipeline = select_pipeline(body.message)

    # SIMPLE: trả lời ngay, không tốn token
    if pipeline == Pipeline.SIMPLE:
        response_text = get_simple_response(body.message)

    # CHITCHAT: LLM trả lời tự do, không gọi tool
    elif pipeline == Pipeline.CHITCHAT:
        llm = get_llm_with_fallback()
        result = await llm.ainvoke(body.message)
        response_text = result.content

    # TOOL: agent đầy đủ
    else:
        history = await load_history(body.session_id)
        response_text = await run_agent(
            message=body.message,
            session_id=body.session_id,
            raw_history=history,
        )

    # Lưu DB (trừ SIMPLE vì quá ngắn, không cần lưu)
    if pipeline != Pipeline.SIMPLE:
        await save_message(body.session_id, "user",
                           body.message, count_tokens(body.message))
        await save_message(body.session_id, "assistant",
                           response_text, count_tokens(response_text))

    return ChatResponse(
        success=True,
        response=response_text,
        session_id=body.session_id,
    )