from odoo import models, fields


class RestaurantLeaveReport(models.Model):
    _name = 'restaurant.leave.report'
    _description = 'Báo cáo nghỉ phép'
    _auto = False
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Nhân viên', readonly=True)
    date_from = fields.Date(string='Từ ngày', readonly=True)
    date_to = fields.Date(string='Đến ngày', readonly=True)
    leave_type = fields.Selection([
        ('annual', 'Nghỉ phép năm'),
        ('sick', 'Nghỉ bệnh'),
        ('unpaid', 'Nghỉ không lương'),
        ('other', 'Khác'),
    ], string='Loại nghỉ', readonly=True)
    status = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã gửi'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Đã hủy'),
    ], string='Trạng thái', readonly=True)
    duration = fields.Float(string='Số ngày', readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW restaurant_leave_report AS (
                SELECT
                    l.id AS id,
                    l.employee_id AS employee_id,
                    l.date_from AS date_from,
                    l.date_to AS date_to,
                    l.leave_type AS leave_type,
                    l.status AS status,
                    (l.date_to - l.date_from + 1) AS duration
                FROM restaurant_leave_request l
            )
        """)