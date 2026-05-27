import httpx
import json
import logging
from langchain_core.tools import tool

from config import settings

logger = logging.getLogger(__name__)

# ── HTTP client helper ────────────────────────────────────────
# Header dùng chung cho mọi request đến Odoo
ODOO_HEADERS = {
    "X-API-Key": settings.odoo_api_key,
    "Content-Type": "application/json",
}


def _trim_list(items: list) -> list:
    """
    Giới hạn số lượng item trả về cho agent.
    Agent đọc text — quá nhiều data làm tốn token và nhiễu.
    max_tool_output_items = 15 (config từ bước 1)
    """
    return items[: settings.max_tool_output_items]


def _to_str(data) -> str:
    """
    Chuyển dict/list thành string, cắt nếu quá dài.
    max_tool_output_chars = 800 (config từ bước 1)
    """
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > settings.max_tool_output_chars:
        text = text[: settings.max_tool_output_chars] + "\n... (đã cắt bớt)"
    return text


# ── Tools ─────────────────────────────────────────────────────

@tool
async def get_employees(query: str = "")G: -> str:
    """
    Lấy danh sách nhân viên trong nhà hàng.
    Dùng khi người dùng hỏi về nhân viên, ca làm việc, số lượng nhân sự,
    hoặc muốn biết ai đang làm ca nào.

    Tham số query có thể chứa: tên nhân viên, ca làm (morning/afternoon/evening),
    vai trò (waiter/chef/manager...). Để trống nếu muốn lấy tất cả.
    """
    logger.info(f"[tool:get_employees] query={query!r}")

    # Xây params — chỉ gửi nếu có giá trị
    params: dict = {"page_size": settings.max_tool_output_items}
    if query.strip():
        params["name"] = query.strip()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.odoo_base_url}/dineflow/api/employees",
                headers=ODOO_HEADERS,
                params=params,
            )
            resp.raise_for_status()   # raise nếu 4xx/5xx
            data = resp.json()

    except httpx.TimeoutException:
        logger.warning("[tool:get_employees] Timeout khi gọi Odoo")
        return "Lỗi: Odoo không phản hồi (timeout). Vui lòng thử lại."

    except httpx.HTTPStatusError as e:
        logger.error(f"[tool:get_employees] HTTP {e.response.status_code}")
        return f"Lỗi: Odoo trả về status {e.response.status_code}."

    except Exception as e:
        logger.error(f"[tool:get_employees] Unexpected error: {e}")
        return f"Lỗi không xác định: {e}"

    # Lấy list nhân viên từ response Odoo
    # Standard response: {success, data, meta, summary}
    employees = data.get("data", [])
    if not employees:
        return "Không tìm thấy nhân viên nào."

    trimmed = _trim_list(employees)
    result = {
        "total": data.get("meta", {}).get("total_count", len(employees)),
        "showing": len(trimmed),
        "employees": trimmed,
    }
    return _to_str(result)


@tool
async def get_employees_on_leave_today(query: str = "")G: -> str:
    """
    Lấy danh sách nhân viên đang nghỉ phép hôm nay.
    Dùng khi hỏi ai đang nghỉ, hôm nay thiếu người không,
    hoặc cần biết nhân sự thực tế có mặt hôm nay.
    Tham số query không dùng, để trống cũng được.
    """
    logger.info("[tool:get_employees_on_leave_today]")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.odoo_base_url}/dineflow/api/employees/on-leave-today",
                headers=ODOO_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        return "Lỗi: Odoo không phản hồi (timeout)."

    except httpx.HTTPStatusError as e:
        return f"Lỗi: Odoo trả về status {e.response.status_code}."

    except Exception as e:
        return f"Lỗi không xác định: {e}"

    employees = data.get("data", [])
    if not employees:
        return "Hôm nay không có nhân viên nào nghỉ phép."

    trimmed = _trim_list(employees)
    result = {
        "on_leave_today": len(employees),
        "employees": trimmed,
    }
    return _to_str(result)