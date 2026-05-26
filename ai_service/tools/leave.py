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
async def get_leave_requests(query: str) -> str:
    """
    Lấy danh sách đơn xin nghỉ phép của nhân viên.
    Dùng khi hỏi về đơn nghỉ phép, ai đang chờ duyệt nghỉ,
    lịch sử nghỉ phép, hoặc trạng thái đơn nghỉ của nhân viên nào đó.

    Tham số query có thể chứa: tên hoặc ID nhân viên, trạng thái
    (pending/approved/refused), khoảng thời gian (tuần này, tháng này).
    Để trống để lấy tất cả đơn đang pending.
    """
    logger.info(f"[tool:get_leave_requests] query={query!r}")

    params: dict = {
        "page_size": settings.max_tool_output_items,
        "status": "pending",   # mặc định xem đơn chờ duyệt
    }

    q = query.strip().lower()
    if "approved" in q or "đã duyệt" in q:
        params["status"] = "approved"
    elif "refused" in q or "từ chối" in q:
        params["status"] = "refused"
    elif "tất cả" in q or "all" in q:
        params.pop("status", None)

    # Tìm employee_id nếu agent truyền vào
    import re
    id_match = re.search(r"employee_id[=:\s]+(\d+)", q)
    if id_match:
        params["employee_id"] = int(id_match.group(1))

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.odoo_base_url}/dineflow/api/leave",
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

    leaves = data.get("data", [])
    if not leaves:
        return "Không có đơn nghỉ phép nào phù hợp."

    trimmed = _trim_list(leaves)
    result = {
        "total": data.get("meta", {}).get("total_count", len(leaves)),
        "showing": len(trimmed),
        "leave_requests": trimmed,
    }
    return _to_str(result)


@tool
async def create_leave_request(query: str) -> str:
    """
    Tạo đơn xin nghỉ phép mới cho nhân viên.
    Dùng khi nhân viên muốn xin nghỉ phép, đăng ký ngày nghỉ,
    hoặc submit đơn nghỉ phép.

    Tham số query phải chứa JSON string:
    {"employee_id": số_id, "date_from": "YYYY-MM-DD",
     "date_to": "YYYY-MM-DD", "reason": "lý do nghỉ"}

    Nếu thiếu thông tin, hỏi lại người dùng trước khi gọi tool này.
    """
    logger.info(f"[tool:create_leave_request] query={query!r}")

    try:
        payload = json.loads(query)
    except json.JSONDecodeError:
        return "Lỗi: Dữ liệu không đúng định dạng JSON."

    required = ["employee_id", "date_from", "date_to"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return f"Thiếu thông tin bắt buộc: {', '.join(missing)}."

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.odoo_base_url}/dineflow/api/leave",
                headers=ODOO_HEADERS,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        return "Lỗi: Odoo không phản hồi (timeout)."
    except httpx.HTTPStatusError as e:
        return f"Lỗi: Odoo trả về status {e.response.status_code}."
    except Exception as e:
        return f"Lỗi không xác định: {e}"

    leave = data.get("data", {})
    return (
        f"Đã tạo đơn nghỉ phép thành công! Mã đơn: #{leave.get('id')}. "
        f"Nhân viên ID: {leave.get('employee_id')}, "
        f"Từ: {leave.get('date_from')} đến {leave.get('date_to')}. "
        f"Trạng thái: đang chờ duyệt."
    )


@tool
async def approve_leave_request(query: str) -> str:
    """
    Duyệt hoặc từ chối đơn xin nghỉ phép.
    Dùng khi quản lý muốn phê duyệt hoặc từ chối đơn nghỉ của nhân viên.

    Tham số query phải chứa JSON string:
    {"leave_id": số_id, "action": "approve|refuse",
     "reason": "lý do từ chối (chỉ cần khi refuse)"}
    """
    logger.info(f"[tool:approve_leave_request] query={query!r}")

    try:
        payload = json.loads(query)
    except json.JSONDecodeError:
        return "Lỗi: Dữ liệu không đúng định dạng JSON."

    leave_id = payload.get("leave_id")
    action = payload.get("action")

    if not leave_id:
        return "Thiếu leave_id."
    if action not in ("approve", "refuse"):
        return "action phải là 'approve' hoặc 'refuse'."

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.odoo_base_url}/dineflow/api/leave/{leave_id}/{action}",
                headers=ODOO_HEADERS,
                json={"reason": payload.get("reason", "")},
            )

            if resp.status_code == 404:
                return f"Không tìm thấy đơn nghỉ phép #{leave_id}."

            resp.raise_for_status()

    except httpx.TimeoutException:
        return "Lỗi: Odoo không phản hồi (timeout)."
    except httpx.HTTPStatusError as e:
        return f"Lỗi: Odoo trả về status {e.response.status_code}."
    except Exception as e:
        return f"Lỗi không xác định: {e}"

    action_text = "Đã duyệt" if action == "approve" else "Đã từ chối"
    return f"{action_text} đơn nghỉ phép #{leave_id} thành công."