from django.utils import timezone
from .models import Shop

class PlanExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        Shop.objects.filter(
            plan='pro',
            plan_expiry__lt=timezone.now()
        ).update(
            plan='free',
            plan_expiry=None
        )

        return self.get_response(request)