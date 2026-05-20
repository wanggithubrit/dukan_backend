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
)


# ─────────────────────────────
# BASIC REGISTRATIONS
# ─────────────────────────────
admin.site.register(Favorite)
admin.site.register(ShopMedia)
admin.site.register(Feedback)
admin.site.register(AppSettings)


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
        'plan',
        'plan_expiry',
        'days_left',
        'plan_status',
        'is_open'
    )

    list_filter = ('plan', 'is_open')
    search_fields = ('name',)

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