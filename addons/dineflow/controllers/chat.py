import json
import re
import time
import hashlib
import requests
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

N8N_WEBHOOK_URL = 'http://n8n:5678/webhook/dineflow-chat'

_api_cache = {}
_CACHE_TTL = 3  # giây

_TOOL_OUTPUT_MAX_ITEMS = 15
_TOOL_OUTPUT_MAX_CHARS = 800


class DineFlowChat(http.Controller):

    # ══════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════

    def _sanitize_response(self, text: str) -> str:
        if not text:
            return text
        text = re.sub(r'<function=[^>]+>.*?</function>', '', text, flags=re.DOTALL)
        text = re.sub(r'```(?:tool_call|tool_use|function_call)[^`]*```', '', text, flags=re.DOTALL)
        text = re.sub(r'\[(?:TOOL_CALL|FUNCTION|TOOL)[^\]]*\]', '', text)
        text = re.sub(r'^\s*\{"name"\s*:\s*"[a-z_]+".*?\}\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text

    def _get_employee_and_role(self):
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.uid)
        ], limit=1)
        user = request.env.user
        if user.has_group('dineflow.group_dineflow_manager'):
            role = 'manager'
        else:
            role = 'employee'
        return employee, role

    def _trim_tool_output(self, text: str) -> str:
        """
        Nén tool output JSON trước khi đưa vào context LLM.
        - Nếu là response chuẩn {success, data, meta}: giữ tối đa N items.
        - Nếu là raw array: giữ tối đa N items.
        - Nếu không phải JSON hoặc quá dài: cắt thẳng.
        """
        if not text or len(text) <= _TOOL_OUTPUT_MAX_CHARS:
            return text

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text[:_TOOL_OUTPUT_MAX_CHARS] + '...[truncated]'

        # Response chuẩn {success, data, meta, summary}
        if isinstance(data, dict) and 'data' in data:
            items = data.get('data', [])
            total = data.get('meta', {}).get('total_count', len(items))
            if len(items) > _TOOL_OUTPUT_MAX_ITEMS:
                data['data'] = items[:_TOOL_OUTPUT_MAX_ITEMS]
                data['_trimmed'] = (
                    f"Hiển thị {_TOOL_OUTPUT_MAX_ITEMS}/{total} item. "
                    f"Dùng ?page=2 để xem tiếp."
                )
            return json.dumps(data, ensure_ascii=False)

        # Raw array
        if isinstance(data, list) and len(data) > _TOOL_OUTPUT_MAX_ITEMS:
            trimmed = data[:_TOOL_OUTPUT_MAX_ITEMS]
            note    = {'_trimmed': f'Hiển thị {_TOOL_OUTPUT_MAX_ITEMS}/{len(data)} item'}
            return json.dumps([*trimmed, note], ensure_ascii=False)

        return text

    def _call_n8n(self, payload: dict) -> tuple[int, str]:
        cache_key = hashlib.md5(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

        now = time.time()
        if cache_key in _api_cache:
            ts, cached = _api_cache[cache_key]
            if now - ts < _CACHE_TTL:
                _logger.info("[CHAT] Dedup cache hit — bỏ qua double call")
                return cached

        resp   = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
        result = (resp.status_code, resp.text)
        _api_cache[cache_key] = (now, result)

        expired = [k for k, (ts, _) in _api_cache.items() if now - ts > _CACHE_TTL * 10]
        for k in expired:
            del _api_cache[k]

        return result

    # ══════════════════════════════════════════════════════════
    # CHAT
    # ══════════════════════════════════════════════════════════

    @http.route('/dineflow/chat', type='json', auth='user', methods=['POST'], csrf=False)
    def chat(self, **kwargs):
        message = kwargs.get('message', '').strip()
        if not message:
            return {'error': 'Tin nhắn không được để trống'}

        employee, role = self._get_employee_and_role()
        employee_id   = employee.id if employee else None
        employee_name = employee.name if employee else 'Unknown'
        session_id    = f"odoo_{request.env.uid}"

        payload = {
            'session_id':    session_id,
            'message':       message,
            'role':          role,
            'employee_id':   employee_id,
            'employee_name': employee_name,
        }

        # Trim tool_results nếu có trong payload (chống token bloat)
        if 'tool_results' in payload:
            raw = json.dumps(payload['tool_results'], ensure_ascii=False)
            payload['tool_results'] = json.loads(self._trim_tool_output(raw))

        _logger.info("=" * 50)
        _logger.info("[CHAT REQUEST]")
        _logger.info(f"  User     : {employee_name} (uid={request.env.uid})")
        _logger.info(f"  Role     : {role}")
        _logger.info(f"  Session  : {session_id}")
        _logger.info(f"  Message  : {message}")
        _logger.info("=" * 50)

        ai_response = ''
        status_code = 0
        try:
            status_code, ai_response = self._call_n8n(payload)
            ai_response = self._sanitize_response(ai_response)

            _logger.info("[CHAT RESPONSE]")
            _logger.info(f"  Status   : {status_code}")
            _logger.info(f"  Body     : {ai_response}")
            _logger.info("=" * 50)

        except requests.exceptions.Timeout:
            _logger.error("[CHAT] TIMEOUT sau 30s")
            ai_response = 'AI đang bận, vui lòng thử lại sau.'
        except requests.exceptions.ConnectionError:
            _logger.error("[CHAT] Không kết nối được n8n")
            ai_response = 'Lỗi kết nối AI.'
        except Exception as e:
            _logger.error(f"[CHAT] ERROR: {str(e)}")
            ai_response = f'Lỗi: {str(e)}'

        if ai_response and ai_response.strip():
            request.env['restaurant.ai.chat'].sudo().create({
                'employee_id': employee_id,
                'session_id':  session_id,
                'message':     message,
                'response':    ai_response,
            })

        return {
            'response':      ai_response,
            'employee_name': employee_name,
            'role':          role,
        }

    # ══════════════════════════════════════════════════════════
    # HISTORY
    # ══════════════════════════════════════════════════════════

    @http.route('/dineflow/chat/history', type='json', auth='user', methods=['POST'], csrf=False)
    def chat_history(self, **kwargs):
        session_id = f"odoo_{request.env.uid}"

        # Lấy 30 turn gần nhất (desc), rồi trim theo token budget
        history = request.env['restaurant.ai.chat'].sudo().search([
            ('session_id', '=', session_id)
        ], order='created_at desc', limit=30)

        TOKEN_BUDGET = 1500        # token dành cho history
        CHARS_BUDGET = TOKEN_BUDGET * 4  # ≈ 6000 ký tự
        used_chars   = 0
        kept         = []

        for h in history:  # desc → từ mới đến cũ
            entry_chars = len(h.message or '') + len(h.response or '')
            if used_chars + entry_chars > CHARS_BUDGET:
                break
            kept.append(h)
            used_chars += entry_chars

        kept.reverse()  # đảo lại asc cho n8n nhận đúng thứ tự

        return [{
            'message':    h.message,
            'response':   h.response,
            'created_at': str(h.created_at),
        } for h in kept]