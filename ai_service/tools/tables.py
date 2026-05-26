import httpx
import json
import logging
from langchain_core.tools import tool

from config import settings

logger = logging.getLogger(__name__)

ODOO_HEADERS = {
    "X-API-Key": settings.odoo_api_key,
    "Content-Type": "application/json",
}


def _trim_list(items: list) -> list:
    return items[: settings.max_tool_output_items]


def _to_str(data) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > settings.max_tool_output_chars:
        text = text[: settings.max_tool_output_chars] + "\n... (đã cắt bớt)"
    return text


# ── Tools ─────────────────────────────────────────────────────

@tool
async def get_tables(query: str) -> str:
    """
    Lấy danh sách bàn trong nhà hàng và trạng thái của từng bàn.
    Dùng khi hỏi bàn nào còn trống, bàn nào đang có khách,
    còn bao nhiêu bàn available, hoặc bàn ở tầng nào còn chỗ.

    Tham số query có thể chứa: trạng thái (available/occupied/reserved),
    tầng (floor), hoặc để trống để lấy tất cả.
    """
    logger.info(f"[tool:get_tables] query={query!r}")

    params: dict = {"page_size": settings.max_tool_output_items}

    q = query.strip().lower()
    if "trống" in q or "available" in q:
        params["status"] = "available"
    elif "có khách" in q or "occupied" in q:
        params["status"] = "occupied"
    elif "reserved" in q or "đặt trước" in q:
        params["status"] = "reserved"

    # Tìm số tầng trong query, ví dụ "tầng 2" → floor=2
    import re
    floor_match = re.search(r"tầng\s*(\d+)|floor\s*(\d+)", q)
    if floor_match:
        floor_num = floor_match.group(1) or floor_match.group(2)
        params["floor"] = int(floor_num)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.odoo_base_url}/dineflow/api/tables",
                headers=ODOO_HEADERS,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        return "Lỗi: Odoo không phản hồi (timeout)."
    except httpx.HTTPStatusError as e:
        return f"Lỗi: Odoo trả về status {e.response.status_code}."
    except Exception as e:
        return f"Lỗi không xác định: {e}"

    tables = data.get("data", [])
    if not tables:
        return "Không tìm thấy bàn nào phù hợp."

    trimmed = _trim_list(tables)
    result = {
        "total": data.get("meta", {}).get("total_count", len(tables)),
        "showing": len(trimmed),
        "tables": trimmed,
    }
    return _to_str(result)


@tool
async def update_table_status(query: str) -> str:
    """
    Cập nhật trạng thái của một bàn.
    Dùng khi cần đổi bàn từ trống sang có khách, hoặc dọn bàn xong muốn
    đánh dấu lại là available.

    Tham số query phải chứa JSON string:
    {"table_id": số_id, "status": "available|occupied|reserved"}

    Ví dụ: {"table_id": 5, "status": "occupied"}
    """
    logger.info(f"[tool:update_table_status] query={query!r}")

    try:
        payload = json.loads(query)
    except json.JSONDecodeError:
        return "Lỗi: Dữ liệu không đúng định dạng JSON."

    table_id = payload.get("table_id")
    status = payload.get("status")

    if not table_id:
        return "Thiếu table_id. Vui lòng cung cấp ID bàn cần cập nhật."
    if status not in ("available", "occupied", "reserved"):
        return "Trạng thái không hợp lệ. Chỉ chấp nhận: available, occupied, reserved."

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{settings.odoo_base_url}/dineflow/api/tables/{table_id}",
                headers=ODOO_HEADERS,
                json={"status": status},
            )

            if resp.status_code == 404:
                return f"Không tìm thấy bàn #{table_id}."

            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        return "Lỗi: Odoo không phản hồi (timeout)."
    except httpx.HTTPStatusError as e:
        return f"Lỗi: Odoo trả về status {e.response.status_code}."
    except Exception as e:
        return f"Lỗi không xác định: {e}"

    table = data.get("data", {})
    return f"Đã cập nhật bàn #{table_id} → trạng thái: {status}."