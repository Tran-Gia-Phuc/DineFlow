import logging
import threading
from itertools import cycle
from langchain_groq import ChatGroq

from config import settings

logger = logging.getLogger(__name__)


# ── Key Rotator ───────────────────────────────────────────────
class GroqKeyRotator:
    """
    Rotate qua nhiều Groq API key theo vòng tròn.

    threading.Lock() đảm bảo thread-safe:
    FastAPI chạy nhiều request đồng thời, nếu 2 request
    cùng gọi next() một lúc có thể bị race condition.
    Lock đảm bảo chỉ 1 thread được gọi next() tại một thời điểm.
    """

    def __init__(self, api_keys: list[str]):
        if not api_keys:
            raise ValueError("Cần ít nhất 1 Groq API key")
        self._keys = api_keys
        self._cycle = cycle(api_keys)   # cycle([A, B, C]) → A B C A B C A...
        self._lock = threading.Lock()
        self._current_index = 0
        logger.info(f"GroqKeyRotator khởi tạo với {len(api_keys)} key(s)")

    def next_key(self) -> str:
        """Lấy key tiếp theo trong vòng xoay."""
        with self._lock:
            key = next(self._cycle)
            # Log 4 ký tự đầu để debug mà không lộ key
            logger.debug(f"Dùng Groq key: {key[:4]}****")
            return key

    @property
    def count(self) -> int:
        return len(self._keys)


# ── Singleton rotator ─────────────────────────────────────────
# Khởi tạo 1 lần khi module được import
# None nếu không có key — các nơi dùng phải kiểm tra
_rotator: GroqKeyRotator | None = None

if settings.has_groq:
    _rotator = GroqKeyRotator(settings.groq_api_keys_list)
else:
    logger.warning("Không có GROQ_API_KEYS — GroqKeyRotator không khởi tạo")


# ── Factory function ──────────────────────────────────────────
def get_groq_llm() -> ChatGroq:
    """
    Tạo ChatGroq instance với key tiếp theo trong vòng xoay.

    Mỗi lần gọi get_groq_llm() → lấy key mới từ rotator.
    Dùng trong agent executor (bước 13) và fallback (bước 12).

    Returns:
        ChatGroq instance sẵn sàng dùng

    Raises:
        RuntimeError nếu không có Groq key nào
    """
    if _rotator is None:
        raise RuntimeError(
            "Không có Groq API key. "
            "Thêm GROQ_API_KEYS vào file .env"
        )

    return ChatGroq(
        api_key=_rotator.next_key(),
        model=settings.groq_model,           # "llama-3.1-8b-instant"
        max_tokens=settings.groq_max_tokens,  # 1000
        temperature=settings.groq_temperature, # 0.1
    )