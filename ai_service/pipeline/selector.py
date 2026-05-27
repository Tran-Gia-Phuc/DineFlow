import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)


# ── Pipeline types ────────────────────────────────────────────
class Pipeline(str, Enum):
    SIMPLE   = "SIMPLE"    # trả lời cứng, không cần LLM
    CHITCHAT = "CHITCHAT"  # LLM trả lời tự do, không cần tool
    TOOL     = "TOOL"      # agent + tool gọi Odoo


# ── Keyword maps ──────────────────────────────────────────────
# Từ khóa → pipeline tương ứng
# Kiểm tra theo thứ tự: SIMPLE trước, TOOL sau

_SIMPLE_PATTERNS = [
    r"\bxin chào\b",
    r"\bhello\b",
    r"\bhi\b",
    r"\bchào\b",
    r"\bcảm ơn\b",
    r"\bthanks?\b",
    r"\bbye\b",
    r"\btạm biệt\b",
]

_CHITCHAT_PATTERNS = [
    r"\bbạn là ai\b",
    r"\bwho are you\b",
    r"\bbạn tên gì\b",
    r"\bbạn có thể làm gì\b",
    r"\bgiúp được gì\b",
    r"\bhướng dẫn\b",
]

_TOOL_PATTERNS = [
    # Nhân viên
    r"\bnhân viên\b",
    r"\bemployee\b",
    r"\bca làm\b",
    r"\bca sáng|ca chiều|ca tối\b",
    r"\bnghỉ phép\b",
    r"\bleave\b",
    # Bàn
    r"\bbàn\b",
    r"\btable\b",
    r"\btrống\b",
    r"\bavailable\b",
    # Đặt bàn
    r"\bđặt bàn\b",
    r"\bbooking\b",
    r"\bbook\b",
    r"\bhủy\b",
    r"\bcancel\b",
    # Doanh thu
    r"\bdoanh thu\b",
    r"\brevenue\b",
    r"\bdoanh số\b",
    r"\bthu nhập\b",
    r"\btổng tiền\b",
]


def _match_any(text: str, patterns: list[str]) -> bool:
    """Kiểm tra text có khớp với bất kỳ pattern nào không."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def select_pipeline(message: str) -> Pipeline:
    """
    Phân loại câu hỏi → chọn pipeline phù hợp.

    Thứ tự ưu tiên:
    1. SIMPLE   — nhanh nhất, không tốn token
    2. TOOL     — cần data thực tế từ Odoo
    3. CHITCHAT — mặc định cho câu hỏi còn lại

    Args:
        message: câu hỏi của user

    Returns:
        Pipeline enum
    """
    text = message.strip().lower()

    # 1. Kiểm tra SIMPLE trước
    if _match_any(text, _SIMPLE_PATTERNS):
        logger.info(f"Pipeline: SIMPLE | '{message[:50]}'")
        return Pipeline.SIMPLE

    # 2. Kiểm tra TOOL
    if _match_any(text, _TOOL_PATTERNS):
        logger.info(f"Pipeline: TOOL | '{message[:50]}'")
        return Pipeline.TOOL

    # 3. Kiểm tra CHITCHAT
    if _match_any(text, _CHITCHAT_PATTERNS):
        logger.info(f"Pipeline: CHITCHAT | '{message[:50]}'")
        return Pipeline.CHITCHAT

    # 4. Default: TOOL — an toàn hơn CHITCHAT
    # Thà gọi tool không cần thiết còn hơn bỏ sót câu hỏi về data
    logger.info(f"Pipeline: TOOL (default) | '{message[:50]}'")
    return Pipeline.TOOL


# ── Simple responses ──────────────────────────────────────────
_SIMPLE_RESPONSES = {
    r"\bxin chào\b|\bchào\b|\bhello\b|\bhi\b": "Xin chào! Tôi có thể giúp gì cho bạn?",
    r"\bcảm ơn\b|\bthanks?\b":                 "Không có gì! Bạn cần hỗ trợ thêm không?",
    r"\bbye\b|\btạm biệt\b":                   "Tạm biệt! Chúc bạn làm việc hiệu quả.",
}


def get_simple_response(message: str) -> str:
    """
    Trả về response cứng cho câu SIMPLE.
    Không cần gọi LLM → tiết kiệm token.
    """
    text = message.strip().lower()
    for pattern, response in _SIMPLE_RESPONSES.items():
        if re.search(pattern, text, re.IGNORECASE):
            return response
    return "Xin chào! Tôi có thể giúp gì cho bạn?"