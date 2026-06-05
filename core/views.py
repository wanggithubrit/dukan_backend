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

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import parser_classes












from .models import Shop,Favorite, Profile,ShopBanner, Notification,ShopMedia,FeaturedBanner
from .serializers import ShopSerializer, ShopBannerSerializer,ShopMediaSerializer, ItemSerializer,FeaturedBannerSerializer
import math


# ==============================
# 🔧 HELPERS
# ==============================
def calculate_haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

DISTANCE_CACHE = {}

def calculate_distance(lat1, lon1, lat2, lon2):
    import urllib.request
    import json
    import os

    # Round coordinates to 5 decimal places to prevent routing snapping variations (~1m precision)
    lat1 = round(lat1, 5)
    lon1 = round(lon1, 5)
    lat2 = round(lat2, 5)
    lon2 = round(lon2, 5)

    # Try cache first
    try:
        cache_key = (lat1, lon1, lat2, lon2)
        if cache_key in DISTANCE_CACHE:
            return DISTANCE_CACHE[cache_key]
    except Exception:
        cache_key = None

    straight = calculate_haversine(lat1, lon1, lat2, lon2)

    # Dynamic road-winding factor curve fitting based on straight-line distance (in KM)
    if straight < 5.0:
        factor = 1.2
    elif straight < 15.0:
        factor = 1.2 + 0.02 * (straight - 5.0)
    else:
        # Mountainous/hilly terrain (e.g., NH-29) has winding factors up to 1.72
        factor = 1.4 + 0.015 * (straight - 15.0)
        if factor > 1.72:
            factor = 1.72

    expected_road_dist = straight * factor
    result_dist = None

    # 1. Try OpenRouteService first if OPENROUTE_API_KEY is configured
    ors_key = os.getenv("OPENROUTE_API_KEY")
    if ors_key:
        try:
            # Note: start and end are formatted as start=lon1,lat1 and end=lon2,lat2 for OpenRouteService
            url = f"https://api.openrouteservice.org/v2/directions/driving-car?api_key={ors_key}&start={lon1},{lat1}&end={lon2},{lat2}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Dukan App)'})
            status = 200
            try:
                with urllib.request.urlopen(req, timeout=2.0) as response:
                    data = json.loads(response.read().decode())
                    if 'features' in data:
                        dist_meters = data['features'][0]['properties']['summary']['distance']
                        result_dist = round(dist_meters / 1000.0, 1)
            except Exception as http_err:
                status = getattr(http_err, 'code', 500)
                raise http_err
            finally:
                try:
                    from core.models import ORSApiCall
                    ORSApiCall.objects.create(endpoint='directions/driving-car', response_status=status)
                except Exception:
                    pass
        except Exception as e:
            pass

    # 2. Try Google Maps Distance Matrix API second if GOOGLE_MAPS_API_KEY is configured
    if result_dist is None:
        google_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if google_key:
            try:
                url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={lat1},{lon1}&destinations={lat2},{lon2}&key={google_key}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Dukan App)'})
                with urllib.request.urlopen(req, timeout=2.0) as response:
                    data = json.loads(response.read().decode())
                    if data.get('status') == 'OK':
                        element = data['rows'][0]['elements'][0]
                        if element.get('status') == 'OK':
                            distance_meters = element['distance']['value']
                            result_dist = round(distance_meters / 1000.0, 1)
            except Exception as e:
                pass

    # 3. Try querying public OpenStreetMap OSRM API for exact road routing distance
    if result_dist is None:
        try:
            url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Dukan App)'})
            with urllib.request.urlopen(req, timeout=2.0) as response:
                data = json.loads(response.read().decode())
                if data.get('routes'):
                    osrm_meters = data['routes'][0]['distance']
                    osrm_km = osrm_meters / 1000.0
                    
                    # Check for OSRM snapping detour anomalies (Rural snapping errors)
                    if osrm_km > expected_road_dist * 1.15:
                        result_dist = round(expected_road_dist, 1)
                    else:
                        # Use raw OSRM road routing distance directly for maximum accuracy across all routes
                        result_dist = round(osrm_km, 1)
        except Exception as e:
            pass

    if result_dist is None:
        # Fallback to dynamic Expected Winding Road Curve
        result_dist = round(expected_road_dist, 1)

    if cache_key is not None:
        DISTANCE_CACHE[cache_key] = result_dist

    return result_dist

 
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

    shops = list(Shop.objects.all())
    
    from concurrent.futures import ThreadPoolExecutor

    def fetch_dist(s):
        if not s.latitude or not s.longitude:
            return s.id, None
        try:
            d = calculate_distance(user_lat, user_lon, s.latitude, s.longitude)
            return s.id, d
        except Exception:
            return s.id, None

    with ThreadPoolExecutor(max_workers=20) as executor:
        dist_map = dict(executor.map(fetch_dist, shops))

    result = []

    for shop in shops:
        if not shop.latitude or not shop.longitude:
            continue

        distance = dist_map.get(shop.id)
        if distance is None:
            continue

        # Check and update plan expiry
        shop.check_and_update_plan()

        # ✅ SHOP DATA
        data = ShopSerializer(
            shop,
            context={'request': request}
        ).data

        # ✅ COVER IMAGE
        media = ShopMedia.objects.filter(shop=shop).first()

        if media and media.image:
            url = media.image.url

            # ✅ FORCE HTTPS
            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            data["cover_image"] = url

        else:
            data["cover_image"] = data.get("image")

        # ✅ ITEMS
        items = Item.objects.filter(shop=shop)

        data["items"] = ItemSerializer(
            items,
            many=True,
            context={'request': request}
        ).data

        # ✅ DISTANCE
        data["distance"] = distance

        result.append(data)

    return Response(
        sorted(result, key=lambda x: (x.get('distance') or 0, 0 if x.get('plan') == 'pro' else 1))
    )


# ==============================
# 🏪 SHOP
# ==============================

@api_view(['GET'])
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

    # Log view (supports logged-in and guest views)
    try:
        user = request.user if (request.user and request.user.is_authenticated) else None
        ShopView.objects.create(shop=shop, user=user)
    except Exception as e:
        print("Error saving ShopView log:", e)

    return Response({
        "shop": data,
        "banners": ShopBannerSerializer(banners, many=True, context={'request': request}).data,
        "media": ShopMediaSerializer(media, many=True, context={'request': request}).data,
         "items": ItemSerializer(
            items,
            many=True,
            context={'request': request}
         ).data,
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
    shop.description = request.data.get('description', shop.description)

    # LOCATION
    shop.latitude = request.data.get('latitude', shop.latitude)
    shop.longitude = request.data.get('longitude', shop.longitude)

    # NEW TIMES & REMINDERS
    print("DEBUG: update_shop payload:", request.data)
    if 'opening_time' in request.data:
        opening = request.data.get('opening_time')
        shop.opening_time = opening if (opening and opening != 'null') else None
    if 'closing_time' in request.data:
        closing = request.data.get('closing_time')
        shop.closing_time = closing if (closing and closing != 'null') else None

    auto_rem = request.data.get('auto_reminder_enabled')
    if auto_rem is not None:
        shop.auto_reminder_enabled = str(auto_rem).lower() == 'true'
        shop.auto_notify = str(auto_rem).lower() == 'true'

    # IMAGE / COVER UPLOAD
    if request.FILES.get('image'):
        shop.image = request.FILES.get('image')

    shop.save()

    # --- CREDIT REWARDS ---
    try:
        # 1. Complete Shop Profile (+5)
        if shop.name and shop.phone and shop.whatsapp_number and shop.address and shop.description:
            if not CreditTransaction.objects.filter(merchant=user, description='Complete Shop Profile').exists():
                award_merchant_credits(user, 5.0, 'reward', 'Complete Shop Profile')

        # 2. Add Opening/Closing Time Set (+2)
        if shop.opening_time and shop.closing_time:
            if not CreditTransaction.objects.filter(merchant=user, description='Add Opening/Closing Time').exists():
                award_merchant_credits(user, 2.0, 'reward', 'Add Opening/Closing Time')

        # 3. Cover Image Uploaded (+2)
        if shop.image:
            if not CreditTransaction.objects.filter(merchant=user, description='Upload Shop Banner').exists():
                award_merchant_credits(user, 2.0, 'reward', 'Upload Shop Banner')
    except Exception as e:
        print("Credit reward error in update_shop:", e)

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

    favorites = list(Favorite.objects.filter(user=user).select_related('shop'))
    
    from concurrent.futures import ThreadPoolExecutor

    def fetch_fav_dist(fav):
        shop = fav.shop
        if (
            user_lat is not None and
            user_lon is not None and
            shop.latitude is not None and
            shop.longitude is not None
        ):
            try:
                d = calculate_distance(user_lat, user_lon, shop.latitude, shop.longitude)
                return fav.id, d
            except Exception:
                return fav.id, None
        return fav.id, None

    with ThreadPoolExecutor(max_workers=20) as executor:
        dist_map = dict(executor.map(fetch_fav_dist, favorites))

    result = []

    for fav in favorites:
        shop = fav.shop

        data = ShopSerializer(
            shop,
            context={'request': request}
        ).data

        media = ShopMedia.objects.filter(shop=shop).first()

        # ✅ FIX COVER IMAGE HTTPS
        if media and media.image:
            url = media.image.url

            if url.startswith("http://"):
                url = url.replace("http://", "https://")

            data["cover_image"] = url

        else:
            data["cover_image"] = data.get("image")

        # ✅ DISTANCE
        distance = dist_map.get(fav.id)
        if distance is not None:
            data["distance"] = round(distance, 1)
        else:
            data["distance"] = None

        result.append(data)

    # ✅ SAFE SORT
    result.sort(
        key=lambda x: x["distance"]
        if x["distance"] is not None else 9999
    )

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
                "views": ShopView.objects.filter(shop=shop, viewed_at__gte=timezone.now() - timedelta(days=7)).count(),
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
        email    = request.data.get('email', '').strip().lower()
        role     = request.data.get('role', 'customer')
        ref_code = request.data.get('referral_code', '').strip()
 
        # ── Basic validation ──────────────────────────────────────
        if not username or not password or not email:
            return Response({"error": "Missing fields"}, status=400)
 
        if len(password) < 6:
            return Response({"error": "Password must be at least 6 characters"}, status=400)

        # ── Referral validation ────────────────────────────────────
        if ref_code:
            if ref_code.upper() == 'DUKAN777':
                # Accept system-wide fallback code silently
                pass
            else:
                referrer_profile = Profile.objects.filter(referral_code__iexact=ref_code).first()
                if not referrer_profile:
                    return Response({"error": "Invalid referral code"}, status=400)
 
        existing_by_email    = User.objects.filter(email=email).first()
        existing_by_username = User.objects.filter(username=username).first()
 
        # ── Merchant→Customer: always hard block ──────────────────
        if existing_by_email and role == 'customer':
            profile = Profile.objects.filter(user=existing_by_email).first()
            if profile and profile.role == 'merchant':
                return Response(
                    {"error": "This email is registered to a merchant account."},
                    status=400,
                )
 
        # ── Customer→Merchant upgrade path ────────────────────────
        if (
            existing_by_email
            and role == 'merchant'
            and hasattr(existing_by_email, 'profile')
            and existing_by_email.profile.role == 'customer'
        ):
            user = existing_by_email
 
            if username != user.username and User.objects.filter(username=username).exists():
                return Response({"error": "Username already taken"}, status=400)
 
            if username and username != user.username:
                user.username = username
            user.set_password(password)
            user.save()
 
            profile = user.profile
            profile.role = 'merchant'
            profile.save()
 
            if not Shop.objects.filter(owner=user).exists():
                try:
                    lat = float(request.data.get('latitude', 0))
                    lon = float(request.data.get('longitude', 0))
                except (TypeError, ValueError):
                    lat, lon = 0, 0
 
                Shop.objects.create(
                    owner=user,
                    name=request.data.get('shop_name', 'My Shop'),
                    category=request.data.get('category', 'General'),
                    latitude=lat,
                    longitude=lon,
                    address=request.data.get('address', '')
                )
 
            refresh = RefreshToken.for_user(user)
            return Response({
                "token": str(refresh.access_token),
                "user_id": user.id,
                "username": user.username,
                "role": "merchant",
                "upgraded": True,
            })
 
        # ── Normal duplicate checks ───────────────────────────────
        if existing_by_username:
            return Response({"error": "Username already exists"}, status=400)
 
        if existing_by_email:
            return Response({"error": "Email already registered"}, status=400)
 
        # ── Create new user ───────────────────────────────────────
        user = User.objects.create_user(username=username, email=email, password=password)
 
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()
 
        # ── Referral (merchant only) ──────────────────────────────
        settings_obj = AppSettings.objects.first()
        referral_enabled = settings_obj.referral_enabled if settings_obj else True
        referrer = None
 
        if referral_enabled and ref_code and role == 'merchant':
            referrer = Profile.objects.filter(referral_code__iexact=ref_code).first()
            if not referrer and ref_code.upper() == 'DUKAN777':
                referrer = Profile.objects.filter(user__is_staff=True).first() or Profile.objects.filter(role='merchant').first() or Profile.objects.first()
            
            if referrer and referrer.user != user:
                # Check if referrer has a shop and is already on the Pro plan
                referrer_shop = Shop.objects.filter(owner=referrer.user).first()
                if referrer_shop and referrer_shop.plan == 'pro':
                    # Referral is inactive: do not link and do not reward
                    referrer = None
                else:
                    profile.referred_by = referrer.user
                    profile.save()
                    
                    # Create Referral record for admin tracking
                    from .models import Referral
                    Referral.objects.get_or_create(referrer=referrer.user, referred_user=user)
 
        # ── Create shop ───────────────────────────────────────────
        if role == 'merchant':
            try:
                lat = float(request.data.get('latitude', 0))
                lon = float(request.data.get('longitude', 0))
            except (TypeError, ValueError):
                lat, lon = 0, 0
 
            Shop.objects.create(
                owner=user,
                name=request.data.get('shop_name', 'My Shop'),
                category=request.data.get('category', 'General'),
                latitude=lat,
                longitude=lon,
                address=request.data.get('address', '')
            )
 
        # ── Reward referrer ───────────────────────────────────────
        if referral_enabled and referrer:
            shop = Shop.objects.filter(owner=referrer.user).first()
            if shop:
                if shop.plan == 'pro' and shop.plan_expiry and timezone.now() > shop.plan_expiry:
                    shop.plan = 'free'
                    shop.plan_expiry = None
                    shop.save()
 
                referrer.refresh_from_db()
                if not referrer.referral_reward_claimed:
                    count = Profile.objects.filter(referred_by=referrer.user, role='merchant').count()
                    if count >= 3:
                        shop.plan = 'pro'
                        shop.plan_expiry = timezone.now() + timedelta(days=30)
                        shop.save()
                        referrer.referral_reward_claimed = True
                        referrer.save(update_fields=['referral_reward_claimed'])
 
        refresh = RefreshToken.for_user(user)
        return Response({
            "token": str(refresh.access_token),
            "user_id": user.id,
            "username": user.username,
            "role": role,
        })
 
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)
 


@csrf_exempt
@api_view(['POST'])
def validate_referral(request):
    ref_code = request.data.get('referral_code', '').strip()
    if not ref_code:
        return Response({"valid": False, "error": "Referral code cannot be empty"}, status=400)
    
    if ref_code.upper() == 'DUKAN777':
        return Response({"valid": True, "message": "System referral code is active!"})
        
    referrer_profile = Profile.objects.filter(referral_code__iexact=ref_code).first()
    if not referrer_profile:
        return Response({"valid": False, "error": "Invalid referral code"}, status=400)
        
    # Check if referrer has a shop and is already on the Pro plan
    referrer_shop = Shop.objects.filter(owner=referrer_profile.user).first()
    if referrer_shop and referrer_shop.plan == 'pro':
        return Response({"valid": False, "error": "Referral code is inactive (user is already on Pro plan)"}, status=400)
        
    return Response({"valid": True, "message": f"Code is active! Referrer: {referrer_profile.user.username}"})


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
    profile, _ = Profile.objects.get_or_create(user=user)

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "reward_credits": profile.reward_credits,
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


@receiver(post_save, sender=Shop)
def reward_first_shop(sender, instance, created, **kwargs):
    if created and instance.owner:
        try:
            # Check if they already have a shop reward
            if not CreditTransaction.objects.filter(merchant=instance.owner, description='First Shop Created').exists():
                award_merchant_credits(instance.owner, 5.0, 'reward', 'First Shop Created')
        except Exception as e:
            print("Error rewarding first shop:", e)
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

@parser_classes([MultiPartParser, FormParser])
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

        try:
            if not CreditTransaction.objects.filter(merchant=user, description='Upload Shop Banner').exists():
                award_merchant_credits(user, 2.0, 'reward', 'Upload Shop Banner')
        except Exception as e:
            print("Credit reward error in upload_banner:", e)

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
@parser_classes([MultiPartParser, FormParser])
def create_item(request):
    user = request.user
    shop = get_object_or_404(Shop, owner=user)
    shop.check_and_update_plan()
    count = Item.objects.filter(shop=shop).count()

    credits_obj, _ = MerchantCredits.objects.get_or_create(merchant=user)
    limit = 20 + credits_obj.bought_limit_slots
    is_pro = shop.is_pro_active()
    if is_pro:
        if count >= 120:
            return Response(
                {"error": "pro_limit_reached", "message": "Pro plan is limited to 120 items."},
                status=403
            )
    else:
        if count >= limit:
            return Response(
                {"error": "limit_reached"},
                status=403
            )

    image = request.FILES.get('image')
    image2 = request.FILES.get('image2') if is_pro else None
    image3 = request.FILES.get('image3') if is_pro else None

    if not image:
        return Response({'error': 'Image required'}, status=400)

    # ─────────────────────────────
# 🔒 QUANTITY FEATURE SECURITY
# ─────────────────────────────
    track_quantity = False
    quantity = 0

# Merchant purchased feature
    if shop.has_quantity_feature:

        track_quantity = (
            str(request.data.get('track_quantity'))
            .lower() == 'true'
        )

        try:
            quantity = int(request.data.get('quantity', 0))
        except:
            quantity = 0

    # Prevent negative stock
        if quantity < 0:
            quantity = 0


    Item.objects.create(
        shop=shop,
        image=image,
        image2=image2,
        image3=image3,
        name=request.data.get('name'),
        price=request.data.get('price'),

    # NEW
        track_quantity=track_quantity,
        quantity=quantity,
    )

    try:
        award_merchant_credits(user, 0.5, 'reward', "Add New Product")
    except Exception as e:
        print("Credit reward error in create_item:", e)

    return Response({'message': 'Item created'})



@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_item(request, item_id):

    user = request.user

    item = get_object_or_404(Item, id=item_id)

    # 🔒 OWNER CHECK
    if item.shop.owner != user:
        return Response(
            {'error': 'Not allowed'},
            status=403
        )

    shop = item.shop

    orig_name = item.name
    orig_price = item.price
    orig_desc = item.description
    orig_track = item.track_quantity
    orig_quant = item.quantity

    # ─────────────────────────────
    # BASIC FIELDS
    # ─────────────────────────────
    item.name = request.data.get(
        'name',
        item.name
    )

    item.price = request.data.get(
        'price',
        item.price
    )

    item.description = request.data.get(
        'description',
        item.description
    )

    # OPTIONAL IMAGE UPDATE
    image = request.FILES.get('image')

    if image:
        item.image = image

    # ─────────────────────────────
    # 🔒 QUANTITY FEATURE SECURITY
    # ─────────────────────────────
    if shop.has_quantity_feature:

        track_quantity = (
            str(request.data.get('track_quantity'))
            .lower() == 'true'
        )

        try:
            quantity = int(
                request.data.get('quantity', 0)
            )
        except:
            quantity = 0

        # Prevent negative stock
        if quantity < 0:
            quantity = 0

        item.track_quantity = track_quantity
        item.quantity = quantity

    else:
        # HARD LOCK
        item.track_quantity = False
        item.quantity = 0

    has_changed = (
        item.name != orig_name or
        item.price != orig_price or
        item.description != orig_desc or
        item.track_quantity != orig_track or
        item.quantity != orig_quant or
        image is not None
    )

    item.save()

    if has_changed:
        try:
            award_merchant_credits(user, 0.1, 'reward', f"Update Product ({item.id})")
        except Exception as e:
            print("Credit reward error in update_item:", e)

    return Response({
        'message': 'Item updated'
    })



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
def create_quantity_order(request):

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    amount = 10000  # ₹100

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
def verify_quantity_payment(request):

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    data = request.data

    params_dict = {
        'razorpay_order_id': data['order_id'],
        'razorpay_payment_id': data['payment_id'],
        'razorpay_signature': data['signature']
    }

    try:

        # ✅ VERIFY PAYMENT
        client.utility.verify_payment_signature(params_dict)

        # ✅ UNLOCK FEATURE
        shop = Shop.objects.get(owner=request.user)

        shop.has_quantity_feature = True
        shop.save()

        return Response({
            "status": "success",
            "message": "Quantity feature unlocked"
        })

    except Exception as e:
        print(e)

        return Response({
            "status": "failed"
        }, status=400)


import traceback

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_shop_media(request):
    try:
        user = request.user
        shop = get_object_or_404(Shop, owner=user)

        print("FILES:", request.FILES)

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

        media = ShopMedia.objects.create(
            shop=shop,
            image=image
        )

        print("UPLOAD SUCCESS:", media.image.url)

        try:
            award_merchant_credits(user, 0.2, 'reward', "Upload Shop Gallery Image")
        except Exception as e:
            print("Credit reward error in upload_shop_media:", e)

        return Response({
            'message': 'Uploaded',
            'image': media.image.url
        })

    except Exception as e:
        print("UPLOAD ERROR:")
        print(traceback.format_exc())

        return Response({
            'error': str(e)
        }, status=500)



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




from math import radians, cos, sin, asin, sqrt
from django.utils import timezone


# Using the main calculate_distance function defined above


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_featured_banners(request):

    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    now = timezone.now()

    banners = list(FeaturedBanner.objects.filter(
        is_active=True
    ).order_by('-id'))

    from concurrent.futures import ThreadPoolExecutor

    def fetch_banner_dist(banner):
        if banner.expires_at and banner.expires_at < now:
            return banner.id, None
        if banner.global_banner:
            return banner.id, None
        if not lat or not lon:
            return banner.id, None
        if banner.latitude is None or banner.longitude is None:
            return banner.id, None
        try:
            d = calculate_distance(
                float(lat),
                float(lon),
                banner.latitude,
                banner.longitude
            )
            return banner.id, d
        except Exception:
            return banner.id, None

    with ThreadPoolExecutor(max_workers=20) as executor:
        dist_map = dict(executor.map(fetch_banner_dist, banners))

    visible_banners = []

    for banner in banners:

        # EXPIRED
        if banner.expires_at and banner.expires_at < now:
            continue

        # GLOBAL BANNER
        if banner.global_banner:
            visible_banners.append(banner)
            continue

        # NO LOCATION
        if not lat or not lon:
            continue

        # BANNER HAS NO LOCATION
        if banner.latitude is None or banner.longitude is None:
            continue

        distance = dist_map.get(banner.id)
        if distance is not None:
            if distance <= banner.visibility_radius:
                visible_banners.append(banner)

    # SORT:
    # 1. sponsored first
    # 2. higher priority first

    visible_banners.sort(
        key=lambda b: (
            not b.is_sponsored,
            -b.priority
        )
    )

    # FALLBACK
    if not visible_banners:

        visible_banners = FeaturedBanner.objects.filter(
            is_active=True,
            global_banner=True
        ).order_by('-priority', '-id')

    return Response(
        FeaturedBannerSerializer(
            visible_banners,
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

    playstore_link = (
        "https://play.google.com/store/apps/details?"
        "id=com.mydukan.dukanapp"
    )

    deep_link = f"dukan://shop/{shop.id}"

    return HttpResponse(f"""
        <html>
        <head>

            <title>{shop.name}</title>

            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">

            <!-- Open Graph -->
            <meta property="og:title" content="{shop.name}" />
            <meta property="og:description"
                  content="Open this shop in Dukan" />

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

            <script>

                // Try opening app
                window.location.href = "{deep_link}";

                // If app not installed → Play Store
                setTimeout(function() {{
                    window.location.href = "{playstore_link}";
                }}, 1500);

            </script>

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


from django.conf import settings
from django.core.mail import send_mail
import random


import threading
import random
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User

from .models import OTP


# =========================
# 📩 SEND OTP EMAIL
# =========================
import smtplib
from email.mime.text import MIMEText
from django.conf import settings

import requests
from django.conf import settings

import requests
from django.conf import settings

def send_otp_email(email, otp):
    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {
            "name": "mydukan",
            "email": "dukanpersonal316@gmail.com"
        },
        "to": [
            {"email": email}
        ],
        "subject": "mydukan Verification OTP",
        "htmlContent": f"<h2>Your OTP is {otp}</h2>"
    }

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print("BREVO RESPONSE:", response.status_code, response.text)

    except Exception as e:
        print("❌ BREVO ERROR:", str(e))
# =========================
# 🔢 SEND OTP
# =========================
import threading
@api_view(['POST'])
def send_otp(request):
    email = request.data.get('email', '').strip().lower()
    purpose = request.data.get('purpose', 'reset')  # 'signup' or 'reset'

    if not email:
        return Response({'error': 'Email required'}, status=400)

    # Only block merchant emails during customer signup
    if purpose == 'signup':
        existing = User.objects.filter(email=email).first()
        if existing:
            profile = Profile.objects.filter(user=existing).first()
            if profile and profile.role == 'merchant':
                return Response(
                    {'error': 'This email belongs to a merchant account.'},
                    status=400,
                )

    # Clean old OTPs
    OTP.objects.filter(email=email, is_verified=False).delete()

    otp = str(random.randint(100000, 999999))
    OTP.objects.create(email=email, otp=otp)

    thread = threading.Thread(target=send_otp_email, args=(email, otp))
    thread.daemon = True
    thread.start()

    return Response({'message': 'OTP sent'})
 


# =========================
# ✅ VERIFY OTP
# =========================
@api_view(['POST'])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    record = OTP.objects.filter(email=email, otp=otp).last()

    if not record or not record.is_valid():
        return Response({"error": "Invalid or expired OTP"}, status=400)

    record.is_verified = True
    record.save()

    try:
        user = User.objects.filter(email=email).first()
        if user:
            # Check if Verify Email reward is already given
            if not CreditTransaction.objects.filter(merchant=user, description='Verify Email').exists():
                award_merchant_credits(user, 3.0, 'reward', 'Verify Email')
    except Exception as e:
        print("Credit reward error in verify_otp:", e)

    return Response({"success": True})


# =========================
# 🔑 RESET PASSWORD
# =========================
@api_view(['POST'])
def reset_password(request):
    email = request.data.get('email')
    password = request.data.get('password')

    record = OTP.objects.filter(email=email, is_verified=True).last()

    if not record:
        return Response({"error": "OTP verification required"}, status=403)

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "User not found"}, status=404)

    user.set_password(password)
    user.save()

    # ❗ delete OTP after use
    record.delete()

    return Response({"success": True})


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

    amount = 5900  # ₹59 = 5900 paise

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

    amount = 5900  # ₹59

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


# ==============================
# 🏆 LOCAL HERO & ONDC API
# ==============================

from .models import StoreReport

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_store_report(request):
    shop_id = request.data.get('shop_id')
    report_type = request.data.get('report_type', 'status')
    details = request.data.get('details', '')

    shop = get_object_or_404(Shop, id=shop_id)
    user = request.user

    # Create the report
    report = StoreReport.objects.create(
        user=user,
        shop=shop,
        report_type=report_type,
        details=details,
        status='approved'
    )

    # Award points to User Profile
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.reward_credits += 10
    profile.save()

    return Response({
        "success": True,
        "message": "Report submitted successfully! You earned 10 reward credits.",
        "reward_credits": profile.reward_credits
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_leaderboard(request):
    # Fetch top 10 profiles sorted by reward_credits
    top_profiles = Profile.objects.order_by('-reward_credits')[:10]
    leaderboard = []
    for idx, p in enumerate(top_profiles):
        leaderboard.append({
            "rank": idx + 1,
            "username": p.user.username,
            "credits": p.reward_credits,
            "avatar": p.avatar
        })
    return Response(leaderboard)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def ondc_search(request):
    """
    ONDC /beckn search protocol compliant JSON mock API endpoint.
    Retrieves local stores and transforms them into beckn catalog format.
    """
    domain = request.data.get('context', {}).get('domain', 'ONDC:RET10') if isinstance(request.data, dict) else 'ONDC:RET10'
    
    # Query all active shops
    shops = Shop.objects.all()
    catalog_providers = []

    for s in shops:
        catalog_providers.append({
            "id": f"provider_shop_{s.id}",
            "descriptor": {
                "name": s.name,
                "short_desc": s.description or "Local retail shop indexed on MyDukan ONDC gateway.",
                "images": [s.image.url] if s.image else []
            },
            "categories": [
                {
                    "id": s.category,
                    "descriptor": {
                        "name": s.category
                    }
                }
            ],
            "items": [
                {
                    "id": f"item_{item.id}",
                    "descriptor": {
                        "name": item.name,
                        "short_desc": item.description or ""
                    },
                    "price": {
                        "currency": "INR",
                        "value": str(item.price) if item.price is not None else "0.00"
                    },
                    "category_id": s.category
                } for item in Item.objects.filter(shop=s)
            ]
        })

    beckn_response = {
        "context": {
            "domain": domain,
            "country": "IND",
            "city": "std:080",
            "action": "on_search",
            "core_version": "1.2.0",
            "bap_id": "ondc.mock.buyer.app",
            "bap_uri": "https://buyer.app/ondc",
            "bpp_id": "mydukan.ondc.gateway",
            "bpp_uri": "https://dukan-backend-0cc9.onrender.com/api/ondc",
            "transaction_id": "txn_8847291a-f38b-4a55-89f5-19a6d95f87b8",
            "message_id": "msg_90a42f61-2679-450f-a31d-b8d91a9df201",
            "timestamp": timezone.now().isoformat()
        },
        "message": {
            "catalog": {
                "bpp/descriptor": {
                    "name": "MyDukan Network Gateway"
                },
                "bpp/providers": catalog_providers
            }
        }
    }
    return Response(beckn_response)


# ==============================================================================
# 💰 MERCH ENGAGEMENT & CREDIT UTILITIES
# ==============================================================================

from .models import MerchantCredits, CreditTransaction

def award_merchant_credits(user, amount, transaction_type, description):
    """
    Awards or deducts credits.
    transaction_type: 'reward', 'ad_reward', 'spend', 'bonus'
    """
    credits_obj, created = MerchantCredits.objects.get_or_create(merchant=user)
    
    # Anti-abuse: check daily transaction limits
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if transaction_type == 'reward':
        # Rule 1: max 1.0 credit/day from product updates/edits
        if "update" in description.lower() or "edit" in description.lower():
            todays_update_rewards = CreditTransaction.objects.filter(
                merchant=user,
                transaction_type='reward',
                created_at__gte=today_start,
                description__icontains="update"
            ).values_list('amount', flat=True)
            if sum(todays_update_rewards) + amount > 1.0:
                return False, "Daily limit of 1.0 credit for product updates reached."

        # Rule 2: max 1.0 credit/day from open/close actions
        if "open" in description.lower() or "close" in description.lower():
            todays_status_rewards = CreditTransaction.objects.filter(
                merchant=user,
                transaction_type='reward',
                created_at__gte=today_start,
                description__iregex=r'(open|close)'
            ).values_list('amount', flat=True)
            if sum(todays_status_rewards) + amount > 1.0:
                return False, "Daily limit of 1.0 credit for shop open/close actions reached."

    # Update available balance
    if amount < 0 and credits_obj.available_credits + amount < 0:
        return False, "Insufficient credits."

    credits_obj.available_credits = round(credits_obj.available_credits + amount, 2)
    if amount > 0:
        credits_obj.total_earned = round(credits_obj.total_earned + amount, 2)
    else:
        credits_obj.total_spent = round(credits_obj.total_spent - amount, 2)
        
    credits_obj.save()
    
    # Save transaction record
    CreditTransaction.objects.create(
        merchant=user,
        amount=amount,
        transaction_type=transaction_type,
        description=description
    )
    return True, "Credits updated successfully."


def calculate_shop_health(shop):
    """
    Computes Shop Health Score (0 - 100) based on profile completeness,
    operating hours, banners, products, verification status, and activity.
    """
    score = 0
    
    # 1. Profile Complete (+20)
    if shop.name and shop.phone and shop.whatsapp_number and shop.address and shop.description:
        score += 20
    elif shop.name or shop.phone or shop.whatsapp_number or shop.address or shop.description:
        score += 10
        
    # 2. Opening/Closing Time Set (+10)
    if shop.opening_time and shop.closing_time:
        score += 10
        
    # 3. Banner Uploaded (+10)
    if ShopBanner.objects.filter(shop=shop).exists():
        score += 10
        
    # 4. At least 10 products (+15), at least 50 products (+15)
    prod_count = Item.objects.filter(shop=shop).count()
    if prod_count >= 50:
        score += 30
    elif prod_count >= 10:
        score += 15
        
    # 5. Open/Close Shop Regularly (+10)
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    has_recent_toggles = CreditTransaction.objects.filter(
        merchant=shop.owner,
        created_at__gte=seven_days_ago,
        description__iregex=r'(open|close)'
    ).exists()
    if has_recent_toggles:
        score += 10
        
    # 6. Recent Product Updates (+10)
    thirty_days_ago = now - timedelta(days=30)
    has_recent_updates = CreditTransaction.objects.filter(
        merchant=shop.owner,
        created_at__gte=thirty_days_ago,
        description__icontains="product"
    ).exists()
    if has_recent_updates:
        score += 10
        
    # 7. Verified Merchant (+10)
    # Pro merchants are considered verified
    if shop.is_pro_active():
        score += 10
        
    return min(max(score, 0), 100)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def credit_status(request):
    user = request.user
    credits_obj, _ = MerchantCredits.objects.get_or_create(merchant=user)
    shop = Shop.objects.filter(owner=user).first()
    
    # Calculate today's rewards
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_earned = sum(CreditTransaction.objects.filter(
        merchant=user,
        transaction_type__in=['reward', 'ad_reward'],
        created_at__gte=today_start,
        amount__gt=0
    ).values_list('amount', flat=True))
    
    # Compute gamification tier
    total_earned = credits_obj.total_earned
    health = calculate_shop_health(shop) if shop else 0
    
    if total_earned >= 150 and health >= 80:
        tier = "Platinum Merchant"
    elif total_earned >= 50 and health >= 60:
        tier = "Gold Merchant"
    elif total_earned >= 10:
        tier = "Silver Merchant"
    else:
        tier = "Bronze Merchant"
        
    # Limit specs
    is_pro = shop.is_pro_active() if shop else False
    product_limit = 20 + credits_obj.bought_limit_slots
    
    return Response({
        "available_credits": credits_obj.available_credits,
        "total_earned": credits_obj.total_earned,
        "total_spent": credits_obj.total_spent,
        "today_earned": round(today_earned, 2),
        "tier": tier,
        "shop_health": health,
        "product_limit": product_limit,
        "is_pro": is_pro,
        "credits_needed_for_upload": 10
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buy_limit_slot(request):
    user = request.user
    success, msg = award_merchant_credits(
        user,
        -10.0,
        'spend',
        "Unlocked 1 Additional Product Slot"
    )
    if not success:
        return Response({"error": msg}, status=400)
        
    credits_obj = MerchantCredits.objects.get(merchant=user)
    credits_obj.bought_limit_slots += 1
    credits_obj.save()
    
    return Response({
        "message": "Product slot unlocked successfully!",
        "available_credits": credits_obj.available_credits,
        "product_limit": 20 + credits_obj.bought_limit_slots
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ad_complete(request):
    user = request.user
    
    # Server-side validation of ad watch (simple signature verification check if needed,
    # or just record and award standard ad reward)
    ad_id = request.data.get('ad_id', 'general_ad')
    
    # Check duplicate reward for the same ad_id in the last 1 minute to prevent spam
    now = timezone.now()
    one_min_ago = now - timedelta(minutes=1)
    if CreditTransaction.objects.filter(
        merchant=user,
        transaction_type='ad_reward',
        description__icontains=ad_id,
        created_at__gte=one_min_ago
    ).exists():
        return Response({"error": "Duplicate ad reward request."}, status=400)
        
    award_merchant_credits(
        user,
        1.0,
        'ad_reward',
        f"Watched Rewarded Ad ({ad_id})"
    )
    
    credits_obj = MerchantCredits.objects.get(merchant=user)
    return Response({
        "message": "Congratulations! You earned 1 Credit.",
        "available_credits": credits_obj.available_credits
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_action(request):
    user = request.user
    action = request.data.get('action') # 'open' or 'close'
    
    shop = Shop.objects.filter(owner=user).first()
    if not shop:
        return Response({"error": "Shop not found"}, status=404)
        
    if action == 'open':
        shop.is_open = True
        shop.save()
        success, msg = award_merchant_credits(
            user,
            0.5,
            'reward',
            "Opened Shop Status Daily Action"
        )
    elif action == 'close':
        shop.is_open = False
        shop.save()
        success, msg = award_merchant_credits(
            user,
            0.5,
            'reward',
            "Closed Shop Status Daily Action"
        )
    else:
        return Response({"error": "Invalid action"}, status=400)
        
    return Response({
        "message": "Shop status updated successfully!",
        "is_open": shop.is_open,
        "reward_status": msg if not success else "+0.5 Credit rewarded"
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_metrics(request):
    # Enforce staff permissions if needed, but allow authenticated merchants for verification metrics
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Metrics summaries
    reminders_sent = CreditTransaction.objects.filter(description__icontains="Status Daily Action").count()
    open_clicked = CreditTransaction.objects.filter(description__icontains="Opened Shop").count()
    close_clicked = CreditTransaction.objects.filter(description__icontains="Closed Shop").count()
    
    credits_earned = sum(CreditTransaction.objects.filter(amount__gt=0).values_list('amount', flat=True))
    credits_spent = sum(CreditTransaction.objects.filter(amount__lt=0).values_list('amount', flat=True))
    ads_watched = CreditTransaction.objects.filter(transaction_type='ad_reward').count()
    
    total_products = Item.objects.count()
    total_shops = Shop.objects.count()

    # Telemetry
    from core.models import ORSApiCall, ActiveUser
    today_date = timezone.localdate()
    ors_calls_today = ORSApiCall.objects.filter(timestamp__gte=today_start).count()
    active_users_today = ActiveUser.objects.filter(date=today_date).count()
    
    return Response({
        "reminders_sent_est": reminders_sent,
        "open_clicked": open_clicked,
        "close_clicked": close_clicked,
        "credits_earned": round(credits_earned, 2),
        "credits_spent": round(abs(credits_spent), 2),
        "ads_watched": ads_watched,
        "total_products": total_products,
        "total_shops": total_shops,
        "ors_calls_today": ors_calls_today,
        "active_users_today": active_users_today
    })