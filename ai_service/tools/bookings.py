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
async def get_bookings(query: str) -> str:
    """
    Lấy danh sách đặt bàn trong nhà hàng.
    Dùng khi hỏi về lịch đặt bàn, đặt bàn hôm nay, ca nào còn trống,
    khách nào sắp đến, hoặc tình trạng đặt bàn hiện tại.

    Tham số query có thể chứa: ngày (YYYY-MM-DD), ca (morning/afternoon/evening),
    trạng thái (confirmed/pending/cancelled), hoặc để trống để lấy tất cả sắp tới.
    """
    logger.info(f"[tool:get_bookings] query={query!r}")

    # Mặc định lấy các booking sắp tới trong 120 phút
    params: dict = {
        "page_size": settings.max_tool_output_items,
        "upcoming_minutes": 120,
    }

    # Parse query đơn giản — agent sẽ truyền keyword vào
    q = query.strip().lower()
    if "hôm nay" in q or "today" in q:
        from datetime import date
        params["date"] = date.today().isoformat()
        params.pop("upcoming_minutes", None)
    if "pending" in q or "chờ" in q:
        params["status"] = "pending"
    if "confirmed" in q or "xác nhận" in q:
        params["status"] = "confirmed"
    if "cancelled" in q or "hủy" in q:
        params["status"] = "cancelled"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.odoo_base_url}/dineflow/api/bookings",
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

    bookings = data.get("data", [])
    if not bookings:
        return "Không có đặt bàn nào phù hợp."

    trimmed = _trim_list(bookings)
    result = {
        "total": data.get("meta", {}).get("total_count", len(bookings)),
        "showing": len(trimmed),
        "bookings": trimmed,
    }
    return _to_str(result)


@tool
async def create_booking(query: str) -> str:
    """
    Tạo đặt bàn mới cho khách.
    Dùng khi khách muốn đặt bàn, yêu cầu giữ bàn, hoặc book bàn cho buổi ăn.

    Tham số query phải chứa đủ thông tin theo định dạng JSON string:
    {"customer_name": "...", "phone": "...", "date": "YYYY-MM-DD",
     "shift": "morning|afternoon|evening", "guests": số_người,
     "table_id": số_id_bàn}

    Nếu thiếu thông tin, hãy hỏi lại người dùng trước khi gọi tool này.
    """
    logger.info(f"[tool:create_booking] query={query!r}")

    # Parse JSON từ query string agent truyền vào
    try:
        payload = json.loads(query)
    except json.JSONDecodeError:
        return "Lỗi: Dữ liệu đặt bàn không đúng định dạng JSON. Vui lòng thử lại."

    # Kiểm tra field bắt buộc
    required = ["customer_name", "date", "shift", "guests"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return f"Thiếu thông tin bắt buộc: {', '.join(missing)}. Vui lòng cung cấp thêm."

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.odoo_base_url}/dineflow/api/bookings",
                headers=ODOO_HEADERS,
                json=payload,   # gửi dict dưới dạng JSON body
            )

            # 409 = conflict — bàn đã được đặt giờ đó
            if resp.status_code == 409:
                error_data = resp.json()
                return f"Không thể đặt bàn: {error_data.get('message', 'Bàn đã được đặt trong khung giờ này.')}"

            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        return "Lỗi: Odoo không phản hồi (timeout)."
    except httpx.HTTPStatusError as e:
        return f"Lỗi: Odoo trả về status {e.response.status_code}."
    except Exception as e:
        return f"Lỗi không xác định: {e}"

    booking = data.get("data", {})
    return f"Đặt bàn thành công! Mã đặt bàn: #{booking.get('id')}. " \
           f"Khách: {booking.get('customer_name')}, " \
           f"Ngày: {booking.get('date')}, Ca: {booking.get('shift')}."


@tool
async def cancel_booking(query: str) -> str:
    """
    Hủy một đặt bàn đã có.
    Dùng khi khách muốn hủy đặt bàn, không đến được, hoặc thay đổi kế hoạch.

    Tham số query phải chứa ID của đặt bàn cần hủy (chỉ số, ví dụ: "42").
    Nếu chưa biết ID, hãy dùng get_bookings để tìm trước.
    """
    logger.info(f"[tool:cancel_booking] query={query!r}")

    # Lấy booking ID từ query
    try:
        booking_id = int(query.strip())
    except ValueError:
        return f"Lỗi: '{query}' không phải ID hợp lệ. ID phải là số nguyên."

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.odoo_base_url}/dineflow/api/bookings/{booking_id}/cancel",
                headers=ODOO_HEADERS,
            )

            if resp.status_code == 404:
                return f"Không tìm thấy đặt bàn #{booking_id}."

            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        return "Lỗi: Odoo không phản hồi (timeout)."
    except httpx.HTTPStatusError as e:
        return f"Lỗi: Odoo trả về status {e.response.status_code}."
    except Exception as e:
        return f"Lỗi không xác định: {e}"

    return f"Đã hủy đặt bàn #{booking_id} thành công."