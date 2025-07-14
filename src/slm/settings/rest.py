"""
Django rest framework configuration parameters

https://www.django-rest-framework.org/
"""

from slm.settings import set_default

set_default(
    "REST_FRAMEWORK",
    {
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework.authentication.SessionAuthentication",
            #'slm.authentication.SignatureAuthentication', TODO library authentication
        ],
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticatedOrReadOnly"
        ],
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
            #'drf_renderer_xlsx.renderers.XLSXRenderer',
            #'rest_framework_csv.renderers.CSVRenderer'
        ],
    },
)
