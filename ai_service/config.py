from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # ── Đọc từ file .env ──────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",          # đọc file .env ở cùng cấp với lúc chạy
        env_file_encoding="utf-8",
        case_sensitive=False,     # GROQ_API_KEY = groq_api_key (không phân biệt hoa thường)
        extra="ignore",           # bỏ qua các biến trong .env không khai báo ở đây
    )

    # ── App ───────────────────────────────────────────────────
    app_name: str = "DineFlow AI Service"
    # debug: bool = false
    debug: bool = True

    # ── Auth ──────────────────────────────────────────────────
    # Phải có trong .env, không có default → khởi động sẽ báo lỗi ngay
    api_key: str

    # ── Odoo ──────────────────────────────────────────────────
    odoo_base_url: str = "http://odoo:8069"   # tên service trong docker-compose
    odoo_api_key: str = "dineflow-secret-2024"
    odoo_internal_key: str = "dineflow-internal-secret"   # ← thêm dòng này

    # ── Groq ──────────────────────────────────────────────────
    # Nhiều key để rotate khi hit rate limit
    # Trong .env viết: GROQ_API_KEYS=key1,key2,key3
    groq_api_keys: str = ""

    groq_model: str = "llama-3.1-8b-instant"
    groq_max_tokens: int = 1000
    groq_temperature: float = 0.1   # thấp → output ổn định, ít sáng tạo

    # ── Gemini (fallback) ─────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    job_ttl_seconds: int = 3600    # job tự xóa sau 1 giờ

    # ── PostgreSQL ────────────────────────────────────────────
    postgres_url: str = "postgresql+asyncpg://odoo:Phuc0312@db:5432/intern"

    # ── Token management ──────────────────────────────────────
    max_history_tokens: int = 1500   # port từ chat_ai_service.py
    max_tool_output_items: int = 15  # port từ _trim_tool_output()
    max_tool_output_chars: int = 800

    # ── @property: computed field, không đọc từ .env ──────────
    @property
    def groq_api_keys_list(self) -> List[str]:
        """Tách chuỗi 'key1,key2,key3' thành list, bỏ key rỗng."""
        if not self.groq_api_keys:
            return []
        return [k.strip() for k in self.groq_api_keys.split(",") if k.strip()]

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_groq(self) -> bool:
        return len(self.groq_api_keys_list) > 0


# ── Singleton pattern ──────────────────────────────────────────
# @lru_cache đảm bảo Settings() chỉ khởi tạo 1 lần duy nhất
# Mọi nơi gọi get_settings() đều nhận cùng 1 object
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Shortcut để import nhanh
settings = get_settings()