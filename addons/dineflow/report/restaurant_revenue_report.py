from odoo import models, fields


class RestaurantRevenueReport(models.Model):
    _name = 'restaurant.revenue.report'
    _description = 'Báo cáo doanh thu'
    _auto = False
    _rec_name = 'order_id'

    order_id = fields.Many2one('restaurant.order', string='Đơn hàng', readonly=True)
    date = fields.Datetime(string='Ngày thanh toán', readonly=True)
    table_id = fields.Many2one('restaurant.table', string='Bàn', readonly=True)
    total_amount = fields.Float(string='Doanh thu', readonly=True)
    payment_method = fields.Selection([
        ('cash', 'Tiền mặt'),
        ('card', 'Thẻ'),
        ('transfer', 'Chuyển khoản'),
    ], string='Phương thức', readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW restaurant_revenue_report AS (
                SELECT
                    o.id AS id,
                    o.id AS order_id,
                    o.write_date AS date,
                    o.table_id AS table_id,
                    o.total_amount AS total_amount,
                    o.payment_method AS payment_method
                FROM restaurant_order o
                WHERE o.status = 'paid'
            )
        """)