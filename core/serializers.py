from rest_framework import serializers
from django.contrib.auth.models import User

from .models import (
    Shop, ShopMedia, ShopBanner,
    Notification, Item, FeaturedBanner, Feedback, Profile
)

# ==============================
# 👤 USER (WITH PROFILE IMAGE)
# ==============================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar']


# ==============================
# 🏪 SHOP
# ==============================
class ShopSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = '__all__'

    def get_image(self, obj):
        if obj.image:
            url = obj.image.url

            # ✅ Force HTTPS for Cloudinary / mobile apps
            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            return url

        return None

# ==============================
# 🏪 MINI SHOP
# ==============================
class ShopMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'latitude', 'longitude', 'phone']


# ==============================
# 🖼️ MEDIA
# ==============================
class ShopMediaSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ShopMedia
        fields = '__all__'

    def get_image(self, obj):
        if obj.image:
            url = obj.image.url

            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            return url

        return None


# ==============================
# 🎯 ITEMS
# ==============================
class ItemSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = "__all__"

    def get_image(self, obj):
        if obj.image:
            url = obj.image.url

            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            return url

        return None
# ==============================
# 🎯 BANNERS
# ==============================
class ShopBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopBanner
        fields = '__all__'


# ==============================
# 🔔 NOTIFICATIONS
# ==============================
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


# ==============================
# 🌟 FEATURED BANNER
# ==============================
class FeaturedBannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = FeaturedBanner
        fields = '__all__'

    def get_image(self, obj):
        if obj.image:
            url = obj.image.url

            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            return url

        return None


# ==============================
# 💬 FEEDBACK
# ==============================
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'