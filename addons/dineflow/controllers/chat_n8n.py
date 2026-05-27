import json
import requests
from odoo import http
from odoo.http import request

N8N_WEBHOOK_URL = 'http://n8n:5678/webhook/dineflow-chat'

class DineFlowChat(http.Controller):

    @http.route('/dineflow/chat', type='json', auth='user', methods=['POST'], csrf=False)
    def chat(self, **kwargs):
        message = kwargs.get('message', '').strip()
        if not message:
            return {'error': 'Tin nhắn không được để trống'}

        # Lấy thông tin nhân viên đang login
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.uid)
        ], limit=1)

        employee_id = employee.id if employee else None
        employee_name = employee.name if employee else 'Unknown'
        session_id = f"odoo_{request.env.uid}"

        # Xác định role
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
            }, timeout=30)
            ai_response = resp.text
        except Exception as e:
            ai_response = f'Lỗi kết nối AI: {str(e)}'

        # Lưu lịch sử chat
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
            ('session_id', '=', session_id)
        ], order='created_at asc', limit=50)

        return [{
            'message': h.message,
            'response': h.response,
            'created_at': str(h.created_at),
        } for h in history]
