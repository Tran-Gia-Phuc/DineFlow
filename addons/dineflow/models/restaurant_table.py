from odoo import models, fields


class RestaurantTable(models.Model):
    _name = 'restaurant.table'
    _description = 'Bàn nhà hàng'
    _order = 'floor, name'

    name = fields.Char(string='Tên bàn', required=True)
    capacity = fields.Integer(string='Sức chứa', default=4)
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