'''
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
'''
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from slm.forms import UserAdminCreationForm, UserAdminChangeForm
from slm.models import Agency, Site


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


class SiteAdmin(admin.ModelAdmin):

    search_fields = ('name',)


class AgencyAdmin(admin.ModelAdmin):

    search_fields = ('name',)


class AlertAdmin(admin.ModelAdmin):
    pass


admin.site.register(User, UserAdmin)
admin.site.register(Agency, AgencyAdmin)
admin.site.register(Site, SiteAdmin)
admin.site.register(Alert, AlertAdmin)
