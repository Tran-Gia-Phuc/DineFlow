from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

# Số ngày nghỉ tối đa theo loại (có thể tuỳ chỉnh)
MAX_DAYS = {
    'annual': 12,
    'sick': 30,
    'personal': 5,
    'unpaid': 30,
}


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

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if not rec.date_from or not rec.date_to:
                continue
            if rec.date_to < rec.date_from:
                raise ValidationError('Ngày kết thúc phải từ ngày bắt đầu trở đi.')
            duration = (rec.date_to - rec.date_from).days + 1
            if duration > 30:
                raise ValidationError(
                    f'Một đơn nghỉ phép không được vượt quá 30 ngày '
                    f'(hiện tại: {duration} ngày).'
                )

    @api.constrains('date_from', 'date_to', 'leave_type', 'employee_id')
    def _check_annual_quota(self):
        """Kiểm tra tổng ngày nghỉ phép năm không vượt hạn mức."""
        for rec in self:
            if rec.leave_type != 'annual' or not rec.date_from or not rec.date_to:
                continue
            year = rec.date_from.year
            duration = (rec.date_to - rec.date_from).days + 1
            # Tổng ngày annual đã dùng trong năm (không tính đơn đang xét và đã từ chối)
            existing = self.search([
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('leave_type', '=', 'annual'),
                ('status', 'not in', ['refused']),
                ('date_from', '>=', date(year, 1, 1)),
                ('date_to', '<=', date(year, 12, 31)),
            ])
            used_days = sum(
                (r.date_to - r.date_from).days + 1 for r in existing
            )
            if used_days + duration > MAX_DAYS['annual']:
                raise ValidationError(
                    f'Vượt hạn mức nghỉ phép năm {year}. '
                    f'Đã dùng: {used_days} ngày, '
                    f'Đang xin: {duration} ngày, '
                    f'Hạn mức: {MAX_DAYS["annual"]} ngày.'
                )

    @api.constrains('date_from', 'date_to', 'employee_id', 'status')
    def _check_overlap(self):
        """Không cho phép 2 đơn nghỉ phép của cùng nhân viên bị trùng ngày."""
        for rec in self:
            if rec.status == 'refused':
                continue
            if not rec.date_from or not rec.date_to or not rec.employee_id:
                continue
            conflict = self.search([
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('status', 'not in', ['refused']),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ])
            if conflict:
                raise ValidationError(
                    f'{rec.employee_id.name} đã có đơn nghỉ trùng thời gian: '
                    f'{conflict[0].date_from.strftime("%d/%m/%Y")} - '
                    f'{conflict[0].date_to.strftime("%d/%m/%Y")} '
                    f'({dict(self._fields["leave_type"].selection).get(conflict[0].leave_type)}).'
                )

    @api.constrains('status', 'manager_id', 'approved_date')
    def _check_approval_fields(self):
        """Khi duyệt phải có người duyệt và ngày duyệt."""
        for rec in self:
            if rec.status == 'approved':
                if not rec.manager_id:
                    raise ValidationError('Đơn đã duyệt phải có thông tin người duyệt.')
                if not rec.approved_date:
                    raise ValidationError('Đơn đã duyệt phải có ngày duyệt.')

    def action_confirm(self):
        for rec in self:
            if rec.status != 'draft':
                raise ValidationError('Chỉ đơn ở trạng thái Nháp mới có thể gửi duyệt.')
            rec.status = 'confirmed'

    def action_approve(self):
        for rec in self:
            if rec.status != 'confirmed':
                raise ValidationError('Chỉ đơn đã gửi mới có thể duyệt.')
            rec.write({
                'status': 'approved',
                'approved_date': fields.Date.today(),
            })

    def action_refuse(self):
        for rec in self:
            if rec.status not in ('confirmed', 'approved'):
                raise ValidationError('Chỉ có thể từ chối đơn đã gửi hoặc đã duyệt.')
            rec.status = 'refused'