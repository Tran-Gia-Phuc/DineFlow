import json
import re
import logging
import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

AI_SERVICE_URL = 'http://ai_service:8000/chat'
AI_SERVICE_KEY = 'dineflow-ai-secret-2024'


class DineFlowChat(http.Controller):
    
    def _sanitize_response(self, text: str) -> str:
        """Xóa artifact tool call còn sót trong response LLM."""
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

    def _call_ai_service(self, session_id: str, message: str) -> tuple[int, str]:
        """
        Gọi ai_service thay vì n8n.
        ai_service tự load history từ PostgreSQL theo session_id
        → không cần gửi history trong payload.
        """
        payload = {
            'session_id': session_id,
            'message':    message,
            'history':    [],   # ai_service tự load, để rỗng
        }

        headers = {
            'Content-Type':  'application/json',
            'X-API-Key':     AI_SERVICE_KEY,
        }

        resp = requests.post(
            AI_SERVICE_URL,
            json=payload,
            headers=headers,
            timeout=60,   # agent có thể mất 10-30s
        )
        return resp.status_code, resp.text

    @http.route('/dineflow/chat', type='json', auth='user', methods=['POST'], csrf=False)
    def chat(self, **kwargs):
        message = kwargs.get('message', '').strip()
        if not message:
            return {'error': 'Tin nhắn không được để trống'}

        employee, role    = self._get_employee_and_role()
        employee_id       = employee.id if employee else None
        employee_name     = employee.name if employee else 'Unknown'
        session_id        = f"odoo_{request.env.uid}"

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
            status_code, raw_response = self._call_ai_service(session_id, message)

            try:
                data        = json.loads(raw_response)
                ai_response = data.get('response', '')
            except json.JSONDecodeError:
                ai_response = raw_response  # fallback nếu không phải JSON

            ai_response = self._sanitize_response(ai_response)

            _logger.info("[CHAT RESPONSE]")
            _logger.info(f"  Status   : {status_code}")
            _logger.info(f"  Body     : {ai_response[:200]}")
            _logger.info("=" * 50)

        except requests.exceptions.Timeout:
            _logger.error("[CHAT] TIMEOUT sau 60s")
            ai_response = 'AI đang xử lý lâu, vui lòng thử lại sau.'
        except requests.exceptions.ConnectionError:
            _logger.error("[CHAT] Không kết nối được ai_service")
            ai_response = 'Lỗi kết nối AI service.'
        except Exception as e:
            _logger.error(f"[CHAT] ERROR: {str(e)}")
            ai_response = f'Lỗi: {str(e)}'

        # Lưu vào Odoo DB để hiển thị lịch sử trong UI
        # (ai_service cũng lưu vào PostgreSQL riêng để dùng cho context)
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

    @http.route('/dineflow/chat/history', type='json', auth='user', methods=['POST'], csrf=False)
    def chat_history(self, **kwargs):
        """
        Trả history để hiển thị trong UI Odoo.
        History thực tế cho AI context được ai_service tự load từ DB riêng.
        """
        session_id = f"odoo_{request.env.uid}"

        history = request.env['restaurant.ai.chat'].sudo().search([
            ('session_id', '=', session_id)
        ], order='created_at desc', limit=30)

        history_list = [{
            'message':    h.message,
            'response':   h.response,
            'created_at': str(h.created_at),
        } for h in reversed(history)]

        return history_list