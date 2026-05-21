from odoo import models, fields


class RestaurantCategory(models.Model):
    _name = 'restaurant.category'
    _description = 'Danh mục món ăn'
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh mục', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    image = fields.Image(string='Hình ảnh')
    active = fields.Boolean(string='Đang hoạt động', default=True)
    parent_id = fields.Many2one('restaurant.category', string='Danh mục cha')
    child_ids = fields.One2many('restaurant.category', 'parent_id', string='Danh mục con')
    menu_item_ids = fields.One2many('restaurant.menu.item', 'category_id', string='Các món')