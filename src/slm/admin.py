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
https://docs.djangoproject.com/en/stable/ref/contrib/admin/
"""

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import BooleanField, Count, Q
from django.db.models.expressions import ExpressionWrapper
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from hijack.contrib.admin import HijackUserAdminMixin
from polymorphic.admin import (
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
    PolymorphicParentModelAdmin,
)

from slm.authentication import initiate_password_resets, permissions
from slm.defines import SiteLogStatus
from slm.models import (
    About,
    Agency,
    AgencyAlert,
    Alert,
    AntCal,
    Antenna,
    ArchivedSiteLog,
    ArchiveIndex,
    DataCenter,
    Equipment,
    GeodesyMLInvalid,
    Help,
    LogEntry,
    Manufacturer,
    Network,
    Radome,
    Receiver,
    ReviewRequested,
    SatelliteSystem,
    Site,
    SiteAlert,
    SiteFileUpload,
    SiteLogPublished,
    TideGauge,
    UnpublishedFilesAlert,
    UpdatesRejected,
    UserAlert,
    UserProfile,
)
from slm.widgets import GraphicTextarea

admin.site.unregister(Group)


class UserAgencyInline(admin.TabularInline):
    model = Agency.users.through
    extra = 0


class TideGaugeInline(admin.TabularInline):
    model = TideGauge.sites.through
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("site", "gauge")


class SiteTGInline(admin.TabularInline):
    model = Site.tide_gauges.through
    extra = 0


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


class ModeratorListFilter(admin.SimpleListFilter):
    title = _("Moderator")

    parameter_name = "moderator"

    def lookups(self, request, model_admin):
        return (
            (True, _("Yes")),
            (False, _("No")),
        )

    def queryset(self, request, queryset):
        queryset = queryset.annotate_moderator_status()
        if self.value() is not None:
            return queryset.filter(moderator=self.value())
        return queryset


class UserAdmin(HijackUserAdminMixin, BaseUserAdmin):
    # chooses which fields to display for admin users
    list_display = (
        "email",
        "first_name",
        "last_name",
        "last_activity",
        "is_active",
        "is_superuser",
        "moderator",
    )
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["last_activity", "date_joined"]

    inlines = [UserAgencyInline, ProfileInline]

    ordering = ("-last_activity",)
    list_filter = (
        "is_superuser",
        "is_active",
        "html_emails",
        "silence_alerts",
        ModeratorListFilter,
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal Info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_superuser", "groups", "user_permissions"),
            },
        ),
        (_("Preferences"), {"fields": ("silence_alerts", "html_emails")}),
        (_("Important Dates"), {"fields": ("last_activity", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "is_superuser",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    actions = [
        "request_password_reset",
        "enable_emails",
        "disable_emails",
        "deactivate",
        "activate",
    ]

    def moderator(self, obj):
        return obj.moderator

    moderator.boolean = True

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

    def request_password_reset(self, request, queryset):
        initiate_password_resets(queryset, request=request)

    request_password_reset.short_description = _("Request password resets.")

    def deactivate(self, request, queryset):
        queryset.update(is_active=False)

    deactivate.short_description = _("Disable user accounts.")

    def activate(self, request, queryset):
        queryset.update(is_active=True)

    activate.short_description = _("Re-activate user accounts.")

    def enable_emails(self, request, queryset):
        queryset.update(silence_alerts=False)

    enable_emails.short_description = _("Enable alert emails for users.")

    def disable_emails(self, request, queryset):
        queryset.update(silence_alerts=True)

    disable_emails.short_description = _("Disable alert emails for users.")

    def get_actions(self, request):
        """
        Remove delete_selected action. too tempting! Preferred method of
        account disabling is deactivation. Accounts can be fully wiped from
        the system using the delete button on the user page but this will
        remove them from all logs and history, so it should only be done in
        extreme or specific cases.
        """
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # remove all of the standard django object permissions from the admin
        # they are just clutter because we restrict access to the admin to
        # superusers. The only permissions that should be shown are permissions
        # specific the to the SLM
        user_permissions = form.base_fields.get("user_permissions", None)
        if user_permissions:
            user_permissions.queryset = permissions()
        silence_alerts = form.base_fields.get("silence_alerts")
        if silence_alerts is not None:
            silence_alerts.initial = getattr(settings, "SLM_EMAILS_REQUIRE_LOGIN", True)
        return form


class GroupAdmin(BaseGroupAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # remove all of the standard django object permissions from the admin
        # they are just clutter because we restrict access to the admin to
        # superusers. The only permissions that should be shown are permissions
        # specific the to the SLM
        permissions_field = form.base_fields.get("permissions", None)
        if permissions_field:
            permissions_field.queryset = permissions()
        return form


class NetworkInline(admin.TabularInline):
    model = Network.sites.through
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("network", "site")


class SiteAgencyInline(admin.TabularInline):
    model = Agency.sites.through
    extra = 0


class SiteIndexInline(admin.TabularInline):
    model = ArchiveIndex
    extra = 0
    readonly_fields = ("time_range_display",)
    fields = ("time_range_display",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("site")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def time_range_display(self, obj):
        if obj and obj.pk:
            begin_formatted = obj.begin.strftime("%Y-%m-%d %H:%M:%S")
            end_formatted = obj.end.strftime("%Y-%m-%d %H:%M:%S") if obj.end else ""
            time_range = f"{begin_formatted} - {end_formatted}"
            url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
                args=[obj.pk],
            )
            return format_html('<a href="{}">{}</a>', url, time_range)
        return "-"

    time_range_display.short_description = "Time Range"


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    inlines = [SiteAgencyInline, NetworkInline, TideGaugeInline, SiteIndexInline]
    exclude = ["agencies"]


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    list_filter = ("public",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "sites":
            kwargs["queryset"] = Site.objects.order_by("name")
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class AgencyUserInline(admin.TabularInline):
    model = Agency.users.through
    extra = 0
    max_num = 0
    readonly_fields = ["user", "is_moderator"]

    def is_moderator(self, obj):
        return obj.user.is_moderator()

    is_moderator.boolean = True


class AgencyAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    list_filter = ("public",)
    inlines = [AgencyUserInline]


class DataCenterAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)


class SatelliteSystemAdmin(admin.ModelAdmin):
    pass


class TideGaugeAdmin(admin.ModelAdmin):
    search_fields = ("name", "sonel_id")
    list_display = ("name", "sonel_link")
    inlines = [SiteTGInline]

    def sonel_link(self, obj):
        return mark_safe(
            f'<a href="{obj.sonel_link}" target="_blank">{obj.sonel_link}</a>'
        )

    def get_queryset(self, request):
        return self.model.objects.prefetch_related("sites")


class AntennaCalibrationAdmin(admin.ModelAdmin):
    search_fields = ("antenna__model", "radome__model")
    list_display = ("antenna", "radome", "method_label", "calibrated")
    list_filter = ("method",)

    ordering = ("-calibrated",)

    def method_label(self, obj):
        return str(obj.method.label)

    def get_queryset(self, request):
        return self.model.objects.select_related("antenna", "radome")


class LogEntryAdmin(admin.ModelAdmin):
    search_fields = ("site__name",)
    list_display = ("timestamp", "site", "type", "ip")
    list_filter = ("type", "section")
    ordering = ("-timestamp",)
    readonly_fields = [
        field.name for field in LogEntry._meta.get_fields() if field.name != "id"
    ]

    def get_queryset(self, request):
        return self.model.objects.select_related("section", "file", "site", "user")


class HelpAdmin(admin.ModelAdmin):
    pass


class AboutAdmin(admin.ModelAdmin):
    pass


class SiteFileUploadAdmin(admin.ModelAdmin):
    search_fields = ["site__name"]
    list_filter = ["file_type", "log_format"]


class AlertAdminMixin:
    actions = ["send_emails"]

    def send_emails(self, request, queryset):
        queryset.send_emails(request)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["issuer"].initial = request.user
        form.base_fields["issuer"].disabled = True
        form.base_fields["issuer"].widget.can_change_related = False
        form.base_fields["issuer"].widget.can_delete_related = False
        form.base_fields["issuer"].widget.can_add_related = False
        form.base_fields["priority"].initial = getattr(
            self.model, "DEFAULT_PRIORITY", 0
        )
        return form


class AlertChildAdmin(AlertAdminMixin, PolymorphicChildModelAdmin):
    base_model = Alert


@admin.register(UserAlert)
class UserAlertAdmin(AlertChildAdmin):
    base_model = UserAlert
    show_in_index = True


@admin.register(SiteAlert)
class SiteAlertAdmin(AlertChildAdmin):
    base_model = SiteAlert
    show_in_index = True


@admin.register(AgencyAlert)
class AgencyAlertAdmin(AlertChildAdmin):
    base_model = AgencyAlert
    show_in_index = True


@admin.register(GeodesyMLInvalid)
class GeodesyMLInvalidAdmin(AlertChildAdmin):
    base_model = GeodesyMLInvalid
    show_in_index = True


@admin.register(ReviewRequested)
class ReviewRequestedAdmin(AlertChildAdmin):
    base_model = ReviewRequested
    show_in_index = True


@admin.register(UnpublishedFilesAlert)
class UnpublishedFilesAlertAdmin(AlertChildAdmin):
    base_model = UnpublishedFilesAlert
    show_in_index = True


@admin.register(SiteLogPublished)
class SiteLogPublishedAdmin(AlertChildAdmin):
    base_model = SiteLogPublished
    show_in_index = True


@admin.register(UpdatesRejected)
class UpdatesRejectedAdmin(AlertChildAdmin):
    base_model = UpdatesRejected
    show_in_index = True


@admin.register(Alert)
class AlertAdmin(AlertAdminMixin, PolymorphicParentModelAdmin):
    """The parent alert model admin"""

    base_model = Alert
    child_models = (
        Alert,
        UserAlert,
        SiteAlert,
        AgencyAlert,
        GeodesyMLInvalid,
        ReviewRequested,
        UpdatesRejected,
    )
    list_filter = (PolymorphicChildModelFilter,)


class ArchiveFileInline(admin.TabularInline):
    model = ArchivedSiteLog
    extra = 0
    readonly_fields = [
        field.name if field.name != "file" else "path"
        for field in ArchivedSiteLog._meta.get_fields()
        if field.name not in ["id", "site", "thumbnail", "name", "timestamp"]
    ] + ["view_file"]
    can_delete = True
    exclude = ["site", "file", "thumbnail", "name", "timestamp"]

    def path(self, obj):
        return format_html('<a href="{}" download>{}</a>', obj.link, obj.file.name)

    def has_add_permission(self, request, obj):
        return False

    def view_file(self, obj):
        if obj.pk:
            return format_html(
                '<button type="button" class="button view-file" data-url="{}">{}</button>',
                obj.link,
                _("View"),
            )
        return ""

    view_file.short_description = _("View")


class ArchiveIndexAdmin(admin.ModelAdmin):
    search_fields = ["site__name"]
    list_display = ("site", "begin", "end")

    inlines = [ArchiveFileInline]
    readonly_fields = ["site"]

    def begin(self, obj):
        return obj.begin

    def end(self, obj):
        return obj.end

    def get_queryset(self, request):
        return self.model.objects.select_related("site").prefetch_related("files")

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "slm/js/file_modal.js",
        )


"""
class SLMAdminSite(admin.AdminSite):

    def get_app_list(self, request, app_label=None):
        #Return a sorted list of all the installed apps that have been
        #registered in this site.
        ret = super().get_app_list(request, app_label=app_label)

        # force group all alerts together
        spoofed_alerts_app = {
            'app_label': 'slm_alerts',
            'app_url': '/admin/slm/alerts/',
            'has_module_perms': True,
            'models': [],
            'name': 'SLM Alerts'
        }

        for app in ret:
            models = []
            for model in app['models']:
                if issubclass(model['model'], Alert):
                    spoofed_alerts_app['models'].append(model)
                else:
                    models.append(model)
            app['models'] = models

        ret.insert(1, spoofed_alerts_app)
        return ret
"""

# admin.site = SLMAdminSite()


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    search_fields = ("name", "full_name")
    ordering = ("name",)
    list_display = ("name", "full_name", "url")


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        obj = kwargs.get("instance", None)
        self.fields["replaced"].required = False
        if obj:
            self.fields["replaced"].queryset = self.Meta.model.objects.filter(
                manufacturer=obj.manufacturer
            )


class EquipmentAdmin(admin.ModelAdmin):
    search_fields = ("model",)
    ordering = ("model",)
    list_display = ("model", "manufacturer", "state", "references", "active")
    list_filter = ("state", "manufacturer")

    @admin.display(ordering="references")
    def references(self, obj):
        return obj.references

    @admin.display(ordering="active")
    def active(self, obj):
        return obj.active

    related_siteform = None  # deriving classes must set this

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("manufacturer")
            .annotate(
                references=Count(
                    self.related_siteform,
                    filter=(Q(**{f"{self.related_siteform}__published": True})),
                    distinct=True,
                ),
                active=Count(
                    f"{self.related_siteform}__site",
                    filter=(
                        Q(**{f"{self.related_siteform}__published": True})
                        & Q(**{f"{self.related_siteform}__removed__isnull": True})
                        & Q(
                            **{
                                f"{self.related_siteform}__site__status__in": SiteLogStatus.active_states()
                            }
                        )
                    ),
                    distinct=True,
                ),
            )
        )


class HasGraphicListFilter(admin.SimpleListFilter):
    title = _("Has Graphic?")

    parameter_name = "graphic"

    def lookups(self, request, model_admin):
        return (
            (True, _("Yes")),
            (False, _("No")),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        qry = ~Q(graphic__isnull=True) & ~Q(graphic="")
        if self.value().lower() == "false":
            qry = ~qry
        return queryset.filter(qry)


@admin.register(Antenna)
class AntennaAdmin(EquipmentAdmin):
    class AntennaForm(EquipmentForm):
        graphic = forms.CharField(
            strip=False,
            widget=GraphicTextarea,
            help_text=Antenna._meta.get_field("graphic").help_text,
        )

        class Meta(EquipmentForm.Meta):
            model = Antenna

    form = AntennaForm
    related_siteform = "site_antennas"

    list_display = (*EquipmentAdmin.list_display, "has_graphic")
    list_filter = (HasGraphicListFilter, *EquipmentAdmin.list_filter)

    def has_graphic(self, obj):
        return _("Yes") if obj.has_graphic else _("No")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                has_graphic=ExpressionWrapper(
                    ~Q(graphic__isnull=True) & ~Q(graphic=""),
                    output_field=BooleanField(),
                )
            )
        )


@admin.register(Receiver)
class ReceiverAdmin(EquipmentAdmin):
    class ReceiverForm(EquipmentForm):
        class Meta(EquipmentForm.Meta):
            model = Receiver

    form = ReceiverForm
    related_siteform = "site_receivers"


@admin.register(Radome)
class RadomeAdmin(EquipmentAdmin):
    class RadomeForm(EquipmentForm):
        class Meta(EquipmentForm.Meta):
            model = Radome

    form = RadomeForm
    related_siteform = "site_radomes"


admin.site.site_header = _("SLM Admin")

admin.site.register(get_user_model(), UserAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Agency, AgencyAdmin)
admin.site.register(TideGauge, TideGaugeAdmin)
admin.site.register(SatelliteSystem, SatelliteSystemAdmin)
admin.site.register(SiteFileUpload, SiteFileUploadAdmin)
admin.site.register(Help, HelpAdmin)
admin.site.register(About, AboutAdmin)
admin.site.register(AntCal, AntennaCalibrationAdmin)
admin.site.register(DataCenter, DataCenterAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(ArchiveIndex, ArchiveIndexAdmin)

admin.autodiscover()
