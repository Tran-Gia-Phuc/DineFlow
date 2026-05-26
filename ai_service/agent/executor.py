import logging
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from llm.fallback import get_llm_with_fallback
from agent.memory import build_history_for_agent
from tools.employees import get_employees, get_employees_on_leave_today
from tools.bookings import get_bookings, create_booking, cancel_booking
from tools.tables import get_tables, update_table_status
from tools.leave import get_leave_requests, create_leave_request, approve_leave_request
from tools.revenue import get_revenue

logger = logging.getLogger(__name__)


# ── Danh sách tools ───────────────────────────────────────────
# Agent sẽ chọn trong số này khi cần
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
    """
    Chuyển history từ format Odoo sang LangChain message objects.

    Odoo gửi:
    [{"role": "user", "content": "..."},
     {"role": "assistant", "content": "..."}]

    LangChain cần:
    [HumanMessage(content="..."),
     AIMessage(content="...")]
    """
    messages = []
    for msg in raw_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            messages.append(AIMessage(content=content))
        # Bỏ qua role khác (system, tool...)
    return messages


def _build_prompt() -> ChatPromptTemplate:
    """
    Tạo prompt template cho agent.

    Gồm 3 phần:
    1. system  — vai trò và hướng dẫn cho agent
    2. history — lịch sử hội thoại (MessagesPlaceholder)
    3. human   — câu hỏi hiện tại của user
    4. agent_scratchpad — nơi agent ghi chú khi suy nghĩ (bắt buộc)
    """
    # Đọc system prompt từ file — sẽ viết ở bước 14
    try:
        with open("agent/prompts/system.txt", encoding="utf-8") as f:
            system_text = f.read().strip()
    except FileNotFoundError:
        # Fallback nếu chưa có file
        system_text = (
            "Bạn là trợ lý AI của nhà hàng DineFlow. "
            "Hỗ trợ quản lý nhân viên, đặt bàn, doanh thu. "
            "Trả lời bằng tiếng Việt, ngắn gọn và chính xác."
        )

    return ChatPromptTemplate.from_messages([
        ("system", system_text),
        MessagesPlaceholder(variable_name="chat_history"),  # history sẽ fill vào đây
        ("human", "{input}"),                               # câu hỏi user
        MessagesPlaceholder(variable_name="agent_scratchpad"),  # bắt buộc cho tool calling
    ])


async def run_agent(
    message: str,
    session_id: str,
    raw_history: list[dict],
) -> str:
    """
    Chạy agent với câu hỏi và lịch sử hội thoại.

    Args:
        message:     câu hỏi hiện tại của user
        session_id:  ID phiên chat (để log)
        raw_history: lịch sử từ Odoo, format list[dict]

    Returns:
        Câu trả lời dạng string
    """
    logger.info(f"[{session_id}] run_agent: {message[:60]}")

    # 1. Trim history để không vượt token limit
    trimmed_history = build_history_for_agent(raw_history)

    # 2. Convert sang LangChain format
    chat_history = _convert_history(trimmed_history)

    # 3. Lấy LLM (Groq + fallback Gemini)
    llm = get_llm_with_fallback()

    # 4. Build prompt
    prompt = _build_prompt()

    # 5. Tạo agent
    # create_tool_calling_agent = agent biết cách gọi tool
    # (khác với ReAct agent dùng text parsing)
    agent = create_tool_calling_agent(
        llm=llm,
        tools=ALL_TOOLS,
        prompt=prompt,
    )

    # 6. Tạo executor — wrapper chạy vòng lặp agent
    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,       # log quá trình agent suy nghĩ
        max_iterations=5,   # tối đa 5 lần gọi tool trong 1 request
        handle_parsing_errors=True,  # không crash khi LLM output lạ
    )

    # 7. Chạy agent
    try:
        result = await executor.ainvoke({
            "input": message,
            "chat_history": chat_history,
        })
        response = result.get("output", "Xin lỗi, tôi không thể xử lý yêu cầu này.")

    except Exception as e:
        logger.error(f"[{session_id}] Agent error: {e}", exc_info=True)
        response = "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."

    logger.info(f"[{session_id}] Agent response: {response[:80]}")
    return response