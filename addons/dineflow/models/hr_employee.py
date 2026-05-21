from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
    leave_request_ids = fields.One2many(
        'restaurant.leave.request', 'employee_id', string='Lịch nghỉ phép'
    )

    @api.constrains('pin_code')
    def _check_pin_code(self):
        for rec in self:
            if not rec.pin_code:
                continue
            if not rec.pin_code.isdigit():
                raise ValidationError('Mã PIN chỉ được chứa chữ số (0–9).')
            if len(rec.pin_code) != 6:
                raise ValidationError('Mã PIN phải có đúng 6 chữ số.')
            # Unique PIN trong toàn bộ nhân viên nhà hàng
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('pin_code', '=', rec.pin_code),
                ('pin_code', '!=', False),
            ])
            if duplicate:
                raise ValidationError(
                    f'Mã PIN {rec.pin_code} đã được dùng bởi nhân viên khác.'
                )

    @api.constrains('employee_code')
    def _check_employee_code(self):
        for rec in self:
            if not rec.employee_code:
                continue
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('employee_code', '=', rec.employee_code),
            ])
            if duplicate:
                raise ValidationError(
                    f'Mã nhân viên "{rec.employee_code}" đã tồn tại.'
                )