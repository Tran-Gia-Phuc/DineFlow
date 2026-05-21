from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
        result = super().create(vals)
        result._sync_table_status()
        return result

    def write(self, vals):
        result = super().write(vals)
        if 'status' in vals or 'table_id' in vals:
            self._sync_table_status()
        return result

    def _sync_table_status(self):
        """
        Khi order open  → bàn chuyển thành occupied.
        Khi order paid/cancelled → trả quyền điều phối về booking._sync_table_status.
        """
        for rec in self:
            if not rec.table_id:
                continue
            if rec.status == 'open':
                rec.table_id.status = 'occupied'
            else:
                # Nhường lại cho booking logic tính trạng thái bàn
                rec.table_id.booking_ids._sync_table_status()
    def action_paid(self):
        for rec in self:
            if rec.status != 'open':
                raise ValidationError('Chỉ order đang phục vụ mới có thể thanh toán.')
            if not rec.payment_method:
                raise ValidationError('Vui lòng chọn phương thức thanh toán trước.')
            rec.status = 'paid'
            if rec.booking_id and rec.booking_id.status == 'confirmed':
                rec.booking_id.action_done()
            rec._sync_table_status()

    def action_cancel(self):
        for rec in self:
            if rec.status == 'paid':
                raise ValidationError('Không thể huỷ order đã thanh toán.')
            rec.status = 'cancelled'
            rec._sync_table_status()

    @api.constrains('table_id', 'status')
    def _check_no_duplicate_open_order(self):
        """Không cho phép 2 order đang mở cùng 1 bàn."""
        for rec in self:
            if rec.status != 'open':
                continue
            conflict = self.search([
                ('id', '!=', rec.id),
                ('table_id', '=', rec.table_id.id),
                ('status', '=', 'open'),
            ])
            if conflict:
                raise ValidationError(
                    f'Bàn {rec.table_id.name} đang có order chưa đóng: '
                    f'{conflict[0].name}. '
                    'Vui lòng thanh toán hoặc huỷ trước khi tạo order mới.'
                )

    @api.constrains('booking_id', 'table_id')
    def _check_booking_table_match(self):
        for rec in self:
            if rec.booking_id and rec.table_id:
                if rec.booking_id.table_id.id != rec.table_id.id:
                    raise ValidationError(
                        f'Bàn của order ({rec.table_id.name}) không khớp với '
                        f'bàn đã đặt trước ({rec.booking_id.table_id.name}).'
                    )


class RestaurantOrderLine(models.Model):
    _name = 'restaurant.order.line'
    _description = 'Chi tiết order'

    order_id = fields.Many2one(
        'restaurant.order', string='Order', required=True, ondelete='cascade'
    )
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

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Số lượng món phải lớn hơn 0.')
            if line.quantity > 999:
                raise ValidationError('Số lượng món không được vượt quá 999.')

    @api.constrains('unit_price')
    def _check_unit_price(self):
        for line in self:
            if line.unit_price < 0:
                raise ValidationError('Đơn giá không được âm.')

    @api.constrains('menu_item_id')
    def _check_menu_item_available(self):
        """Món phải còn phục vụ VÀ danh mục phải đang active."""
        for line in self:
            item = line.menu_item_id
            if not item:
                continue
            if not item.available:
                raise ValidationError(
                    f'Món "{item.name}" hiện không còn phục vụ.'
                )
            # Kiểm tra danh mục (dùng sudo để đọc cả record inactive)
            category = item.with_context(active_test=False).category_id
            if category and not category.active:
                raise ValidationError(
                    f'Không thể order món "{item.name}" vì danh mục '
                    f'"{category.name}" đang tạm ngưng hoạt động.'
                )