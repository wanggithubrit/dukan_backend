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
    Item,
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
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from django.http import HttpResponse

class SupportContributionDateFilter(admin.SimpleListFilter):
    title = 'Date Created'
    parameter_name = 'date_range'
    template = 'admin/date_range_filter.html'

    def __init__(self, request, params, model, model_admin):
        self.request = request
        super().__init__(request, params, model, model_admin)

    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Date Range'),
        )

    def start_value(self):
        return self.request.GET.get('date_created_start', '')

    def end_value(self):
        return self.request.GET.get('date_created_end', '')

    def preserved_params(self):
        params = []
        for k, v in self.request.GET.items():
            if k not in ['date_created_start', 'date_created_end', 'date_range']:
                params.append({'key': k, 'value': v})
        return params

    def queryset(self, request, queryset):
        now = timezone.now()
        local_now = timezone.localtime(now)
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        val = self.value()
        if val == 'today':
            return queryset.filter(created_at__gte=today_start)
        elif val == 'this_week':
            start_of_week = today_start - timedelta(days=today_start.weekday())
            return queryset.filter(created_at__gte=start_of_week)
        elif val == 'this_month':
            start_of_month = today_start.replace(day=1)
            return queryset.filter(created_at__gte=start_of_month)
        elif val == 'last_month':
            first_of_this_month = today_start.replace(day=1)
            last_day_of_last_month = first_of_this_month - timedelta(days=1)
            first_of_last_month = last_day_of_last_month.replace(day=1)
            return queryset.filter(created_at__gte=first_of_last_month, created_at__lt=first_of_this_month)
        elif val == 'this_year':
            start_of_year = today_start.replace(month=1, day=1)
            return queryset.filter(created_at__gte=start_of_year)
        elif val == 'custom' or (not val and (request.GET.get('date_created_start') or request.GET.get('date_created_end'))):
            start_date_str = request.GET.get('date_created_start')
            end_date_str = request.GET.get('date_created_end')
            if start_date_str:
                try:
                    start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
                    queryset = queryset.filter(created_at__gte=start_date)
                except ValueError:
                    pass
            if end_date_str:
                try:
                    end_date = timezone.make_aware(datetime.strptime(end_date_str + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))
                    queryset = queryset.filter(created_at__lte=end_date)
                except ValueError:
                    pass
            return queryset
            
        return queryset


@admin.register(SupportContribution)
class SupportContributionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'amount', 'platform', 'razorpay_order_id', 'razorpay_payment_id', 'created_at')
    list_filter = ('platform', SupportContributionDateFilter)
    search_fields = ('user__email', 'platform')
    readonly_fields = ('created_at',)
    actions = ['delete_selected_contributions', 'export_selected_to_csv', 'export_all_to_csv']

    def user_display(self, obj):
        return obj.user.email if obj.user else "Anonymous / Guest"
    user_display.short_description = "User / Email"

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            try:
                amount_val = float(search_term)
                queryset |= self.model.objects.filter(amount=amount_val)
            except ValueError:
                pass
        return queryset, use_distinct

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def delete_selected_contributions(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Successfully deleted {count} support contributions.", level="success")
    delete_selected_contributions.short_description = "Delete Selected Contributions"

    def export_selected_to_csv(self, request, queryset):
        month_year = timezone.now().strftime("%B_%Y").lower()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=support_contributions_{month_year}.csv'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Email', 'Amount', 'Platform', 'Date Created'])
        
        for obj in queryset:
            email = obj.user.email if obj.user else "Anonymous"
            writer.writerow([obj.id, email, obj.amount, obj.platform, obj.created_at.strftime('%Y-%m-%d %H:%M:%S')])
            
        return response
    export_selected_to_csv.short_description = "Export Selected Contributions to CSV"

    def export_all_to_csv(self, request, queryset):
        cl = self.get_changelist_instance(request)
        full_queryset = cl.get_queryset(request)
        
        month_year = timezone.now().strftime("%B_%Y").lower()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=support_contributions_{month_year}.csv'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Email', 'Amount', 'Platform', 'Date Created'])
        
        for obj in full_queryset:
            email = obj.user.email if obj.user else "Anonymous"
            writer.writerow([obj.id, email, obj.amount, obj.platform, obj.created_at.strftime('%Y-%m-%d %H:%M:%S')])
            
        return response
    export_all_to_csv.short_description = "Export All Contributions to CSV"

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


from django.db.models import Min, Max

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'shop', 'price', 'quantity', 'track_quantity', 'created_at')
    search_fields = ('name', 'shop__name', 'shop__owner__email')
    list_filter = ('track_quantity', 'created_at')
    readonly_fields = ('created_at',)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        stats = qs.aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            total_items=Count('id')
        )
        min_pr = stats['min_price'] or 0.00
        max_pr = stats['max_price'] or 0.00
        total_its = stats['total_items'] or 0
        self.message_user(
            request,
            f"🏷️ Total Uploaded Items: {total_its} | Minimum Item Price: ₹{min_pr:.2f} | Maximum Item Price: ₹{max_pr:.2f}",
            level="info"
        )
        return super().changelist_view(request, extra_context=extra_context)