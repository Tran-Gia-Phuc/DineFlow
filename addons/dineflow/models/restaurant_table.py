from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RestaurantTable(models.Model):
    _name = 'restaurant.table'
    _description = 'Bàn nhà hàng'
    _order = 'floor, name'

    name = fields.Char(string='Tên bàn', required=True)
    capacity = fields.Integer(string='Sức chứa tối đa', default=4)
    min_capacity = fields.Integer(string='Sức chứa tối thiểu', default=1)
    status = fields.Selection([
        ('available', 'Trống'),
        ('occupied', 'Có khách'),
        ('reserved', 'Đã đặt trước'),
    ], string='Trạng thái', default='available', required=True)
    floor = fields.Char(string='Khu vực / Tầng', default='A')
    note = fields.Text(string='Ghi chú')
    active = fields.Boolean(string='Đang hoạt động', default=True)
    qr_code = fields.Char(string='QR Code')

    booking_ids = fields.One2many('restaurant.booking', 'table_id', string='Đặt bàn')
    order_ids = fields.One2many('restaurant.order', 'table_id', string='Order')

    # --- Computed: thông tin booking hiện tại đang chiếm bàn ---
    current_booking_id = fields.Many2one(
        'restaurant.booking',
        string='Đặt bàn hiện tại',
        compute='_compute_current_booking',
        store=False,
    )
    current_guest = fields.Char(
        string='Khách hiện tại',
        compute='_compute_current_booking',
        store=False,
    )
    current_time_start = fields.Datetime(
        string='Giờ đến',
        compute='_compute_current_booking',
        store=False,
    )
    current_time_end = fields.Datetime(
        string='Giờ kết thúc',
        compute='_compute_current_booking',
        store=False,
    )
    next_booking_id = fields.Many2one(
        'restaurant.booking',
        string='Đặt bàn tiếp theo',
        compute='_compute_next_booking',
        store=False,
    )
    next_booking_time = fields.Datetime(
        string='Giờ đặt tiếp theo',
        compute='_compute_next_booking',
        store=False,
    )

    def _compute_current_booking(self):
        now = fields.Datetime.now()
        for rec in self:
            booking = self.env['restaurant.booking'].search([
                ('table_id', '=', rec.id),
                ('status', 'in', ['confirmed', 'pending']),
                ('date_start', '<=', now),
                ('date_end', '>=', now),
            ], limit=1, order='date_start asc')
            rec.current_booking_id = booking
            rec.current_guest = booking.customer_name if booking else False
            rec.current_time_start = booking.date_start if booking else False
            rec.current_time_end = booking.date_end if booking else False

    def _compute_next_booking(self):
        now = fields.Datetime.now()
        for rec in self:
            booking = self.env['restaurant.booking'].search([
                ('table_id', '=', rec.id),
                ('status', 'in', ['confirmed', 'pending']),
                ('date_start', '>', now),
            ], limit=1, order='date_start asc')
            rec.next_booking_id = booking
            rec.next_booking_time = booking.date_start if booking else False

    @api.constrains('capacity', 'min_capacity')
    def _check_capacity(self):
        for rec in self:
            if rec.capacity <= 0:
                raise ValidationError('Sức chứa tối đa phải lớn hơn 0.')
            if rec.min_capacity <= 0:
                raise ValidationError('Sức chứa tối thiểu phải lớn hơn 0.')
            if rec.min_capacity > rec.capacity:
                raise ValidationError(
                    f'Sức chứa tối thiểu ({rec.min_capacity}) '
                    f'không được lớn hơn sức chứa tối đa ({rec.capacity}).'
                )

    @api.constrains('name')
    def _check_name_unique(self):
        for rec in self:
            if not rec.name or not rec.name.strip():
                raise ValidationError('Tên bàn không được để trống.')
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('name', '=', rec.name.strip()),
            ])
            if duplicate:
                raise ValidationError(f'Tên bàn "{rec.name}" đã tồn tại.')

    def check_availability(self, date_start, date_end, exclude_booking_id=False):
        domain = [
            ('table_id', '=', self.id),
            ('status', 'in', ['pending', 'confirmed']),
            ('date_start', '<', date_end),
            ('date_end', '>', date_start),
        ]
        if exclude_booking_id:
            domain.append(('id', '!=', exclude_booking_id))
        return self.env['restaurant.booking'].search_count(domain) == 0