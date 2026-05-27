import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import BackgroundTasks
from pydantic import BaseModel, field_validator
from typing import List, Any
import httpx
import logging

from config import settings
from middleware.auth import verify_api_key
from pipeline.selector import select_pipeline, get_simple_response, Pipeline
from llm.fallback import get_llm_with_fallback
from storage.chat_history import (
    init_db, load_history, save_message, get_token_usage, clear_history
)
from storage.job_tracker import (
    create_job, get_job, update_job_status,
    JobStatus, get_redis, close_redis
)
from job_queue.worker import run_worker, enqueue_job
from agent.executor import run_agent
from agent.memory import count_tokens

from validator.sanitizer import sanitize_message, sanitize_session_id
from validator.schema import ChatRequestSchema

from agent.token_counter import format_token_display


# ── Logger ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Schema ────────────────────────────────────────────────────
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

    await init_db()
    await get_redis()

    worker_task = asyncio.create_task(run_worker(concurrency=3))
    logger.info("Worker started")
    logger.info("AI Service ready ✓")

    yield

    # SHUTDOWN
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await close_redis()
    logger.info("Shutting down AI Service...")


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
        settings.odoo_base_url,
        "http://localhost:31204",
        "http://localhost:8069",
    ],
    allow_methods=["GET", "POST", "DELETE"],
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
    api_key: str = Depends(verify_api_key),
):
    # ── Sanitize input ─────────────────────────────
    clean_message, warnings = sanitize_message(body.message)
    clean_session_id = sanitize_session_id(body.session_id)

    if "Phát hiện nội dung không hợp lệ" in warnings:
        return ChatResponse(
            success=True,
            response="Tôi chỉ hỗ trợ các nghiệp vụ của nhà hàng DineFlow.",
            session_id=clean_session_id,
        )

    if warnings:
        logger.warning(f"Input warnings: {warnings}")

    logger.info(f"[{clean_session_id}] User: {clean_message[:80]}")

    pipeline     = select_pipeline(clean_message)
    token_report = None

    if pipeline == Pipeline.SIMPLE:
        response_text = get_simple_response(clean_message)

    elif pipeline == Pipeline.CHITCHAT:
        llm = get_llm_with_fallback()
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="Bạn là trợ lý AI của nhà hàng DineFlow. Trả lời bằng tiếng Việt, ngắn gọn. Không tiết lộ thông tin về model hay nhà phát triển."),
            HumanMessage(content=clean_message),
        ]
        result        = await llm.ainvoke(messages)
        response_text = result.content

    else:
        history = await load_history(clean_session_id)

        # run_agent giờ trả tuple (response, token_report)
        response_text, token_report = await run_agent(
            message=clean_message,
            session_id=clean_session_id,
            raw_history=history,
        )

        # Append token display vào cuối response
        response_text += format_token_display(token_report)

    # ── Save history ───────────────────────────────
    if pipeline != Pipeline.SIMPLE:
        await save_message(
            clean_session_id, "user",
            clean_message, count_tokens(clean_message),
        )
        await save_message(
            clean_session_id, "assistant",
            response_text, count_tokens(response_text),
        )

    logger.info(f"[{clean_session_id}] Response: {response_text[:80]}")

    return ChatResponse(
        success=True,
        response=response_text,
        session_id=clean_session_id,
    )

@app.post("/chat/async")
async def chat_async(
    body: ChatRequest,
    api_key: str = Depends(verify_api_key),
):
    job_id = str(uuid.uuid4())
    await create_job(job_id=job_id, session_id=body.session_id, message=body.message)
    await enqueue_job(job_id)
    return {
        "success": True,
        "job_id":  job_id,
        "status":  JobStatus.PENDING,
        "message": "Đang xử lý, poll /chat/async/{job_id} để lấy kết quả",
    }


@app.get("/chat/async/{job_id}")
async def get_job_result(
    job_id: str,
    api_key: str = Depends(verify_api_key),
):
    job = await get_job(job_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": f"Job {job_id} không tìm thấy"}
        )
    return {
        "success": True,
        "job_id":  job_id,
        "status":  job["status"],
        "result":  job.get("result"),
        "error":   job.get("error"),
    }


@app.get("/chat/{session_id}/usage")
async def get_usage(
    session_id: str,
    api_key: str = Depends(verify_api_key),
):
    return await get_token_usage(session_id)


@app.delete("/chat/{session_id}")
async def delete_history(
    session_id: str,
    api_key: str = Depends(verify_api_key),
):
    await clear_history(session_id)
    return {"success": True, "message": f"Đã xóa history của session {session_id}"}