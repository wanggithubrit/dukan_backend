from django.db import models
from django.contrib.auth.models import User
import random
from django.utils import timezone
from datetime import timedelta
import random
import string
import uuid
# ==============================
# 🏪 SHOP
# ==============================

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Shop(models.Model):
    CATEGORY_CHOICES = [
        ('Grocery', 'Grocery'),
        ('Footwear', 'Footwear'),
        ('Fashion', 'Fashion'),
        ('Medicine', 'Medicine'),
        ('Electronics', 'Electronics'),
        ('Bakeries', 'Bakeries'),
        ('Rentals', 'Rentals'),
        ('Stationery', 'Stationery'),
        ('Furniture', 'Furniture'),
        ('Books', 'Books'),
        ('Others', 'Others'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    phone = models.CharField(max_length=15)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True)

    image = models.ImageField(upload_to='shops/', null=True, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    is_open = models.BooleanField(default=True)

    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    auto_notify = models.BooleanField(default=True)

    # ───────── PLAN SYSTEM ─────────
    plan = models.CharField(
        max_length=10,
        choices=[
            ('free', 'Free'),
            ('pro', 'Pro')
        ],
        default='free'
    )

    plan_expiry = models.DateTimeField(null=True, blank=True)

    # ───────── ACTIVATE / EXTEND PRO ─────────
    def activate_pro(self):
        now = timezone.now()

        if self.plan == 'pro' and self.plan_expiry and self.plan_expiry > now:
            # extend existing plan
            self.plan_expiry += timedelta(days=30)
        else:
            # new activation
            self.plan = 'pro'
            self.plan_expiry = now + timedelta(days=30)

        self.save(update_fields=['plan', 'plan_expiry'])

    # ───────── CHECK PRO ACTIVE ─────────
    def is_pro_active(self):
        return (
            self.plan == 'pro' and
            self.plan_expiry and
            self.plan_expiry > timezone.now()
        )

    # ───────── AUTO DOWNGRADE ─────────
    def check_and_update_plan(self):
        if self.plan == 'pro' and self.plan_expiry:
            if self.plan_expiry <= timezone.now():
                self.plan = 'free'
                self.plan_expiry = None
                self.save(update_fields=['plan', 'plan_expiry'])

    # ───────── DAYS LEFT ─────────
    def days_left(self):
        if not self.is_pro_active():
            return 0

        diff = self.plan_expiry - timezone.now()
        return max(diff.days, 0)

    # ───────── SAVE OVERRIDE (AUTO CHECK) ─────────
    def save(self, *args, **kwargs):
        # auto downgrade if expired before saving
        if self.plan == 'pro' and self.plan_expiry:
            if self.plan_expiry <= timezone.now():
                self.plan = 'free'
                self.plan_expiry = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
#  SHOP BANNER (Dashboard Offers)
class ShopBanner(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)

    banner_type = models.CharField(
        max_length=10,
        choices=[('image', 'Image'), ('text', 'Text')],
        default='image'
    )

    image = models.ImageField(upload_to='banners/', null=True, blank=True)

    title = models.CharField(max_length=100, blank=True)
    subtitle = models.CharField(max_length=150, blank=True)

    discount = models.IntegerField(null=True, blank=True)

    template = models.CharField(max_length=20, default='green')


    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Banner {self.id}"


# 🔔 NOTIFICATION


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True)

    title = models.CharField(max_length=100)
    message = models.TextField()

    type = models.CharField(max_length=20, default='general')

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


# ==============================
# 📢 POST
# ==============================
# models.py


class ShopView(models.Model):
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shop.id} - {self.user.id}"


# ==============================
# ❤️ FAVORITE
# ==============================
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.user.username} - {self.shop.name}"


# ==============================
# 👤 PROFILE
# ==============================

import random, string

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class Profile(models.Model):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('merchant', 'Merchant'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    avatar = models.CharField(max_length=50, default='male_1')
    reward_credits = models.IntegerField(default=0)

    referral_code = models.CharField(max_length=10, unique=True, blank=True, null=True)

    referred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_users_profile'  # 🔥 FIXED ERROR
    )

    def save(self, *args, **kwargs):
        if not self.referral_code:
            code = generate_referral_code()
            while Profile.objects.filter(referral_code=code).exists():
                code = generate_referral_code()
            self.referral_code = code

        super().save(*args, **kwargs)



# ==============================
# 🔐 OTP
# ==============================
# models.py


class OTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() < self.created_at + timedelta(minutes=5)

    def __str__(self):
        return f"{self.email} - {self.otp}"
    
class ShopMedia(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='shop_media/')

class Item(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='items/')
    name = models.CharField(max_length=100)
    price = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class FeaturedBanner(models.Model):
    # 🔥 TYPE
    BANNER_TYPE = (
        ('image', 'Image'),
        ('text', 'Text'),
    )
    banner_type = models.CharField(max_length=10, choices=BANNER_TYPE, default='image')

    # IMAGE
    image = models.ImageField(upload_to='featured_banners/', null=True, blank=True)

    # TEXT CONTENT
    small_text = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=100, blank=True)
    subtitle = models.CharField(max_length=150, blank=True)

    # STYLE (optional)
    background_color = models.CharField(max_length=20, default='#2F5D50')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title or "Banner"
    
class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"
    


class Referral(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referred_user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.username} -> {self.referred_user.username}"
    









class AppSettings(models.Model):
    referral_enabled = models.BooleanField(default=True)

    def __str__(self):
        return "App Settings"
    