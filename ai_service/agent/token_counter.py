import logging
from pathlib import Path
from agent.memory import count_tokens

logger = logging.getLogger(__name__)

# Cache system prompt tokens — chỉ đọc file 1 lần
_system_prompt_tokens: int | None = None


def get_system_prompt_tokens() -> int:
    """
    Đếm token của system prompt từ file system.txt.
    Cache kết quả — file không đổi thường xuyên.
    """
    global _system_prompt_tokens
    if _system_prompt_tokens is not None:
        return _system_prompt_tokens

    try:
        path = Path("agent/prompts/system.txt")
        text = path.read_text(encoding="utf-8")
        _system_prompt_tokens = count_tokens(text)
        logger.info(f"System prompt: {_system_prompt_tokens} tokens")
    except FileNotFoundError:
        logger.warning("Không tìm thấy system.txt — dùng ước tính 400 tokens")
        _system_prompt_tokens = 400

    return _system_prompt_tokens


def get_history_tokens(history: list[dict]) -> int:
    """
    Đếm tổng token của toàn bộ history.

    Args:
        history: list[{"role": ..., "content": ...}]
    """
    if not history:
        return 0
    total = sum(count_tokens(msg.get("content", "")) for msg in history)
    logger.debug(f"History tokens: {total} ({len(history)} messages)")
    return total


def get_input_tokens(message: str) -> int:
    """Đếm token của message user hiện tại."""
    return count_tokens(message)


def build_token_report(
    system_tokens: int,
    history_tokens: int,
    input_tokens: int,
    tool_tokens: int,
    output_tokens: int,
    elapsed: float,
) -> dict:
    """
    Tổng hợp token report đầy đủ.

    Returns dict để:
    1. Embed vào response trả về Odoo
    2. Hiển thị trong chat UI
    """
    total = system_tokens + history_tokens + input_tokens + tool_tokens + output_tokens

    return {
        "system_prompt": system_tokens,
        "history":       history_tokens,
        "input":         input_tokens,
        "tool_output":   tool_tokens,
        "output":        output_tokens,
        "total":         total,
        "elapsed":       elapsed,
    }


def format_token_display(report: dict) -> str:
    """
    Format token report thành string để append vào response.

    Output:
    ─────────────────────────────
    📊 System prompt : 412 tokens
       History       : 89 tokens
       Input         : 23 tokens
       Tool output   : 156 tokens
       Output        : 67 tokens
       ─────────────────
       Tổng          : 747 tokens
    ⏱  Thời gian     : 2.3s
    """
    lines = [
        "\n─────────────────────────────",
        f"📊 System prompt : {report['system_prompt']} tokens",
        f"   History       : {report['history']} tokens",
        f"   Input         : {report['input']} tokens",
        f"   Tool output   : {report['tool_output']} tokens",
        f"   Output        : {report['output']} tokens",
        "   ─────────────────",
        f"   Tổng          : {report['total']} tokens",
        f"⏱  Thời gian     : {report['elapsed']}s",
    ]
    return "\n".join(lines)