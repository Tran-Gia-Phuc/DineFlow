from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class TestRestaurantTable(TransactionCase):

    def setUp(self):
        super().setUp()
        self.table = self.env['restaurant.table'].create({
            'name': 'Bàn Test 01',
            'capacity': 4,
            'min_capacity': 1,
            'status': 'available',
        })

    def test_create_table_success(self):
        """Tạo bàn hợp lệ"""
        self.assertEqual(self.table.name, 'Bàn Test 01')
        self.assertEqual(self.table.status, 'available')

    def test_capacity_invalid(self):
        """capacity phải > 0"""
        with self.assertRaises(ValidationError):
            self.env['restaurant.table'].create({
                'name': 'Bàn Test 02',
                'capacity': 0,
                'min_capacity': 1,
            })

    def test_min_capacity_greater_than_capacity(self):
        """min_capacity không được lớn hơn capacity"""
        with self.assertRaises(ValidationError):
            self.env['restaurant.table'].create({
                'name': 'Bàn Test 03',
                'capacity': 2,
                'min_capacity': 5,
            })


class TestRestaurantMenuItem(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category = self.env['restaurant.category'].create({
            'name': 'Test Category',
        })
        self.item = self.env['restaurant.menu.item'].create({
            'name': 'Pizza Test',
            'category_id': self.category.id,
            'price': 50000,
            'type': 'food',
            'available': True,
        })

    def test_create_menu_item_success(self):
        """Tạo món ăn hợp lệ"""
        self.assertEqual(self.item.name, 'Pizza Test')
        self.assertEqual(self.item.price, 50000)

    def test_price_invalid(self):
        """Giá phải > 0"""
        with self.assertRaises(ValidationError):
            self.env['restaurant.menu.item'].create({
                'name': 'Món Test',
                'category_id': self.category.id,
                'price': -1,
                'type': 'food',
            })

    def test_duplicate_name_in_category(self):
        """Không tạo 2 món cùng tên trong cùng danh mục"""
        with self.assertRaises(ValidationError):
            self.env['restaurant.menu.item'].create({
                'name': 'Pizza Test',
                'category_id': self.category.id,
                'price': 60000,
                'type': 'food',
            })


class TestRestaurantBooking(TransactionCase):

    def setUp(self):
        super().setUp()
        self.table = self.env['restaurant.table'].create({
            'name': 'Bàn Booking Test',
            'capacity': 4,
            'min_capacity': 1,
            'status': 'available',
        })

    def test_create_booking_success(self):
        """Tạo booking hợp lệ"""
        tomorrow = date.today() + timedelta(days=1)
        booking = self.env['restaurant.booking'].create({
            'customer_name': 'Nguyễn Văn A',
            'phone': '0901234567',
            'table_id': self.table.id,
            'date_start': f'{tomorrow} 10:00:00',
            'date_end': f'{tomorrow} 12:00:00',
            'guest_count': 2,
        })
        self.assertEqual(booking.customer_name, 'Nguyễn Văn A')
        self.assertEqual(booking.status, 'pending')

    def test_booking_overlap(self):
        """Không cho phép 2 booking trùng bàn và giờ"""
        tomorrow = date.today() + timedelta(days=1)
        self.env['restaurant.booking'].create({
            'customer_name': 'Khách 1',
            'phone': '0901234567',
            'table_id': self.table.id,
            'date_start': f'{tomorrow} 10:00:00',
            'date_end': f'{tomorrow} 12:00:00',
            'guest_count': 2,
            'status': 'confirmed',
        })
        with self.assertRaises(ValidationError):
            self.env['restaurant.booking'].create({
                'customer_name': 'Khách 2',
                'phone': '0901234568',
                'table_id': self.table.id,
                'date_start': f'{tomorrow} 11:00:00',
                'date_end': f'{tomorrow} 13:00:00',
                'guest_count': 2,
                'status': 'confirmed',
            })

    def test_guest_count_exceeds_capacity(self):
        """Số khách không được vượt capacity bàn"""
        tomorrow = date.today() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.env['restaurant.booking'].create({
                'customer_name': 'Khách Test',
                'phone': '0901234567',
                'table_id': self.table.id,
                'date_start': f'{tomorrow} 10:00:00',
                'date_end': f'{tomorrow} 12:00:00',
                'guest_count': 10,
            })


class TestRestaurantLeave(TransactionCase):

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Nhân viên Test',
            'restaurant_role': 'waiter',
        })

    def test_create_leave_success(self):
        """Tạo đơn nghỉ hợp lệ"""
        leave = self.env['restaurant.leave.request'].create({
            'employee_id': self.employee.id,
            'date_from': date.today() + timedelta(days=1),
            'date_to': date.today() + timedelta(days=2),
            'leave_type': 'annual',
            'status': 'confirmed',
        })
        self.assertEqual(leave.status, 'confirmed')

    def test_date_to_before_date_from(self):
        """Ngày kết thúc không được trước ngày bắt đầu"""
        with self.assertRaises(ValidationError):
            self.env['restaurant.leave.request'].create({
                'employee_id': self.employee.id,
                'date_from': date.today() + timedelta(days=5),
                'date_to': date.today() + timedelta(days=1),
                'leave_type': 'annual',
            })

    def test_leave_overlap(self):
        """Không cho phép 2 đơn nghỉ trùng ngày cùng nhân viên"""
        self.env['restaurant.leave.request'].create({
            'employee_id': self.employee.id,
            'date_from': date.today() + timedelta(days=1),
            'date_to': date.today() + timedelta(days=3),
            'leave_type': 'annual',
            'status': 'confirmed',
        })
        with self.assertRaises(ValidationError):
            self.env['restaurant.leave.request'].create({
                'employee_id': self.employee.id,
                'date_from': date.today() + timedelta(days=2),
                'date_to': date.today() + timedelta(days=4),
                'leave_type': 'annual',
                'status': 'confirmed',
            })

    def test_annual_quota_exceeded(self):
        """Tổng nghỉ phép năm không vượt 12 ngày"""
        self.env['restaurant.leave.request'].create({
            'employee_id': self.employee.id,
            'date_from': date(date.today().year, 1, 1),
            'date_to': date(date.today().year, 1, 10),
            'leave_type': 'annual',
            'status': 'confirmed',
        })
        with self.assertRaises(ValidationError):
            self.env['restaurant.leave.request'].create({
                'employee_id': self.employee.id,
                'date_from': date(date.today().year, 2, 1),
                'date_to': date(date.today().year, 2, 10),
                'leave_type': 'annual',
                'status': 'confirmed',
            })


class TestRestaurantOrder(TransactionCase):

    def setUp(self):
        super().setUp()
        self.table = self.env['restaurant.table'].create({
            'name': 'Bàn Order Test',
            'capacity': 4,
            'min_capacity': 1,
            'status': 'available',
        })
        self.category = self.env['restaurant.category'].create({
            'name': 'Category Order Test',
        })
        self.item = self.env['restaurant.menu.item'].create({
            'name': 'Món Order Test',
            'category_id': self.category.id,
            'price': 50000,
            'type': 'food',
            'available': True,
        })

    def test_create_order_success(self):
        """Tạo order hợp lệ"""
        order = self.env['restaurant.order'].create({
            'table_id': self.table.id,
            'status': 'open',
            'order_line_ids': [(0, 0, {
                'menu_item_id': self.item.id,
                'quantity': 2,
                'unit_price': 50000,
            })]
        })
        self.assertEqual(order.status, 'open')
        self.assertEqual(order.total_amount, 100000)

    def test_duplicate_open_order_same_table(self):
        """Không cho phép 2 order open cùng bàn"""
        self.env['restaurant.order'].create({
            'table_id': self.table.id,
            'status': 'open',
        })
        with self.assertRaises(ValidationError):
            self.env['restaurant.order'].create({
                'table_id': self.table.id,
                'status': 'open',
            })