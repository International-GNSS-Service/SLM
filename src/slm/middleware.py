from django.conf import settings
from django.utils.timezone import now

from slm.utils import set_protocol


class SetLastVisitMiddleware:
    """
    A simple middleware that updates the last_activity time on a User object
    for each request that user makes. Remove from the middleware stack to
    disable.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_protocol(request)
        if request.user.is_authenticated:
            # if this is the first login - check if we should enable emails
            if request.user.last_activity is None and getattr(
                settings, "SLM_EMAILS_REQUIRE_LOGIN", True
            ):
                request.user.silence_alerts = False
            request.user.last_activity = now()
            request.user.save()

        response = self.get_response(request)
        return response
