import logging
from typing import Any
import tiktoken

from config import settings

logger = logging.getLogger(__name__)

# ── Tokenizer ─────────────────────────────────────────────────
# tiktoken là thư viện đếm token của OpenAI
# cl100k_base là encoding dùng cho GPT-4, cũng dùng được cho Groq/Gemini
# (không chính xác 100% nhưng đủ gần để estimate)
try:
    _ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENCODER = None
    logger.warning("Không load được tiktoken encoder — dùng ước tính ký tự")


def count_tokens(text: str) -> int:
    """
    Đếm số token trong một đoạn text.

    Token ≠ từ. Ví dụ:
    - "hello" = 1 token
    - "unhappy" = 2 token (un + happy)
    - "DineFlow" = 3 token
    - Tiếng Việt thường 1 âm tiết ≈ 1-2 token
    """
    if _ENCODER:
        return len(_ENCODER.encode(text))
    # Fallback nếu tiktoken không load được: ước tính 4 ký tự = 1 token
    return len(text) // 4


def _message_to_text(message: Any) -> str:
    """
    Chuyển message object thành string để đếm token.
    Message có thể là:
    - dict:   {"role": "user", "content": "..."}
    - object: HumanMessage, AIMessage của LangChain
    """
    if isinstance(message, dict):
        return str(message.get("content", ""))
    # LangChain message object có attribute .content
    return str(getattr(message, "content", ""))


def trim_history(
    history: list[Any],
    max_tokens: int | None = None,
) -> list[Any]:
    """
    Cắt bớt history để tổng token không vượt quá giới hạn.

    Chiến lược: giữ message MỚI NHẤT, bỏ message CŨ NHẤT.
    Lý do: message gần đây thường quan trọng hơn message cũ.

    Args:
        history:    list message theo thứ tự thời gian (cũ → mới)
        max_tokens: giới hạn token, mặc định lấy từ config

    Returns:
        list message đã cắt bớt
    """
    if not history:
        return []

    limit = max_tokens or settings.max_history_tokens

    # Đếm tổng token hiện tại
    total = sum(count_tokens(_message_to_text(m)) for m in history)

    if total <= limit:
        # Chưa vượt giới hạn → giữ nguyên
        return history

    # Cắt từ đầu (message cũ nhất) cho đến khi đủ giới hạn
    trimmed = list(history)  # copy để không sửa list gốc
    while trimmed and total > limit:
        removed = trimmed.pop(0)  # bỏ message đầu tiên (cũ nhất)
        total -= count_tokens(_message_to_text(removed))
        logger.debug(f"Trimmed 1 message, còn {total} tokens / {limit}")

    logger.info(
        f"trim_history: {len(history)} → {len(trimmed)} messages "
        f"({total}/{limit} tokens)"
    )
    return trimmed


def build_history_for_agent(raw_history: list[dict]) -> list[dict]:
    """
    Nhận history thô từ Odoo (list dict), trim rồi trả về.

    raw_history format từ Odoo chat.py:
    [
        {"role": "user",      "content": "hôm nay có bàn trống không?"},
        {"role": "assistant", "content": "Còn 5 bàn trống"},
        ...
    ]

    Returns:
        list dict đã trim, sẵn sàng truyền vào agent
    """
    if not raw_history:
        return []

    trimmed = trim_history(raw_history)
    return trimmed