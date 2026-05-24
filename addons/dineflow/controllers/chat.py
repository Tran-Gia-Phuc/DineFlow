import json
import requests
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

N8N_WEBHOOK_URL = 'http://n8n:5678/webhook/dineflow-chat'

class DineFlowChat(http.Controller):

    @http.route('/dineflow/chat', type='json', auth='user', methods=['POST'], csrf=False)
    def chat(self, **kwargs):
        message = kwargs.get('message', '').strip()
        if not message:
            return {'error': 'Tin nhắn không được để trống'}

        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.uid)
        ], limit=1)

        employee_id = employee.id if employee else None
        employee_name = employee.name if employee else 'Unknown'
        session_id = f"odoo_{request.env.uid}"

        user = request.env.user
        if user.has_group('dineflow.group_dineflow_manager'):
            role = 'manager'
        else:
            role = 'employee'

        # Gọi n8n webhook
        try:
            resp = requests.post(N8N_WEBHOOK_URL, json={
                'session_id': session_id,
                'message': message,
                'role': role,
                'employee_id': employee_id,
                'employee_name': employee_name,
            }, timeout=60)
            ai_response = resp.text
            _logger.info(f"n8n status={resp.status_code}, body={ai_response}")  # log full body
        except requests.exceptions.Timeout:
            _logger.error("n8n TIMEOUT sau 60s")
            ai_response = 'AI đang bận, vui lòng thử lại'
        except requests.exceptions.ConnectionError:
            _logger.error("Không kết nối được n8n")
            ai_response = 'Lỗi kết nối AI'
        except Exception as e:
            _logger.error(f"n8n error: {str(e)}")
            ai_response = f'Lỗi: {str(e)}'

        request.env['restaurant.ai.chat'].sudo().create({
            'employee_id': employee_id,
            'session_id': session_id,
            'message': message,
            'response': ai_response,
        })

        return {
            'response': ai_response,
            'employee_name': employee_name,
            'role': role,
        }

    @http.route('/dineflow/chat/history', type='json', auth='user', methods=['POST'], csrf=False)
    def chat_history(self, **kwargs):
        session_id = f"odoo_{request.env.uid}"
        history = request.env['restaurant.ai.chat'].sudo().search([
            ('session_id', '=', session_id),
            ('response', '!=', False),
            ('response', '!=', ''),
        ], order='created_at desc', limit=20)
        history = history.sorted('created_at')

        _logger.info(f"Chat history query: session_id={session_id}, found={len(history)}")

        return [{
            'message': h.message,
            'response': h.response,
            'created_at': str(h.created_at),
        } for h in history]