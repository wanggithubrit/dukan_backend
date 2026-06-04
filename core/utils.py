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

        # 🔥 APPLY REWARD (ONLY ONCE)
        referrer_profile = Profile.objects.filter(user=user).first()
        if referrer_profile and not referrer_profile.referral_reward_claimed:
            if ref_count >= settings.REFERRAL_REQUIRED:
                shop.activate_pro()
                referrer_profile.referral_reward_claimed = True
                referrer_profile.save(update_fields=['referral_reward_claimed'])

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