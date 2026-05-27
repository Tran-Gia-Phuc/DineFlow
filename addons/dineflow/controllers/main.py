import json
import datetime
from collections import defaultdict
from odoo import http, fields
from odoo.http import request


class DineFlowAPI(http.Controller):

    # ══════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════
    def _check_api_key(self):
        api_key = request.httprequest.headers.get('X-API-Key')
        return api_key == 'dineflow-secret-2024'

    def _json_response(self, data, status=200):
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status
        )

    def _ok(self, data=None, meta=None, summary=None):
        body = {'success': True, 'data': data if data is not None else []}
        if meta:
            body['meta'] = meta
        if summary:
            body['summary'] = summary
        return self._json_response(body)

    def _err(self, code, message, status=400):
        return self._json_response(
            {'success': False, 'error_code': code, 'message': message},
            status=status
        )

    def _auth(self):
        if not self._check_api_key():
            return self._err('UNAUTHORIZED', 'API key không hợp lệ', 401)
        return None

    def _paginate(self, domain, model_name, order, page, page_size):
        Model   = request.env[model_name].sudo()
        total   = Model.search_count(domain)
        offset  = (page - 1) * page_size
        records = Model.search(domain, order=order, limit=page_size, offset=offset)
        meta = {
            'page':        page,
            'page_size':   page_size,
            'total_count': total,
            'has_more':    (offset + page_size) < total,
        }
        return records, meta

    def _get_sort(self, allowed_fields, default, field_param='sort_by', order_param='sort_order'):
        sort_by    = request.httprequest.args.get(field_param, default)
        sort_order = request.httprequest.args.get(order_param, 'desc').lower()
        if sort_by not in allowed_fields:
            sort_by = default
        if sort_order not in ('asc', 'desc'):
            sort_order = 'desc'
        return f'{sort_by} {sort_order}'

    def _get_page(self):
        try:
            page      = max(1, int(request.httprequest.args.get('page', 1)))
            page_size = min(100, max(1, int(request.httprequest.args.get('page_size', 20))))
        except (ValueError, TypeError):
            page, page_size = 1, 20
        return page, page_size

    def _filter_fields(self, record_dict: dict, fields_param: str) -> dict:
        """
        ?fields=name,shift,status → chỉ trả đúng các field đó.
        Không truyền fields → trả hết (backward compatible).
        """
        if not fields_param:
            return record_dict
        allowed = {f.strip() for f in fields_param.split(',')}
        return {k: v for k, v in record_dict.items() if k in allowed}

    # ══════════════════════════════════════════════════════════
    # EMPLOYEES
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/employees', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_employees(self):
        err = self._auth()
        if err:
            return err

        role         = request.httprequest.args.get('role')
        name         = request.httprequest.args.get('name')
        shift        = request.httprequest.args.get('shift')
        code         = request.httprequest.args.get('code')
        fields_param = request.httprequest.args.get('fields')  # MỚI

        domain = []
        if role:
            domain.append(('restaurant_role', '=', role))
        if name:
            domain.append(('name', 'ilike', name))
        if shift:
            domain.append(('shift', '=', shift))
        if code:
            domain.append(('employee_code', '=', code))

        order      = self._get_sort({'name', 'restaurant_role', 'shift'}, 'name')
        page, size = self._get_page()
        employees, meta = self._paginate(domain, 'hr.employee', order, page, size)

        result = []
        for e in employees:
            result.append(self._filter_fields({  # MỚI
                'id':    e.id,
                'name':  e.name,
                'role':  e.restaurant_role,
                'code':  e.employee_code,
                'shift': e.shift,
            }, fields_param))
        return self._ok(result, meta=meta)

    # ══════════════════════════════════════════════════════════
    # LEAVE
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/leave', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_leaves(self):
        err = self._auth()
        if err:
            return err

        employee_id   = request.httprequest.args.get('employee_id')
        employee_name = request.httprequest.args.get('employee_name')
        status        = request.httprequest.args.get('status')
        leave_type    = request.httprequest.args.get('leave_type')
        date_from     = request.httprequest.args.get('date_from')
        date_to       = request.httprequest.args.get('date_to')
        month         = request.httprequest.args.get('month')
        year          = request.httprequest.args.get('year')
        shift         = request.httprequest.args.get('shift')
        role          = request.httprequest.args.get('role')
        with_summary  = request.httprequest.args.get('with_summary')
        summary_only  = request.httprequest.args.get('summary_only')   # MỚI
        fields_param  = request.httprequest.args.get('fields')          # MỚI

        domain = []
        if employee_id:
            domain.append(('employee_id', '=', int(employee_id)))
        if employee_name:
            domain.append(('employee_id.name', 'ilike', employee_name))
        if status:
            domain.append(('status', '=', status))
        if leave_type:
            domain.append(('leave_type', '=', leave_type))
        if date_from:
            domain.append(('date_from', '>=', date_from))
        if date_to:
            domain.append(('date_to', '<=', date_to))
        if month and year:
            domain.append(('date_from', '>=', f'{year}-{month.zfill(2)}-01'))
            domain.append(('date_from', '<=', f'{year}-{month.zfill(2)}-31'))
        elif month:
            y = datetime.date.today().year
            domain.append(('date_from', '>=', f'{y}-{month.zfill(2)}-01'))
            domain.append(('date_from', '<=', f'{y}-{month.zfill(2)}-31'))
        if shift or role:
            emp_domain = []
            if shift:
                emp_domain.append(('shift', '=', shift))
            if role:
                emp_domain.append(('restaurant_role', '=', role))
            emp_ids = request.env['hr.employee'].sudo().search(emp_domain).ids
            domain.append(('employee_id', 'in', emp_ids))

        order      = self._get_sort({'date_from', 'date_to', 'employee_id'}, 'date_from')
        page, size = self._get_page()
        leaves, meta = self._paginate(domain, 'restaurant.leave.request', order, page, size)

        result = []
        for l in leaves:
            result.append(self._filter_fields({  # MỚI
                'id':            l.id,
                'employee':      l.employee_id.name,
                'employee_id':   l.employee_id.id,
                'role':          l.employee_id.restaurant_role,
                'shift':         l.employee_id.shift,
                'date_from':     str(l.date_from),
                'date_to':       str(l.date_to),
                'duration_days': (l.date_to - l.date_from).days + 1,
                'reason':        l.reason,
                'leave_type':    l.leave_type,
                'status':        l.status,
                'manager':       l.manager_id.name if l.manager_id else None,
                'approved_date': str(l.approved_date) if l.approved_date else None,
            }, fields_param))

        summary = None
        if with_summary == 'true':
            all_leaves = request.env['restaurant.leave.request'].sudo().search(domain)
            agg = defaultdict(lambda: {'employee': '', 'employee_id': 0, 'total_days': 0, 'count': 0})
            for l in all_leaves:
                eid = l.employee_id.id
                agg[eid]['employee']    = l.employee_id.name
                agg[eid]['employee_id'] = eid
                agg[eid]['total_days'] += (l.date_to - l.date_from).days + 1
                agg[eid]['count']      += 1
            summary = {'by_employee': sorted(agg.values(), key=lambda x: x['total_days'], reverse=True)}

        # MỚI: summary_only — không trả records, chỉ trả summary
        if summary_only == 'true' and summary:
            return self._ok([], summary=summary)

        return self._ok(result, meta=meta, summary=summary)

    @http.route('/dineflow/api/leave', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_leave(self):
        err = self._auth()
        if err:
            return err
        try:
            data        = json.loads(request.httprequest.data)
            employee_id = data.get('employee_id')
            date_from   = data.get('date_from')
            date_to     = data.get('date_to')
            reason      = data.get('reason', '')
            leave_type  = data.get('leave_type', 'annual')
            if not all([employee_id, date_from, date_to]):
                return self._err('MISSING_FIELDS', 'Thiếu employee_id, date_from hoặc date_to')
            leave = request.env['restaurant.leave.request'].sudo().create({
                'employee_id':   int(employee_id),
                'date_from':     date_from,
                'date_to':       date_to,
                'reason':        reason,
                'leave_type':    leave_type,
                'created_by_ai': True,
            })
            return self._ok({'leave_id': leave.id})
        except Exception as e:
            return self._err('CREATE_FAILED', str(e), 500)

    @http.route('/dineflow/api/leave/<int:leave_id>/approve', type='http', auth='none',
                methods=['POST'], csrf=False)
    def approve_leave(self, leave_id):
        err = self._auth()
        if err:
            return err
        try:
            data       = json.loads(request.httprequest.data or '{}')
            manager_id = data.get('manager_id')
            leave      = request.env['restaurant.leave.request'].sudo().browse(leave_id)
            if not leave.exists():
                return self._err('NOT_FOUND', 'Không tìm thấy đơn nghỉ', 404)
            leave.sudo().write({
                'status':        'approved',
                'manager_id':    int(manager_id) if manager_id else None,
                'approved_date': fields.Date.today(),
            })
            return self._ok({'leave_id': leave_id})
        except Exception as e:
            return self._err('APPROVE_FAILED', str(e), 500)

    @http.route('/dineflow/api/leave/<int:leave_id>/refuse', type='http', auth='none',
                methods=['POST'], csrf=False)
    def refuse_leave(self, leave_id):
        err = self._auth()
        if err:
            return err
        try:
            leave = request.env['restaurant.leave.request'].sudo().browse(leave_id)
            if not leave.exists():
                return self._err('NOT_FOUND', 'Không tìm thấy đơn nghỉ', 404)
            leave.sudo().write({'status': 'refused'})
            return self._ok({'leave_id': leave_id})
        except Exception as e:
            return self._err('REFUSE_FAILED', str(e), 500)

    # ══════════════════════════════════════════════════════════
    # EMPLOYEES ON LEAVE TODAY
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/employees/on-leave-today', type='http', auth='none',
                methods=['GET'], csrf=False)
    def employees_on_leave_today(self):
        err = self._auth()
        if err:
            return err

        today        = str(datetime.date.today())
        shift        = request.httprequest.args.get('shift')
        role         = request.httprequest.args.get('role')
        fields_param = request.httprequest.args.get('fields')  # MỚI

        leave_domain = [
            ('status', 'in', ['confirmed', 'approved']),
            ('date_from', '<=', today),
            ('date_to',   '>=', today),
        ]
        leaves = request.env['restaurant.leave.request'].sudo().search(leave_domain)

        result = []
        for l in leaves:
            emp = l.employee_id
            if shift and emp.shift != shift:
                continue
            if role and emp.restaurant_role != role:
                continue
            result.append(self._filter_fields({  # MỚI
                'employee_id':   emp.id,
                'employee_name': emp.name,
                'shift':         emp.shift,
                'role':          emp.restaurant_role,
                'leave_type':    l.leave_type,
                'date_from':     str(l.date_from),
                'date_to':       str(l.date_to),
                'reason':        l.reason,
            }, fields_param))
        return self._ok(result)

    # ══════════════════════════════════════════════════════════
    # TABLES
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/tables', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_tables(self):
        err = self._auth()
        if err:
            return err

        status           = request.httprequest.args.get('status')
        floor            = request.httprequest.args.get('floor')
        name             = request.httprequest.args.get('name')
        min_capacity     = request.httprequest.args.get('min_capacity')
        max_capacity     = request.httprequest.args.get('max_capacity')
        available_at     = request.httprequest.args.get('available_at')
        available_at_end = request.httprequest.args.get('available_at_end')
        fields_param     = request.httprequest.args.get('fields')  # MỚI

        domain = []
        if status:
            domain.append(('status', '=', status))
        if floor:
            domain.append(('floor', '=', floor))
        if name:
            domain.append(('name', 'ilike', name))
        if min_capacity:
            domain.append(('capacity', '>=', int(min_capacity)))
        if max_capacity:
            domain.append(('capacity', '<=', int(max_capacity)))

        order      = self._get_sort({'name', 'capacity', 'floor', 'status'}, 'floor')
        page, size = self._get_page()
        tables, meta = self._paginate(domain, 'restaurant.table', order, page, size)

        if available_at:
            end        = available_at_end or available_at
            booked_ids = request.env['restaurant.booking'].sudo().search([
                ('status', 'in', ['pending', 'confirmed']),
                ('date_start', '<', end),
                ('date_end',   '>', available_at),
            ]).mapped('table_id.id')
            tables = tables.filtered(lambda t: t.id not in booked_ids)

        result = []
        for t in tables:
            result.append(self._filter_fields({  # MỚI
                'id':           t.id,
                'name':         t.name,
                'capacity':     t.capacity,
                'min_capacity': t.min_capacity,
                'status':       t.status,
                'floor':        t.floor,
                'note':         t.note,
                'active':       t.active,
            }, fields_param))
        return self._ok(result, meta=meta)

    @http.route('/dineflow/api/tables', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_table(self):
        err = self._auth()
        if err:
            return err
        try:
            data = json.loads(request.httprequest.data)
            if not data.get('name'):
                return self._err('MISSING_FIELDS', 'Thiếu tên bàn')
            table = request.env['restaurant.table'].sudo().create({
                'name':         data.get('name'),
                'capacity':     data.get('capacity', 4),
                'min_capacity': data.get('min_capacity', 1),
                'floor':        data.get('floor', 'A'),
                'note':         data.get('note', ''),
            })
            return self._ok({'table_id': table.id})
        except Exception as e:
            return self._err('CREATE_FAILED', str(e), 500)

    @http.route('/dineflow/api/tables/<int:table_id>', type='http', auth='none',
                methods=['PUT'], csrf=False)
    def update_table(self, table_id):
        err = self._auth()
        if err:
            return err
        try:
            data  = json.loads(request.httprequest.data)
            table = request.env['restaurant.table'].sudo().browse(table_id)
            if not table.exists():
                return self._err('NOT_FOUND', 'Không tìm thấy bàn', 404)
            table.write({k: v for k, v in data.items()
                         if k in ['name', 'capacity', 'min_capacity', 'floor', 'note', 'status', 'active']})
            return self._ok({'table_id': table_id})
        except Exception as e:
            return self._err('UPDATE_FAILED', str(e), 500)

    @http.route('/dineflow/api/tables/<int:table_id>', type='http', auth='none',
                methods=['DELETE'], csrf=False)
    def delete_table(self, table_id):
        err = self._auth()
        if err:
            return err
        try:
            table = request.env['restaurant.table'].sudo().browse(table_id)
            if not table.exists():
                return self._err('NOT_FOUND', 'Không tìm thấy bàn', 404)
            table.write({'active': False})
            return self._ok({'table_id': table_id})
        except Exception as e:
            return self._err('DELETE_FAILED', str(e), 500)

    # ══════════════════════════════════════════════════════════
    # CATEGORIES
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/categories', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_categories(self):
        err = self._auth()
        if err:
            return err

        fields_param = request.httprequest.args.get('fields')  # MỚI
        domain       = []
        order        = self._get_sort({'name', 'sequence'}, 'sequence', order_param='sort_order')
        page, size   = self._get_page()
        cats, meta   = self._paginate(domain, 'restaurant.category', order, page, size)

        result = []
        for c in cats:
            result.append(self._filter_fields({  # MỚI
                'id':        c.id,
                'name':      c.name,
                'sequence':  c.sequence,
                'active':    c.active,
                'parent_id': c.parent_id.id if c.parent_id else None,
                'parent':    c.parent_id.name if c.parent_id else None,
            }, fields_param))
        return self._ok(result, meta=meta)

    @http.route('/dineflow/api/categories', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_category(self):
        err = self._auth()
        if err:
            return err
        try:
            data = json.loads(request.httprequest.data)
            if not data.get('name'):
                return self._err('MISSING_FIELDS', 'Thiếu tên danh mục')
            cat = request.env['restaurant.category'].sudo().create({
                'name':      data.get('name'),
                'sequence':  data.get('sequence', 10),
                'parent_id': data.get('parent_id'),
            })
            return self._ok({'category_id': cat.id})
        except Exception as e:
            return self._err('CREATE_FAILED', str(e), 500)

    @http.route('/dineflow/api/categories/<int:cat_id>', type='http', auth='none',
                methods=['PUT'], csrf=False)
    def update_category(self, cat_id):
        err = self._auth()
        if err:
            return err
        try:
            data = json.loads(request.httprequest.data)
            cat  = request.env['restaurant.category'].sudo().browse(cat_id)
            if not cat.exists():
                return self._err('NOT_FOUND', 'Không tìm thấy danh mục', 404)
            cat.write({k: v for k, v in data.items()
                       if k in ['name', 'sequence', 'active', 'parent_id']})
            return self._ok({'category_id': cat_id})
        except Exception as e:
            return self._err('UPDATE_FAILED', str(e), 500)

    # ══════════════════════════════════════════════════════════
    # MENU ITEMS
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/menu-items', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_menu_items(self):
        err = self._auth()
        if err:
            return err

        category_id   = request.httprequest.args.get('category_id')
        category_name = request.httprequest.args.get('category_name')
        available     = request.httprequest.args.get('available')
        name          = request.httprequest.args.get('name')
        item_type     = request.httprequest.args.get('type')
        max_price     = request.httprequest.args.get('max_price')
        min_price     = request.httprequest.args.get('min_price')
        max_prep_time = request.httprequest.args.get('max_prep_time')
        fields_param  = request.httprequest.args.get('fields')  # MỚI

        domain = []
        if category_id:
            domain.append(('category_id', '=', int(category_id)))
        if category_name:
            domain.append(('category_id.name', 'ilike', category_name))
        if available is not None:
            domain.append(('available', '=', available == 'true'))
        if name:
            domain.append(('name', 'ilike', name))
        if item_type:
            domain.append(('type', '=', item_type))
        if max_price:
            domain.append(('price', '<=', float(max_price)))
        if min_price:
            domain.append(('price', '>=', float(min_price)))
        if max_prep_time:
            domain.append(('preparation_time', '<=', int(max_prep_time)))

        order      = self._get_sort({'name', 'price', 'preparation_time', 'category_id'}, 'name')
        page, size = self._get_page()
        items, meta = self._paginate(domain, 'restaurant.menu.item', order, page, size)

        result = []
        for i in items:
            result.append(self._filter_fields({  # MỚI
                'id':               i.id,
                'name':             i.name,
                'category':         i.category_id.name,
                'category_id':      i.category_id.id,
                'price':            i.price,
                'type':             i.type,
                'available':        i.available,
                'description':      i.description,
                'preparation_time': i.preparation_time,
            }, fields_param))
        return self._ok(result, meta=meta)

    @http.route('/dineflow/api/menu-items', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_menu_item(self):
        err = self._auth()
        if err:
            return err
        try:
            data = json.loads(request.httprequest.data)
            if not all([data.get('name'), data.get('category_id'), data.get('price')]):
                return self._err('MISSING_FIELDS', 'Thiếu name, category_id hoặc price')
            item = request.env['restaurant.menu.item'].sudo().create({
                'name':             data.get('name'),
                'category_id':      int(data.get('category_id')),
                'price':            float(data.get('price')),
                'type':             data.get('type', 'food'),
                'description':      data.get('description', ''),
                'preparation_time': data.get('preparation_time', 10),
                'available':        data.get('available', True),
            })
            return self._ok({'item_id': item.id})
        except Exception as e:
            return self._err('CREATE_FAILED', str(e), 500)

    @http.route('/dineflow/api/menu-items/<int:item_id>', type='http', auth='none',
                methods=['PUT'], csrf=False)
    def update_menu_item(self, item_id):
        err = self._auth()
        if err:
            return err
        try:
            data = json.loads(request.httprequest.data)
            item = request.env['restaurant.menu.item'].sudo().browse(item_id)
            if not item.exists():
                return self._err('NOT_FOUND', 'Không tìm thấy món', 404)
            allowed = ['name', 'price', 'type', 'description', 'preparation_time', 'available', 'category_id']
            item.write({k: v for k, v in data.items() if k in allowed})
            return self._ok({'item_id': item_id})
        except Exception as e:
            return self._err('UPDATE_FAILED', str(e), 500)

    @http.route('/dineflow/api/menu-items/<int:item_id>', type='http', auth='none',
                methods=['DELETE'], csrf=False)
    def delete_menu_item(self, item_id):
        err = self._auth()
        if err:
            return err
        try:
            item = request.env['restaurant.menu.item'].sudo().browse(item_id)
            if not item.exists():
                return self._err('NOT_FOUND', 'Không tìm thấy món', 404)
            item.write({'available': False})
            return self._ok({'item_id': item_id})
        except Exception as e:
            return self._err('DELETE_FAILED', str(e), 500)

    # ══════════════════════════════════════════════════════════
    # BOOKINGS
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/bookings', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_bookings(self):
        err = self._auth()
        if err:
            return err

        status           = request.httprequest.args.get('status')
        table_id         = request.httprequest.args.get('table_id')
        customer_name    = request.httprequest.args.get('customer_name')
        date             = request.httprequest.args.get('date')
        date_from        = request.httprequest.args.get('date_from')
        date_to          = request.httprequest.args.get('date_to')
        guest_count      = request.httprequest.args.get('guest_count')
        hour_from        = request.httprequest.args.get('hour_from')
        hour_to          = request.httprequest.args.get('hour_to')
        floor            = request.httprequest.args.get('floor')
        shift            = request.httprequest.args.get('shift')
        upcoming_minutes = request.httprequest.args.get('upcoming_minutes')
        fields_param     = request.httprequest.args.get('fields')  # MỚI

        domain = []
        if status:
            domain.append(('status', '=', status))
        if table_id:
            domain.append(('table_id', '=', int(table_id)))
        if customer_name:
            domain.append(('customer_name', 'ilike', customer_name))
        if date:
            domain.append(('date_start', '>=', f'{date} 00:00:00'))
            domain.append(('date_start', '<=', f'{date} 23:59:59'))
        if date_from:
            domain.append(('date_start', '>=', f'{date_from} 00:00:00'))
        if date_to:
            domain.append(('date_start', '<=', f'{date_to} 23:59:59'))
        if guest_count:
            domain.append(('guest_count', '>=', int(guest_count)))
        if hour_from and date:
            domain.append(('date_start', '>=', f'{date} {hour_from.zfill(2)}:00:00'))
        if hour_to and date:
            domain.append(('date_start', '<=', f'{date} {hour_to.zfill(2)}:59:59'))
        if floor:
            domain.append(('table_id.floor', '=', floor))

        SHIFT_HOURS = {
            'morning':   ('06', '11'),
            'afternoon': ('11', '17'),
            'evening':   ('17', '23'),
        }
        if shift and shift in SHIFT_HOURS:
            h_from, h_to = SHIFT_HOURS[shift]
            target_date  = date or str(datetime.date.today())
            domain.append(('date_start', '>=', f'{target_date} {h_from}:00:00'))
            domain.append(('date_start', '<=', f'{target_date} {h_to}:59:59'))

        if upcoming_minutes:
            now    = fields.Datetime.now()
            future = now + datetime.timedelta(minutes=int(upcoming_minutes))
            domain.append(('date_start', '>=', str(now)))
            domain.append(('date_start', '<=', str(future)))
            if not status:
                domain.append(('status', 'in', ['pending', 'confirmed']))

        order      = self._get_sort({'date_start', 'guest_count', 'customer_name', 'status'}, 'date_start')
        page, size = self._get_page()
        bookings, meta = self._paginate(domain, 'restaurant.booking', order, page, size)

        result = []
        for b in bookings:
            result.append(self._filter_fields({  # MỚI
                'id':            b.id,
                'name':          b.name,
                'customer_name': b.customer_name,
                'phone':         b.phone,
                'email':         b.email,
                'table':         b.table_id.name,
                'table_id':      b.table_id.id,
                'floor':         b.table_id.floor,
                'date_start':    str(b.date_start),
                'date_end':      str(b.date_end),
                'guest_count':   b.guest_count,
                'status':        b.status,
                'note':          b.note,
                'deposit_paid':  b.deposit_paid,
            }, fields_param))
        return self._ok(result, meta=meta)

    @http.route('/dineflow/api/bookings', type='http', auth='none',
                methods=['POST'], csrf=False)
    def create_booking(self):
        err = self._auth()
        if err:
            return err
        try:
            data     = json.loads(request.httprequest.data)
            required = ['customer_name', 'phone', 'table_id', 'date_start', 'date_end']
            if not all(data.get(f) for f in required):
                return self._err('MISSING_FIELDS', f'Thiếu một trong: {required}')

            conflict = request.env['restaurant.booking'].sudo().search([
                ('table_id', '=',  int(data['table_id'])),
                ('status',   'in', ['pending', 'confirmed']),
                ('date_start', '<', data['date_end']),
                ('date_end',   '>', data['date_start']),
            ], limit=1)
            if conflict:
                return self._err(
                    'BOOKING_CONFLICT',
                    f"Bàn đã có booking [{conflict.name}] "
                    f"từ {conflict.date_start.strftime('%H:%M')} "
                    f"đến {conflict.date_end.strftime('%H:%M %d/%m/%Y')}",
                    409
                )

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
            return self._ok({'booking_id': booking.id, 'name': booking.name})
        except Exception as e:
            return self._err('CREATE_FAILED', str(e), 500)

    @http.route('/dineflow/api/bookings/<int:booking_id>/cancel', type='http', auth='none',
                methods=['POST'], csrf=False)
    def cancel_booking(self, booking_id):
        err = self._auth()
        if err:
            return err
        try:
            booking = request.env['restaurant.booking'].sudo().browse(booking_id)
            if not booking.exists():
                return self._err('NOT_FOUND', 'Không tìm thấy booking', 404)
            booking.action_cancel()
            return self._ok({'booking_id': booking_id})
        except Exception as e:
            return self._err('CANCEL_FAILED', str(e), 500)

    # ══════════════════════════════════════════════════════════
    # REVENUE
    # ══════════════════════════════════════════════════════════
    @http.route('/dineflow/api/revenue', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_revenue(self):
        err = self._auth()
        if err:
            return err

        date_from    = request.httprequest.args.get('date_from')
        date_to      = request.httprequest.args.get('date_to')
        month        = request.httprequest.args.get('month')
        year         = request.httprequest.args.get('year')
        with_summary = request.httprequest.args.get('with_summary')
        summary_only = request.httprequest.args.get('summary_only')  # MỚI

        domain = []
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if month and year:
            domain.append(('date', '>=', f'{year}-{month.zfill(2)}-01'))
            domain.append(('date', '<=', f'{year}-{month.zfill(2)}-31'))
        elif month:
            y = datetime.date.today().year
            domain.append(('date', '>=', f'{y}-{month.zfill(2)}-01'))
            domain.append(('date', '<=', f'{y}-{month.zfill(2)}-31'))

        order = self._get_sort({'date', 'total_amount', 'payment_method'}, 'date', order_param='sort_order')
        page, size = self._get_page()
        records, meta = self._paginate(domain, 'restaurant.revenue.report', order, page, size)

        result = []
        for r in records:
            result.append({
                'date':           str(r.date),
                'total_amount':   r.total_amount,
                'payment_method': r.payment_method,
                'table':          r.table_id.name if r.table_id else None,
            })
        summary = None
        if with_summary == 'true' or summary_only == 'true':  # MỚI: summary_only cũng trigger build summary
            all_records = request.env['restaurant.revenue.report'].sudo().search(
                domain, order='date asc'
            )
            revenues = [r.total_amount for r in all_records]
            if revenues:
                max_r  = max(all_records, key=lambda r: r.total_amount)
                min_r  = min(all_records, key=lambda r: r.total_amount)
                wd_rev = [r.total_amount for r in all_records
                        if r.date.weekday() < 5]
                we_rev = [r.total_amount for r in all_records
                        if r.date.weekday() >= 5]
                mid    = len(revenues) // 2
                f_avg  = sum(revenues[:mid]) / mid if mid else 0
                s_avg  = sum(revenues[mid:]) / (len(revenues) - mid) if mid else 0

                summary = {
                    'total_revenue':      sum(revenues),
                    'total_days':         len(revenues),
                    'avg_daily_revenue':  round(sum(revenues) / len(revenues), 0),
                    'max_revenue_date': str(max_r.date.date()),
                    'max_revenue': max_r.total_amount,
                    'min_revenue_date': str(min_r.date.date()),
                    'min_revenue': min_r.total_amount,
                    'avg_weekday':        round(sum(wd_rev) / len(wd_rev), 0) if wd_rev else 0,
                    'avg_weekend':        round(sum(we_rev) / len(we_rev), 0) if we_rev else 0,
                    'weekend_vs_weekday': ( 
                        'weekend_higher'
                        if we_rev and wd_rev and
                           sum(we_rev) / len(we_rev) > sum(wd_rev) / len(wd_rev)
                        else 'weekday_higher'
                    ),
                    'trend':     'increasing' if s_avg > f_avg else 'decreasing',
                    'trend_pct': round((s_avg - f_avg) / f_avg * 100, 1) if f_avg else 0,
                }

        # MỚI: summary_only — bỏ qua records array, chỉ trả summary
        if summary_only == 'true' and summary:
            return self._ok([], summary=summary)

        return self._ok(result, meta=meta, summary=summary)