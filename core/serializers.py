from rest_framework import serializers
from django.contrib.auth.models import User

from .models import (
    Shop, ShopMedia, ShopBanner,
    Notification, Item, FeaturedBanner, Feedback, Profile
)

# Helper function to normalize URL to absolute URI if relative
def normalize_image_url(serializer, field):
    if not field:
        return None
    url = field.url
    if url.startswith("http://"):
        # Only force HTTPS if not local development
        if not any(local_ip in url for local_ip in ["127.0.0.1", "localhost", "10.14.104.206"]):
            url = url.replace("http://", "https://")
    elif url.startswith("/"):
        request = serializer.context.get('request')
        if request is not None:
            abs_url = request.build_absolute_uri(url)
            if not any(local_ip in abs_url for local_ip in ["127.0.0.1", "localhost", "10.14.104.206"]):
                if abs_url.startswith("http://"):
                    abs_url = abs_url.replace("http://", "https://")
            return abs_url
    return url


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
        return normalize_image_url(self, obj.image)

    def to_representation(self, instance):
        instance.sync_status()
        return super().to_representation(instance)


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
        return normalize_image_url(self, obj.image)


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
        return normalize_image_url(self, obj.image)

    def get_image2(self, obj):
        return normalize_image_url(self, obj.image2)

    def get_image3(self, obj):
        return normalize_image_url(self, obj.image3)

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
        return normalize_image_url(self, obj.image)


# ==============================
# 💬 FEEDBACK
# ==============================
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'