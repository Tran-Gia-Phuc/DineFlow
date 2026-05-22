import json
from odoo import http
from odoo.http import request


class DineFlowAPI(http.Controller):

    # ── AUTH HELPER ──────────────────────────────────────────
    def _check_api_key(self):
        api_key = request.httprequest.headers.get('X-API-Key')
        return api_key == 'dineflow-secret-2024'

    def _json_response(self, data, status=200):
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status
        )

    # ── LEAVE ─────────────────────────────────────────────────
    @http.route('/dineflow/api/leave', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_leave(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)

        try:
            data = json.loads(request.httprequest.data)
            employee_id = data.get('employee_id')
            date_from   = data.get('date_from')
            date_to     = data.get('date_to')
            reason      = data.get('reason', '')

            if not all([employee_id, date_from, date_to]):
                return self._json_response({'error': 'Thiếu employee_id, date_from hoặc date_to'}, 400)

            leave = request.env['restaurant.leave.request'].sudo().create({
                'employee_id': int(employee_id),
                'date_from':   date_from,
                'date_to':     date_to,
                'reason':      reason,
            })
            return self._json_response({'success': True, 'leave_id': leave.id})

        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/leave', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_leaves(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)

        employee_id = request.httprequest.args.get('employee_id')
        domain = []
        if employee_id:
            domain.append(('employee_id', '=', int(employee_id)))

        leaves = request.env['restaurant.leave.request'].sudo().search(domain)
        result = []
        for l in leaves:
            result.append({
                'id':          l.id,
                'employee':    l.employee_id.name,
                'date_from':   str(l.date_from),
                'date_to':     str(l.date_to),
                'reason':      l.reason,
                'state':       l.status,
            })
        return self._json_response(result)

    # ── REVENUE ───────────────────────────────────────────────
    @http.route('/dineflow/api/revenue', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_revenue(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)

        records = request.env['restaurant.revenue.report'].sudo().search([])
        result = []
        for r in records:
            result.append({
                'date':     str(r.date),
                'revenue':  r.revenue,
                'order_count': r.order_count,
            })
        return self._json_response(result)