"""
This is taken and modified from here: https://github.com/ahknight/drf-httpsig

There is an http signature IETF standard in the works, presumably a more mature and maintained
library will emerge at some point - when that happens this should be replaced with that one.
"""

from functools import lru_cache

from allauth.account import app_settings
from allauth.account.adapter import get_adapter
from allauth.account.app_settings import AuthenticationMethod  # do not remove!
from allauth.account.forms import EmailAwarePasswordResetTokenGenerator
from allauth.account.utils import user_pk_to_url_str, user_username
from allauth.utils import build_absolute_uri
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.module_loading import import_string
from rest_framework import authentication, exceptions

"""
Reusing failure exceptions serves several purposes:
    1. Lack of useful information regarding the failure inhibits attackers
    from learning about valid keyIDs or other forms of information leakage.
    Using the same actual object for any failure makes preventing such
    leakage through mistakenly-distinct error messages less likely.
    2. In an API scenario, the object is created once and raised many times
    rather than generated on every failure, which could lead to higher loads
    or memory usage in high-volume attack scenarios.
"""
FAILED = exceptions.AuthenticationFailed("Invalid signature.")


class SignatureAuthentication(authentication.BaseAuthentication):
    """
    DRF authentication class for HTTP Signature support.

    You must subclass this class in your own project and implement the
    `fetch_user_data(self, keyId, algorithm)` method, returning a tuple of
    the User object and a bytes object containing the user's secret. Note
    that key_id and algorithm are DIRTY as they are supplied by the client
    and so must be verified in your subclass!

    You may set the following class properties in your subclass to configure
    authentication for your particular use case:

    :param www_authenticate_realm:  Default: "api"
    :param required_headers:        Default: ["(request-target)", "date"]
    """

    www_authenticate_realm = "api"
    required_headers = ["date"]

    def fetch_user_data(self, api_key, algorithm="hmac-sha256"):
        """Retuns a tuple (User, secret) or (None, None)."""
        try:
            user = get_user_model().objects.get(username=api_key)
            if not user.is_active:
                return None, None
            secret = user.secret
            if isinstance(secret, memoryview):
                secret = secret.tobytes()
            return user, secret
        except get_user_model().DoesNotExist:
            return None, None

    def authenticate_header(self, request):
        """
        DRF sends this for unauthenticated responses if we're the primary
        authenticator.
        """
        h = " ".join(self.required_headers)
        return 'Signature realm="%s",headers="%s"' % (self.www_authenticate_realm, h)

    def authenticate(self, request):
        from httpsig import HeaderVerifier, utils

        """
        Perform the actual authentication.

        Note that the exception raised is always the same. This is so that we
        don't leak information about in/valid keyIds and other such useful
        things.
        """
        auth_header = authentication.get_authorization_header(request)
        if not auth_header or len(auth_header) == 0:
            return None

        method, fields = utils.parse_authorization_header(auth_header)

        # Ignore foreign Authorization headers.
        if method.lower() != "signature":
            return None

        # Verify basic header structure.
        if len(fields) == 0:
            raise FAILED

        # Ensure all required fields were included.
        if len(set(("keyid", "algorithm", "signature")) - set(fields.keys())) > 0:
            raise FAILED

        # Fetch the secret associated with the keyid
        user, secret = self.fetch_user_data(
            fields["keyid"], algorithm=fields["algorithm"]
        )

        if not (user and secret):
            raise FAILED

        # Gather all request headers and translate them as stated in the Django docs:
        # https://docs.djangoproject.com/en/1.6/ref/request-response/#django.http.HttpRequest.META
        headers = {}
        for key in request.META.keys():
            if key.startswith("HTTP_") or key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                header = key[5:].lower().replace("_", "-")
                headers[header] = request.META[key]

        # Verify headers
        hs = HeaderVerifier(
            headers,
            secret,
            required_headers=self.required_headers,
            method=request.method.lower(),
            path=request.get_full_path(),
        )

        # All of that just to get to this.
        if not hs.verify():
            raise FAILED

        return (user, fields["keyid"])


def initiate_password_resets(users, request=None):
    """

    :param users: Either an iterable (including queryset) of user accounts or
        a single user account.
    :return:
    """
    if isinstance(users, get_user_model()):
        users = [users]

    token_generator = EmailAwarePasswordResetTokenGenerator()

    for user in users:
        temp_key = token_generator.make_token(user)

        # send the password reset email
        path = reverse(
            "account_reset_password_from_key",
            kwargs=dict(uidb36=user_pk_to_url_str(user), key=temp_key),
        )
        url = build_absolute_uri(request, path)

        context = {
            "current_site": get_current_site(request),
            "user": user,
            "password_reset_url": url,
            "request": request,
        }

        if app_settings.AUTHENTICATION_METHOD != AuthenticationMethod.EMAIL:
            context["username"] = user_username(user)

        get_adapter(request).send_mail(
            "account/email/password_reset_key", user.email, context
        )


@lru_cache(maxsize=None)
def permissions():
    try:
        return import_string(
            getattr(
                settings, "SLM_PERMISSIONS", "slm.authentication.default_permissions"
            )
        )().all()
    except ImportError:
        # this is not critical don't make it mean! - so we fail quietly
        # a check for this setting is performed in check
        from django.contrib.auth.models import Permission

        return Permission.objects.all()


def default_permissions() -> QuerySet[Permission]:
    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType

    return Permission.objects.filter(
        content_type=ContentType.objects.get_for_model(get_user_model()),
        codename__in=[perm[0] for perm in get_user_model()._meta.permissions],
    )
