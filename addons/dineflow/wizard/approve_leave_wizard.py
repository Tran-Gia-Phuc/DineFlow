from odoo import models, fields
from odoo.exceptions import ValidationError

class ApproveLeaveWizard(models.TransientModel):
    _name = 'restaurant.approve.leave.wizard'
    _description = 'Duyệt đơn nghỉ phép hàng loạt'

    leave_ids = fields.Many2many(
        'restaurant.leave.request',
        string='Danh sách đơn',
        domain=[('status', '=', 'confirmed')],
    )
    manager_id = fields.Many2one('hr.employee', string='Người duyệt', required=True)
    note = fields.Text(string='Ghi chú')

    def action_approve_all(self):
        if not self.leave_ids:
            raise ValidationError('Chưa chọn đơn nào!')
        for leave in self.leave_ids:
            leave.manager_id = self.manager_id
            leave.action_approve()
        return {'type': 'ir.actions.act_window_close'}

    def action_refuse_all(self):
        if not self.leave_ids:
            raise ValidationError('Chưa chọn đơn nào!')
        for leave in self.leave_ids:
            leave.action_refuse()
        return {'type': 'ir.actions.act_window_close'}