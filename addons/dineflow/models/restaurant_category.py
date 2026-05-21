from odoo import models, fields, api
from odoo.exceptions import ValidationError


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

    def write(self, vals):
        result = super().write(vals)
        if 'active' in vals:
            self._cascade_active_to_items(vals['active'])
        return result

    def _cascade_active_to_items(self, active_value):
        """
        Khi danh mục bị tắt (active=False):
          - Tất cả món trong danh mục → available = False
        Khi danh mục được bật lại (active=True):
          - Không tự động bật lại món (tránh bật nhầm món đã tắt thủ công)
          - Chỉ hiển thị cảnh báo nếu cần, logic bật lại do người dùng tự làm
        Danh mục inactive vẫn hiện trên list (dùng active_test=False trong view).
        """
        if not active_value:
            items = self.with_context(active_test=False).mapped('menu_item_ids')
            items.filtered(lambda i: i.available).write({'available': False})

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for rec in self:
            if not rec.parent_id:
                continue
            if rec.parent_id.id == rec.id:
                raise ValidationError('Danh mục không thể là cha của chính nó.')
            current = rec.parent_id
            visited = {rec.id}
            while current:
                if current.id in visited:
                    raise ValidationError(
                        'Phát hiện vòng lặp trong cấu trúc danh mục cha-con.'
                    )
                visited.add(current.id)
                current = current.parent_id

    @api.constrains('sequence')
    def _check_sequence(self):
        for rec in self:
            if rec.sequence < 0:
                raise ValidationError('Thứ tự hiển thị không được âm.')

    @api.constrains('name')
    def _check_name(self):
        for rec in self:
            if not rec.name or not rec.name.strip():
                raise ValidationError('Tên danh mục không được để trống.')