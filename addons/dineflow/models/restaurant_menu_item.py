from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RestaurantMenuItem(models.Model):
    _name = 'restaurant.menu.item'
    _description = 'Món ăn / Đồ uống'
    _order = 'category_id, name'

    name = fields.Char(string='Tên món', required=True)
    category_id = fields.Many2one('restaurant.category', string='Danh mục', required=True)
    price = fields.Float(string='Giá', required=True, digits=(15, 0))
    type = fields.Selection([
        ('food', 'Món ăn'),
        ('drink', 'Đồ uống'),
    ], string='Loại', default='food', required=True)
    image = fields.Image(string='Hình ảnh')
    description = fields.Text(string='Mô tả')
    available = fields.Boolean(string='Còn phục vụ', default=True)
    preparation_time = fields.Integer(string='Thời gian chuẩn bị (phút)', default=10)

    @api.constrains('name', 'category_id')
    def _check_name(self):
        for rec in self:
            if not rec.name or not rec.name.strip():
                raise ValidationError('Tên món không được để trống.')
            if len(rec.name.strip()) < 2:
                raise ValidationError('Tên món phải có ít nhất 2 ký tự.')
            # Tên món không trùng trong cùng danh mục
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('name', '=', rec.name.strip()),
                ('category_id', '=', rec.category_id.id),
            ])
            if duplicate:
                raise ValidationError(
                    f'Món "{rec.name}" đã tồn tại trong danh mục này.'
                )

    @api.constrains('price')
    def _check_price(self):
        for rec in self:
            if rec.price <= 0:
                raise ValidationError('Giá món ăn phải lớn hơn 0.')

    @api.constrains('preparation_time')
    def _check_preparation_time(self):
        for rec in self:
            if rec.preparation_time < 0:
                raise ValidationError('Thời gian chuẩn bị không được âm.')
            if rec.preparation_time > 180:
                raise ValidationError('Thời gian chuẩn bị không được vượt quá 180 phút.')