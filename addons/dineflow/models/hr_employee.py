from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    restaurant_role = fields.Selection([
        ('manager', 'Quản lý'),
        ('chef', 'Đầu bếp'),
        ('waiter', 'Phục vụ'),
        ('cashier', 'Thu ngân'),
    ], string='Vai trò nhà hàng')
    employee_code = fields.Char(string='Mã nhân viên')
    shift = fields.Selection([
        ('morning', 'Ca sáng'),
        ('afternoon', 'Ca chiều'),
        ('evening', 'Ca tối'),
    ], string='Ca làm')
    pin_code = fields.Char(string='Mã PIN', size=6)
    leave_request_ids = fields.One2many('restaurant.leave.request', 'employee_id', string='Lịch nghỉ phép') 