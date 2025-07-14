from slm.settings import set_default

set_default("SECURE_SSL_REDIRECT", True)
set_default("CSRF_COOKIE_SECURE", True)
set_default("SESSION_COOKIE_SECURE", True)
set_default("SECURE_REFERRER_POLICY", "origin")
set_default("X_FRAME_OPTIONS", "DENY")
