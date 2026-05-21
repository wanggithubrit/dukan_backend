from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
import string

# ✅ Cloudinary
from cloudinary.models import CloudinaryField


# ==============================
# 🏪 SHOP
# ==============================

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
    has_quantity_feature = models.BooleanField(default=False)
    phone = models.CharField(max_length=15)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True)

    # ✅ Cloudinary
    image = CloudinaryField("image", null=True, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    is_open = models.BooleanField(default=True)

    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    auto_notify = models.BooleanField(default=True)

    plan = models.CharField(
        max_length=10,
        choices=[('free', 'Free'), ('pro', 'Pro')],
        default='free'
    )
    is_premium = models.BooleanField( default=False )
    plan_expiry = models.DateTimeField(null=True, blank=True)

    def activate_pro(self):
        now = timezone.now()
        if self.plan == 'pro' and self.plan_expiry and self.plan_expiry > now:
            self.plan_expiry += timedelta(days=30)
        else:
            self.plan = 'pro'
            self.plan_expiry = now + timedelta(days=30)
        self.save(update_fields=['plan', 'plan_expiry'])

    def is_pro_active(self):
        return self.plan == 'pro' and self.plan_expiry and self.plan_expiry > timezone.now()

    def check_and_update_plan(self):
        if self.plan == 'pro' and self.plan_expiry and self.plan_expiry <= timezone.now():
            self.plan = 'free'
            self.plan_expiry = None
            self.save(update_fields=['plan', 'plan_expiry'])

    def days_left(self):
        if not self.is_pro_active():
            return 0
        return max((self.plan_expiry - timezone.now()).days, 0)

    def save(self, *args, **kwargs):
        if self.plan == 'pro' and self.plan_expiry and self.plan_expiry <= timezone.now():
            self.plan = 'free'
            self.plan_expiry = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ==============================
# 🖼️ SHOP BANNER
# ==============================

class ShopBanner(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)

    banner_type = models.CharField(
        max_length=10,
        choices=[('image', 'Image'), ('text', 'Text')],
        default='image'
    )

    # ✅ Cloudinary
    image = CloudinaryField("image", null=True, blank=True)

    title = models.CharField(max_length=100, blank=True)
    subtitle = models.CharField(max_length=150, blank=True)
    discount = models.CharField(max_length=100, null=True, blank=True)  # ✅

    template = models.CharField(max_length=20, default='green')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Banner {self.id}"


# ==============================
# 🔔 NOTIFICATION
# ==============================

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True)

    title = models.CharField(max_length=100)
    message = models.TextField()
    type = models.CharField(max_length=20, default='general')

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


# ==============================
# 📊 SHOP VIEW
# ==============================

class ShopView(models.Model):
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)


# ==============================
# ❤️ FAVORITE
# ==============================
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'shop')  # 🔥 IMPORTANT

    def __str__(self):
        return f"{self.user.username} - {self.shop.name}"


# ==============================
# 👤 PROFILE
# ==============================

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
        related_name='referred_users_profile'
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

from django.utils import timezone
from datetime import timedelta

class OTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_valid(self):
        return timezone.now() < self.created_at + timedelta(minutes=5)


# ==============================
# 📸 MEDIA
# ==============================

class ShopMedia(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    image = CloudinaryField("image")


class Item(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    image = CloudinaryField("image")
    name = models.CharField(max_length=100)

    description = models.TextField(
        blank=True,
        null=True
    )

    price = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    quantity = models.PositiveIntegerField(default=0)

    track_quantity = models.BooleanField(default=False)

class FeaturedBanner(models.Model):

    title = models.CharField(max_length=200, blank=True)
    subtitle = models.CharField(max_length=300, blank=True)

    image = models.ImageField(
        upload_to='featured_banners/',
        blank=True,
        null=True
    )

    banner_type = models.CharField(
        max_length=20,
        default='image'
    )

    background_color = models.CharField(
        max_length=20,
        default='#1B6B50'
    )

    small_text = models.CharField(
        max_length=100,
        blank=True
    )
    # HIGHER NUMBER = HIGHER PRIORITY
    priority = models.IntegerField(
        default=0
    )

# OPTIONAL SPONSORED TAG
    is_sponsored = models.BooleanField(
        default=False
    )
    # OPTIONAL LINK
    link = models.URLField(
        blank=True,
        null=True
    )

    # LOCATION
    latitude = models.FloatField(
        blank=True,
        null=True
    )

    longitude = models.FloatField(
        blank=True,
        null=True
    )

    # 25 / 50 / etc
    visibility_radius = models.IntegerField(
        default=25
    )

    # SHOW EVERYWHERE
    global_banner = models.BooleanField(
        default=False
    )

    # EXPIRY
    expires_at = models.DateTimeField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or "Banner"


# ==============================
# 📝 FEEDBACK
# ==============================

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


# ==============================
# 🔗 REFERRAL
# ==============================

class Referral(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referred_user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


# ==============================
# ⚙️ SETTINGS
# ==============================

class AppSettings(models.Model):
    referral_enabled = models.BooleanField(default=True)

    def __str__(self):
        return "App Settings"