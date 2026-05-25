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