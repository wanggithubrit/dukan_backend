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
from core.models import Shop

def seed_database():
    print("⏳ Fetching shops data from production Render backend...")
    url = "https://dukan-backend-0cc9.onrender.com/api/shops/?lat=25.7937&lon=93.7297"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            shops_data = json.loads(response.read().decode())
    except Exception as e:
        print(f"❌ Failed to fetch production data: {e}")
        return

    print(f"✅ Fetched {len(shops_data)} shops. Populating local database...")
    
    # Create a default owner user if not exists
    default_owner, _ = User.objects.get_or_create(
        username="default_merchant",
        defaults={"email": "merchant@mydukan.online", "is_staff": False}
    )
    default_owner.set_password("merchant123")
    default_owner.save()

    # Clear existing local shops to prevent duplicates
    Shop.objects.all().delete()

    created_count = 0
    for s in shops_data:
        try:
            # We recreate the shop locally with accurate production coordinates
            Shop.objects.create(
                owner=default_owner,
                name=s.get('name', 'Mock Shop'),
                category=s.get('category', 'General'),
                phone=s.get('phone', '1234567890'),
                whatsapp_number=s.get('whatsapp_number', ''),
                address=s.get('address', 'Local Address'),
                description=s.get('description', 'Local Description'),
                latitude=s.get('latitude'),
                longitude=s.get('longitude'),
                is_open=s.get('is_open', True),
                plan=s.get('plan', 'free')
            )
            created_count += 1
            print(f"  🏪 Seeded shop: {s.get('name')}")
        except Exception as err:
            print(f"  ❌ Error seeding {s.get('name')}: {err}")

    print(f"\n✨ Successfully seeded {created_count} shops into db.sqlite3!")

if __name__ == '__main__':
    seed_database()
