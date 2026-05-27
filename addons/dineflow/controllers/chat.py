import json
import re
import logging
import requests
from odoo import http, fields
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

AI_SERVICE_URL  = 'http://ai_service:8000'
AI_SERVICE_KEY  = 'dineflow-ai-secret-2024'
INTERNAL_KEY    = 'dineflow-internal-secret'   # phải khớp với odoo_internal_key trong ai_service


class DineFlowChat(http.Controller):

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
        role = 'manager' if user.has_group('dineflow.group_dineflow_manager') else 'employee'
        return employee, role

    def _call_ai_service(self, session_id: str, message: str) -> tuple[int, str]:
        payload = {
            'session_id': session_id,
            'message':    message,
            'history':    [],
        }
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key':    AI_SERVICE_KEY,
        }
        resp = requests.post(
            f'{AI_SERVICE_URL}/chat',
            json=payload,
            headers=headers,
            timeout=60,
        )
        return resp.status_code, resp.text

    # ── Route cũ — giữ nguyên ─────────────────────────────────
    @http.route('/dineflow/chat', type='json', auth='user', methods=['POST'], csrf=False)
    def chat(self, **kwargs):
        message = kwargs.get('message', '').strip()
        if not message:
            return {'error': 'Tin nhắn không được để trống'}

        employee, role = self._get_employee_and_role()
        employee_id    = employee.id if employee else None
        employee_name  = employee.name if employee else 'Unknown'
        session_id     = f"odoo_{request.env.uid}"

        _logger.info(f"[CHAT] {employee_name} | {session_id} | {message}")

        ai_response = ''
        try:
            status_code, raw = self._call_ai_service(session_id, message)
            try:
                data = json.loads(raw)
                ai_response = data.get('response', '')
            except json.JSONDecodeError:
                ai_response = raw
            ai_response = self._sanitize_response(ai_response)
        except requests.exceptions.Timeout:
            ai_response = 'AI đang xử lý lâu, vui lòng thử lại sau.'
        except requests.exceptions.ConnectionError:
            ai_response = 'Lỗi kết nối AI service.'
        except Exception as e:
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

    @http.route('/dineflow/chat/history', type='json', auth='user', methods=['POST'], csrf=False)
    def chat_history(self, **kwargs):
        session_id = f"odoo_{request.env.uid}"
        history = request.env['restaurant.ai.chat'].sudo().search([
            ('session_id', '=', session_id)
        ], order='created_at desc', limit=30)
        return [{
            'message':    h.message,
            'response':   h.response,
            'created_at': str(h.created_at),
        } for h in reversed(history)]

    # ── Route mới: async + SSE ────────────────────────────────

    @http.route('/dineflow/chat/async', type='json', auth='user', methods=['POST'], csrf=False)
    def chat_async(self, **kwargs):
        message = kwargs.get('message', '').strip()
        if not message:
            return {'error': 'Tin nhắn không được để trống'}

        employee, role = self._get_employee_and_role()
        session_id     = f"odoo_{request.env.uid}"

        _logger.info(f"[CHAT ASYNC] session={session_id} | {message[:80]}")

        try:
            resp = requests.post(
                f'{AI_SERVICE_URL}/chat/async',
                json={'session_id': session_id, 'message': message, 'history': []},
                headers={'Content-Type': 'application/json', 'X-API-Key': AI_SERVICE_KEY},
                timeout=10,
            )
            data = resp.json()
            return {
                'job_id':     data.get('job_id'),
                'session_id': data.get('session_id', session_id),
            }
        except Exception as e:
            _logger.error(f"[CHAT ASYNC] ERROR: {e}")
            return {'error': str(e)}

    @http.route('/dineflow/chat/stream/<string:session_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def chat_stream(self, session_id, **kwargs):
        """Proxy SSE từ ai_service về Odoo JS client."""
        def generate():
            try:
                with requests.get(
                    f'{AI_SERVICE_URL}/chat/stream/{session_id}',
                    headers={'X-API-Key': AI_SERVICE_KEY},
                    stream=True,
                    timeout=310,
                ) as r:
                    for line in r.iter_lines():
                        if line:
                            yield line.decode('utf-8') + '\n\n'
                        else:
                            yield '\n'
            except Exception as e:
                _logger.error(f"[SSE PROXY] ERROR: {e}")
                yield f'data: {{"type":"error","message":"Proxy lỗi"}}\n\n'

        return Response(
            generate(),
            content_type='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
        )

    @http.route('/dineflow/chat/result', type='json', auth='user', methods=['POST'], csrf=False)
    def chat_result(self, **kwargs):
        session_id = kwargs.get('session_id') or f"odoo_{request.env.uid}"
        job_id     = kwargs.get('job_id', '')
        try:
            if job_id:
                last = request.env['restaurant.ai.chat'].sudo().search([
                    ('job_id', '=', job_id)
                ], limit=1)
            else:
                last = request.env['restaurant.ai.chat'].sudo().search([
                    ('session_id', '=', session_id)
                ], order='created_at desc', limit=1)

            if last:
                return {'response': last.response}
            return {'response': None}   # ← None thay vì string để JS retry đúng
        except Exception as e:
            _logger.error(f"[CHAT RESULT] ERROR: {e}")
            return {'error': str(e)}

    @http.route('/dineflow/chat/save_result', type='json', auth='none', methods=['POST'], csrf=False)
    def chat_save_result(self, **kwargs):
        """
        Được gọi từ ai_service worker sau khi job xong.
        auth='none' vì worker không có Odoo session — bảo vệ bằng X-Internal-Key.
        """
        # Xác thực internal key
        api_key = request.httprequest.headers.get('X-Internal-Key', '')
        if api_key != INTERNAL_KEY:
            _logger.warning(f"[SAVE RESULT] Unauthorized — key sai: {api_key[:20]}")
            return {'error': 'Unauthorized'}

        session_id = kwargs.get('session_id', '').strip()
        message    = kwargs.get('message', '').strip()
        response   = kwargs.get('response', '').strip()

        if not session_id or not response:
            return {'error': 'Thiếu session_id hoặc response'}

        try:
            request.env['restaurant.ai.chat'].sudo().create({
                'session_id': session_id,
                'job_id':     kwargs.get('job_id', ''),   # ← thêm
                'message':    message,
                'response':   response,
                'created_at': fields.Datetime.now(),
            })
            _logger.info(f"[SAVE RESULT] Đã lưu — session={session_id}")
            return {'ok': True}
        except Exception as e:
            _logger.error(f"[SAVE RESULT] ERROR: {e}", exc_info=True)
            return {'error': str(e)}