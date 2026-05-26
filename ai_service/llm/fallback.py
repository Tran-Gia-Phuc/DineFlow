import logging
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from config import settings
from llm.groq_client import get_groq_llm

logger = logging.getLogger(__name__)


def get_llm_with_fallback() -> BaseChatModel:
    """
    Trả về LLM đã được cấu hình fallback chain.

    Thứ tự ưu tiên:
    1. Groq (primary) — nhanh, rẻ
    2. Gemini (fallback) — dùng khi Groq fail

    Nếu không có Groq key → dùng Gemini trực tiếp.
    Nếu không có cả hai → raise RuntimeError.

    Returns:
        LLM instance với fallback đã cấu hình

    Raises:
        RuntimeError nếu không có LLM nào khả dụng
    """

    # ── Trường hợp 1: có cả Groq lẫn Gemini ──────────────────
    if settings.has_groq and settings.has_gemini:
        logger.info("LLM: Groq (primary) + Gemini (fallback)")

        primary = get_groq_llm()

        fallback = ChatGoogleGenerativeAI(
            google_api_key=settings.gemini_api_key,
            model=settings.gemini_model,          # "gemini-1.5-flash"
            max_output_tokens=settings.groq_max_tokens,
            temperature=settings.groq_temperature,
        )

        # with_fallbacks() là method của LangChain
        # Khi primary raise exception → tự động thử fallback
        return primary.with_fallbacks(
            fallbacks=[fallback],
            exceptions_to_handle=(Exception,),  # bắt mọi lỗi
        )

    # ── Trường hợp 2: chỉ có Groq ────────────────────────────
    elif settings.has_groq:
        logger.info("LLM: Groq only (không có Gemini fallback)")
        return get_groq_llm()

    # ── Trường hợp 3: chỉ có Gemini ──────────────────────────
    elif settings.has_gemini:
        logger.warning("LLM: Gemini only (không có Groq key)")
        return ChatGoogleGenerativeAI(
            google_api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            max_output_tokens=settings.groq_max_tokens,
            temperature=settings.groq_temperature,
        )

    # ── Trường hợp 4: không có gì ────────────────────────────
    else:
        raise RuntimeError(
            "Không có LLM nào khả dụng. "
            "Thêm GROQ_API_KEYS hoặc GEMINI_API_KEY vào .env"
        )