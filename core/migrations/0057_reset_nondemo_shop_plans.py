from django.db import migrations

def reset_nondemo_plans(apps, schema_editor):
    Shop = apps.get_model('core', 'Shop')
    for shop in Shop.objects.all():
        is_demo = False
        if "demo" in shop.name.lower():
            is_demo = True
        elif shop.owner and ("demo" in shop.owner.username.lower() or "default_merchant" in shop.owner.username.lower()):
            is_demo = True
        elif not shop.owner:
            is_demo = True

        if not is_demo and shop.plan == 'pro_plus':
            shop.plan = 'free'
            shop.plan_expiry = None
            shop.save()

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0056_order_customer_latitude_order_customer_longitude"),
    ]

    operations = [
        migrations.RunPython(reset_nondemo_plans),
    ]
