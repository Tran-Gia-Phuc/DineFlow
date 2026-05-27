from pydantic import BaseModel, field_validator, model_validator
from typing import Any
import logging

logger = logging.getLogger(__name__)

MAX_HISTORY_ITEMS = 50   # tối đa 50 message trong history


class MessageSchema(BaseModel):
    """Schema validate 1 message trong history."""
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "assistant", "system"}
        if v not in allowed:
            raise ValueError(f"role phải là một trong: {allowed}")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content không được rỗng")
        return v.strip()


class ChatRequestSchema(BaseModel):
    """Schema validate toàn bộ request /chat."""
    message: str
    session_id: str = "default"
    history: list[Any] = []

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message không được rỗng")
        return v.strip()

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not v.strip():
            return "default"
        return v.strip()

    @model_validator(mode="after")
    def validate_history_length(self) -> "ChatRequestSchema":
        """Giới hạn history không quá MAX_HISTORY_ITEMS."""
        if len(self.history) > MAX_HISTORY_ITEMS:
            # Giữ lại message mới nhất
            self.history = self.history[-MAX_HISTORY_ITEMS:]
            logger.warning(
                f"History quá dài, đã trim còn {MAX_HISTORY_ITEMS} messages"
            )
        return self

    def validated_history(self) -> list[dict]:
        """
        Lọc history — chỉ giữ message hợp lệ.
        Message sai format sẽ bị bỏ qua thay vì crash.
        """
        result = []
        for item in self.history:
            if not isinstance(item, dict):
                continue
            try:
                msg = MessageSchema(**item)
                result.append({"role": msg.role, "content": msg.content})
            except Exception:
                # Bỏ qua message không hợp lệ
                pass
        return result