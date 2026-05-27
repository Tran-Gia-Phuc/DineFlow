import re
import logging

logger = logging.getLogger(__name__)

# ── Giới hạn ──────────────────────────────────────────────────
MAX_MESSAGE_LENGTH = 500    # ký tự tối đa 1 message
MAX_SESSION_ID_LENGTH = 100

# ── Prompt injection patterns ─────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all)\s+instructions?",
    r"forget\s+(everything|all|previous)",
    r"you\s+are\s+now\s+",
    r"act\s+as\s+(if\s+you\s+are|a\s+)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS),
    re.IGNORECASE,
)


def sanitize_message(message: str) -> tuple[str, list[str]]:
    """
    Làm sạch message từ user.

    Returns:
        (clean_message, warnings) 
        warnings: list cảnh báo nếu có, rỗng nếu không vấn đề gì
    """
    warnings = []
    text = message

    # 1. Strip whitespace thừa
    text = text.strip()

    # 2. Kiểm tra độ dài
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[:MAX_MESSAGE_LENGTH]
        warnings.append(f"Message đã bị cắt bớt còn {MAX_MESSAGE_LENGTH} ký tự")
        logger.warning(f"Message quá dài ({len(message)} ký tự), đã cắt")

    # 3. Kiểm tra prompt injection
    if _INJECTION_RE.search(text):
        logger.warning(f"Phát hiện prompt injection: {text[:50]!r}")
        warnings.append("Phát hiện nội dung không hợp lệ")
        # Không block hẳn — chỉ log và cảnh báo
        # Agent với system prompt tốt sẽ tự handle

    # 4. Xóa ký tự null và control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text, warnings


def sanitize_session_id(session_id: str) -> str:
    """
    Làm sạch session_id — chỉ cho phép alphanumeric và dấu gạch.
    """
    # Chỉ giữ chữ cái, số, gạch dưới, gạch ngang
    clean = re.sub(r"[^\w\-]", "_", session_id)
    return clean[:MAX_SESSION_ID_LENGTH]