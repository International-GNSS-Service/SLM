"""
https://docs.djangoproject.com/en/stable/ref/applications/
"""

from django.apps import AppConfig


class {{ extension_app_class }}Config(AppConfig):
    
    name = "{{ extension_app }}"

    def ready(self):
        pass

