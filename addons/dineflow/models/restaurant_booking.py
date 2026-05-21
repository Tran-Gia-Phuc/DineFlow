from odoo import models, fields, api


class RestaurantBooking(models.Model):
    _name = 'restaurant.booking'
    _description = 'Đặt bàn'
    _order = 'date desc'

    name = fields.Char(string='Mã đặt bàn', readonly=True, default='New')
    customer_name = fields.Char(string='Tên khách', required=True)
    phone = fields.Char(string='Số điện thoại', required=True)
    email = fields.Char(string='Email')
    table_id = fields.Many2one('restaurant.table', string='Bàn', required=True)
    date = fields.Datetime(string='Thời gian', required=True)
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




    def action_confirm(self):
        self.status = 'confirmed'

    def action_cancel(self):
        self.status = 'cancelled'
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.booking') or 'New'
        return super().create(vals)