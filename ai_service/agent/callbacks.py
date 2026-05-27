import time
import logging
from typing import Any, Union
from uuid import UUID
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentFinish, AgentAction

logger = logging.getLogger(__name__)


class StreamingCallbackHandler(BaseCallbackHandler):
    """
    Callback handler để:
    1. Emit SSE event mỗi bước agent chạy
    2. Đếm token từng bước

    Cách dùng:
        handler = StreamingCallbackHandler(session_id="u1", sse_queue=queue)
        executor.invoke(..., config={"callbacks": [handler]})
    """

    def __init__(self, session_id: str, sse_queue=None):
        super().__init__()
        self.session_id   = session_id
        self.sse_queue    = sse_queue   # asyncio.Queue — sẽ dùng ở Bước 3
        self.start_time   = time.time()

        # Token tracking
        self.tokens = {
            "system_prompt": 0,
            "history":       0,
            "input":         0,
            "tool_output":   0,
            "output":        0,
        }

        # Internal state
        self._tool_name = ""

    # ── Helpers ───────────────────────────────────────────────

    def _elapsed(self) -> float:
        """Thời gian đã chạy tính từ lúc khởi tạo."""
        return round(time.time() - self.start_time, 2)

    def _emit(self, event_type: str, message: str, data: dict = None):
        """
        Đẩy event vào SSE queue.
        Nếu chưa có queue (test mode) → chỉ log.
        """
        event = {
            "type":       event_type,
            "message":    message,
            "elapsed":    self._elapsed(),
            "session_id": self.session_id,
        }
        if data:
            event.update(data)

        logger.debug(f"[SSE:{self.session_id}] {event_type}: {message}")

        if self.sse_queue:
            # put_nowait vì callback có thể không phải async context
            try:
                self.sse_queue.put_nowait(event)
            except Exception as e:
                logger.warning(f"SSE queue full hoặc lỗi: {e}")

    # ── LLM callbacks ─────────────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs,
    ) -> None:
        """Gọi khi LLM bắt đầu xử lý."""
        self._emit("status", "🤖 LLM đang xử lý...")

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """
        Gọi khi LLM xong — đây là nơi lấy token count chính xác.
        Groq trả token usage trong response.llm_output.
        """
        if response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            # Groq trả: prompt_tokens, completion_tokens, total_tokens
            prompt_tokens     = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            # Cộng dồn — LLM có thể được gọi nhiều lần (mỗi tool call 1 lần)
            self.tokens["output"] += completion_tokens

            # prompt_tokens bao gồm system + history + input + tool results
            # Lần gọi đầu: chủ yếu là system + history + input
            # Lần gọi sau: cộng thêm tool output
            # Tạm thời lưu tổng vào input, Bước 2 sẽ tách chi tiết hơn
            self.tokens["input"] = max(
                self.tokens["input"],
                prompt_tokens - self.tokens["tool_output"]
            )

            logger.debug(
                f"LLM tokens — prompt: {prompt_tokens}, "
                f"completion: {completion_tokens}"
            )

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        self._emit("error", f"❌ LLM lỗi: {str(error)[:100]}")

    # ── Tool callbacks ────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs,
    ) -> None:
        """Gọi khi agent quyết định dùng tool."""
        tool_name = serialized.get("name", "unknown")
        self._tool_name = tool_name

        # Map tên tool → message thân thiện
        TOOL_MESSAGES = {
            "get_employees":              "👥 Đang lấy danh sách nhân viên...",
            "get_employees_on_leave_today": "🏖 Đang kiểm tra nhân viên nghỉ hôm nay...",
            "get_bookings":               "📅 Đang lấy danh sách đặt bàn...",
            "create_booking":             "✍️ Đang tạo đặt bàn...",
            "cancel_booking":             "🚫 Đang hủy đặt bàn...",
            "get_tables":                 "🪑 Đang kiểm tra trạng thái bàn...",
            "update_table_status":        "🔄 Đang cập nhật trạng thái bàn...",
            "get_leave_requests":         "📋 Đang lấy đơn nghỉ phép...",
            "create_leave_request":       "📝 Đang tạo đơn nghỉ phép...",
            "approve_leave_request":      "✅ Đang xử lý đơn nghỉ phép...",
            "get_revenue":                "💰 Đang lấy dữ liệu doanh thu...",
        }
        message = TOOL_MESSAGES.get(tool_name, f"⚙️ Đang gọi {tool_name}...")
        self._emit("tool_start", message, {"tool": tool_name})

    def on_tool_end(self, output: str, **kwargs) -> None:
        """Gọi khi tool trả kết quả — đếm token của tool output."""
        from agent.memory import count_tokens
        tool_tokens = count_tokens(str(output))
        self.tokens["tool_output"] += tool_tokens

        self._emit(
            "tool_end",
            f"✅ {self._tool_name} xong",
            {"tool": self._tool_name, "tokens": tool_tokens},
        )

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        self._emit("error", f"❌ Tool lỗi: {str(error)[:100]}")

    # ── Agent callbacks ───────────────────────────────────────

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        """Gọi khi agent quyết định action tiếp theo."""
        pass  # on_tool_start đã handle rồi

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """Gọi khi agent hoàn thành — emit done event với token summary."""
        total = sum(self.tokens.values())
        self._emit(
            "done",
            "✅ Hoàn thành",
            {
                "tokens": {
                    **self.tokens,
                    "total": total,
                },
                "elapsed": self._elapsed(),
            },
        )

    # ── Chain callbacks ───────────────────────────────────────

    def on_chain_start(self, serialized, inputs, **kwargs) -> None:
        self._emit("status", "🔍 Đang phân tích câu hỏi...")

    def on_chain_error(self, error: Exception, **kwargs) -> None:
        self._emit("error", f"❌ Lỗi: {str(error)[:100]}")

    # ── Public API ────────────────────────────────────────────

    def set_system_tokens(self, count: int) -> None:
        """Gọi từ executor để set system prompt tokens trước khi chạy."""
        self.tokens["system_prompt"] = count

    def set_history_tokens(self, count: int) -> None:
        """Gọi từ executor để set history tokens trước khi chạy."""
        self.tokens["history"] = count

    def get_token_summary(self) -> dict:
        """Trả token summary để embed vào response cuối."""
        total = sum(self.tokens.values())
        return {
            "system_prompt": self.tokens["system_prompt"],
            "history":       self.tokens["history"],
            "input":         self.tokens["input"],
            "tool_output":   self.tokens["tool_output"],
            "output":        self.tokens["output"],
            "total":         total,
            "elapsed":       self._elapsed(),
        }