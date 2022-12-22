from django.utils.timezone import now
from slm.utils import set_protocol


class SetLastVisitMiddleware:
    """
    A simple middleware that updates the last_visit time on a User object
    for each request that user makes. Remove from the middleware stack to
    disable.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_protocol(request)
        if request.user.is_authenticated:
            request.user.last_visit = now()
            request.user.save()

        response = self.get_response(request)
        return response
