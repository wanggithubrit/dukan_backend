from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from core.models import Profile, Shop


def handle_referral_upgrade(user):
    try:
        shop = Shop.objects.filter(owner=user).first()
        if not shop:
            return

        # ✅ ALWAYS SYNC PLAN FIRST
        shop.check_and_update_plan()

        # 🔒 REFERRAL DISABLED
        if not settings.REFERRAL_ENABLED:
            return

        # 🔥 COUNT REFERRALS
        ref_count = Profile.objects.filter(referred_by=user).count()

        # 🔥 APPLY REWARD
        if ref_count >= settings.REFERRAL_REQUIRED and not shop.is_pro_active():
            shop.activate_pro()

    except Exception as e:
        print("Referral error:", e)


def update_all_shop_plans():
    expired_shops = Shop.objects.filter(
        plan='pro',
        plan_expiry__lt=timezone.now()
    )

    count = expired_shops.count()

    expired_shops.update(
        plan='free',
        plan_expiry=None
    )

    return count