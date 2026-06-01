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
    image2 = serializers.SerializerMethodField()
    image3 = serializers.SerializerMethodField()
    quantity_status = serializers.SerializerMethodField()
    shop_has_quantity_feature = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            'id',
            'shop',
            'name',
            'price',
            'description',
            'image',
            'image2',
            'image3',
            'quantity',
            'track_quantity',
            'quantity_status',
            'shop_has_quantity_feature',
        ]

    def get_image(self, obj):
        if obj.image:
            url = obj.image.url

            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            return url

        return None

    def get_image2(self, obj):
        if obj.image2:
            url = obj.image2.url

            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            return url

        return None

    def get_image3(self, obj):
        if obj.image3:
            url = obj.image3.url

            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            return url

        return None

    def get_quantity_status(self, obj):

        if not obj.shop.has_quantity_feature:
            return None

        if not obj.track_quantity:
            return None

        if obj.quantity <= 0:
            return "out"

        if obj.quantity <= 5:
            return "low"

        return "in"

    def get_shop_has_quantity_feature(self, obj):
        return obj.shop.has_quantity_feature

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