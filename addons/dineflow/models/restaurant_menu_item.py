from odoo import models, fields


class RestaurantMenuItem(models.Model):
    _name = 'restaurant.menu.item'
    _description = 'Món ăn / Đồ uống'
    _order = 'category_id, name'

    name = fields.Char(string='Tên món', required=True)
    category_id = fields.Many2one('restaurant.category', string='Danh mục', required=True)
    price = fields.Float(string='Giá', required=True)
    type = fields.Selection([
        ('food', 'Món ăn'),
        ('drink', 'Đồ uống'),
    ], string='Loại', default='food', required=True)
    image = fields.Image(string='Hình ảnh')
    description = fields.Text(string='Mô tả')
    available = fields.Boolean(string='Còn phục vụ', default=True)
    preparation_time = fields.Integer(string='Thời gian chuẩn bị (phút)', default=10)