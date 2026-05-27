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

    # ══════════════════════════════════════════════════════════
    # LEAVE
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/leave', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_leaves(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        employee_id = request.httprequest.args.get('employee_id')
        status = request.httprequest.args.get('status')
        domain = []
        if employee_id:
            domain.append(('employee_id', '=', int(employee_id)))
        if status:
            domain.append(('status', '=', status))
        leaves = request.env['restaurant.leave.request'].sudo().search(domain, order='date_from desc')
        result = []
        for l in leaves:
            result.append({
                'id':         l.id,
                'employee':   l.employee_id.name,
                'employee_id': l.employee_id.id,
                'date_from':  str(l.date_from),
                'date_to':    str(l.date_to),
                'reason':     l.reason,
                'leave_type': l.leave_type,
                'status':     l.status,
            })
        return self._json_response(result)

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
            leave_type  = data.get('leave_type', 'annual')
            if not all([employee_id, date_from, date_to]):
                return self._json_response({'error': 'Thiếu employee_id, date_from hoặc date_to'}, 400)
            leave = request.env['restaurant.leave.request'].sudo().create({
                'employee_id': int(employee_id),
                'date_from':   date_from,
                'date_to':     date_to,
                'reason':      reason,
                'leave_type':  leave_type,
                'created_by_ai': True,
            })
            return self._json_response({'success': True, 'leave_id': leave.id})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/leave/<int:leave_id>/approve', type='http', auth='none',
                methods=['POST'], csrf=False)
    def approve_leave(self, leave_id):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data or '{}')
            manager_id = data.get('manager_id')
            leave = request.env['restaurant.leave.request'].sudo().browse(leave_id)
            if not leave.exists():
                return self._json_response({'error': 'Không tìm thấy đơn nghỉ'}, 404)
            leave.sudo().write({
                'status': 'approved',
                'manager_id': int(manager_id) if manager_id else None,
                'approved_date': fields.Date.today(),
            })
            return self._json_response({'success': True})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/leave/<int:leave_id>/refuse', type='http', auth='none',
                methods=['POST'], csrf=False)
    def refuse_leave(self, leave_id):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            leave = request.env['restaurant.leave.request'].sudo().browse(leave_id)
            if not leave.exists():
                return self._json_response({'error': 'Không tìm thấy đơn nghỉ'}, 404)
            leave.sudo().write({'status': 'refused'})
            return self._json_response({'success': True})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    # ══════════════════════════════════════════════════════════
    # TABLES
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/tables', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_tables(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        status = request.httprequest.args.get('status')
        domain = []
        if status:
            domain.append(('status', '=', status))
        tables = request.env['restaurant.table'].sudo().search(domain, order='floor, name')
        result = []
        for t in tables:
            result.append({
                'id':           t.id,
                'name':         t.name,
                'capacity':     t.capacity,
                'min_capacity': t.min_capacity,
                'status':       t.status,
                'floor':        t.floor,
                'note':         t.note,
                'active':       t.active,
            })
        return self._json_response(result)

    @http.route('/dineflow/api/tables', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_table(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data)
            if not data.get('name'):
                return self._json_response({'error': 'Thiếu tên bàn'}, 400)
            table = request.env['restaurant.table'].sudo().create({
                'name':         data.get('name'),
                'capacity':     data.get('capacity', 4),
                'min_capacity': data.get('min_capacity', 1),
                'floor':        data.get('floor', 'A'),
                'note':         data.get('note', ''),
            })
            return self._json_response({'success': True, 'table_id': table.id})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/tables/<int:table_id>', type='http', auth='none',
                methods=['PUT'], csrf=False)
    def update_table(self, table_id):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data)
            table = request.env['restaurant.table'].sudo().browse(table_id)
            if not table.exists():
                return self._json_response({'error': 'Không tìm thấy bàn'}, 404)
            table.write({k: v for k, v in data.items() if k in ['name', 'capacity', 'min_capacity', 'floor', 'note', 'status', 'active']})
            return self._json_response({'success': True})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/tables/<int:table_id>', type='http', auth='none',
                methods=['DELETE'], csrf=False)
    def delete_table(self, table_id):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            table = request.env['restaurant.table'].sudo().browse(table_id)
            if not table.exists():
                return self._json_response({'error': 'Không tìm thấy bàn'}, 404)
            table.write({'active': False})
            return self._json_response({'success': True})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    # ══════════════════════════════════════════════════════════
    # CATEGORIES
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/categories', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_categories(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        cats = request.env['restaurant.category'].sudo().search([], order='sequence, name')
        result = []
        for c in cats:
            result.append({
                'id':        c.id,
                'name':      c.name,
                'sequence':  c.sequence,
                'active':    c.active,
                'parent_id': c.parent_id.id if c.parent_id else None,
                'parent':    c.parent_id.name if c.parent_id else None,
            })
        return self._json_response(result)

    @http.route('/dineflow/api/categories', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_category(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data)
            if not data.get('name'):
                return self._json_response({'error': 'Thiếu tên danh mục'}, 400)
            cat = request.env['restaurant.category'].sudo().create({
                'name':      data.get('name'),
                'sequence':  data.get('sequence', 10),
                'parent_id': data.get('parent_id'),
            })
            return self._json_response({'success': True, 'category_id': cat.id})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/categories/<int:cat_id>', type='http', auth='none',
                methods=['PUT'], csrf=False)
    def update_category(self, cat_id):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data)
            cat = request.env['restaurant.category'].sudo().browse(cat_id)
            if not cat.exists():
                return self._json_response({'error': 'Không tìm thấy danh mục'}, 404)
            cat.write({k: v for k, v in data.items() if k in ['name', 'sequence', 'active', 'parent_id']})
            return self._json_response({'success': True})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    # ══════════════════════════════════════════════════════════
    # MENU ITEMS
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/menu-items', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_menu_items(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        category_id = request.httprequest.args.get('category_id')
        available   = request.httprequest.args.get('available')
        domain = []
        if category_id:
            domain.append(('category_id', '=', int(category_id)))
        if available is not None:
            domain.append(('available', '=', available == 'true'))
        items = request.env['restaurant.menu.item'].sudo().search(domain, order='category_id, name')
        result = []
        for i in items:
            result.append({
                'id':               i.id,
                'name':             i.name,
                'category':         i.category_id.name,
                'category_id':      i.category_id.id,
                'price':            i.price,
                'type':             i.type,
                'available':        i.available,
                'description':      i.description,
                'preparation_time': i.preparation_time,
            })
        return self._json_response(result)

    @http.route('/dineflow/api/menu-items', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_menu_item(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data)
            if not all([data.get('name'), data.get('category_id'), data.get('price')]):
                return self._json_response({'error': 'Thiếu name, category_id hoặc price'}, 400)
            item = request.env['restaurant.menu.item'].sudo().create({
                'name':             data.get('name'),
                'category_id':      int(data.get('category_id')),
                'price':            float(data.get('price')),
                'type':             data.get('type', 'food'),
                'description':      data.get('description', ''),
                'preparation_time': data.get('preparation_time', 10),
                'available':        data.get('available', True),
            })
            return self._json_response({'success': True, 'item_id': item.id})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/menu-items/<int:item_id>', type='http', auth='none',
                methods=['PUT'], csrf=False)
    def update_menu_item(self, item_id):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data)
            item = request.env['restaurant.menu.item'].sudo().browse(item_id)
            if not item.exists():
                return self._json_response({'error': 'Không tìm thấy món'}, 404)
            allowed = ['name', 'price', 'type', 'description', 'preparation_time', 'available', 'category_id']
            item.write({k: v for k, v in data.items() if k in allowed})
            return self._json_response({'success': True})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/menu-items/<int:item_id>', type='http', auth='none',
                methods=['DELETE'], csrf=False)
    def delete_menu_item(self, item_id):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            item = request.env['restaurant.menu.item'].sudo().browse(item_id)
            if not item.exists():
                return self._json_response({'error': 'Không tìm thấy món'}, 404)
            item.write({'available': False})
            return self._json_response({'success': True})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    # ══════════════════════════════════════════════════════════
    # BOOKINGS
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/bookings', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_bookings(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        status   = request.httprequest.args.get('status')
        table_id = request.httprequest.args.get('table_id')
        domain = []
        if status:
            domain.append(('status', '=', status))
        if table_id:
            domain.append(('table_id', '=', int(table_id)))
        bookings = request.env['restaurant.booking'].sudo().search(domain, order='date_start desc')
        result = []
        for b in bookings:
            result.append({
                'id':            b.id,
                'name':          b.name,
                'customer_name': b.customer_name,
                'phone':         b.phone,
                'email':         b.email,
                'table':         b.table_id.name,
                'table_id':      b.table_id.id,
                'date_start':    str(b.date_start),
                'date_end':      str(b.date_end),
                'guest_count':   b.guest_count,
                'status':        b.status,
                'note':          b.note,
                'deposit_paid':  b.deposit_paid,
            })
        return self._json_response(result)

    @http.route('/dineflow/api/bookings', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_booking(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data)
            required = ['customer_name', 'phone', 'table_id', 'date_start', 'date_end']
            if not all(data.get(f) for f in required):
                return self._json_response({'error': f'Thiếu: {required}'}, 400)
            booking = request.env['restaurant.booking'].sudo().create({
                'customer_name': data.get('customer_name'),
                'phone':         data.get('phone'),
                'email':         data.get('email', ''),
                'table_id':      int(data.get('table_id')),
                'date_start':    data.get('date_start'),
                'date_end':      data.get('date_end'),
                'guest_count':   data.get('guest_count', 2),
                'note':          data.get('note', ''),
                'deposit_paid':  data.get('deposit_paid', False),
            })
            return self._json_response({'success': True, 'booking_id': booking.id, 'name': booking.name})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    @http.route('/dineflow/api/bookings/<int:booking_id>/cancel', type='http', auth='none',
                methods=['POST'], csrf=False)
    def cancel_booking(self, booking_id):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        try:
            booking = request.env['restaurant.booking'].sudo().browse(booking_id)
            if not booking.exists():
                return self._json_response({'error': 'Không tìm thấy booking'}, 404)
            booking.action_cancel()
            return self._json_response({'success': True})
        except Exception as e:
            return self._json_response({'error': str(e)}, 500)

    # ══════════════════════════════════════════════════════════
    # EMPLOYEES
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/employees', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_employees(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        role = request.httprequest.args.get('role')
        domain = []
        if role:
            domain.append(('restaurant_role', '=', role))
        employees = request.env['hr.employee'].sudo().search(domain, order='name')
        result = []
        for e in employees:
            result.append({
                'id':              e.id,
                'name':            e.name,
                'restaurant_role': e.restaurant_role,
                'employee_code':   e.employee_code,
                'shift':           e.shift,
            })
        return self._json_response(result)

    # ══════════════════════════════════════════════════════════
    # REVENUE
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/revenue', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_revenue(self):
        if not self._check_api_key():
            return self._json_response({'error': 'Unauthorized'}, 401)
        records = request.env['restaurant.revenue.report'].sudo().search([])
        result = []
        for r in records:
            result.append({
                'date':        str(r.date),
                'revenue':     r.revenue,
                'order_count': r.order_count,
            })
        return self._json_response(result)
    
    