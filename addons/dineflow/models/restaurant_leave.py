from odoo import models, fields


class RestaurantLeaveRequest(models.Model):
    _name = 'restaurant.leave.request'
    _description = 'Xin nghỉ phép'
    _order = 'date_from desc'

    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    date_from = fields.Date(string='Từ ngày', required=True)
    date_to = fields.Date(string='Đến ngày', required=True)
    reason = fields.Text(string='Lý do')
    leave_type = fields.Selection([
        ('annual', 'Nghỉ phép năm'),
        ('sick', 'Nghỉ ốm'),
        ('personal', 'Việc cá nhân'),
        ('unpaid', 'Nghỉ không lương'),
    ], string='Loại nghỉ phép', default='annual')
    status = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã gửi'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Từ chối'),
    ], string='Trạng thái', default='draft')
    manager_id = fields.Many2one('hr.employee', string='Người duyệt')
    approved_date = fields.Date(string='Ngày duyệt')
    created_by_ai = fields.Boolean(string='Tạo bởi AI', default=False)