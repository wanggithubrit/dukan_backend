from django.apps import AppConfig
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            username = "admin"

            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(
                    username=username,
                    email="admin@gmail.com",
                    password="admin123"
                )

        except Exception:
            pass

        # Start background thread to automatically sync shop open/close status
        import os
        import threading
        import time

        def auto_status_sync_worker():
            print("[AutoSync] Starting shop status auto-sync background thread...")
            while True:
                try:
                    from core.models import Shop
                    for shop in Shop.objects.filter(auto_reminder_enabled=True):
                        shop.sync_status()
                except Exception as e:
                    print("[AutoSync] Error in auto-sync worker:", e)
                
                time.sleep(15)

        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('RUN_MAIN'):
            t = threading.Thread(target=auto_status_sync_worker, daemon=True)
            t.start()