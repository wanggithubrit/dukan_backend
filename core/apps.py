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