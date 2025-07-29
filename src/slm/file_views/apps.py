from django.apps import AppConfig


class FileViewsConfig(AppConfig):
    name = "slm.file_views"
    label = name.replace(".", "_")
    verbose_name = " File Views"
