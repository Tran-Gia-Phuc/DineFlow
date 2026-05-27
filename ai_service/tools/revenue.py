import httpx
import json
import logging
from datetime import date, timedelta
from langchain_core.tools import tool

from config import settings

logger = logging.getLogger(__name__)

ODOO_HEADERS = {
    "X-API-Key": settings.odoo_api_key,
    "Content-Type": "application/json",
}


def _to_str(data) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > settings.max_tool_output_chars:
        text = text[: settings.max_tool_output_chars] + "\n... (đã cắt bớt)"
    return text


# ── Tools ─────────────────────────────────────────────────────

@tool
async def get_revenue(query: str = "")G: -> str:
    """
    Lấy thông tin doanh thu của nhà hàng.
    Dùng khi hỏi về doanh thu,oanh số, thu nhập, tổng tiền bán được,
    doanh thu hôm nay, tuần này, tháng này, hoặc so sánh doanh thu.

    Tham số query có thể chứa: "hôm nay", "tuần này", "tháng này",
    "tháng 5", "năm 2026", hoặc khoảng ngày cụ thể "2026-05-01 đến 2026-05-31".
    Để trống để lấy doanh thu tháng hiện tại.
    """
    logger.info(f"[tool:get_revenue] query={query!r}")

    today = date.today()
    params: dict = {"summary_only": True}  # mặc định chỉ lấy tổng, không lấy chi tiết

    q = query.strip().lower()

    if "hôm nay" in q or "today" in q:
        params["date_from"] = today.isoformat()
        params["date_to"] = today.isoformat()

    elif "tuần này" in q or "this week" in q:
        # Thứ Hai tuần này → hôm nay
        start_of_week = today - timedelta(days=today.weekday())
        params["date_from"] = start_of_week.isoformat()
        params["date_to"] = today.isoformat()

    elif "tháng này" in q or "this month" in q:
        params["month"] = today.month
        params["year"] = today.year

    elif "năm nay" in q or "this year" in q:
        params["year"] = today.year
        params.pop("summary_only", None)  # lấy chi tiết theo tháng

    else:
        # Tìm "tháng X" hoặc "tháng X năm Y"
        import re
        month_match = re.search(r"tháng\s*(\d+)(?:\s*năm\s*(\d+))?", q)
        year_match = re.search(r"năm\s*(\d{4})", q)

        if month_match:
            params["month"] = int(month_match.group(1))
            params["year"] = int(month_match.group(2)) if month_match.group(2) else today.year
        elif year_match:
            params["year"] = int(year_match.group(1))
        else:
            # Default: tháng hiện tại
            params["month"] = today.month
            params["year"] = today.year

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.odoo_base_url}/dineflow/api/revenue",
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

    # Revenue API trả summary trong data hoặc data.summary
    revenue_data = data.get("summary") or data.get("data") or {}
    if not revenue_data:
        return "Không có dữ liệu doanh thu cho khoảng thời gian này."

    return _to_str(revenue_data)