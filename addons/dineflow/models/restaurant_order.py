from odoo import models, fields, api


class RestaurantOrder(models.Model):
    _name = 'restaurant.order'
    _description = 'Order nhà hàng'
    _order = 'create_date desc'

    name = fields.Char(string='Mã order', readonly=True, default='New')
    table_id = fields.Many2one('restaurant.table', string='Bàn', required=True)
    booking_id = fields.Many2one('restaurant.booking', string='Đặt bàn liên kết')
    waiter_id = fields.Many2one('hr.employee', string='Nhân viên phục vụ')
    order_line_ids = fields.One2many('restaurant.order.line', 'order_id', string='Chi tiết order')
    total_amount = fields.Float(string='Tổng tiền', compute='_compute_total', store=True)
    payment_method = fields.Selection([
        ('cash', 'Tiền mặt'),
        ('card', 'Thẻ'),
        ('vnpay', 'VNPay'),
        ('transfer', 'Chuyển khoản'),
    ], string='Phương thức thanh toán')
    status = fields.Selection([
        ('open', 'Đang phục vụ'),
        ('paid', 'Đã thanh toán'),
        ('cancelled', 'Đã huỷ'),
    ], string='Trạng thái', default='open')
    note = fields.Text(string='Ghi chú')

    @api.depends('order_line_ids.subtotal')
    def _compute_total(self):
        for order in self:
            order.total_amount = sum(order.order_line_ids.mapped('subtotal'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.order') or 'New'
        return super().create(vals)


class RestaurantOrderLine(models.Model):
    _name = 'restaurant.order.line'
    _description = 'Chi tiết order'

    order_id = fields.Many2one('restaurant.order', string='Order', required=True, ondelete='cascade')
    menu_item_id = fields.Many2one('restaurant.menu.item', string='Món', required=True)
    quantity = fields.Integer(string='Số lượng', default=1)
    unit_price = fields.Float(string='Đơn giá')
    subtotal = fields.Float(string='Thành tiền', compute='_compute_subtotal', store=True)
    note = fields.Char(string='Yêu cầu đặc biệt')

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.onchange('menu_item_id')
    def _onchange_menu_item(self):
        if self.menu_item_id:
            self.unit_price = self.menu_item_id.price