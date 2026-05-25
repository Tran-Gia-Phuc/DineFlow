from fastapi import Depends
from fastapi.security import APIKeyHeader
from fastapi.exceptions import HTTPException
import logging

from config import settings

logger = logging.getLogger(__name__)

# ── APIKeyHeader ──────────────────────────────────────────────
# FastAPI tự đọc header "X-API-Key" từ request
# auto_error=False → không tự throw lỗi, để mình xử lý bên dưới
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)) -> str:
    """
    Dependency — dùng với Depends(verify_api_key) ở bất kỳ route nào.

    Luồng:
    - Thiếu header  → 401 MISSING_API_KEY
    - Sai key       → 401 UNAUTHORIZED  (log 4 ký tự đầu để debug)
    - Đúng key      → return key string, route tiếp tục chạy
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error_code": "MISSING_API_KEY",
                "message": "Thiếu header X-API-Key",
            },
        )

    if api_key != settings.api_key:
        logger.warning(f"Invalid API key attempt: {api_key[:4]}****")
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error_code": "UNAUTHORIZED",
                "message": "API key không hợp lệ",
            },
        )

    return api_key