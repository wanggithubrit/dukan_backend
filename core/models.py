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
        ('Home & Kitchen', 'Home & Kitchen'),
        ('🔧 Hardware & Tools', '🔧 Hardware & Tools'),
        ('Computers & Accessories', 'Computers & Accessories'),
        ('🎁 Gifts & Toys', '🎁 Gifts & Toys'),
        ('Others', 'Others'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    has_quantity_feature = models.BooleanField(default=False)
    phone = models.CharField(max_length=15, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True, null=True)

    # ✅ Cloudinary
    image = CloudinaryField("image", null=True, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    is_open = models.BooleanField(default=True)

    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    last_auto_open = models.DateTimeField(null=True, blank=True)
    last_auto_close = models.DateTimeField(null=True, blank=True)

    auto_notify = models.BooleanField(default=True)
    auto_reminder_enabled = models.BooleanField(default=True)

    plan = models.CharField(
        max_length=10,
        choices=[('free', 'Free'), ('pro', 'Pro')],
        default='free'
    )

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

    def sync_status(self):
        if not self.auto_reminder_enabled:
            return self.is_open
        if not self.opening_time or not self.closing_time:
            return self.is_open

        import pytz
        from django.utils import timezone
        from datetime import datetime, timedelta

        tz = pytz.timezone('Asia/Kolkata')
        local_now = timezone.now().astimezone(tz)
        local_date = local_now.date()

        def get_local_datetime(t):
            dt = datetime.combine(local_date, t)
            return tz.localize(dt)

        local_open = get_local_datetime(self.opening_time)
        if local_open > local_now:
            most_recent_open = local_open - timedelta(days=1)
        else:
            most_recent_open = local_open

        local_close = get_local_datetime(self.closing_time)
        if local_close > local_now:
            most_recent_close = local_close - timedelta(days=1)
        else:
            most_recent_close = local_close

        if most_recent_open > most_recent_close:
            if not self.last_auto_open or self.last_auto_open < most_recent_open:
                self.is_open = True
                self.last_auto_open = local_now
                self.save(update_fields=['is_open', 'last_auto_open'])
                print(f"[AutoSync] Automated state update: {self.name} is now Open (Local Time: {local_now.time()})")
                
                # Notify merchant
                try:
                    # Notify merchant (owner)
                    if self.owner:
                        Notification.objects.create(
                            user=self.owner,
                            shop=self,
                            title="⏰ Shop Opened Automatically",
                            message=f"Your shop '{self.name}' has been automatically opened according to your scheduled business hours.",
                            type='general'
                        )
                except Exception as ex:
                    print("[AutoSync] Error sending open notifications:", ex)
        else:
            if not self.last_auto_close or self.last_auto_close < most_recent_close:
                self.is_open = False
                self.last_auto_close = local_now
                self.save(update_fields=['is_open', 'last_auto_close'])
                print(f"[AutoSync] Automated state update: {self.name} is now Closed (Local Time: {local_now.time()})")
                
                # Notify merchant
                try:
                    # Notify merchant (owner)
                    if self.owner:
                        Notification.objects.create(
                            user=self.owner,
                            shop=self,
                            title="⏰ Shop Closed Automatically",
                            message=f"Your shop '{self.name}' has been automatically closed according to your scheduled business hours.",
                            type='general'
                        )
                except Exception as ex:
                    print("[AutoSync] Error sending close notifications:", ex)

        return self.is_open

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
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
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
    referral_reward_claimed = models.BooleanField(default=False)

    referred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_users_profile'
    )

    app_version_code = models.IntegerField(null=True, blank=True)
    app_version_name = models.CharField(max_length=20, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            code = generate_referral_code()
            while Profile.objects.filter(referral_code=code).exists():
                code = generate_referral_code()
            self.referral_code = code
        super().save(*args, **kwargs)


# ==============================
# ⚙️ SETTINGS
# ==============================

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
    image2 = CloudinaryField("image2", blank=True, null=True)
    image3 = CloudinaryField("image3", blank=True, null=True)
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
# ⚙️ AppSettings
# ==============================

class AppSettings(models.Model):
    referral_enabled = models.BooleanField(default=True)
    free_tier_limit = models.IntegerField(default=20, help_text="Base item limit for free tier shops")
    pro_tier_limit = models.IntegerField(default=120, help_text="Base item limit for pro tier shops")

    def __str__(self):
        return "App Settings"


# ==============================
# 🏆 STORE REPORT & COMMUNITY
# ==============================

class StoreReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('status', 'Status Report'),
        ('new_shop', 'New Shop Info'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    details = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved') # auto-approve for simulated rewards
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.shop.name} ({self.report_type})"


# ==============================
# 💰 CREDIT SYSTEM
# ==============================

class MerchantCredits(models.Model):
    merchant = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credits')
    available_credits = models.FloatField(default=0.0)
    total_earned = models.FloatField(default=0.0)
    total_spent = models.FloatField(default=0.0)
    bought_limit_slots = models.IntegerField(default=0)  # tracks purchased extra product slots (+1 per 10 credits)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.merchant.username} - {self.available_credits} Credits"


class CreditTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('reward', 'Reward'),
        ('ad_reward', 'Ad Reward'),
        ('spend', 'Spend'),
        ('bonus', 'Bonus'),
    ]
    merchant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_transactions')
    amount = models.FloatField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.merchant.username} - {self.transaction_type} ({self.amount})"


# ==============================
# 📊 MONITORING & TELEMETRY
# ==============================

class ORSApiCall(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    endpoint = models.CharField(max_length=255, default='directions')
    response_status = models.IntegerField(default=200)

    class Meta:
        verbose_name = "ORS API Call"
        verbose_name = "ORS API Calls"


class ActiveUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    last_active = models.DateTimeField(auto_now=True)
    date = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = ('user', 'date')
        verbose_name = "Active User"
        verbose_name_plural = "Active Users"


# ==============================
# 💳 SUBSCRIPTIONS & PURCHASES
# ==============================

class ProPurchase(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='pro_purchases')
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=59.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pro Purchase"
        verbose_name_plural = "Pro Purchases"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.shop.name} - Pro Purchase ({self.razorpay_payment_id})"


# ==============================
# 🚀 APP RELEASES & UPDATES
# ==============================

class AppRelease(models.Model):
    version_code = models.IntegerField(unique=True)
    version_name = models.CharField(max_length=50)
    release_notes = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=False)
    notify_users = models.BooleanField(default=False, help_text="Set to True to trigger the update prompt in the app.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "App Release"
        verbose_name_plural = "App Releases"
        ordering = ['-version_code']

    def __str__(self):
        return f"{self.version_name} ({self.version_code})"


# ==============================
# ❤️ SUPPORT MYDUKAN
# ==============================

class SupportContribution(models.Model):
    PLATFORM_CHOICES = [
        ('customer', 'Customer App'),
        ('merchant', 'Merchant App'),
        ('web', 'Web Platform'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_contributions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    platform = models.CharField(max_length=15, choices=PLATFORM_CHOICES, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Support Contribution"
        verbose_name_plural = "Support Contributions"
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"{user_str} - ₹{self.amount} ({self.get_platform_display()})"