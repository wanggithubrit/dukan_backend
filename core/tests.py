from django.test import TestCase
from django.utils import timezone
from datetime import time, timezone as dt_timezone
from unittest.mock import patch
from core.models import Shop

class ShopStatusSyncTestCase(TestCase):
    def setUp(self):
        # Create test shops
        self.shop_day = Shop.objects.create(
            name="Day Shop",
            opening_time=time(9, 0),
            closing_time=time(18, 0),
            auto_reminder_enabled=True,
            is_open=False
        )
        self.shop_night = Shop.objects.create(
            name="Night Shop",
            opening_time=time(22, 0),
            closing_time=time(6, 0),
            auto_reminder_enabled=True,
            is_open=False
        )

    @patch('django.utils.timezone.now')
    def test_day_shop_status(self, mock_now):
        # Test case: Local 08:00 IST -> UTC 02:30:00 (closed)
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 6, 10, 2, 30, 0),
            dt_timezone.utc
        )
        self.assertFalse(self.shop_day.sync_status())

        # Test case: Local 09:00 IST -> UTC 03:30:00 (open)
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 6, 10, 3, 30, 0),
            dt_timezone.utc
        )
        self.assertTrue(self.shop_day.sync_status())

        # Test case: Local 12:00 IST -> UTC 06:30:00 (open)
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 6, 10, 6, 30, 0),
            dt_timezone.utc
        )
        self.assertTrue(self.shop_day.sync_status())

        # Test manual override: merchant manually CLOSES the shop during business hours
        self.shop_day.is_open = False
        self.shop_day.save()
        # It should remain closed since the 09:00 open boundary has already been processed
        self.assertFalse(self.shop_day.sync_status())

        # Test case: Local 18:00 IST -> UTC 12:30:00 (closed)
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 6, 10, 12, 30, 0),
            dt_timezone.utc
        )
        self.assertFalse(self.shop_day.sync_status())

        # Test manual override: merchant manually OPENS the shop after close hours
        self.shop_day.is_open = True
        self.shop_day.save()
        # It should remain open since the 18:00 close boundary has already been processed
        self.assertTrue(self.shop_day.sync_status())

    @patch('django.utils.timezone.now')
    def test_night_shop_status(self, mock_now):
        # Test case: Local 21:00 IST -> UTC 15:30:00 (closed)
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 6, 10, 15, 30, 0),
            dt_timezone.utc
        )
        self.assertFalse(self.shop_night.sync_status())

        # Test case: Local 22:00 IST -> UTC 16:30:00 (open)
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 6, 10, 16, 30, 0),
            dt_timezone.utc
        )
        self.assertTrue(self.shop_night.sync_status())

        # Test manual override: merchant manually CLOSES the shop during business hours (overnight)
        self.shop_night.is_open = False
        self.shop_night.save()
        self.assertFalse(self.shop_night.sync_status())

        # Test case: Local 02:00 (next day) IST -> UTC 20:30:00 (stays closed because transition already happened at 22:00)
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 6, 10, 20, 30, 0),
            dt_timezone.utc
        )
        self.assertFalse(self.shop_night.sync_status())

        # Test case: Local 06:00 (next day) IST -> UTC 00:30:00 (closed)
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2026, 6, 11, 0, 30, 0),
            dt_timezone.utc
        )
        self.assertFalse(self.shop_night.sync_status())


class ProPlusTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from core.models import Shop, Item
        
        self.user = User.objects.create_user(username="merchant", password="password")
        self.shop = Shop.objects.create(
            name="Super Shop",
            owner=self.user,
            plan="pro_plus",
            plan_expiry=timezone.now() + timezone.timedelta(days=10)
        )
        self.item = Item.objects.create(
            shop=self.shop,
            name="Pro Product",
            price=99.99
        )

    def test_item_limits_by_tier(self):
        self.assertEqual(self.shop.get_item_limit(), 500)
        
        # Test custom limit override
        self.shop.item_limit = 750
        self.shop.save()
        self.assertEqual(self.shop.get_item_limit(), 750)
        
        # Revert plan
        self.shop.item_limit = None
        self.shop.plan = 'free'
        self.shop.save()
        self.assertEqual(self.shop.get_item_limit(), 10)

    def test_submit_order_view(self):
        from django.urls import reverse
        from core.models import Order
        
        # Test submitting a valid order
        url = "/api/orders/"
        payload = {
            "shop_id": self.shop.id,
            "item_id": self.item.id,
            "quantity": 2,
            "customer_name": "John Doe",
            "customer_phone": "1234567890",
            "delivery_address": "123 Main St",
            "notes": "Please deliver after 5 PM"
        }
        
        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)
        
        order = Order.objects.first()
        self.assertEqual(order.customer_name, "John Doe")
        self.assertEqual(order.quantity, 2)
        
        # Test submitting order to a free shop (should fail)
        self.shop.plan = "free"
        self.shop.save()
        response2 = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response2.status_code, 403)

