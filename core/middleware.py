from django.db import OperationalError
from django.utils import timezone

class PlanExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from core.models import Shop

            Shop.objects.filter(
                plan='pro',
                plan_expiry__lt=timezone.now()
            ).update(plan='free', plan_expiry=None)

        except OperationalError:
            pass

        return self.get_response(request)