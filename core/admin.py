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
@admin.register(FeaturedBanner)
class FeaturedBannerAdmin(admin.ModelAdmin):
    list_display = ['id', 'banner_type', 'title', 'is_active', 'link']

    fieldsets = (
        ("Type", {
            'fields': ('banner_type',)
        }),

        ("Image Banner", {
            'fields': ('image',),
        }),

        ("Text Banner", {
            'fields': ('small_text', 'title', 'subtitle', 'background_color'),
        }),

        ("Link (Optional)", {
            'fields': ('link',),
            'description': 'Add URL (e.g. https://...)',
        }),

        ("Control", {
            'fields': ('is_active',),
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