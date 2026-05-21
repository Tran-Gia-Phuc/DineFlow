import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError

# Thời gian đặt bàn tối thiểu phải cách hiện tại (phút)
MIN_ADVANCE_MINUTES = 30


class RestaurantBooking(models.Model):
    _name = 'restaurant.booking'
    _description = 'Đặt bàn'
    _order = 'date_start desc'

    name = fields.Char(string='Mã đặt bàn', readonly=True, default='New')
    customer_name = fields.Char(string='Tên khách', required=True)
    phone = fields.Char(string='Số điện thoại', required=True)
    email = fields.Char(string='Email')
    table_id = fields.Many2one('restaurant.table', string='Bàn', required=True)
    date_start = fields.Datetime(string='Thời gian đến', required=True)
    date_end = fields.Datetime(string='Thời gian kết thúc', required=True)
    date = fields.Datetime(string='Thời gian', compute='_compute_date', store=True)
    guest_count = fields.Integer(string='Số khách', default=2)
    note = fields.Text(string='Ghi chú')
    deposit_paid = fields.Boolean(string='Đã đặt cọc', default=False)
    confirmed_by = fields.Many2one('hr.employee', string='Xác nhận bởi')
    status = fields.Selection([
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('cancelled', 'Đã huỷ'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='pending', required=True)

    @api.depends('date_start')
    def _compute_date(self):
        for rec in self:
            rec.date = rec.date_start

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.booking') or 'New'
        result = super().create(vals)
        result._sync_table_status()
        return result

    def write(self, vals):
        result = super().write(vals)
        if 'status' in vals or 'table_id' in vals or 'date_start' in vals or 'date_end' in vals:
            self._sync_table_status()
        return result

    def _sync_table_status(self):
        """
        Đồng bộ trạng thái bàn dựa trên booking hiện tại.
        - Có booking confirmed/pending đang diễn ra → occupied
        - Có booking confirmed/pending sắp tới      → reserved
        - Không có gì                                → available
        Chỉ thay đổi nếu bàn không đang có order open.
        """
        now = fields.Datetime.now()
        tables = self.mapped('table_id')
        for table in tables:
            # Không ghi đè nếu bàn đang có order open
            open_order = self.env['restaurant.order'].search([
                ('table_id', '=', table.id),
                ('status', '=', 'open'),
            ], limit=1)
            if open_order:
                continue

            current = self.env['restaurant.booking'].search([
                ('table_id', '=', table.id),
                ('status', 'in', ['confirmed', 'pending']),
                ('date_start', '<=', now),
                ('date_end', '>=', now),
            ], limit=1)

            if current:
                table.status = 'occupied'
                continue

            upcoming = self.env['restaurant.booking'].search([
                ('table_id', '=', table.id),
                ('status', 'in', ['confirmed', 'pending']),
                ('date_start', '>', now),
            ], limit=1)

            table.status = 'reserved' if upcoming else 'available'

    def action_confirm(self):
        self.status = 'confirmed'
        self._sync_table_status()

    def action_cancel(self):
        self.status = 'cancelled'
        self._sync_table_status()

    def action_done(self):
        self.status = 'done'
        self._sync_table_status()

    @api.constrains('customer_name')
    def _check_customer_name(self):
        for rec in self:
            if not rec.customer_name or not rec.customer_name.strip():
                raise ValidationError('Tên khách không được để trống.')
            if len(rec.customer_name.strip()) < 2:
                raise ValidationError('Tên khách phải có ít nhất 2 ký tự.')

    @api.constrains('phone')
    def _check_phone(self):
        for rec in self:
            if not rec.phone:
                continue
            phone_clean = re.sub(r'[\s\-\.]', '', rec.phone)
            if not re.match(r'^(\+84|84|0)\d{9,10}$', phone_clean):
                raise ValidationError(
                    f'Số điện thoại "{rec.phone}" không hợp lệ. '
                    'Vui lòng nhập đúng định dạng Việt Nam (VD: 0912345678).'
                )

    @api.constrains('email')
    def _check_email(self):
        for rec in self:
            if not rec.email:
                continue
            if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', rec.email):
                raise ValidationError(f'Email "{rec.email}" không đúng định dạng.')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if not rec.date_start or not rec.date_end:
                continue
            if rec.date_end <= rec.date_start:
                raise ValidationError('Thời gian kết thúc phải sau thời gian đến.')
            duration = (rec.date_end - rec.date_start).total_seconds() / 3600
            if duration > 8:
                raise ValidationError('Thời gian đặt bàn không được vượt quá 8 tiếng.')
            if duration < 0.5:
                raise ValidationError('Thời gian đặt bàn tối thiểu là 30 phút.')

    @api.constrains('date_start')
    def _check_advance_time(self):
        """Booking phải cách thời điểm hiện tại ít nhất MIN_ADVANCE_MINUTES phút."""
        from datetime import timedelta
        for rec in self:
            if not rec.date_start:
                continue
            # Bỏ qua khi chỉnh sửa booking đã tồn tại (chỉ check khi tạo mới)
            if rec._origin.id:
                continue
            min_start = fields.Datetime.now() + timedelta(minutes=MIN_ADVANCE_MINUTES)
            if rec.date_start <= fields.Datetime.now():
                raise ValidationError('Thời gian đặt bàn phải lớn hơn thời điểm hiện tại.')
            if rec.date_start < min_start:
                raise ValidationError(
                    f'Thời gian đặt bàn phải cách hiện tại ít nhất '
                    f'{MIN_ADVANCE_MINUTES} phút.'
                )

    @api.constrains('guest_count', 'table_id')
    def _check_guest_count(self):
        for rec in self:
            if rec.guest_count <= 0:
                raise ValidationError('Số khách phải lớn hơn 0.')
            if rec.table_id:
                if rec.guest_count > rec.table_id.capacity:
                    raise ValidationError(
                        f'Số khách ({rec.guest_count}) vượt quá sức chứa tối đa '
                        f'của bàn ({rec.table_id.capacity}).'
                    )
                if rec.guest_count < rec.table_id.min_capacity:
                    raise ValidationError(
                        f'Số khách ({rec.guest_count}) ít hơn sức chứa tối thiểu '
                        f'của bàn ({rec.table_id.min_capacity}).'
                    )

    @api.constrains('date_start', 'date_end', 'table_id', 'status')
    def _check_table_overlap(self):
        for rec in self:
            if rec.status == 'cancelled':
                continue
            if not rec.date_start or not rec.date_end or not rec.table_id:
                continue
            conflict = self.search([
                ('id', '!=', rec.id),
                ('table_id', '=', rec.table_id.id),
                ('status', 'in', ['pending', 'confirmed']),
                ('date_start', '<', rec.date_end),
                ('date_end', '>', rec.date_start),
            ])
            if conflict:
                raise ValidationError(
                    f'Bàn {rec.table_id.name} đã có lịch đặt trùng: '
                    f'{conflict[0].name} ({conflict[0].customer_name}) '
                    f'lúc {conflict[0].date_start.strftime("%d/%m/%Y %H:%M")} - '
                    f'{conflict[0].date_end.strftime("%H:%M")}.'
                )