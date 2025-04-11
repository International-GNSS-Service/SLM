from django.apps import AppConfig


class MapConfig(AppConfig):
    name = "slm.map"
    label = name.replace(".", "_")
    verbose_name = " SLM Map"
