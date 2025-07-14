from slm.settings import set_default

set_default("ACCOUNT_LOGIN_ON_PASSWORD_RESET", True)
set_default("ACCOUNT_UNIQUE_EMAIL", True)
set_default("ACCOUNT_USER_MODEL_USERNAME_FIELD", None)
set_default("ACCOUNT_LOGIN_METHODS", {"email"})
set_default("ACCOUNT_SIGNUP_FIELDS", ["email*", "password1*", "password2*"])
set_default("LOGIN_URL", "/accounts/login/")
set_default("LOGIN_REDIRECT_URL", "/")

set_default(
    "AUTHENTICATION_BACKENDS",
    [
        # Needed to login by username in Django admin, regardless of `allauth`
        "django.contrib.auth.backends.ModelBackend",
        # `allauth` specific authentication methods, such as login by e-mail
        "allauth.account.auth_backends.AuthenticationBackend",
    ],
)
