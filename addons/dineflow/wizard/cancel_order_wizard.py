from odoo import models, fields
from odoo.exceptions import ValidationError

class CancelOrderWizard(models.TransientModel):
    _name = 'restaurant.cancel.order.wizard'
    _description = 'Xác nhận huỷ order'

    order_id = fields.Many2one('restaurant.order', required=True)
    table_id = fields.Many2one(related='order_id.table_id', readonly=True)
    total_amount = fields.Float(related='order_id.total_amount', readonly=True)
    cancel_reason = fields.Text(string='Lý do huỷ', required=True)

    def action_confirm_cancel(self):
        if not self.cancel_reason:
            raise ValidationError('Vui lòng nhập lý do huỷ!')
        self.order_id.note = f"[Huỷ] {self.cancel_reason}"
        self.order_id.action_cancel()
        return {'type': 'ir.actions.act_window_close'}