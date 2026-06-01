import os
import sys
import django
import urllib.request
import json

# Setup Django environment
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dukan_backend.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Shop, FeaturedBanner, Item, ShopMedia, ShopBanner

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"❌ Failed to fetch URL ({url}): {e}")
        return None

def seed_database():
    print("⏳ Fetching shops list from production Render backend...")
    shops_data = fetch_json("https://dukan-backend-0cc9.onrender.com/api/shops/?lat=25.7937&lon=93.7297")
    if not shops_data:
        print("❌ Could not load shops list.")
        return

    print(f"✅ Fetched {len(shops_data)} shops. Populating local database...")
    
    # Create a default owner user if not exists
    default_owner, _ = User.objects.get_or_create(
        username="default_merchant",
        defaults={"email": "merchant@mydukan.online", "is_staff": False}
    )
    default_owner.set_password("merchant123")
    default_owner.save()

    # Clear existing local data
    Item.objects.all().delete()
    ShopMedia.objects.all().delete()
    ShopBanner.objects.all().delete()
    Shop.objects.all().delete()

    created_count = 0
    for s in shops_data:
        shop_id = s.get('id')
        if not shop_id:
            continue
        try:
            # We recreate the shop locally with accurate production coordinates and images
            shop = Shop.objects.create(
                id=shop_id,
                owner=default_owner,
                name=s.get('name', 'Mock Shop'),
                category=s.get('category', 'General'),
                phone=s.get('phone', '1234567890'),
                whatsapp_number=s.get('whatsapp_number', ''),
                address=s.get('address', 'Local Address'),
                description=s.get('description', 'Local Description'),
                image=s.get('image', ''),
                latitude=s.get('latitude'),
                longitude=s.get('longitude'),
                is_open=s.get('is_open', True),
                plan=s.get('plan', 'free')
            )
            created_count += 1
            print(f"  🏪 Seeded shop: {shop.name} (ID: {shop.id})")

            # Fetch details for this shop to seed items, media, and banners
            details = fetch_json(f"https://dukan-backend-0cc9.onrender.com/api/shops/{shop_id}/")
            if details:
                # Seed Items
                items_data = details.get('items', [])
                for item in items_data:
                    Item.objects.create(
                        shop=shop,
                        id=item.get('id'),
                        name=item.get('name', 'Item'),
                        description=item.get('description', ''),
                        price=item.get('price'),
                        image=item.get('image', ''),
                        quantity=item.get('quantity', 0),
                        track_quantity=item.get('track_quantity', False)
                    )
                if items_data:
                    print(f"    📦 Seeded {len(items_data)} products")

                # Seed Media (Gallery)
                media_data = details.get('media', [])
                for media_item in media_data:
                    ShopMedia.objects.create(
                        shop=shop,
                        id=media_item.get('id'),
                        image=media_item.get('image', '')
                    )
                if media_data:
                    print(f"    📸 Seeded {len(media_data)} gallery media entries")

                # Seed Shop Banners
                banners_data = details.get('banners', [])
                for banner in banners_data:
                    ShopBanner.objects.create(
                        shop=shop,
                        id=banner.get('id'),
                        banner_type=banner.get('banner_type', 'image'),
                        image=banner.get('image', ''),
                        title=banner.get('title', ''),
                        subtitle=banner.get('subtitle', ''),
                        discount=banner.get('discount', ''),
                        template=banner.get('template', 'green')
                    )
                if banners_data:
                    print(f"    📢 Seeded {len(banners_data)} banners")

        except Exception as err:
            print(f"  ❌ Error seeding {s.get('name')}: {err}")

    # Seed featured banners
    FeaturedBanner.objects.all().delete()
    try:
        FeaturedBanner.objects.create(
            title="DUKAN",
            subtitle="MAKE LOCAL SHOPPING EASY",
            banner_type="image",
            background_color="#1B6B50",
            small_text="save your time, energy and money.",
            priority=0,
            is_sponsored=False,
            link="https://www.instagram.com/dukan.service/",
            latitude=None,
            longitude=None,
            visibility_radius=25,
            global_banner=True,
            expires_at=None,
            is_active=True
        )
        print("  Status: Seeded FeaturedBanner: DUKAN")
    except Exception as err:
        print(f"  ❌ Error seeding FeaturedBanner: {err}")

    print(f"\n✨ Successfully seeded {created_count} shops, items, media, and banners into db.sqlite3!")

if __name__ == '__main__':
    seed_database()
