from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Shop,
    ShopMedia,
    Favorite,
    FeaturedBanner,
    Feedback,
    AppSettings,
    ShopView,
    MerchantCredits,
    CreditTransaction,
)


# ─────────────────────────────
# BASIC REGISTRATIONS
# ─────────────────────────────
admin.site.register(Favorite)
admin.site.register(ShopMedia)
admin.site.register(Feedback)
admin.site.register(AppSettings)
admin.site.register(ShopView)


# ─────────────────────────────
# FEATURED BANNER ADMIN
# ─────────────────────────────
from django.contrib import admin
from .models import FeaturedBanner

from django.contrib import admin
from .models import FeaturedBanner

@admin.register(FeaturedBanner)
class FeaturedBannerAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'title',
        'visibility_radius',
        'global_banner',
        'expires_at',
        'is_active',
        'created_at',
        'priority',
        'is_sponsored',
    )

    list_filter = (
        'is_active',
        'global_banner',
        'visibility_radius',
        'is_sponsored',
    )

    search_fields = (
        'title',
        'subtitle',
    )

    readonly_fields = (
        'created_at',
    )

    fieldsets = (

        ('Banner Content', {
            'fields': (
                'title',
                'subtitle',
                'small_text',
                'image',
                'banner_type',
                'background_color',
                'link',
            )
        }),

        ('Location Targeting', {
            'fields': (
                'global_banner',
                'latitude',
                'longitude',
                'visibility_radius',
            )
        }),

        ('Banner Status', {
            'fields': (
                'expires_at',
                'is_active',
                'created_at',
                'priority',
                'is_sponsored',
            )
        }),
    )
# ─────────────────────────────
# SHOP ADMIN (FIXED VERSION)
# ─────────────────────────────
# 🔥 IMPORTANT: unregister first to avoid AlreadyRegistered error
try:
    admin.site.unregister(Shop)
except admin.sites.NotRegistered:
    pass


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'merchant_email',
        'plan',
        'plan_expiry',
        'days_left',
        'plan_status',
        'is_open',
        'referred_by_user',
        'referred_by_code'
    )

    list_filter = ('plan', 'is_open')
    search_fields = ('name', 'owner__email', 'owner__username')

    # ✅ MERCHANT EMAIL COLUMN
    def merchant_email(self, obj):
        return obj.owner.email if obj.owner and obj.owner.email else "-"
    merchant_email.short_description = "Merchant Email"

    # ✅ STATUS COLUMN
    def plan_status(self, obj):
        if obj.plan != 'pro':
            return "Free"

        if not obj.plan_expiry:
            return "No Expiry"

        if obj.plan_expiry < timezone.now():
            return "❌ Expired"

        return "✅ Active"

    plan_status.short_description = "Status"

    # ✅ DAYS LEFT COLUMN
    def days_left(self, obj):
        if obj.plan != 'pro' or not obj.plan_expiry:
            return "-"

        diff = obj.plan_expiry - timezone.now()
        return f"{diff.days} days"

    days_left.short_description = "Days Left"

    # ✅ REFERRAL COLUMNS FOR SHOP LIST
    def referred_by_user(self, obj):
        profile = getattr(obj.owner, 'profile', None)
        if profile and profile.referred_by:
            return profile.referred_by.username
        return "-"
    referred_by_user.short_description = "Referred By"

    def referred_by_code(self, obj):
        profile = getattr(obj.owner, 'profile', None)
        if profile and profile.referred_by and hasattr(profile.referred_by, 'profile'):
            return profile.referred_by.profile.referral_code
        return "-"
    referred_by_code.short_description = "Used Code"


# ─────────────────────────────
# PROFILE & REFERRAL ADMIN
# ─────────────────────────────
from .models import Profile, Referral

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'referral_code', 'referred_by_user', 'referred_by_code', 'reward_credits', 'referral_reward_claimed', 'app_version_code', 'app_version_name')
    search_fields = ('user__username', 'user__email', 'referral_code', 'app_version_name')
    list_filter = ('role', 'referral_reward_claimed', 'app_version_code')

    def referred_by_user(self, obj):
        return obj.referred_by.username if obj.referred_by else "-"
    referred_by_user.short_description = "Referred By"

    def referred_by_code(self, obj):
        if obj.referred_by and hasattr(obj.referred_by, 'profile'):
            return obj.referred_by.profile.referral_code or "-"
        return "-"
    referred_by_code.short_description = "Used Code"


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred_user', 'created_at')
    search_fields = ('referrer__username', 'referred_user__username')
    list_filter = ('created_at',)


from .models import ProPurchase, AppRelease

@admin.register(ProPurchase)
class ProPurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop', 'shop_owner_email', 'amount', 'razorpay_order_id', 'razorpay_payment_id', 'created_at')
    search_fields = ('shop__name', 'shop__owner__username', 'shop__owner__email', 'razorpay_payment_id', 'razorpay_order_id')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

    def shop_owner_email(self, obj):
        return obj.shop.owner.email if obj.shop and obj.shop.owner else "-"
    shop_owner_email.short_description = "Owner Email"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total_amount=Sum('amount'),
            total_count=Count('id'),
            unique_shops=Count('shop', distinct=True)
        )
        total_amt = stats['total_amount'] or 0.00
        total_cnt = stats['total_count'] or 0
        uniq_shops = stats['unique_shops'] or 0
        self.message_user(
            request,
            f"🚀 Total Pro Subscriptions: ₹{total_amt:.2f} | Total Purchases: {total_cnt} | Unique Shops: {uniq_shops}",
            level="info"
        )
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display = ('version_code', 'version_name', 'is_mandatory', 'notify_users', 'created_at')
    list_filter = ('is_mandatory', 'notify_users', 'created_at')
    search_fields = ('version_name', 'version_code')


from .models import SupportContribution
from django.db.models import Sum, Count

@admin.register(SupportContribution)
class SupportContributionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'amount', 'platform', 'razorpay_order_id', 'razorpay_payment_id', 'created_at')
    list_filter = ('platform', 'created_at')
    search_fields = ('user__username', 'user__email', 'razorpay_payment_id', 'razorpay_order_id')
    readonly_fields = ('created_at',)

    def user_display(self, obj):
        return obj.user.email if obj.user else "Anonymous / Guest"
    user_display.short_description = "User / Email"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total_amount=Sum('amount'),
            total_count=Count('id')
        )
        total_amt = stats['total_amount'] or 0.00
        total_cnt = stats['total_count'] or 0
        self.message_user(request, f"❤️ Total Contributions: ₹{total_amt} | Total Supporters: {total_cnt}", level="info")
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(MerchantCredits)
class MerchantCreditsAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'available_credits', 'total_earned', 'total_spent', 'bought_limit_slots', 'updated_at')
    search_fields = ('merchant__username', 'merchant__email')
    list_filter = ('updated_at',)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total_slots=Sum('bought_limit_slots'),
            total_merchants=Count('merchant', distinct=True)
        )
        total_slots = stats['total_slots'] or 0
        total_merchants = stats['total_merchants'] or 0
        self.message_user(
            request,
            f"📦 Total Bought Limit Slots (Quantity): {total_slots} | Total Merchants with Slots: {total_merchants}",
            level="info"
        )
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant', 'amount', 'transaction_type', 'description', 'created_at')
    search_fields = ('merchant__username', 'merchant__email', 'description')
    list_filter = ('transaction_type', 'created_at')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            total_amount=Sum('amount'),
            total_count=Count('id')
        )
        total_amt = stats['total_amount'] or 0.0
        total_cnt = stats['total_count'] or 0
        self.message_user(
            request,
            f"💰 Total Transactions: {total_cnt} | Net Transaction Amount: {total_amt} Credits",
            level="info"
        )
        return super().changelist_view(request, extra_context=extra_context)