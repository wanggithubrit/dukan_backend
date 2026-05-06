from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from .models import Item
from .serializers import ItemSerializer
from django.utils import timezone
from datetime import timedelta
from .models import Feedback
from django.http import HttpResponse
import random
from django.core.mail import send_mail
from .models import OTP
from .models import Profile, Shop, AppSettings


from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .serializers import NotificationSerializer


from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import Shop










from .models import Shop,Favorite, Profile,ShopBanner, Notification,ShopMedia,FeaturedBanner
from .serializers import ShopSerializer, ShopBannerSerializer,ShopMediaSerializer, ItemSerializer,FeaturedBannerSerializer
import math


# ==============================
# 🔧 HELPERS
# ==============================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return round(R * c, 2)

 
# ==============================
# 📍 NEARBY SHOPS
# ==============================
@api_view(['GET'])
def get_nearby_shops(request):
    try:
        user_lat = float(request.GET.get('lat'))
        user_lon = float(request.GET.get('lon'))
    except:
        return Response({"error": "Provide lat & lon"}, status=400)

    shops = Shop.objects.all()
    result = []

    for shop in shops:

        if not shop.latitude or not shop.longitude:
            continue

        distance = calculate_distance(
            user_lat, user_lon,
            shop.latitude, shop.longitude
        )

        # ✅ ALWAYS DEFINE data FIRST
        data = ShopSerializer(shop, context={'request': request}).data

        # 🔥 COVER IMAGE FIX
        media = ShopMedia.objects.filter(shop=shop).first()

        if media:
            data["cover_image"] = request.build_absolute_uri(media.image.url)
        else:
            data["cover_image"] = data.get("image")

        # 🔥 INCLUDE ITEMS (for search)
        items = Item.objects.filter(shop=shop)
        data["items"] = ItemSerializer(items, many=True).data

        # ADD DISTANCE
        data["distance"] = distance

        result.append(data)

    return Response(sorted(result, key=lambda x: x['distance']))



# ==============================
# 🏪 SHOP
# ==============================

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_shop_detail(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)

    items = Item.objects.filter(shop=shop)
    banners = ShopBanner.objects.filter(shop=shop)
    media = ShopMedia.objects.filter(shop=shop)

    # 🔥 GET USER LOCATION
    try:
        user_lat = float(request.GET.get('lat'))
        user_lon = float(request.GET.get('lon'))
    except:
        user_lat = None
        user_lon = None

    data = ShopSerializer(shop, context={'request': request}).data

    # 🔥 DISTANCE
    if (
        user_lat is not None and
        user_lon is not None and
        shop.latitude is not None and
        shop.longitude is not None
    ):
        data['distance'] = calculate_distance(
            user_lat,
            user_lon,
            shop.latitude,
            shop.longitude
        )
    else:
        data['distance'] = None

    return Response({
        "shop": data,
        "banners": ShopBannerSerializer(banners, many=True, context={'request': request}).data,
        "media": ShopMediaSerializer(media, many=True, context={'request': request}).data,
        "items": ItemSerializer(items, many=True).data,
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_shop(request):
    user = request.user
    shop = get_object_or_404(Shop, owner=user)

    shop.name = request.data.get('name', shop.name)
    shop.phone = request.data.get('phone', shop.phone)

    # ✅ ADD THIS LINE (MAIN FIX)
    shop.whatsapp_number = request.data.get(
        'whatsapp_number',
        shop.whatsapp_number
    )

    shop.address = request.data.get('address', shop.address)

    # LOCATION
    shop.latitude = request.data.get('latitude', shop.latitude)
    shop.longitude = request.data.get('longitude', shop.longitude)

    shop.save()

    return Response({'message': 'Shop updated'})

@api_view(['GET'])
def my_shop(request, user_id):
    shop = Shop.objects.filter(owner_id=user_id).first()

    if not shop:
        return Response({"error": "No shop found"}, status=404)

    return Response(ShopSerializer(shop, context={'request': request}).data)


# ==============================
# ❤️ FAVORITES
# ==============================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request):
    user = request.user
    shop_id = request.data.get('shop_id')

    shop = get_object_or_404(Shop, id=shop_id)

    fav = Favorite.objects.filter(user=user, shop=shop).first()

    if fav:
        fav.delete()
        return Response({"favorited": False})

    Favorite.objects.create(user=user, shop=shop)
    return Response({"favorited": True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_favorites(request):
    user = request.user

    try:
        user_lat = float(request.GET.get('lat'))
        user_lon = float(request.GET.get('lon'))
    except:
        user_lat = None
        user_lon = None

    favorites = Favorite.objects.filter(user=user).select_related('shop')
    result = []

    for fav in favorites:
        shop = fav.shop

        data = ShopSerializer(shop, context={'request': request}).data

        media = ShopMedia.objects.filter(shop=shop).first()
        data["cover_image"] = (
            request.build_absolute_uri(media.image.url)
            if media and media.image else data.get("image")
        )

        # ✅ FIXED CONDITION
        if (
            user_lat is not None and user_lon is not None and
            shop.latitude is not None and shop.longitude is not None
        ):
            distance = calculate_distance(user_lat, user_lon, shop.latitude, shop.longitude)
            data["distance"] = round(distance, 1)
        else:
            data["distance"] = None

        result.append(data)

    # ✅ SAFE SORT
    result.sort(key=lambda x: x["distance"] if x["distance"] is not None else 9999)

    return Response(result)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_shop_status(request):
    shop_id = request.data.get('shop_id')
    status = request.data.get('status')

    shop = get_object_or_404(Shop, id=shop_id)

    if status == 'open':
        shop.is_open = True
    elif status == 'close':
        shop.is_open = False
 
    shop.save()

    return Response({'success': True})









# ==============================
# 📊 MERCHANT DASHBOARD
# ==============================




from core.models import (
    Shop, ShopMedia, Item, Profile,
    Favorite, ShopBanner
)
from core.serializers import (
    ShopSerializer, ShopMediaSerializer, ShopBannerSerializer
)

from core.utils import handle_referral_upgrade


@api_view(['GET'])
def merchant_dashboard(request, user_id):
    try:
        user = get_object_or_404(User, id=user_id)

        # 🔥 HANDLE REFERRAL + EXPIRY
        handle_referral_upgrade(user)

        shop = get_object_or_404(Shop, owner=user)
        profile, _ = Profile.objects.get_or_create(user=user)

        media = ShopMedia.objects.filter(shop=shop)
        items = Item.objects.filter(shop=shop)
        banners = ShopBanner.objects.filter(shop=shop)

        # PLAN LIMITS
        if not shop.is_pro_active():
            cover_limit = 1
            item_limit = 15
        else:
            cover_limit = 5
            item_limit = -1

        return Response({
            "shop": ShopSerializer(shop, context={'request': request}).data,

            "media": ShopMediaSerializer(
                media, many=True, context={'request': request}
            ).data,

            "banners": ShopBannerSerializer(
                banners, many=True, context={'request': request}
            ).data,

            # 🔥 REFERRAL
            "referral_code": profile.referral_code,
            "referral_count": Profile.objects.filter(referred_by=user).count(),

            "stats": {
                "followers": Favorite.objects.filter(shop=shop).count(),
                "cover_images": media.count(),
                "items": items.count(),
                "offers": banners.count(),
            },

            "plan": {
                "type": shop.plan,
                "cover_limit": cover_limit,
                "item_limit": item_limit,
                "expiry": shop.plan_expiry,
                 "credits": profile.reward_credits  # 🔥 ADD THIS
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("❌ DASHBOARD ERROR:", e)
        return Response({"error": "Something went wrong"}, status=500)
# ==============================
# 🔐 AUTH
# ==============================




@csrf_exempt
@api_view(['POST'])
def signup(request):
    try:
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        email = request.data.get('email', '').strip().lower()
        role = request.data.get('role', 'customer')
        ref_code = request.data.get('referral_code', '').strip()

        # 🔴 VALIDATION
        if not username or not password or not email:
            return Response({"error": "Missing fields"}, status=400)

        if len(password) < 6:
            return Response({"error": "Password must be at least 6 characters"}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered"}, status=400)

        # ✅ CREATE USER
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # ✅ PROFILE
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()

        # 🔥 REFERRAL TOGGLE (DB CONTROL)
        settings_obj = AppSettings.objects.first()
        referral_enabled = settings_obj.referral_enabled if settings_obj else True

        referrer = None

        # 🔥 APPLY REFERRAL (ONLY IF ENABLED + MERCHANT)
        if referral_enabled and ref_code and role == 'merchant':
            referrer = Profile.objects.filter(
                referral_code=ref_code.upper()
            ).first()

            # ❌ prevent self-referral
            if referrer and referrer.user != user:
                profile.referred_by = referrer.user
                profile.save()

        # ✅ CREATE SHOP IF MERCHANT
        if role == "merchant":
            try:
                lat = float(request.data.get('latitude', 0))
                lon = float(request.data.get('longitude', 0))
            except:
                lat, lon = 0, 0

            Shop.objects.create(
                owner=user,
                name=request.data.get('shop_name', 'My Shop'),
                category=request.data.get('category', 'General'),
                latitude=lat,
                longitude=lon,
                address=request.data.get('address', '')
            )

        # 🔥 REWARD REFERRER
        if referral_enabled and referrer:
            shop = Shop.objects.filter(owner=referrer.user).first()

            if shop:
                # 🔒 HANDLE EXPIRY FIRST
                if shop.plan == 'pro' and shop.plan_expiry:
                    if timezone.now() > shop.plan_expiry:
                        shop.plan = 'free'
                        shop.plan_expiry = None
                        shop.save()

                # 🔥 COUNT VALID MERCHANT REFERRALS
                count = Profile.objects.filter(
                    referred_by=referrer.user,
                    role='merchant'
                ).count()

                # 🔥 APPLY REWARD (ONLY ONCE)
                if count >= 3 and shop.plan == 'free':
                    shop.plan = 'pro'
                    shop.plan_expiry = timezone.now() + timedelta(days=30)
                    shop.save()

        # ✅ TOKEN
        refresh = RefreshToken.for_user(user)

        return Response({
            "token": str(refresh.access_token),
            "user_id": user.id,
            "username": user.username,
            "role": role
        })

    except Exception as e:
        import traceback
        traceback.print_exc()  # 🔥 full error in terminal
        return Response({"error": str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])

def login(request):
    input_value = request.data.get('username') or request.data.get('email')
    password = request.data.get('password')

    user_obj = User.objects.filter(email__iexact=input_value).first()
    username = user_obj.username if user_obj else input_value

    user = authenticate(username=username, password=password)

    if not user:
        return Response({"error": "Invalid credentials"}, status=400)

    profile, _ = Profile.objects.get_or_create(user=user)

    refresh = RefreshToken.for_user(user)

    return Response({
        "token": str(refresh.access_token),
        "user_id": user.id,
        "username": user.username,
        "role": profile.role or "customer"
    })


# ==============================
# 👤 USER
# ==============================
@api_view(['GET'])
def get_user(request, id):
    user = get_object_or_404(User, id=id)

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
    })

from .models import ShopView






# ==============================
# 🔄 AUTO PROFILE
# ==============================
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """
    Automatically create a Profile when a new User is created.
    SAFE: no business logic, no crashes.
    """
    if created:
        Profile.objects.get_or_create(user=instance)
# ADMIN FEATURED BANNER

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_offer(request):
    user = request.user
    shop = Shop.objects.filter(owner=user).first()
    shop.check_and_update_plan()
    if not shop:
        return Response({'error': 'No shop found'}, status=404)

    if not shop.is_pro_active():
        return Response({'error': 'Upgrade to Pro'}, status=403)

    if ShopBanner.objects.filter(shop=shop).count() >= 3:
        return Response({'error': 'Maximum 3 offers allowed'}, status=403)

    image = request.FILES.get('image')
    discount = request.data.get('discount')
    template = request.data.get('template', 'green')
    title = request.data.get('title', '')

    if discount in ['', None]:
        discount = None
    

    banner_type = 'image' if image else 'text'

    ShopBanner.objects.create(
        shop=shop,
        banner_type=banner_type,
        image=image,
        discount=discount,
        template=template,
        title=title
    )

    return Response({'message': 'Offer created'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_banner(request):
    try:
        user = request.user
        shop = get_object_or_404(Shop, owner=user)
        shop.check_and_update_plan()

        try:
            notify_favorite_users(
                shop,
                "🔥 New Offer Available",
                f"{shop.name} just posted a new offer!"
            )
        except Exception as e:
            print("Notification error:", e)

        if not shop.is_pro_active():
            return Response({'error': 'Upgrade to Pro'}, status=403)

        if ShopBanner.objects.filter(shop=shop).count() >= 3:
            return Response({'error': 'Maximum 3 offers allowed'}, status=403)

        image = request.FILES.get('image')
        discount = str(request.data.get('discount', ''))[:30]
        template = request.data.get('template', 'green')
        title = request.data.get('title', '')
        subtitle = request.data.get('subtitle', '')
        link = request.data.get('link', '')

        if discount in ['', None]:
            discount = None
        else:
            discount = str(discount).strip()

        if not image and discount is None and not title:
            return Response({'error': 'Provide image or text'}, status=400)

        banner_type = 'image' if image else 'text'

        banner = ShopBanner.objects.create(
            shop=shop,
            banner_type=banner_type,
            image=image,
            discount=discount,
            title=title,
            subtitle=subtitle,
            template=template,
        )

        return Response({
            'message': 'Banner created',
            'id': banner.id
        })

    except Exception as e:
        print("UPLOAD ERROR:", str(e))
        return Response({'error': str(e)}, status=500)
    
@api_view(['GET'])
def get_notifications(request, user_id):
    notifications = Notification.objects.filter(user_id=user_id).order_by('-created_at')

    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


def notify_favorite_users(shop, title, message):
    favorites = Favorite.objects.filter(shop=shop)

    Notification.objects.bulk_create([
        Notification(
            user=fav.user,
            shop=shop,  # 🔥 IMPORTANT
            title=title,
            message=message,
            type='offer'
        )
        for fav in favorites
    ])


@api_view(['POST'])
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)

        notification.is_read = True
        notification.save()

        return Response({"message": "Marked as read"})
    except Notification.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
    

@api_view(['DELETE'])
def delete_notification(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.delete()
        return Response({"message": "Deleted"})
    except Notification.DoesNotExist:
        return Response({"error": "Not found"}, status=404)


@api_view(['DELETE'])
def delete_all_notifications(request, user_id):
    Notification.objects.filter(user_id=user_id).delete()
    return Response({"message": "All deleted"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_item(request):
    user = request.user
    shop = get_object_or_404(Shop, owner=user)
    profile = Profile.objects.get(user=user)
    shop.check_and_update_plan()
    count = Item.objects.filter(shop=shop).count()

    if not shop.is_pro_active() and count >= 15:
        if profile.reward_credits > 0:
            profile.reward_credits -= 1
            profile.save()
        else:
            return Response(
                {"error": "limit_reached"},
                status=403
            )

    image = request.FILES.get('image')

    if not image:
        return Response({'error': 'Image required'}, status=400)

    Item.objects.create(
        shop=shop,
        image=image,
        name=request.data.get('name'),
        price=request.data.get('price')
    )

    return Response({'message': 'Item created'})



@api_view(['GET'])
def get_items(request, shop_id):
    items = Item.objects.filter(shop_id=shop_id)
    return Response(ItemSerializer(items, many=True, context={'request': request}).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    if item.shop.owner != request.user:
        return Response({'error': 'Not allowed'}, status=403)

    item.delete()
    return Response({'message': 'Deleted'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_shop_media(request):
    user = request.user
    shop = get_object_or_404(Shop, owner=user)

    image = request.FILES.get('image')

    if not image:
        return Response({'error': 'Image required'}, status=400)

    count = ShopMedia.objects.filter(shop=shop).count()

    # 🆓 FREE → only 1
    if not shop.is_pro_active() and count >= 1:
        return Response({'error': 'Free plan allows only 1 image'}, status=403)

    # 💎 PRO → max 5
    if shop.is_pro_active() and count >= 5:
        return Response({'error': 'Max 5 images allowed'}, status=403)

    ShopMedia.objects.create(shop=shop, image=image)

    return Response({'message': 'Uploaded'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_shop_media(request, media_id):
    user = request.user

    media = get_object_or_404(ShopMedia, id=media_id)

    # 🔒 SECURITY CHECK
    if media.shop.owner != user:
        return Response({'error': 'Not allowed'}, status=403)

    media.delete()

    return Response({'message': 'Deleted'})





@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_plan(request):
    # ⚠️ TEMP — REMOVE AFTER RAZORPAY
    # TODO: verify payment before upgrading

    shop = Shop.objects.get(owner=request.user)
    shop.activate_pro()

    return Response({"message": "Upgraded"})


def check_plan_expiry(shop):
    if shop.plan == 'pro' and shop.plan_expiry:
        if timezone.now() > shop.plan_expiry:
            shop.plan = 'free'
            shop.plan_expiry = None
            shop.save()





@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_featured_banners(request):
    banners = FeaturedBanner.objects.filter(is_active=True).order_by('-id')

    return Response(
        FeaturedBannerSerializer(
            banners,
            many=True,
            context={'request': request}
        ).data
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    user = request.user
    message = request.data.get('message')

    if not message:
        return Response({'error': 'Message required'}, status=400)

    Feedback.objects.create(
        user=user,
        message=message
    )

    return Response({'message': 'Feedback submitted'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_avatar(request):
    user = request.user
    avatar = request.data.get('avatar')

    if not avatar:
        return Response({'error': 'Avatar required'}, status=400)

    try:
        # ✅ If using Profile model
        profile = user.profile
        profile.avatar = avatar
        profile.save()

    except:
        # ✅ fallback (if avatar is in User model)
        user.avatar = avatar
        user.save()

    return Response({
        'success': True,
        'avatar': avatar
    })



from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import Shop

def shop_page(request, id):
    shop = get_object_or_404(Shop, id=id)

    return HttpResponse(f"""
        <html>
        <head>
            <title>{shop.name}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial;
                    padding: 20px;
                    background: #f4f6f5;
                }}
                .card {{
                    background: white;
                    padding: 20px;
                    border-radius: 12px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    margin-bottom: 10px;
                }}
                p {{
                    color: #555;
                }}
                .btn {{
                    margin-top: 15px;
                    padding: 12px;
                    background: #2F5D50;
                    color: white;
                    text-align: center;
                    border-radius: 8px;
                    text-decoration: none;
                    display: inline-block;
                }}
            </style>
        </head>

        <body>
            <div class="card">
                <h1>{shop.name}</h1>
                <p>📍 {shop.address}</p>
                <p>📞 {shop.phone}</p>

                <a class="btn" href="tel:{shop.phone}">
                    Call Now
                </a>
            </div>
        </body>
        </html>
    """)



@api_view(['POST'])
def send_otp(request):
    email = request.data.get('email')

    if not email:
        return Response({'error': 'Email required'}, status=400)

    # ✅ CHECK IF USER EXISTS
    user = User.objects.filter(email=email).first()
    if not user:
        return Response({'error': 'Email not registered'}, status=404)

    otp = str(random.randint(100000, 999999))

    OTP.objects.create(email=email, otp=otp)

    send_mail(
        'Reset Password OTP',
        f'Your OTP is {otp}',
        'yourgmail@gmail.com',
        [email],
    )

    return Response({'message': 'OTP sent'})



@api_view(['POST'])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    record = OTP.objects.filter(email=email, otp=otp).last()

    if not record:
        return Response({'error': 'Invalid OTP'}, status=400)

    return Response({'message': 'OTP verified'})





@api_view(['POST'])
def reset_password(request):
    print("🔥 RESET API HIT")

    email = request.data.get('email')
    password = request.data.get('password')

    print("RESET DATA:", email, password)

    if not email or not password:
        return Response({'error': 'Missing data'}, status=400)

    user = User.objects.filter(email=email).first()

    if not user:
        return Response({'error': 'User not found'}, status=404)

    # ✅ update password
    user.set_password(password)
    user.save()

    # ✅ delete OTP
    OTP.objects.filter(email=email).delete()

    # ✅ ALWAYS RETURN RESPONSE
    return Response({
        'message': 'Password reset successful'
    }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reward_user(request):
    profile = Profile.objects.get(user=request.user)

    profile.reward_credits += 1
    profile.save()

    return Response({
        "message": "Reward added",
        "credits": profile.reward_credits
    })





@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_order(request):
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    amount = 4000  # ₹40 = 4000 paise

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return Response({
        "order_id": order["id"],
        "amount": amount,
        "key": settings.RAZORPAY_KEY_ID
    })

from datetime import timedelta
from django.utils import timezone

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_plan(request):
    user = request.user
    shop = Shop.objects.get(owner=user)

    shop.plan = 'pro'
    shop.plan_expiry = timezone.now() + timedelta(days=30)
    shop.save()

    return Response({"message": "Upgraded to Pro"})


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_shop_cover(request):
    try:
        user = request.user
        shop = Shop.objects.get(owner=user)

        # delete media
        media = ShopMedia.objects.filter(shop=shop).first()
        if media:
            media.delete()

        return Response({"message": "Cover image deleted"})

    except Exception as e:
        return Response({"error": str(e)}, status=400)
    

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_banner(request, banner_id):
    try:
        user = request.user
        banner = ShopBanner.objects.get(id=banner_id)

        if banner.shop.owner != user:
            return Response({"error": "Unauthorized"}, status=403)

        banner.delete()

        return Response({"message": "Banner deleted"})

    except Exception as e:
        return Response({"error": str(e)}, status=400)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def merchant_banners(request):
    shop = Shop.objects.get(owner=request.user)
    banners = ShopBanner.objects.filter(shop=shop)
    serializer = ShopBannerSerializer(banners, many=True)
    return Response(serializer.data)



import razorpay



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    amount = 4000  # ₹40

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return Response({
        "order_id": order['id'],
        "amount": amount,
        "key": settings.RAZORPAY_KEY_ID
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    data = request.data

    params_dict = {
        'razorpay_order_id': data['order_id'],
        'razorpay_payment_id': data['payment_id'],
        'razorpay_signature': data['signature']
    }

    try:
        client.utility.verify_payment_signature(params_dict)

        shop = Shop.objects.get(owner=request.user)
        shop.activate_pro()

        return Response({"status": "success"})

    except Exception as e:
        print(e)
        return Response({"status": "failed"}, status=400)