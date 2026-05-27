import logging
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from llm.fallback import get_llm_with_fallback
from agent.memory import build_history_for_agent
from agent.callbacks import StreamingCallbackHandler
from agent.token_counter import (
    get_system_prompt_tokens,
    get_history_tokens,
    get_input_tokens,
)
from tools.employees import get_employees, get_employees_on_leave_today
from tools.bookings import get_bookings, create_booking, cancel_booking
from tools.tables import get_tables, update_table_status
from tools.leave import get_leave_requests, create_leave_request, approve_leave_request
from tools.revenue import get_revenue

logger = logging.getLogger(__name__)

ALL_TOOLS = [
    get_employees,
    get_employees_on_leave_today,
    get_bookings,
    create_booking,
    cancel_booking,
    get_tables,
    update_table_status,
    get_leave_requests,
    create_leave_request,
    approve_leave_request,
    get_revenue,
]


def _convert_history(raw_history: list[dict]) -> list:
    messages = []
    for msg in raw_history:
        role    = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            messages.append(AIMessage(content=content))
    return messages


def _build_prompt() -> ChatPromptTemplate:
    try:
        with open("agent/prompts/system.txt", encoding="utf-8") as f:
            system_text = f.read().strip()
    except FileNotFoundError:
        system_text = (
            "Bạn là trợ lý AI của nhà hàng DineFlow. "
            "Hỗ trợ quản lý nhân viên, đặt bàn, doanh thu. "
            "Trả lời bằng tiếng Việt, ngắn gọn và chính xác."
        )

    return ChatPromptTemplate.from_messages([
        ("system", system_text),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])


async def run_agent(
    message: str,
    session_id: str,
    raw_history: list[dict],
    sse_queue=None,
) -> tuple[str, dict]:
    """
    Chạy agent với câu hỏi và lịch sử hội thoại.

    Args:
        message:     câu hỏi hiện tại của user
        session_id:  ID phiên chat (để log)
        raw_history: lịch sử từ Odoo, format list[dict]
        sse_queue:   asyncio.Queue để stream event (None nếu không dùng SSE)

    Returns:
        (response_text, token_report)
    """
    logger.info(f"[{session_id}] run_agent: {message[:60]}")

    # 1. Trim history
    trimmed_history = build_history_for_agent(raw_history)
    chat_history    = _convert_history(trimmed_history)

    # 2. Tính token trước khi chạy
    system_tokens  = get_system_prompt_tokens()
    history_tokens = get_history_tokens(trimmed_history)
    input_tokens   = get_input_tokens(message)

    # 3. Tạo callback handler
    handler = StreamingCallbackHandler(
        session_id=session_id,
        sse_queue=sse_queue,
    )
    handler.set_system_tokens(system_tokens)
    handler.set_history_tokens(history_tokens)

    # 4. LLM + prompt
    llm    = get_llm_with_fallback()
    prompt = _build_prompt()

    # 5. Agent
    agent = create_tool_calling_agent(
        llm=llm,
        tools=ALL_TOOLS,
        prompt=prompt,
    )

    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=False,
        max_iterations=5,
        handle_parsing_errors=True,
    )

    # 6. Chạy với callback
    try:
        result = await executor.ainvoke(
            {
                "input":        message,
                "chat_history": chat_history,
            },
            config={"callbacks": [handler]},
        )
        response = result.get("output", "Xin lỗi, tôi không thể xử lý yêu cầu này.")

    except Exception as e:
        logger.error(f"[{session_id}] Agent error: {e}", exc_info=True)
        response = "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."

    # 7. Lấy token report
    token_report = handler.get_token_summary()
    token_report["input"] = input_tokens   # dùng giá trị chính xác từ token_counter

    logger.info(
        f"[{session_id}] Done — "
        f"{token_report['total']} tokens, "
        f"{token_report['elapsed']}s"
    )

    return response, token_report