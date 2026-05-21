from odoo import models, fields
from odoo.exceptions import ValidationError

class CancelBookingWizard(models.TransientModel):
    _name = 'restaurant.cancel.booking.wizard'
    _description = 'Xác nhận huỷ đặt bàn'

    booking_id = fields.Many2one('restaurant.booking', required=True)
    customer_name = fields.Char(related='booking_id.customer_name', readonly=True)
    cancel_reason = fields.Text(string='Lý do huỷ', required=True)

    def action_confirm_cancel(self):
        if not self.cancel_reason:
            raise ValidationError('Vui lòng nhập lý do huỷ!')
        self.booking_id.note = f"[Huỷ] {self.cancel_reason}"
        self.booking_id.action_cancel()
        return {'type': 'ir.actions.act_window_close'}