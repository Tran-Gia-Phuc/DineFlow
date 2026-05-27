from odoo import models, fields

class RestaurantAIChat(models.Model):
    _name = 'restaurant.ai.chat'
    _description = 'AI Chat History'
    _order = 'created_at asc'

    employee_id = fields.Many2one('hr.employee', string='Nhân viên')
    session_id = fields.Char(string='Session ID')
    job_id      = fields.Char(string='Job ID')          
    message = fields.Text(string='Tin nhắn người dùng')
    response = fields.Text(string='Phản hồi AI')
    created_at = fields.Datetime(string='Thời gian', default=fields.Datetime.now)