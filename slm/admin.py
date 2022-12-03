"""
Handles admin site for Django project.


NOTES:
This file essentially controls what is seen on the admin site
as well as overriding the default methods for adding
a new admin user. 

To add a new model group to admin site simply add 
"admin.site.register(NEW MODEL GROUP NAME)"
to bottom of file.

Same process can be applied for unregistering a model
group (same command with unregister).

More info:
https://docs.djangoproject.com/en/3.2/ref/contrib/admin/
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from slm.forms import UserAdminCreationForm, UserAdminChangeForm
from slm.models import Agency, Site, SatelliteSystem
from django.utils.translation import gettext as _
from slm.authentication import initiate_password_resets


User = get_user_model() # accesses custom user model

# Note that "Group" is a built in feature
admin.site.unregister(Group) # no initial need to see Group


class UserAdmin(BaseUserAdmin):
    add_form = UserAdminCreationForm # see slm/forms.py
    form = UserAdminChangeForm # see slm/forms.py

    # chooses which fields to display for admin users
    list_display = ('email', 'is_superuser', 'is_staff', 'agency')
    search_fields = ['email']
    readonly_fields = []

    ordering = ['email']
    filter_horizontal = ()
    list_filter = ('agency__name',)
    fieldsets = (
        (None, {
            'fields': ('email', 'password', 'is_superuser', 'is_staff', 'agency')}
         ),
    )
    add_fieldsets = (
        (None, {
            'fields': ('email', 'password', 'password_2', 'is_superuser', 'is_staff', 'agency')}
         ),
    )

    actions = ['request_password_reset']

    def request_password_reset(self, request, queryset):
        initiate_password_resets(queryset, request=request)

    request_password_reset.short_description = _(
        'Request password resets.'
    )


class NetworkInline(admin.TabularInline):
    model = Network.sites.through
    extra = 0


class AgencyInline(admin.TabularInline):
    model = Agency.sites.through
    extra = 0


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):

    search_fields = ('name',)
    inlines = [AgencyInline, NetworkInline]
    exclude = ['agencies']


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):

    search_fields = ('name',)


class AgencyAdmin(admin.ModelAdmin):

    search_fields = ('name',)


class AlertAdmin(admin.ModelAdmin):
    pass


class SatelliteSystemAdmin(admin.ModelAdmin):
    pass


class AntennaAdmin(admin.ModelAdmin):
    pass


class ReceiverAdmin(admin.ModelAdmin):
    pass


class RadomeAdmin(admin.ModelAdmin):
    pass


class ManufacturerAdmin(admin.ModelAdmin):
    pass


class SiteFileUploadAdmin(admin.ModelAdmin):

    search_fields = ['site__name']
    list_filter = ['file_type', 'log_format']


admin.site.register(User, UserAdmin)
admin.site.register(Agency, AgencyAdmin)
admin.site.register(Alert, AlertAdmin)
admin.site.register(SatelliteSystem, SatelliteSystemAdmin)
admin.site.register(Antenna, AntennaAdmin)
admin.site.register(Receiver, ReceiverAdmin)
admin.site.register(Radome, RadomeAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(SiteFileUpload, SiteFileUploadAdmin)
