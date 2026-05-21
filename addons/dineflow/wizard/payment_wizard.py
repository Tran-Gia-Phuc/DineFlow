from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PaymentWizard(models.TransientModel):
    _name = 'restaurant.payment.wizard'
    _description = 'Xác nhận thanh toán'

    order_id = fields.Many2one('restaurant.order', required=True)
    total_amount = fields.Float(related='order_id.total_amount', readonly=True)
    payment_method = fields.Selection([
        ('cash', 'Tiền mặt'),
        ('card', 'Thẻ'),
        ('transfer', 'Chuyển khoản'),
    ], required=True, default='cash')
    amount_received = fields.Float(string='Tiền khách đưa', required=True)
    change_amount = fields.Float(string='Tiền thối lại', compute='_compute_change', readonly=True)

    @api.depends('amount_received', 'total_amount')
    def _compute_change(self):
        for rec in self:
            rec.change_amount = rec.amount_received - rec.total_amount

    def action_confirm_payment(self):
        if self.amount_received < self.total_amount:
            raise ValidationError('Tiền khách đưa không đủ!')
        self.order_id.payment_method = self.payment_method
        self.order_id.action_paid()
        return {'type': 'ir.actions.act_window_close'}