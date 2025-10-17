import json
from collections import namedtuple
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import (
    CheckConstraint,
    ExpressionWrapper,
    F,
    Max,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import (
    Cast,
    Coalesce,
    Concat,
    ExtractDay,
    ExtractMonth,
    ExtractYear,
    Greatest,
    Lower,
    LPad,
    Now,
    Substr,
)
from django.utils.functional import cached_property, classproperty
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django_enum import EnumField

from slm import signals as slm_signals
from slm.defines import (
    AlertLevel,
    AntennaReferencePoint,
    Aspiration,
    CollocationStatus,
    CoordinateMode,
    FractureSpacing,
    FrequencyStandardType,
    ISOCountry,
    RinexVersion,
    SiteLogFormat,
    SiteLogStatus,
    TectonicPlates,
)
from slm.models.fields import StationNameField
from slm.utils import date_to_str
from slm.validators import get_validators


def utc_now_date():
    return datetime.now(timezone.utc).date()


# a named tuple used as meta information to dynamically determine what the
# section models are and how to access them from the Site model
Section = namedtuple(
    "Section",
    [
        "field",  # the name of the section for database queries
        "accessor",  # the section manager attribute on Site instances
        "cls",  # the section's python model class
        "subsection",  # true if this is a subsection (i.e. multiple instances)
    ],
)


class SubquerySum(Subquery):
    """
    The django ORM is still really clunky around aggregating subqueries.
    https://code.djangoproject.com/ticket/28296
    """

    output_field = models.IntegerField()

    def __init__(self, *args, **kwargs):
        self.template = f"(SELECT SUM({kwargs.pop('field')}) FROM (%(subquery)s) _sum)"
        super().__init__(*args, **kwargs)


def bool_condition(*args, **kwargs):
    return ExpressionWrapper(Q(*args, **kwargs), output_field=models.BooleanField())


class DefaultToStrEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def default(self, obj):
        return str(obj)


class SiteManager(models.Manager):
    pass


class SiteQuerySet(models.QuerySet):
    """
    A custom queryset for the Site model that adds some useful methods for
    common annotations. Information about sites is spread across a large number
    of tables, and it is often useful to annotate a queryset with information
    from those tables. This queryset provides a few methods to do that.
    """

    def annotate_files(self, log_format=SiteLogFormat.LEGACY, prefix=None):
        from slm.models import ArchivedSiteLog

        latest_archive = ArchivedSiteLog.objects.filter(
            Q(site=OuterRef("pk")) & Q(log_format=log_format)
        ).order_by("-index__valid_range")
        size_field = f"{log_format.ext if prefix is None else prefix}_size"
        file_field = f"{log_format.ext if prefix is None else prefix}_file"
        return self.annotate(
            **{
                size_field: Subquery(latest_archive.values("size")[:1]),
                file_field: Subquery(latest_archive.values("pk")[:1]),
            }
        )

    def annotate_filenames(
        self, published=True, name_len=None, field_name="filename", lower_case=False
    ):
        """
        Add the log names (w/o) extension as a property called filename to
        each site.
        :param published: If true (default) annotate with the filename for the
            most recently published version of the log. If false, will generate
            a filename for the HEAD version of the log whether published or in
            moderation.
        :param name_len: If given a number, the filename will start with only
            the first name_len characters of the site name.
        :param field_name: Change the name of the annotated field.
        :param lower_case: Filenames will be lowercase if true.
        :return: A queryset with the filename annotation added.
        """
        name_str = F("name")
        if name_len:
            name_str = Cast(Substr("name", 1, length=name_len), models.CharField())

        if lower_case:
            name_str = Lower(name_str)

        form = SiteForm.objects.filter(Q(site=OuterRef("pk")) & Q(published=published))

        return self.annotate(
            date_prepared=Subquery(form.values("date_prepared")[:1]),
            **{
                field_name: Concat(
                    name_str,
                    Value("_"),
                    Cast(ExtractYear("date_prepared"), models.CharField()),
                    LPad(
                        Cast(ExtractMonth("date_prepared"), models.CharField()),
                        2,
                        fill_text=Value("0"),
                    ),
                    LPad(
                        Cast(ExtractDay("date_prepared"), models.CharField()),
                        2,
                        fill_text=Value("0"),
                    ),
                )
            },
        )

    def active(self):
        """
        Active stations include all stations that are public and not former or
        suspended.

        :return:
        """
        return self.public().filter(
            ~Q(
                status__in=[
                    SiteLogStatus.PROPOSED,
                    SiteLogStatus.FORMER,
                    SiteLogStatus.SUSPENDED,
                ]
            )
        )

    def public(self):
        """
        Return all publicly visible sites. This includes sites that are
        in non-active states (i.e. proposed, former, suspended).
        :return:
        """
        from slm.models import Agency, Network

        public = Site.objects.filter(
            (
                Q(agencies__in=Agency.objects.filter(public=True))
                | Q(agencies__isnull=True)
            )
            & (
                Q(networks__in=Network.objects.filter(public=True))
                | Q(networks__isnull=True)
            )
            &
            # must have been published at least once! - even if in proposed
            # state
            Q(last_publish__isnull=False)
        ).distinct()
        return self.filter(pk__in=public)

    def editable_by(self, user):
        """
        Return the list of sites that should be visible in the editor to the
        given user.

        :param user: The user model.
        :return: A queryset with all sites un-editable by the user filtered
            out.
        """
        if user.is_authenticated:
            if user.is_superuser:
                return self
            return self.filter(agencies__in=user.agencies.all())
        return self.none()

    def moderated(self, user):
        if user.is_authenticated:
            if user.is_superuser:
                return self.all()
            elif user.is_moderator():
                return self.filter(agencies__in=user.agencies.all()).distinct()
        return self.none()

    def update_alert_levels(self):
        """
        Update the denormalized max alert level for sites in this queryset to
        reflect their active alerts.

        return: calling queryset for chaining
        """
        from slm.models import Alert

        max_alert = Alert.objects.for_site(OuterRef("pk")).order_by("-level")
        self.annotate(_max_alert=Subquery(max_alert.values("level")[:1])).update(
            max_alert=F("_max_alert")
        )
        return self

    def needs_publish(self):
        qry = self
        mod_q = Q()
        for idx, section in enumerate(self.model.sections()):
            mod_qry = section.cls.objects._current(
                published=False, filter=Q(site=OuterRef("pk"))
            )
            qry = qry.annotate(**{f"_mod{idx}": Subquery(mod_qry.values("pk")[:1])})
            mod_q |= Q(**{f"_mod{idx}__isnull": False})
        return qry.filter(mod_q).exists()

    def synchronize_denormalized_state(self, skip_form_updates=False):
        """
        Some state is denormalized and cached onto site records to speed up
        reads. This ensures this denormalized state
        (max_alert, num_flags, status, and some site form fields) accurately
        reflect the normal data.
        :param skip_form_updates: If true do not update the forms section
            with modified section info.
        :return:
        """
        self.update_alert_levels()

        aggregate = None
        qry = self
        mod_q = Q()
        for idx, section in enumerate(self.model.sections()):
            # head query - exclude deleted
            head_qry = section.cls.objects._current(
                published=None, include_deleted=False, filter=Q(site=OuterRef("pk"))
            )

            mod_qry = section.cls.objects._current(
                published=False, filter=Q(site=OuterRef("pk"))
            )
            qry = qry.annotate(
                **{
                    f"_num_flags{idx}": SubquerySum(
                        head_qry.values("num_flags"), field="num_flags"
                    ),
                    f"_mod{idx}": Subquery(mod_qry.values("pk")[:1]),
                }
            )
            mod_q |= Q(**{f"_mod{idx}__isnull": False})
            if aggregate is None:
                aggregate = Coalesce(f"_num_flags{idx}", 0)
            else:
                aggregate += Coalesce(f"_num_flags{idx}", 0)

        qry.order_by().annotate(_num_flags=aggregate).update(
            num_flags=Coalesce("_num_flags", 0)
        )

        qry.filter(
            Q(status__in=[SiteLogStatus.UPDATED, SiteLogStatus.PUBLISHED])
        ).filter(mod_q).update(status=SiteLogStatus.UPDATED)

        exists_q = Q()
        for required_section in getattr(
            settings, "SLM_REQUIRED_SECTIONS_TO_PUBLISH", []
        ):
            exists_q &= Q(**{f"{required_section}__isnull": False})
        qry.filter(
            Q(
                status__in=[
                    SiteLogStatus.UPDATED,
                    SiteLogStatus.PUBLISHED,
                    # SiteLogStatus.PROPOSED,
                ]
            )  # do not allow PROPOSED to be transitioned to PUBLISHED without explicit top level change
            & exists_q
        ).filter(~mod_q).update(status=SiteLogStatus.PUBLISHED)

        # this is the longest operation - there might be a way to squash it
        # into a single query
        if not skip_form_updates:
            for site in qry.filter(mod_q):
                form = site.siteform_set.head()
                if form.published:
                    form.pk = None
                    form.published = False
                    form.save()

                form.modified_section = ", ".join(site.modified_sections)
                if site.last_publish and form.report_type == "NEW":
                    form.report_type = "UPDATE"
                form.save()

    def availability(self):
        from slm.models import DataAvailability

        last_data_avail = DataAvailability.objects.filter(site=OuterRef("pk")).order_by(
            "-last"
        )
        return self.annotate(
            last_data_time=Subquery(last_data_avail.values("last")[:1]),
            last_data=Now() - F("last_data_time"),
            last_rinex2=Subquery(
                last_data_avail.filter(RinexVersion(2).major_q()).values("last")[:1]
            ),
            last_rinex3=Subquery(
                last_data_avail.filter(RinexVersion(3).major_q()).values("last")[:1]
            ),
            last_rinex4=Subquery(
                last_data_avail.filter(RinexVersion(4).major_q()).values("last")[:1]
            ),
        )

    def with_last_info(self):
        """
        Adds a datetime field called last_info which should reflect the last
        time there was any notable public information update for the site. For
        instance this is useful for search engine indexing.
        :return: queryset with a last_info field added
        """
        from slm.models import DataAvailability

        last_data_avail = DataAvailability.objects.filter(site=OuterRef("pk")).order_by(
            F("last").desc(nulls_last=True)
        )
        return self.annotate(
            last_info=Greatest(
                Subquery(last_data_avail.values("last")[:1]),
                "last_publish",
                output_field=models.DateTimeField(),
            )
        )

    def with_identification_fields(self, *fields, **renamed_fields):
        """
        Annotate the given identification fields valid now onto the site
        objects in this queryset.

        :param fields: The names of the fields to annotate, by default these
            will include: iers_domes_number, cdp_number
        :param renamed_fields: Named arguments where the names of the arguments
            are the field accessors for the fields to annotate and the values
            are the names to use for the annotated fields.
        :return: The queryset with the annotations made
        """
        fields = {
            **{field: field for field in fields},
            **{field: name for field, name in renamed_fields.items()},
        }

        fields = fields or {
            **{field: field for field in ["iers_domes_number", "cdp_number"]}
        }

        identification = SiteIdentification.objects.filter(
            Q(site=OuterRef("pk")) & Q(published=True)
        )
        return self.annotate(
            **{
                name: Subquery(identification.values(field)[:1])
                for field, name in fields.items()
            }
        )

    def with_location_fields(self, *fields, **renamed_fields):
        """
        Annotate the given location fields valid now or at the given epoch
        onto the site objects in this queryset.

        :param fields: The names of the fields to annotate, by default these
            will include: XYZ, LLH, city, state, and
            country
        :param renamed_fields: Named arguments where the names of the arguments
            are the field accessors for the fields to annotate and the values
            are the names to use for the annotated fields.
        :return: The queryset with the annotations made
        """
        fields = {
            **{field: field for field in fields},
            **{field: name for field, name in renamed_fields.items()},
        }

        fields = fields or {
            **{field: field for field in ["xyz", "llh", "city", "state", "country"]}
        }

        location = SiteLocation.objects.filter(
            Q(site=OuterRef("pk")) & Q(published=True)
        )
        return self.annotate(
            **{
                name: Subquery(location.values(field)[:1])
                for field, name in fields.items()
            }
        )

    def with_receiver_fields(self, *fields, epoch=None, **renamed_fields):
        """
        Annotate the given receiver fields valid now or at the given epoch
        onto the site objects in this queryset. The field names should be
        the Django ORM field accessor names. For instance the receiver model
        type would be: receiver_type__model. To use a different name than the
        accessor for the annotated field you may pass the fields renamed as
        keyword arguments. For instance to rename serial_number to
        receiver_serial_number you would pass:

            with_receiver_fields(serial_number='receiver_serial_number')

        :param fields: The names of the fields to annotate, by default these
            will include:
                receiver_type__model -> receiver,
                serial_number -> receiver_sn
                firmware -> receiver_firmware
        :param epoch: The point in time at which the receiver information
            should be valid for, default is now
        :param renamed_fields: Named arguments where the names of the arguments
            are the field accessors for the fields to annotate and the values
            are the names to use for the annotated fields.
        :return: The queryset with the annotations made
        """
        fields = {
            **{field: field for field in fields},
            **{field: name for field, name in renamed_fields.items()},
        }

        fields = fields or {
            "receiver_type__model": "receiver",
            "serial_number": "receiver_sn",
            "firmware": "receiver_firmware",
        }

        epoch_q = (
            Q()
            if epoch is None
            else (
                (Q(installed__lte=epoch) | Q(installed__isnull=True))
                & (Q(removed__gt=epoch) | Q(removed__isnull=True))
            )
        )
        receiver = SiteReceiver.objects.filter(
            Q(site=OuterRef("pk")) & Q(published=True) & epoch_q
        ).order_by("-installed")

        return self.annotate(
            **{
                name: Subquery(receiver.values(field)[:1])
                for field, name in fields.items()
            }
        )

    def with_antenna_fields(self, *fields, epoch=None, **renamed_fields):
        """
        Annotate the given antenna fields valid now or at the given epoch
        onto the site objects in this queryset. The field names should be
        the Django ORM field accessor names. For instance the receiver model
        type would be: receiver_type__model. To use a different name than the
        accessor for the annotated field you may pass the fields renamed as
        keyword arguments. For instance to rename serial_number to
        antenna_sn you would pass:

            with_antenna_fields(serial_number='antenna_sn')

        The antenna calibration method is available as the field 'antcal'.

        :param fields: The names of the fields to annotate, by default these
            will include:
                antenna_type__model -> antenna,
                radome_type__model -> radome,
                antcal -> antcal

        :param epoch: The point in time at which the receiver information
            should be valid for, default is now
        :param renamed_fields: Named arguments where the names of the arguments
            are the field accessors for the fields to annotate and the values
            are the names to use for the annotated fields.
        :return: The queryset with the annotations made
        """
        from slm.models import AntCal

        fields = {
            **{field: field for field in fields},
            **{field: name for field, name in renamed_fields.items()},
        }

        fields = fields or {
            "antenna_type__model": "antenna",
            "radome_type__model": "radome",
            "antcal": "antcal",
        }

        epoch_q = (
            Q()
            if epoch is None
            else (
                (Q(installed__lte=epoch) | Q(installed__isnull=True))
                & (Q(removed__gt=epoch) | Q(removed__isnull=True))
            )
        )

        antenna = SiteAntenna.objects.filter(
            Q(site=OuterRef("pk")) & Q(published=True) & epoch_q
        ).order_by("-installed")
        if "antcal" in fields:
            antenna = antenna.annotate(
                antcal=Subquery(
                    AntCal.objects.filter(
                        Q(antenna=OuterRef("antenna_type"))
                        & Q(radome=OuterRef("radome_type"))
                    ).values("method")[:1]
                )
            )

        return self.annotate(
            **{
                name: Subquery(antenna.values(field)[:1])
                for field, name in fields.items()
            }
        )

    def with_frequency_standard_fields(self, *fields, epoch=None, **renamed_fields):
        """
        Annotate the given frequency standard fields valid now or at the given
        epoch onto the site objects in this queryset. The field names should be
        the Django ORM field accessor names.

        :param fields: The names of the fields to annotate, by default these
            will include:
                standard_type -> clock
        :param epoch: The point in time at which the receiver information
            should be valid for, default is now
        :param renamed_fields: Named arguments where the names of the arguments
            are the field accessors for the fields to annotate and the values
            are the names to use for the annotated fields.
        :return: The queryset with the annotations made
        """
        fields = {
            **{field: field for field in fields},
            **{field: name for field, name in renamed_fields.items()},
        }

        fields = fields or {"standard_type": "clock"}

        epoch_q = (
            Q()
            if epoch is None
            else (
                (Q(effective_start__lte=epoch) | Q(effective_start__isnull=True))
                & (Q(effective_end__gt=epoch) | Q(effective_end__isnull=True))
            )
        )
        freq = SiteFrequencyStandard.objects.filter(
            Q(site=OuterRef("pk")) & Q(published=True) & epoch_q
        ).order_by("-effective_start")

        return self.annotate(
            **{name: Subquery(freq.values(field)[:1]) for field, name in fields.items()}
        )

    def with_info_fields(self, *fields, **renamed_fields):
        """
        Annotate the given identification fields valid now onto the site
        objects in this queryset.

        :param fields: The names of the fields to annotate, by default these
            will include: iers_domes_number, cdp_number
        :param renamed_fields: Named arguments where the names of the arguments
            are the field accessors for the fields to annotate and the values
            are the names to use for the annotated fields.
        :return: The queryset with the annotations made
        """
        fields = {
            **{field: field for field in fields},
            **{field: name for field, name in renamed_fields.items()},
        }

        fields = fields or {
            "primary": "primary_datacenter",
            "secondary": "secondary_datacenter",
        }

        more_info = SiteMoreInformation.objects.filter(
            Q(site=OuterRef("pk")) & Q(published=True)
        )
        return self.annotate(
            **{
                name: Subquery(more_info.values(field)[:1])
                for field, name in fields.items()
            }
        )


class Site(models.Model):
    """
    XXXX Site Information Form (site log)
    International GNSS Service
    See Instructions at:
      https://files.igs.org/pub/station/general/sitelog_instr.txt
    """

    # API_RELATED_FIELD = 'name'

    objects = SiteManager.from_queryset(SiteQuerySet)()

    name = StationNameField(
        max_length=50,
        unique=True,
        help_text=_("The name of the station."),
        db_index=True,
    )

    # todo can site exist without agency?
    agencies = models.ManyToManyField("slm.Agency", related_name="sites")

    # dormant is now deduplicated into status field
    status = EnumField(
        SiteLogStatus,
        default=SiteLogStatus.PROPOSED,
        blank=True,
        help_text=_("The current status of the site."),
        db_index=True,
    )

    owner = models.ForeignKey(
        "slm.User", null=True, default=None, blank=True, on_delete=models.SET_NULL
    )

    # Denormalized data ###########################
    # These fields are cached onto the site table to speed up lookups, issues
    # can arise if they get out of synch with the data
    num_flags = models.PositiveSmallIntegerField(
        default=0,
        blank=True,
        help_text=_("The number of flags the most recent site log version has."),
        db_index=True,
    )

    max_alert = EnumField(
        AlertLevel,
        default=None,
        blank=True,
        null=True,
        help_text=_("The number of flags the most recent site log version has."),
        db_index=True,
    )
    ##############################################

    # todo deprecated
    preferred = models.IntegerField(default=0, blank=True)
    modified_user = models.IntegerField(default=0, blank=True)
    #######

    created = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        help_text=_("The time this site was first registered."),
        db_index=True,
    )

    join_date = models.DateField(
        blank=True,
        null=True,
        help_text=_("The date this site was first published."),
        db_index=True,
    )

    # todo, normalize onto log join
    last_user = models.ForeignKey(
        "slm.User",
        null=True,
        default=None,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recent_sites",
        help_text=_("The last user to make edits to the site log."),
    )
    ######################################

    last_publish = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=_("The publish date of the current log file."),
        db_index=True,
    )

    last_update = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=_("The time of the most recent update to the site log."),
        db_index=True,
    )

    def needs_publish(self):
        if self.status in [SiteLogStatus.PROPOSED, SiteLogStatus.UPDATED]:
            return True
        elif self.status == SiteLogStatus.PUBLISHED:
            return False
        return self.__class__.objects.filter(pk=self.pk).needs_publish()

    @lru_cache(maxsize=32)
    def is_moderator(self, user):
        if user:
            if user.is_superuser:
                return True
            return self.moderators.filter(pk=user.pk).exists()
        return False

    def get_filename(self, log_format, epoch=None, name_len=None, lower_case=False):
        """
        Get the filename (including extension) to be used for the rendered
        site log given the parameters.

        :param log_format: The SiteLogFormat of the rendered log
        :param epoch: The date (or datetime) when the site log was valid. If
            not given the last published date will be used, then the time of the
            last_update, and ultimately if the first two are null the created time
            will be used.
        :param name_len: The number of characters from the site log name to use
            as the prefix. (default: 9 - all of them)
        :param lower_case: True if the filename should be lower case.
            (default False)
        :return: The filename including extension.
        """
        # TODO - make this pluggable
        if epoch is None:
            epoch = self.last_publish or self.last_update or self.created
        if name_len is None and log_format is SiteLogFormat.LEGACY:
            name_len = 4
        name = self.name[:name_len]
        return (
            f"{name.lower() if lower_case else name.upper()}_"
            f"{epoch.year}{epoch.month:02}"
            f"{epoch.day:02}.{log_format.ext}"
        )

    def refresh_from_db(self, **kwargs):
        if hasattr(self, "_max_alert"):
            del self._max_alert
        return super().refresh_from_db(**kwargs)

    @classproperty
    def alert_fields(cls):
        from slm.models import Alert

        return [
            field.get_accessor_name()
            for field in cls._meta.related_objects
            if issubclass(field.related_model, Alert)
        ]

    @cached_property
    def moderators(self):
        """
        Get the users who have moderate permission for this site. Moderators
        are also editors, but are not listed in editors

        :return: A queryset containing users with moderate permission for the
            site
        """
        perm = Permission.objects.get_by_natural_key("moderate_sites", "slm", "user")
        return (
            get_user_model()
            .objects.filter(
                Q(is_superuser=True)
                | (
                    Q(agencies__in=self.agencies.all())
                    & (Q(groups__permissions=perm) | Q(user_permissions=perm))
                )
            )
            .distinct()
        )

    @cached_property
    def editors(self):
        """
        Get the users who have edit permission for this site. This may include
        moderators who are part of the same agency.

        :return: A queryset containing users with edit permissions for the site
        """
        qry = Q(agencies__in=self.agencies.all())
        if self.owner:
            qry |= Q(pk=self.owner.pk)
        return get_user_model().objects.filter(qry)

    @classmethod
    def sections(cls):
        if hasattr(cls, "sections_"):
            return cls.sections_

        cls.sections_ = [
            Section(
                field=section.name,
                accessor=section.get_accessor_name(),
                cls=section.related_model,
                subsection=SiteSubSection in section.related_model.__mro__,
            )
            for section in Site._meta.get_fields()
            if section.related_model and (SiteSection in section.related_model.__mro__)
        ]
        return cls.sections_

    def is_publishable(self):
        has_required_sections = Q(id=self.id)
        for required_section in getattr(
            settings, "SLM_REQUIRED_SECTIONS_TO_PUBLISH", []
        ):
            has_required_sections &= Q(**{f"{required_section}__isnull": False})
        return bool(Site.objects.filter(has_required_sections).count())

    def can_publish(self, user):
        """
        This is a future hook to use for instances where non-moderators are
        allowed to publish a site log under certain conditions.

        :param user:
        :return:
        """
        if user:
            # cannot publish without these minimum sectons
            has_required_sections = Q(id=self.id)
            for required_section in getattr(
                settings, "SLM_REQUIRED_SECTIONS_TO_PUBLISH", []
            ):
                has_required_sections &= Q(**{f"{required_section}__isnull": False})
            return self.is_moderator(user) and self.is_publishable()
        return False

    def can_edit(self, user):
        if user and user.is_authenticated:
            if self.is_moderator(user) or self.owner == user:
                return True
            return user.agencies.filter(pk__in=self.agencies.all()).count() > 0
        return False

    def update_status(
        self, save=True, user=None, timestamp=None, first_publish=False, reverted=False
    ):
        """
        Update the denormalized data that is too expensive to query on the
        fly. This includes flag count, moderation status and DateTimes. Also
        check for and delete any review requests if a publish was done.

        :param save: If true the site row will be saved to the database.
        :param user: The user responsible for a status update check
        :param timestamp: The time at which the status update is triggered
        :param first_publish: True if this is the first time the site log is being published.
        :param reverted: A boolean indicating if this update was triggered by a reversion or not.
        :return:
        """
        if not timestamp:
            timestamp = now()

        self.last_update = timestamp
        if first_publish:
            self.last_publish = timestamp

        if user:
            self.last_user = user

        status = self.status
        self.synchronize()

        # if in either of these two states - status update must come from
        # a global publish of the site log, not from this which can be
        # triggered by a section publish
        if first_publish or (
            status != self.status and self.status == SiteLogStatus.PUBLISHED
        ):
            self.last_publish = timestamp
            self.status = SiteLogStatus.PUBLISHED
            if hasattr(self, "review_request"):
                self.review_request.delete()

        if save:
            setattr(  # ugly but we need to pass info to the post_save signal handler somehow
                self, "_reverted", reverted
            )
            self.save()

    def revert(self):
        reverted = False
        for section in self.sections():
            reverted |= getattr(self, section.accessor).revert()
        if reverted:
            self.update_status(reverted=reverted)
        return reverted

    def published(self, epoch=None):
        return self._current(epoch=epoch, published=True)

    def head(self, epoch=None, include_deleted=False):
        return self._current(
            epoch=epoch, published=None, include_deleted=include_deleted
        )

    def _current(self, epoch=None, published=None, filter=None, include_deleted=False):
        for section in self.sections():
            setattr(
                self,
                section.field,
                (
                    getattr(self, section.accessor)._current(
                        epoch=epoch,
                        published=published,
                        filter=filter,
                        include_deleted=include_deleted,
                    )
                    if section.subsection
                    else getattr(self, section.accessor)
                    ._current(
                        epoch=epoch,
                        published=published,
                        filter=filter,
                        include_deleted=include_deleted,
                    )
                    .first()
                ),
            )

    @cached_property
    def modified_sections(self):
        modified_sections = []
        for section in self.sections():
            if section.cls is SiteForm:
                continue
            if section.subsection:
                idx = 0
                for subsection in getattr(self, section.accessor).head().sort():
                    idx += 1
                    if not subsection.published:
                        dot_index = f"{subsection.section_number()}"
                        if subsection.subsection_number():
                            dot_index += f".{subsection.subsection_number()}"
                        dot_index += f".{idx}"
                        modified_sections.append(dot_index)
            else:
                modified = getattr(self, section.accessor).head()
                if modified and not modified.published:
                    modified_sections.append(str(modified.section_number()))
        return modified_sections

    @property
    def four_id(self):
        return self.name[:4]

    def publish(self, request=None, silent=False, timestamp=None):
        """
        Publish the current HEAD edits on this SiteLog.

        :param request: The request that triggered the publish (optional)
        :param silent: If True, no publish signal will be sent.
        :param timestamp: Timestamp to use for the publish, if none - will
            be the time of this call
        :return: The number of sections and subsections that had changes
            that were published or 0 if no changes were at HEAD to publish.
        """
        if timestamp is None:
            timestamp = now()

        form = self.siteform_set.head()
        if form is None:
            SiteForm.objects.create(site=self, published=False, report_type="NEW")
        elif form.published:
            form.pk = None
            form.published = False
            form.save()

        sections_published = 0
        for section in self.sections():
            if section.subsection:
                for subsection in getattr(self, section.accessor).head(
                    include_deleted=True
                ):
                    sections_published += int(
                        subsection.publish(
                            request=request,
                            silent=True,
                            timestamp=timestamp,
                            update_site=False,
                        )
                    )
            else:
                current = getattr(self, section.accessor).head(include_deleted=True)
                if current:
                    sections_published += int(
                        current.publish(
                            request=request,
                            silent=True,
                            timestamp=timestamp,
                            update_site=False,
                        )
                    )

        # this might be an initial PUBLISH when we're in PROPOSED or FORMER
        if sections_published or self.status != SiteLogStatus.PUBLISHED:
            self.last_publish = timestamp
            # self.save()
            self.update_status(
                save=True,
                user=request.user if request else None,
                timestamp=timestamp,
                first_publish=(self.status is SiteLogStatus.PROPOSED),
            )
            if hasattr(self, "review_request"):
                self.review_request.delete()
            if not silent:
                slm_signals.site_published.send(
                    sender=self,
                    site=self,
                    user=request.user if request else None,
                    timestamp=timestamp,
                    request=request,
                    section=None,
                )
        return sections_published

    @cached_property
    def equipment_list(self):
        """
        Returns a list of published equipment pairings in date order:

        [
            (date, {receiver: <receiver>, antenna: <antenna>}),
            (date, {receiver: <receiver>, antenna: <antenna>}),
            (date, {receiver: <receiver>, antenna: <antenna>})
        ]
        """
        equipment = {}
        self.published()
        for receiver in self.sitereceiver_set.all():
            equipment.setdefault(receiver.installed.date(), {})
            equipment[receiver.installed.date()]["receiver"] = receiver
        for antenna in self.siteantenna_set.all():
            equipment.setdefault(antenna.installed.date(), {})
            equipment[antenna.installed.date()]["antenna"] = antenna

        # build the time ordered list of equipment pairings
        time_ordered = []
        dates = sorted(equipment.keys())
        for idx, eq_date in enumerate(dates):
            time_ordered.append(
                (
                    eq_date,
                    {
                        "receiver": equipment[eq_date].get(
                            "receiver",
                            None if idx == 0 else time_ordered[idx - 1][1]["receiver"],
                        ),
                        "antenna": equipment[eq_date].get(
                            "antenna",
                            None if idx == 0 else time_ordered[idx - 1][1]["antenna"],
                        ),
                    },
                )
            )

        # remove any gaps at the front without full equipment
        start = 0
        for idx, eq in enumerate(time_ordered):
            if eq[1]["receiver"] and eq[1]["antenna"]:
                break
            start = idx + 1

        return list(reversed(time_ordered[start:]))

    def __str__(self):
        return self.name

    def synchronize(self, refresh=True, skip_form_updates=False):
        Site.objects.filter(pk=self.pk).synchronize_denormalized_state(
            skip_form_updates=skip_form_updates
        )
        if refresh:
            self.refresh_from_db()


class SiteSectionManager(gis_models.Manager):
    is_head = False

    def get_queryset(self):
        return super().get_queryset().select_related("site")

    def revert(self):
        return bool(self.get_queryset().filter(published=False).delete()[0])

    def published(self, epoch=None):
        return self.get_queryset().published(epoch=epoch)

    def head(self, epoch=None, include_deleted=False):
        self.is_head = True
        return self.get_queryset().head(epoch=epoch, include_deleted=include_deleted)

    def _current(self, epoch=None, published=None, filter=None, include_deleted=False):
        self.is_head = published is None
        return self.get_queryset()._current(
            epoch=epoch,
            published=published,
            filter=filter,
            include_deleted=include_deleted,
        )


class SiteSectionQueryset(gis_models.QuerySet):
    is_head = False

    def editable_by(self, user):
        if user.is_superuser:
            return self
        return self.filter(site__agencies__in=user.agencies.all())

    def station(self, station):
        if isinstance(station, str):
            return self.filter(site__name=station)
        return self.filter(site=station)

    def published(self, epoch=None):
        return self._current(epoch=epoch, published=True).first()

    def head(self, epoch=None, include_deleted=False):
        self.is_head = True
        return self._current(
            epoch=epoch, published=None, include_deleted=include_deleted
        ).first()

    def _current(self, epoch=None, published=None, filter=None, include_deleted=False):
        self.is_head = published is None
        pub_q = filter or Q()
        if published is not None:
            pub_q &= Q(published=published)
        if epoch and getattr(self.model, "valid_time", ""):
            # todo does epoch make sense for non-subsections??
            ret = (
                self.filter(pub_q)
                .order_by("published")
                .filter({f"{self.model.valid_time}__lte": epoch})[0:1]
            )
        else:
            ret = self.filter(pub_q).order_by("published")[0:1]

        ret.is_head = self.is_head
        return ret

    def sort(self, reverse=False):
        return self

    class Meta:
        order_by = ("name",)


class SiteLocationManager(SiteSectionManager):
    pass


class SiteLocationQueryset(SiteSectionQueryset):
    def countries(self):
        """
        Return the list of unique countries that this queryset of SiteLocations
        is in.

        .. note::

            Site locations with invalid ISO-3166 ountry codes will not be
            included.

        :return: A list of ISOCountry enumerations.
        """
        return list(
            set(
                [
                    country
                    for country in self.values_list("country", flat=True)
                    .distinct()
                    .order_by("country")
                    if isinstance(country, ISOCountry)
                ]
            )
        )


class SiteSection(gis_models.Model):
    site = models.ForeignKey("slm.Site", on_delete=models.CASCADE)

    edited = models.DateTimeField(auto_now_add=True, db_index=True, null=False)

    published = models.BooleanField(default=False, db_index=True)

    _flags = models.JSONField(
        null=False, blank=True, default=dict, encoder=DefaultToStrEncoder
    )

    num_flags = models.PositiveSmallIntegerField(default=0, null=False, db_index=True)

    objects = SiteSectionManager.from_queryset(SiteSectionQueryset)()

    def publishable(self):
        return not self.published or (getattr(self, "is_deleted", False))

    @cached_property
    def has_published(self):
        return self.__class__.objects.filter(
            Q(site=self.site) & Q(published=True)
        ).exists()

    def save(self, *args, **kwargs):
        self.num_flags = len(self._flags) if self._flags else 0
        super().save(*args, **kwargs)

    def revert(self):
        reverted = bool(
            self.__class__.objects.filter(
                Q(site=self.site) & Q(published=False)
            ).delete()[0]
        )
        if reverted:
            self.site.update_status(reverted=reverted)
        return reverted

    @property
    def dot_index(self):
        return self.section_number()

    def publish(self, request=None, silent=False, timestamp=None, update_site=True):
        """
        Publish the current HEAD edits on this section - this will delete the
        last published section instance.

        :param request: The request that triggered the publish (optional)
        :param silent: If True, no publish signal will be sent.
        :param timestamp: Timestamp to use for the publish, if none - will
            be the time of this call
        :param update_site: If True, site will be updated with publish
            information (i.e. pass False if this section is being published as
            part of a larger site publish)
        :return: True if a change was published, False otherwise.
        """
        if not self.publishable():
            return False

        if timestamp is None:
            timestamp = now()

        with transaction.atomic():
            if getattr(self, "is_deleted", False):
                self.delete()
            else:
                # delete the previously published row if it exists
                kwargs = {"site": self.site, "published": True}
                if hasattr(self, "subsection"):
                    kwargs["subsection"] = self.subsection

                self.__class__.objects.filter(**kwargs).delete()

                self.published = True
                if isinstance(self, SiteForm):
                    self.save(skip_update=True)
                else:
                    self.save()

            if update_site:
                self.site.last_publish = timestamp
                self.site.save()
                self.site.update_status(save=True, timestamp=timestamp)

            if not silent and self.site.last_publish:
                # only send this signal if publishing this section results
                # in a newly published site log. It will not if this section
                # publish is part of a large site log publish or if the site
                # log has never been published before.
                slm_signals.site_published.send(
                    sender=self.site,
                    site=self.site,
                    user=request.user if request else None,
                    timestamp=timestamp,
                    request=request,
                    section=self,
                )
            return True

    def can_publish(self, user):
        """
        This is a future hook to use for instances where non-moderators are
        allowed to publish a site log section under certain conditions.

        :param user:
        :return:
        """
        return self.site.is_moderator(user)

    def can_edit(self, user):
        return self.site.can_edit(user)

    def clean(self):
        """
        Run configured validation routines. Routines are configured in
        the SLM_DATA_VALIDATORS setting. This setting maps model fields to
        validation logic. We run through those routines here and depending
        on severity we either add flags or throw an error.

        :except ValidationError: If a save-blocking validation error has
            occurred.
        """
        errors = {}
        for field in [*self._meta.fields, *self._meta.many_to_many]:
            for validator in get_validators(self._meta.label, field.name):
                try:
                    validator(self, field, getattr(self, field.name, None))
                except ValidationError as val_err:
                    errors[field.name] = val_err.error_list
        if errors:
            raise ValidationError(errors)

    @property
    def mod_status(self):
        if getattr(self, "is_deleted", False):
            return SiteLogStatus.UPDATED
        if self.published:
            return SiteLogStatus.PUBLISHED
        return SiteLogStatus.UPDATED

    def published_diff(self, epoch=None):
        """
        Get a dictionary representing the diff with the current published HEAD
        """
        diff = {}
        if getattr(self, "is_deleted", None):
            return {}

        if isinstance(self, SiteSubSection):
            published = self.__class__.objects.filter(site=self.site).published(
                subsection=self.subsection, epoch=epoch
            )
        else:
            published = self.__class__.objects.filter(site=self.site).published(
                epoch=epoch
            )

        if published and published.id == self.id:
            return diff

        def transform(value, field_name):
            if isinstance(value, models.Model):
                return str(value)
            elif isinstance(self._meta.get_field(field), models.ManyToManyField):
                if value:
                    return "+".join([str(val) for val in value.all()])
            elif isinstance(self._meta.get_field(field), gis_models.PointField):
                if value:
                    return value.coords
            return value

        def differ(value1, value2):
            if isinstance(value1, str) and isinstance(value2, str):
                return value1.strip() != value2.strip()
            return value1 != value2

        for field in self.site_log_fields():
            pub = transform(getattr(published, field, None), field)
            head = transform(getattr(self, field), field)
            if differ(head, pub) and head not in [None, ""] and pub not in [None, ""]:
                diff[field] = {"pub": pub, "head": head}
        return diff

    @classmethod
    def section_number(cls):
        raise NotImplementedError("SiteSection models must implement section_number()")

    @classmethod
    def section_name(cls):
        return cls._meta.verbose_name.replace("site", "").strip().title()

    @classmethod
    def section_slug(cls):
        return cls.__name__.lower().replace("site", "").strip()

    @classmethod
    def site_log_fields(cls):
        """
        Return the editable fields for the given sitelog section
        """
        return [
            field.name
            for field in cls._meta.fields
            if field.name
            not in {
                "id",
                "site",
                "edited",
                "published",
                "error",
                "subsection",
                "is_deleted",
                "deleted",
                "_flags",
                "inserted",
                "num_flags",
            }
        ]

    @classmethod
    def structure(cls):
        """
        todo remove?
        Return the structure of the legacy site log section in the form:
        [
            'field name0',
            ('section name1', ('field name1', 'field name2', ...),
            'field name3',
            ...
        ]

        The field name is the name of the field on the class, it may be a
        database field or a callable that returns an object coercible to a
        string.
        """
        # raise NotImplementedError(f'SiteSections must implement structure
        # classmethod!')
        return cls.site_log_fields()

    @classmethod
    def legacy_name(cls, field):
        if callable(getattr(cls, field, None)):
            return getattr(cls, field).verbose_name
        return cls._meta.get_field(field).verbose_name

    def __init__(self, *args, **kwargs):
        """
        After our model is initialized we cache the values of the fields. This
        is used by get_initial_value to eliminate the need for another database
        round trip.

        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self._init_values_ = {}
        deferred = self.get_deferred_fields()
        for field in self.site_log_fields():
            if field not in deferred and not isinstance(
                self._meta.get_field(field), (models.ManyToManyField, models.ForeignKey)
            ):
                self._init_values_[field] = getattr(self, field)

    def get_initial_value(self, field):
        """
        Get the current value of the field at the time of initialization. This
        call may result in a database lookup if the field was deferred on
        initialization. The field must be in the model's site_log_fields().

        :param field:
        :return:
        """
        if field not in self.site_log_fields():
            raise ValueError(
                f"Field {field} is not a site log field for {self.__class__}"
            )
        if field not in self._init_values_:
            current = self.__class__.objects.filter(pk=self.pk).first()
            for field in self.site_log_fields():
                self._init_values_[field] = getattr(current, field)
        return self._init_values_[field]

    def sort(self):
        """
        This is a kludge that's in place until the data model refactor can
        separate the edit and state tables
        """
        return self

    class Meta:
        abstract = True
        ordering = ("-edited",)
        unique_together = (
            "site",
            "published",
        )
        indexes = [
            models.Index(fields=("edited", "published")),
            models.Index(fields=("site", "edited")),
            models.Index(fields=("site", "edited", "published")),
        ]


class SiteSubSectionManager(SiteSectionManager):
    def revert(self):
        reverted = super().revert()
        reverted |= bool(
            self.get_queryset()
            .filter(Q(published=True) & Q(is_deleted=True))
            .update(is_deleted=False)
        )
        return reverted

    def create(self, *args, **kwargs):
        # some DBs only support one auto field per table, so we have to
        # manually increment the subsection identifier for new subsections
        # using select_for_update to avoid race conditions
        if "subsection" not in kwargs:
            last = (
                self.model.objects.select_for_update()
                .filter(site=kwargs.get("site"))
                .aggregate(Max("subsection"))["subsection__max"]
            )
            kwargs["subsection"] = last + 1 if last is not None else 0
        return super().create(*args, **kwargs)


class SiteSubSectionQuerySet(SiteSectionQueryset):
    is_head = False

    def last(self):
        """
        The technique we use to restrict head() is to order by unpublished vs
        published and then use DISTINCT on subsection to pick the first
        row for each subsection - this unfortunately breaks when last() is used
        because it will pull out the published version instead of one exists.
        We work around that here by pulling out the last from the original
        query rather than asking the database to do it. first() is unaffected
        by this problem.
        """
        if self.is_head:
            for sct in reversed(self):
                return sct
        return super().last()

    def published(self, subsection=None, epoch=None):
        return self._current(subsection=subsection, epoch=epoch, published=True)

    def head(self, subsection=None, epoch=None, include_deleted=False):
        self.is_head = True
        return self._current(
            subsection=subsection,
            epoch=epoch,
            published=None,
            include_deleted=include_deleted,
        )

    def _current(
        self,
        subsection=None,
        epoch=None,
        published=None,
        filter=None,
        include_deleted=False,
    ):
        """
        Fetch the subsection stack that matches the parameters.

        :param subsection: A subsection identifier to fetch a specific
            subsection
        :param epoch: A point in time at which to fetch the subsection stack.
        :param published: If None (Default) fetch the latest HEAD version of
            the subsection stack, if True fetch only the latest published
            versions of the subsection stack. If False, fetch only unpublished
            members of the subsection stack.
        :param filter: An additional Q object to filter the subsection stack
            by.
        :param include_deleted: Include deleted sections if True, this param is
            meaningless if published is True.
        :return:
        """
        self.is_head = published is None
        section_q = filter or Q()

        if epoch and self.model.valid_time is not None:
            section_q &= Q(**{f"{self.model.valid_time}__lte": epoch})

        if published:
            section_q &= Q(published=True)
        elif published is None:
            if not include_deleted:
                section_q &= Q(is_deleted=False)
        else:
            section_q &= Q(published=False) | Q(is_deleted=True)

        if subsection is not None:
            return self.filter(Q(subsection=subsection) & section_q).first()

        elif published is not None:
            qry = self.filter(section_q).order_by(self.model.order_field, "subsection")
        else:
            ordering = ["subsection", "published"]

            qry = self.filter(section_q).order_by(*ordering).distinct("subsection")

        qry.is_head = self.is_head
        return qry

    def sort(self, reverse=False):
        """
        When fetching head() lists - we must sort in memory because changes to
        the sort field can screw up the head() selection. In short - if
        you call head() on a subsection and ordering matters, call sort next.
        This does not alter the query but instead runs the query and returns
        an in-memory list that is sorted. It should therefore not be called
        on large querysets on that pull from more than one site.

        This will be fixed in the data model architectural refactor when the
        edit tables are separated from the published tables.

        :param reverse: Reverse the sorted order
        :return: An iterable of sorted objects
        """

        class OrderTuple:
            def __init__(self, field, subsection):
                self.field = field
                self.subsection = subsection

            def __lt__(self, other):
                """
                Custom < operator allows for None values of field to be
                ignored - there's some old/bad data we have to allow
                """
                if other.field is not None and self.field is not None:
                    if self.field < other.field:
                        return True
                return self.subsection < other.subsection

        sorted_sections = sorted(
            (obj for obj in self),
            key=lambda o: OrderTuple(getattr(o, o.order_field), o.subsection)
            if getattr(self.model, "order_field", None)
            else lambda o: o.subsection,
        )
        if reverse:
            return list(reversed(sorted_sections))
        return list(sorted_sections)


class SiteSubSection(SiteSection):
    subsection = models.PositiveSmallIntegerField(blank=True, db_index=True)

    is_deleted = models.BooleanField(default=False, null=False, blank=True)

    inserted = models.DateTimeField(default=now, db_index=True)

    objects = SiteSubSectionManager.from_queryset(SiteSubSectionQuerySet)()

    def revert(self):
        reverted = self.__class__.objects.filter(
            Q(site=self.site) & Q(published=False) & Q(subsection=self.subsection)
        ).delete()[0] | self.__class__.objects.filter(
            Q(site=self.site)
            & Q(published=True)
            & Q(is_deleted=True)
            & Q(subsection=self.subsection)
        ).update(is_deleted=False)
        if reverted:
            self.site.update_status(reverted=reverted)
        return reverted

    @cached_property
    def has_published(self):
        return self.__class__.objects.filter(
            Q(site=self.site) & Q(published=True) & Q(subsection=self.subsection)
        ).exists()

    @property
    def dot_index(self, published=False):
        """
        Get the published dot index of this subsection. (e.g. 8.1.2). This
        performs a query - it's usually best to compute these indexes during
        serialization or inline when subsections are iterated over.
        """
        dot_index = f"{self.section_number()}"
        if self.subsection_number():
            dot_index += f".{self.subsection_number()}"

        # ordering gets tricky because some legacy data might have nulls in the
        # expected order field
        ordering = (self.order_field, getattr(self, self.order_field))
        if ordering[1] is None:
            ordering = ("subsection", getattr(self, "subsection"))

        list_idx = (
            self.__class__.objects.filter(site=self.site)
            .published()
            .filter(**{f"{ordering[0]}__lt": ordering[1]})
            .count()
            + 1
        )
        dot_index += f".{list_idx}"
        return dot_index

    @classproperty
    def valid_time(cls):
        """
        The field that defines when this subsection became valid. All
        subsections should have time ranges of validity.
        :return:
        """
        for field in ["installed", "effective_start"]:
            try:
                return field if cls._meta.get_field(field) else None
            except FieldDoesNotExist:
                continue
        raise NotImplementedError(f"{cls} must implement valid_time()")

    @classproperty
    def order_field(cls):
        return cls.valid_time if cls.valid_time else "subsection"

    @property
    def heading(self):
        """
        A brief name for this instance useful for UI display.
        """
        raise NotImplementedError("Site subsection models should implement heading().")

    @cached_property
    def subsection_prefix(self):
        idx = f"{self.section_number()}"
        if self.subsection_number():
            idx += f".{self.subsection_number()}"
        return idx

    @classmethod
    def subsection_number(cls):
        raise NotImplementedError(
            "SiteSubSection models must implement subsection_number()"
        )

    @classmethod
    def subsection_name(cls):
        return cls._meta.verbose_name.replace("site", "").strip().title()

    """
    @cached_property
    def subsection_id(self):
        # This cached property remaps section identifiers onto a monotonic 
        # counter, (i.e. the x in 8.1.x)
        #if hasattr(self, 'subsection_id_'):
        #    return self.subsection_id_
        #if not self.published:
        #    return None
        return {
            # MySQL backend doesnt support distinct on field so we hav to use 
            # a set to deduplicate, sigh
            sub: idx for idx, sub in enumerate({
                sub[0] for sub in self.__class__.objects.filter(
                    published=True,
                    site=self.site
                ).order_by('subsection').values_list('subsection')
            })
        }[self.subsection] + 1
    """

    class Meta:
        abstract = True
        ordering = ("-edited",)
        unique_together = ("site", "published", "subsection")
        indexes = [
            models.Index(fields=("site", "edited")),
            models.Index(fields=("site", "edited", "published")),
            models.Index(fields=("site", "edited", "subsection")),
            models.Index(fields=("site", "edited", "published", "subsection")),
            models.Index(fields=("site", "subsection", "published")),
            models.Index(fields=("subsection", "published")),
        ]
        constraints = [
            CheckConstraint(
                check=~(Q(published=False) & Q(is_deleted=True)),
                name="%(app_label)s_%(class)s_no_mod_deleted",
            )
        ]


class SiteForm(SiteSection):
    """
    0.   Form

         Prepared by (full name)  :
         Date Prepared            : (CCYY-MM-DD)
         Report Type              : (NEW/UPDATE)
         If Update:
          Previous Site Log       : (ssss_ccyymmdd.log)
          Modified/Added Sections : (n.n,n.n,...)
    """

    @classmethod
    def structure(cls):
        return [
            "prepared_by",
            "date_prepared",
            "report_type",
            (_("If Update"), ("previous_log", "modified_section")),
        ]

    @classmethod
    def section_number(cls):
        return 0

    @classmethod
    def section_header(cls):
        return "Form"

    prepared_by = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Prepared by (full name)"),
        help_text=_("Enter the name of who prepared this site log"),
    )
    date_prepared = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date Prepared"),
        help_text=_("Enter the date the site log was prepared (CCYY-MM-DD)."),
        db_index=True,
        validators=[MaxValueValidator(utc_now_date)],
    )

    report_type = models.CharField(
        max_length=50,
        blank=True,
        default="NEW",
        verbose_name=_("Report Type"),
        help_text=_("Enter type of report. Example: (UPDATE)."),
    )

    previous = models.ForeignKey(
        "slm.ArchiveIndex",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    @property
    def previous_log(self):
        return self.site.get_filename(
            log_format=SiteLogFormat.LEGACY,
            lower_case=True,
            epoch=self.previous.begin,
        )

    @property
    def previous_log_9char(self):
        if self.previous.files.filter(log_format=SiteLogFormat.ASCII_9CHAR).exists():
            return self.site.get_filename(
                log_format=SiteLogFormat.ASCII_9CHAR,
                lower_case=True,
                epoch=self.previous.begin,
            )
        return self.previous_log

    @property
    def previous_xml(self):
        return self.site.get_filename(
            log_format=SiteLogFormat.GEODESY_ML,
            lower_case=True,
            epoch=self.previous.begin,
        )

    @property
    def previous_json(self):
        return self.site.get_filename(
            log_format=SiteLogFormat.JSON,
            name_len=4,
            lower_case=True,
            epoch=self.previous.begin,
        )

    modified_section = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Modified/Added Sections"),
        help_text=_(
            "Enter the sections which have changed from the previous version "
            "of the log. Example: (3.2, 4.2)"
        ),
    )

    def save(self, *args, skip_update=False, set_previous=True, **kwargs):
        from slm.models import ArchiveIndex

        if set_previous:
            self.previous = ArchiveIndex.objects.filter(site=self.site).first()
            if self.previous:
                self.report_type = "UPDATE"
        if not skip_update:
            self.modified_section = kwargs.pop(
                "modified_section", ", ".join(self.site.modified_sections)
            )
            self.date_prepared = datetime.now(timezone.utc).date()
            self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        from slm.models import ArchiveIndex

        super().clean()
        head = ArchiveIndex.objects.filter(
            Q(site=self.site) & Q(end__isnull=True)
        ).first()
        if head and self.date_prepared < head.begin.date():
            raise ValidationError(
                {
                    "date_prepared": [
                        _("Date prepared cannot be before the previous log.")
                    ]
                }
            )

    def publish(self, request=None, silent=False, timestamp=None, update_site=True):
        self.date_prepared = datetime.now(timezone.utc).date()
        return super().publish(
            request=request, silent=silent, timestamp=timestamp, update_site=update_site
        )


class SiteIdentification(SiteSection):
    """
    Old Table(s):
        'SiteLog_Identification',
        'SiteLog_IdentificationGeologic',
        'SiteLog_IdentificationMonument'

    -----------------------------

    1.   Site Identification of the GNSS Monument

    Site Name                :
    Four Character ID        : (A4)
    Monument Inscription     :
    IERS DOMES Number        : (A9)
    CDP Number               : (A4)
    Monument Description     : (PILLAR/BRASS PLATE/STEEL MAST/etc)
      Height of the Monument : (m)
      Monument Foundation    : (STEEL RODS, CONCRETE BLOCK, ROOF, etc)
      Foundation Depth       : (m)
    Marker Description       : (CHISELLED CROSS/DIVOT/BRASS NAIL/etc)
    Date Installed           : (CCYY-MM-DDThh:mmZ)
    Geologic Characteristic  : (BEDROCK/CLAY/CONGLOMERATE/GRAVEL/SAND/etc)
      Bedrock Type           : (IGNEOUS/METAMORPHIC/SEDIMENTARY)
      Bedrock Condition      : (FRESH/JOINTED/WEATHERED)
      Fracture Spacing       : (1-10 cm/11-50 cm/51-200 cm/over 200 cm)
      Fault Zones Nearby     : (YES/NO/Name of the zone)
        Distance/Activity    : (multiple lines)
    Additional Information   : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            "site_name",
            # "four_character_id",
            "nine_character_id",
            "monument_inscription",
            "iers_domes_number",
            "cdp_number",
            (
                "monument_description",
                ("monument_height", "monument_foundation", "foundation_depth"),
            ),
            "marker_description",
            "date_installed",
            (
                "geologic_characteristic",
                (
                    "bedrock_type",
                    "bedrock_condition",
                    "fracture_spacing",
                    ("fault_zones", ("distance",)),
                ),
            ),
            "additional_information",
        ]

    @classmethod
    def section_number(cls):
        return 1

    @classmethod
    def section_header(cls):
        return "Site Identification of the GNSS Monument"

    site_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Site Name"),
        help_text=_("Enter the name of the site."),
        db_index=True,
    )

    @cached_property
    def four_character_id(self):
        return self.site.name[0:4].upper()

    @cached_property
    def nine_character_id(self):
        return self.site.name.upper()

    monument_inscription = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Monument Inscription"),
        help_text=_("Enter what is stamped on the monument"),
        db_index=True,
    )

    iers_domes_number = models.CharField(
        max_length=9,
        blank=True,
        default="",
        verbose_name=_("IERS DOMES Number"),
        help_text=_(
            "This is strictly required. "
            "See https://itrf.ign.fr/en/network/domes/request to obtain one. "
            "Format: 9 character alphanumeric (A9)"
        ),
        db_index=True,
    )

    cdp_number = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("CDP Number"),
        help_text=_(
            "Enter the NASA CDP identifier if available. "
            "Format: 4 character alphanumeric (A4)"
        ),
        db_index=True,
    )

    date_installed = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date Installed (UTC)"),
        help_text=_(
            "Enter the original date that this site was included in the IGS. "
            "Format: (CCYY-MM-DDThh:mmZ)"
        ),
        db_index=True,
    )

    # Monument fields
    monument_description = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Monument Description"),
        help_text=_(
            "Provide a general description of the GNSS monument. "
            "Format: (PILLAR/BRASS PLATE/STEEL MAST/etc)"
        ),
        db_index=True,
    )

    monument_height = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_("Height of the Monument (m)"),
        help_text=_(
            "Enter the height of the monument above the ground surface in "
            "meters. Units: (m)"
        ),
        db_index=True,
    )
    monument_foundation = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Monument Foundation"),
        help_text=_(
            "Describe how the GNSS monument is attached to the ground. "
            "Format: (STEEL RODS, CONCRETE BLOCK, ROOF, etc)"
        ),
        db_index=True,
    )
    foundation_depth = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_("Foundation Depth (m)"),
        help_text=_(
            "Enter the depth of the monument foundation below the ground "
            "surface in meters. Format: (m)"
        ),
        db_index=True,
    )

    marker_description = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Marker Description"),
        help_text=_(
            "Describe the actual physical marker reference point. "
            "Format: (CHISELLED CROSS/DIVOT/BRASS NAIL/etc)"
        ),
        db_index=True,
    )

    geologic_characteristic = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Geologic Characteristic"),
        help_text=_(
            "Describe the general geologic characteristics of the GNSS site. "
            "Format: (BEDROCK/CLAY/CONGLOMERATE/GRAVEL/SAND/etc)"
        ),
        db_index=True,
    )

    bedrock_type = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Bedrock Type"),
        help_text=_(
            "If the site is located on bedrock, describe the nature of that "
            "bedrock. Format: (IGNEOUS/METAMORPHIC/SEDIMENTARY)"
        ),
        db_index=True,
    )

    bedrock_condition = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Bedrock Condition"),
        help_text=_(
            "If the site is located on bedrock, describe the condition of "
            "that bedrock. Format: (FRESH/JOINTED/WEATHERED)"
        ),
        db_index=True,
    )

    fracture_spacing = EnumField(
        FractureSpacing,
        strict=False,
        max_length=50,
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Fracture Spacing"),
        help_text=_(
            "If known, describe the fracture spacing of the bedrock. "
            "Format: (1-10 cm/11-50 cm/51-200 cm/over 200 cm)"
        ),
        db_index=True,
    )

    fault_zones = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Fault Zones Nearby"),
        help_text=_(
            "Enter the name of any known faults near the site. "
            "Format: (YES/NO/Name of the zone)"
        ),
        db_index=True,
    )

    distance = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Distance/activity"),
        help_text=_(
            "Describe proximity of the site to any known faults. "
            "Format: (multiple lines)"
        ),
    )

    additional_information = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Additional Information"),
        help_text=_(
            "Enter any additional information about the geologic "
            "characteristics of the GNSS site. Format: (multiple lines)"
        ),
    )


class SiteLocation(SiteSection):
    """
    Old Table(s):
        'SiteLog_Location'
    -----------------------------

    2.   Site Location Information

         City or Town             :
         State or Province        :
         Country                  :
         Tectonic Plate           :
         Approximate Position (ITRF)
           X Coordinate (m)       :
           Y Coordinate (m)       :
           Z Coordinate (m)       :
           Latitude (N is +)      : (+/-DDMMSS.SS)
           Longitude (E is +)     : (+/-DDDMMSS.SS)
           Elevation (m,ellips.)  : (F7.1)
         Additional Information   : (multiple lines)
    """

    objects = SiteLocationManager.from_queryset(SiteLocationQueryset)()

    coordinate_mode = getattr(
        settings, "SLM_COORDINATE_MODE", CoordinateMode.INDEPENDENT
    )

    @classmethod
    def structure(cls):
        return [
            "city",
            "state",
            "country",
            "tectonic",
            (
                _("Approximate Position (ITRF)"),
                (
                    "xyz",
                    "llh",
                ),
            ),
            "additional_information",
        ]

    @classmethod
    def section_number(cls):
        return 2

    @classmethod
    def section_header(cls):
        return "Site Location Information"

    city = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("City or Town"),
        help_text=_("Enter the city or town the site is located in"),
        db_index=True,
    )
    state = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("State or Province"),
        help_text=_("Enter the state or province the site is located in"),
        db_index=True,
    )

    country = EnumField(
        ISOCountry,
        strict=False,
        max_length=100,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Country or Region"),
        help_text=_("Enter the country/region the site is located in"),
        db_index=True,
    )

    tectonic = EnumField(
        TectonicPlates,
        strict=False,
        max_length=50,
        null=True,
        default=None,
        blank=True,
        verbose_name=_("Tectonic Plate"),
        help_text=_("Select the primary tectonic plate that the GNSS site occupies"),
        db_index=True,
    )

    # https://epsg.io/7789
    xyz = gis_models.PointField(
        srid=7789,
        dim=3,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Enter the ITRF position to a one meter precision. Format (m)"),
        verbose_name=_("Position (X, Y, Z) (m)"),
    )

    # https://epsg.io/4979
    llh = gis_models.PointField(
        srid=4979,
        dim=3,
        null=True,
        blank=False,
        verbose_name=_("Position (Lat, Lon, Elev (m))"),
        help_text=_(
            "Enter the ITRF latitude and longitude in decimal degrees and "
            "elevation in meters to one meter precision. Note, legacy site "
            "log format is (+/-DDMMSS.SS) and elevation may be given to more "
            "decimal places than F7.1. F7.1 is the minimum for the SINEX "
            "format."
        ),
        db_index=True,
    )

    additional_information = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Additional Information"),
        help_text=_(
            "Describe the source of these coordinates or any other relevant "
            "information. Format: (multiple lines)"
        ),
    )


class SiteReceiverManager(SiteSubSectionManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("receiver_type")
            .prefetch_related("satellite_system")
        )


class SiteReceiverQueryset(SiteSubSectionQuerySet):
    pass


class SiteReceiver(SiteSubSection):
    """
    3.   GNSS Receiver Information

    3.x  Receiver Type            : (A20, from rcvr_ant.tab; see instructions)
         Satellite System         : (GPS+GLO+GAL+BDS+QZSS+SBAS)
         Serial Number            : (A20, but note the first A5 is used in SINEX)
         Firmware Version         : (A11)
         Elevation Cutoff Setting : (deg)
         Date Installed           : (CCYY-MM-DDThh:mmZ)
         Date Removed             : (CCYY-MM-DDThh:mmZ)
         Temperature Stabiliz.    : (none or tolerance in degrees C)
         Additional Information   : (multiple lines)
    """

    @classmethod
    def site_log_fields(cls):
        # satellite_system is not picked up by the super site_log_fields
        # because its many to many - just establish this list here manually
        # instead
        return [
            "receiver_type",
            "satellite_system",
            "serial_number",
            "firmware",
            "elevation_cutoff",
            "installed",
            "removed",
            "temp_stabilized",
            "temp_nominal",
            "temp_deviation",
            "additional_info",
        ]

    # objects = SiteReceiverManager.from_queryset(SiteReceiverQueryset)()

    @classmethod
    def section_number(cls):
        return 3

    @classmethod
    def section_header(cls):
        return "GNSS Receiver Information"

    @classmethod
    def subsection_number(cls):
        return None

    @property
    def heading(self):
        return self.receiver_type.model

    @property
    def effective(self):
        if self.installed and self.removed:
            return f"{date_to_str(self.installed)}/{date_to_str(self.removed)}"
        elif self.installed:
            return f"{date_to_str(self.installed)}"
        return ""

    receiver_type = models.ForeignKey(
        "slm.Receiver",
        blank=False,
        verbose_name=_("Receiver Type"),
        help_text=_(
            "Please find your receiver in "
            "https://files.igs.org/pub/station/general/rcvr_ant.tab and use "
            "the official name, taking care to get capital letters, hyphens, "
            "etc. exactly correct. If you do not find a listing for your "
            "receiver, please notify the IGS Central Bureau. "
            "Format: (A20, from rcvr_ant.tab; see instructions)"
        ),
        on_delete=models.PROTECT,
        related_name="site_receivers",
    )

    satellite_system = models.ManyToManyField(
        "slm.SatelliteSystem",
        verbose_name=_("Satellite System"),
        blank=True,
        help_text=_("Check all GNSS systems that apply"),
    )

    serial_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Serial Number"),
        help_text=_(
            "Enter the receiver serial number. "
            "Format: (A20, but note the first A5 is used in SINEX)"
        ),
        db_index=True,
    )

    firmware = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Firmware Version"),
        help_text=_("Enter the receiver firmware version. Format: (A11)"),
        db_index=True,
    )

    elevation_cutoff = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Elevation Cutoff Setting (°)"),
        help_text=_(
            "Please respond with the tracking cutoff as set in the receiver, "
            "regardless of terrain or obstructions in the area. Format: (deg)"
        ),
        validators=[MinValueValidator(-5), MaxValueValidator(15)],
        db_index=True,
    )

    installed = models.DateTimeField(
        null=True,
        blank=False,
        verbose_name=_("Date Installed (UTC)"),
        help_text=_(
            "Enter the date and time the receiver was installed. "
            "Format: (CCYY-MM-DDThh:mmZ)"
        ),
        db_index=True,
    )

    removed = models.DateTimeField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_("Date Removed (UTC)"),
        help_text=_(
            "Enter the date and time the receiver was removed. It is important"
            " that the date removed is entered BEFORE the addition of a new "
            "receiver. Format: (CCYY-MM-DDThh:mmZ)"
        ),
        db_index=True,
    )

    temp_stabilized = models.BooleanField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_("Temperature Stabilized"),
        help_text=_(
            "If null (default) the temperature stabilization status is "
            "unknown. If true the receiver is in a temperature stabilized "
            "environment, if false the receiver is not in a temperature "
            "stabilized environment."
        ),
    )

    temp_nominal = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Nominal Temperature (°C)"),
        help_text=_(
            "If the receiver is in a temperature controlled environment, "
            "please enter the approximate temperature of that environment. "
            "Format: (°C)"
        ),
        db_index=True,
    )
    # this field is a string in GeodesyML - therefore leaving it as character
    temp_deviation = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Temperature Deviation (± °C)"),
        help_text=_(
            "If the receiver is in a temperature controlled environment, "
            "please enter the expected temperature deviation from nominal of "
            "that environment. Format: (± °C)"
        ),
        db_index=True,
    )

    additional_info = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Additional Information"),
        help_text=_(
            "Enter any additional relevant information about the receiver. "
            "Format: (multiple lines)"
        ),
    )

    def __str__(self):
        return str(self.receiver_type)

    class Meta(SiteSubSection.Meta):
        indexes = [
            models.Index(fields=("site", "subsection", "published", "installed")),
            models.Index(fields=("subsection", "published", "installed")),
        ]


class SiteAntennaManager(SiteSubSectionManager):
    def get_queryset(self):
        return super().get_queryset().select_related("antenna_type", "radome_type")


class SiteAntennaQueryset(SiteSubSectionQuerySet):
    pass


class SiteAntenna(SiteSubSection):
    """
    4.   GNSS Antenna Information

    4.x  Antenna Type             : (A20, from rcvr_ant.tab; see instructions)
         Serial Number            : (A*, but note the first A5 is used in SINEX)
         Antenna Reference Point  : (BPA/BCR/XXX from "antenna.gra"; see instr.)
         Marker->ARP Up Ecc. (m)  : (F8.4)
         Marker->ARP North Ecc(m) : (F8.4)
         Marker->ARP East Ecc(m)  : (F8.4)
         Alignment from True N    : (deg; + is clockwise/east)
         Antenna Radome Type      : (A4 from rcvr_ant.tab; see instructions)
         Radome Serial Number     :
         Antenna Cable Type       : (vendor & type number)
         Antenna Cable Length     : (m)
         Date Installed           : (CCYY-MM-DDThh:mmZ)
         Date Removed             : (CCYY-MM-DDThh:mmZ)
         Additional Information   : (multiple lines)
    """

    # objects = SiteAntennaManager.from_queryset(SiteAntennaQueryset)()

    @property
    def heading(self):
        return self.antenna_type.model

    @property
    def effective(self):
        if self.installed and self.removed:
            return f"{date_to_str(self.installed)}/{date_to_str(self.removed)}"
        elif self.installed:
            return f"{date_to_str(self.installed)}"
        return ""

    @classmethod
    def section_number(cls):
        return 4

    @classmethod
    def section_header(cls):
        return "GNSS Antenna Information"

    @classmethod
    def subsection_number(cls):
        return None

    antenna_type = models.ForeignKey(
        "slm.Antenna",
        on_delete=models.PROTECT,
        blank=False,
        verbose_name=_("Antenna Type"),
        help_text=_(
            "Please find your antenna radome type in "
            "https://files.igs.org/pub/station/general/rcvr_ant.tab and use "
            "the official name, taking care to get capital letters, hyphens, "
            "etc. exactly correct. The radome code from rcvr_ant.tab must be "
            'indicated in columns 17-20 of the Antenna Type, use "NONE" if no '
            "radome is installed. The antenna+radome pair must have an entry "
            "in https://files.igs.org/pub/station/general/igs05.atx with "
            "zenith- and azimuth-dependent calibration values down to the "
            "horizon. If not, notify the CB. Format: (A20, from rcvr_ant.tab; "
            "see instructions)"
        ),
        related_name="site_antennas",
    )

    serial_number = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_("Serial Number"),
        help_text=_("Only Alpha Numeric Chars and - . Symbols allowed"),
        db_index=True,
    )

    # todo remove this b/c it belongs solely on antenna type?
    reference_point = EnumField(
        AntennaReferencePoint,
        blank=True,
        default=None,
        verbose_name=_("Antenna Reference Point"),
        null=True,
        help_text=_(
            "Locate your antenna in the file "
            "https://files.igs.org/pub/station/general/antenna.gra. Indicate "
            "the three-letter abbreviation for the point which is indicated "
            "equivalent to ARP for your antenna. Contact the Central Bureau if"
            " your antenna does not appear. Format: (BPA/BCR/XXX from "
            "antenna.gra; see instr.)"
        ),
        db_index=True,
    )

    marker_une = gis_models.PointField(
        srid=0,  # env is a local reference frame
        dim=3,
        verbose_name=_("Marker->ARP UNE Ecc (m)"),
        default=None,
        null=True,
        blank=True,
        help_text=_(
            "Up-North-East eccentricity is the offset between the ARP and "
            "marker described in section 1 measured to an accuracy of 1mm. "
            "Format: (F8.4) Value 0 is OK"
        ),
    )

    alignment = models.FloatField(
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Alignment from True N (°)"),
        help_text=_(
            "Enter the clockwise offset from true north in degrees. The "
            "positive direction is clockwise, so that due east would be "
            'equivalent to a response of "+90". '
            "Format: (deg; + is clockwise/east)"
        ),
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        db_index=True,
    )

    radome_type = models.ForeignKey(
        "slm.Radome",
        blank=False,
        verbose_name=_("Antenna Radome Type"),
        help_text=_(
            "Please find your antenna radome type in "
            "https://files.igs.org/pub/station/general/rcvr_ant.tab and use "
            "the official name, taking care to get capital letters, hyphens, "
            "etc. exactly correct. The radome code from rcvr_ant.tab must be "
            'indicated in columns 17-20 of the Antenna Type, use "NONE" if no '
            "radome is installed. The antenna+radome pair must have an entry "
            "in https://files.igs.org/pub/station/general/igs05.atx with "
            "zenith- and azimuth-dependent calibration values down to the "
            "horizon. If not, notify the CB. Format: (A20, from rcvr_ant.tab; "
            "see instructions)"
        ),
        on_delete=models.PROTECT,
        related_name="site_radomes",
    )

    radome_serial_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Radome Serial Number"),
        help_text=_("Enter the serial number of the radome if available"),
        db_index=True,
    )

    cable_type = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Antenna Cable Type"),
        help_text=_(
            "Enter the antenna cable specification if know. "
            "Format: (vendor & type number)"
        ),
        db_index=True,
    )

    cable_length = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_("Antenna Cable Length"),
        help_text=_("Enter the antenna cable length in meters. Format: (m)"),
        db_index=True,
    )

    installed = models.DateTimeField(
        blank=False,
        verbose_name=_("Date Installed (UTC)"),
        help_text=_(
            "Enter the date the receiver was installed. Format: (CCYY-MM-DDThh:mmZ)"
        ),
        db_index=True,
    )

    removed = models.DateTimeField(
        default=None,
        blank=True,
        null=True,
        verbose_name=_("Date Removed (UTC)"),
        help_text=_(
            "Enter the date the receiver was removed. It is important that "
            "the date removed is entered before the addition of a new "
            "receiver. Format: (CCYY-MM-DDThh:mmZ)"
        ),
        db_index=True,
    )

    additional_information = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Additional Information"),
        help_text=_(
            "Enter additional relevant information about the antenna, cable "
            "and radome. Indicate if a signal splitter has been used. "
            "Format: (multiple lines)"
        ),
    )

    @property
    def graphic(self):
        if self.custom_graphic:
            return self.custom_graphic
        return self.antenna_type.graphic

    custom_graphic = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Antenna Graphic"),
        help_text=_(
            "A custom graphic may be provided, otherwise the default graphic "
            "for the antenna type will be used."
        ),
    )

    def __str__(self):
        return str(self.antenna_type)

    class Meta(SiteSubSection.Meta):
        indexes = [
            models.Index(fields=("site", "subsection", "published", "installed")),
            models.Index(fields=("subsection", "published", "installed")),
        ]


class SiteSurveyedLocalTies(SiteSubSection):
    """
    5.   Surveyed Local Ties

    5.x  Tied Marker Name         :
         Tied Marker Usage        : (SLR/VLBI/LOCAL CONTROL/FOOTPRINT/etc)
         Tied Marker CDP Number   : (A4)
         Tied Marker DOMES Number : (A9)
         Differential Components from GNSS Marker to the tied monument (ITRS)
           dx (m)                 : (m)
           dy (m)                 : (m)
           dz (m)                 : (m)
         Accuracy (mm)            : (mm)
         Survey method            : (GPS CAMPAIGN/TRILATERATION/TRIANGULATION/etc)
         Date Measured            : (CCYY-MM-DDThh:mmZ)
         Additional Information   : (multiple lines)
    """

    @classproperty
    def valid_time(cls):
        """
        surveyed local ties are always valid -
        todo is this correct even if date measured is not null??
        """
        return None

    @classmethod
    def structure(cls):
        return [
            "name",
            "usage",
            "cdp_number",
            "domes_number",
            (
                _(
                    "Differential Components from GNSS Marker to the tied "
                    "monument (ITRS)"
                ),
                ("diff_xyz",),
            ),
            "accuracy",
            "survey_method",
            "measured",
            "additional_information",
        ]

    @property
    def heading(self):
        return self.name

    @property
    def effective(self):
        if self.measured:
            return f"{date_to_str(self.measured)}"
        return ""

    @classmethod
    def section_number(cls):
        return 5

    @classmethod
    def section_header(cls):
        return "Surveyed Local Ties"

    @classmethod
    def subsection_number(cls):
        return None

    name = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Tied Marker Name"),
        help_text=_("Enter name of Tied Marker"),
        db_index=True,
    )
    usage = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Tied Marker Usage"),
        help_text=_(
            "Enter the purpose of the tied marker such as SLR, VLBI, DORIS, "
            "or other. Format: (SLR/VLBI/LOCAL CONTROL/FOOTPRINT/etc)"
        ),
        db_index=True,
    )
    cdp_number = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Tied Marker CDP Number"),
        help_text=_("Enter the NASA CDP identifier if available. Format: (A4)"),
        db_index=True,
    )
    domes_number = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Tied Marker DOMES Number"),
        help_text=_("Enter the tied marker DOMES number if available. Format: (A9)"),
        db_index=True,
    )

    diff_xyz = gis_models.PointField(
        srid=7789,
        dim=3,
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text=_(
            "Enter the differential ITRF coordinates to one millimeter "
            "precision. Format: dx, dy, dz (m)"
        ),
        verbose_name=_("Δ XYZ (m)"),
    )

    accuracy = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Accuracy (mm)"),
        help_text=_("Enter the accuracy of the tied survey. Format: (mm)."),
        db_index=True,
    )

    survey_method = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Survey method"),
        help_text=_(
            "Enter the source or the survey method used to determine the "
            "differential coordinates, such as GNSS survey, conventional "
            "survey, or other. "
            "Format: (GPS CAMPAIGN/TRILATERATION/TRIANGULATION/etc)"
        ),
        db_index=True,
    )

    measured = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Date Measured (UTC)"),
        help_text=_(
            "Enter the date of the survey local ties measurement. "
            "Format: (CCYY-MM-DDThh:mmZ)"
        ),
        db_index=True,
    )

    additional_information = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Additional Information"),
        help_text=_(
            "Enter any additional information relevant to surveyed local ties."
            " Format: (multiple lines)"
        ),
    )


class SiteFrequencyStandard(SiteSubSection):
    """
    6.   Frequency Standard

    6.x  Standard Type            : (INTERNAL or EXTERNAL H-MASER/CESIUM/etc)
           Input Frequency        : (if external)
           Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
           Notes                  : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [("standard_type", ("input_frequency", "effective_dates", "notes"))]

    @property
    def heading(self):
        return (
            self.standard_type.label
            if isinstance(self.standard_type, Enum)
            else str(self.standard_type)
        )

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return (
                f"{date_to_str(self.effective_start)}/{date_to_str(self.effective_end)}"
            )
        elif self.effective_start:
            return f"{date_to_str(self.effective_start)}"
        return ""

    @classmethod
    def section_number(cls):
        return 6

    @classmethod
    def section_header(cls):
        return "Frequency Standard"

    @classmethod
    def subsection_number(cls):
        return None

    standard_type = EnumField(
        FrequencyStandardType,
        max_length=50,
        strict=False,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Standard Type"),
        help_text=_(
            "Select whether the frequency standard is INTERNAL or EXTERNAL "
            "and describe the oscillator type. "
            "Format: (INTERNAL or EXTERNAL H-MASER/CESIUM/etc)"
        ),
        db_index=True,
    )

    input_frequency = models.FloatField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Input Frequency (MHz)"),
        help_text=_("Enter the input frequency in MHz if known."),
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Notes"),
        help_text=_(
            "Enter any additional information relevant to frequency standard. "
            "Format: (multiple lines)"
        ),
    )

    effective_start = models.DateField(
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Enter the effective start date for the frequency standard. "
            "Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )

    effective_end = models.DateField(
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Enter the effective end date for the frequency standard. "
            "Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )

    def effective_dates(self):
        return self.effective

    effective_dates.field = (effective_start, effective_end)
    effective_dates.verbose_name = _("Effective Dates")

    class Meta(SiteSubSection.Meta):
        indexes = [
            models.Index(fields=("site", "subsection", "published", "effective_start")),
            models.Index(fields=("subsection", "published", "effective_start")),
        ]


class SiteCollocation(SiteSubSection):
    """
    7.   Collocation Information

    7.1  Instrumentation Type     : (GPS/GLONASS/DORIS/PRARE/SLR/VLBI/TIME/etc)
           Status                 : (PERMANENT/MOBILE)
           Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
           Notes                  : (multiple lines)

    7.x  Instrumentation Type     : (GPS/GLONASS/DORIS/PRARE/SLR/VLBI/TIME/etc)
           Status                 : (PERMANENT/MOBILE)
           Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
           Notes                  : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [("instrument_type", ("status", "effective_dates", "notes"))]

    @property
    def heading(self):
        return self.instrument_type

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return (
                f"{date_to_str(self.effective_start)}/{date_to_str(self.effective_end)}"
            )
        elif self.effective_start:
            return f"{date_to_str(self.effective_start)}"
        return ""

    @classmethod
    def section_number(cls):
        return 7

    @classmethod
    def subsection_number(cls):
        return None

    @classmethod
    def section_header(cls):
        return "Collocation Information"

    instrument_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Instrumentation Type"),
        help_text=_("Select all collocated instrument types that apply"),
        db_index=True,
    )

    status = EnumField(
        CollocationStatus,
        max_length=50,
        strict=False,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Status"),
        help_text=_("Select appropriate status"),
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Notes"),
        help_text=_(
            "Enter any additional information relevant to collocation. "
            "Format: (multiple lines)"
        ),
    )

    effective_start = models.DateField(
        max_length=50,
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Enter the effective start date of the collocated instrument. "
            "Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )
    effective_end = models.DateField(
        max_length=50,
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Enter the effective end date of the collocated instrument. "
            "Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )

    def effective_dates(self):
        return self.effective

    effective_dates.field = (effective_start, effective_end)
    effective_dates.verbose_name = _("Effective Dates")

    class Meta(SiteSubSection.Meta):
        indexes = [
            models.Index(fields=("site", "subsection", "published", "effective_start")),
            models.Index(fields=("subsection", "published", "effective_start")),
        ]


class MeteorologicalInstrumentation(SiteSubSection):
    """
    8.   Meteorological Instrumentation

    8.x.x ...
       Manufacturer           :
       Serial Number          :
       Height Diff to Ant     : (m)
       Calibration date       : (CCYY-MM-DD)
       Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
       Notes                  : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            "manufacturer",
            "serial_number",
            "height_diff",
            "calibration",
            "effective_dates",
            "notes",
        ]

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return (
                f"{date_to_str(self.effective_start)}/{date_to_str(self.effective_end)}"
            )
        elif self.effective_start:
            return f"{date_to_str(self.effective_start)}"
        return ""

    @classmethod
    def section_number(cls):
        return 8

    @classmethod
    def section_header(cls):
        return "Meteorological Instrumentation"

    manufacturer = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Manufacturer"),
        help_text=_("Enter manufacturer's name"),
        db_index=True,
    )
    serial_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Serial Number"),
        help_text=_("Enter the serial number of the sensor"),
        db_index=True,
    )

    height_diff = models.FloatField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Height Diff to Ant (m)"),
        help_text=_(
            "In meters, enter the difference in height between the sensor and "
            "the GNSS antenna. Positive number indicates the sensor is above "
            "the GNSS antenna. Decimeter accuracy preferred. Format: (m)"
        ),
        db_index=True,
    )

    calibration = models.DateField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Calibration Date"),
        help_text=_("Enter the date the sensor was calibrated. Format: (CCYY-MM-DD)"),
        db_index=True,
    )

    def calibration_date(self):
        return date_to_str(self.calibration)

    calibration_date.verbose_name = _("Calibration Date")
    calibration_date.field = calibration

    effective_start = models.DateField(
        blank=False,
        null=True,
        help_text=_(
            "Enter the effective start date for the sensor. Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )
    effective_end = models.DateField(
        null=True,
        blank=True,
        default=None,
        help_text=_(
            "Enter the effective end date for the sensor. Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Notes"),
        help_text=_(
            "Enter any additional information relevant to the sensor."
            " Format: (multiple lines)"
        ),
    )

    def effective_dates(self):
        return self.effective

    effective_dates.field = (effective_start, effective_end)
    effective_dates.verbose_name = _("Effective Dates")

    class Meta(SiteSubSection.Meta):
        abstract = True
        indexes = [
            models.Index(fields=("site", "subsection", "published", "effective_start")),
            models.Index(fields=("subsection", "published", "effective_start")),
        ]


class SiteHumiditySensor(MeteorologicalInstrumentation):
    """
    8.1.1 Humidity Sensor Model   :
           Manufacturer           :
           Serial Number          :
           Data Sampling Interval : (sec)
           Accuracy (% rel h)     : (% rel h)
           Aspiration             : (UNASPIRATED/NATURAL/FAN/etc)
           Height Diff to Ant     : (m)
           Calibration date       : (CCYY-MM-DD)
           Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
           Notes                  : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            "model",
            "manufacturer",
            "serial_number",
            "sampling_interval",
            "accuracy",
            "aspiration",
            "height_diff",
            "calibration_date",
            "effective_dates",
            "notes",
        ]

    @property
    def heading(self):
        return self.model

    @classmethod
    def subsection_number(cls):
        return 1

    model = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Humidity Sensor Model"),
        help_text=_("Enter humidity sensor model"),
        db_index=True,
    )

    sampling_interval = models.PositiveSmallIntegerField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Data Sampling Interval (sec)"),
        help_text=_("Enter the sample interval in seconds. Format: (sec)"),
        db_index=True,
    )

    accuracy = models.FloatField(
        default=None,
        blank=True,
        null=True,
        verbose_name=_("Accuracy (% rel h)"),
        help_text=_("Enter the accuracy in % relative humidity. Format: (% rel h)"),
        db_index=True,
    )

    aspiration = EnumField(
        Aspiration,
        null=True,
        default=None,
        blank=True,
        strict=False,
        max_length=50,
        verbose_name=_("Aspiration"),
        help_text=_(
            "Enter the aspiration type if known. Format: (UNASPIRATED/NATURAL/FAN/etc)"
        ),
        db_index=True,
    )


class SitePressureSensor(MeteorologicalInstrumentation):
    """
    8.2.x Pressure Sensor Model   :
       Manufacturer           :
       Serial Number          :
       Data Sampling Interval : (sec)
       Accuracy               : (hPa)
       Height Diff to Ant     : (m)
       Calibration date       : (CCYY-MM-DD)
       Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
       Notes                  : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            "model",
            "manufacturer",
            "serial_number",
            "sampling_interval",
            "accuracy",
            "height_diff",
            "calibration_date",
            "effective_dates",
            "notes",
        ]

    @property
    def heading(self):
        return self.model

    @classmethod
    def subsection_number(cls):
        return 2

    model = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_("Pressure Sensor Model"),
        help_text=_("Enter pressure sensor model"),
        db_index=True,
    )

    sampling_interval = models.PositiveSmallIntegerField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Data Sampling Interval"),
        help_text=_("Enter the sample interval in seconds. Format: (sec)"),
        db_index=True,
    )

    accuracy = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Accuracy (hPa)"),
        help_text=_("Enter the accuracy in hectopascal. Format: (hPa)"),
        db_index=True,
    )


class SiteTemperatureSensor(MeteorologicalInstrumentation):
    """
    8.3.x Temp. Sensor Model  :
       Manufacturer           :
       Serial Number          :
       Data Sampling Interval : (sec)
       Accuracy               : (deg C)
       Aspiration             : (UNASPIRATED/NATURAL/FAN/etc)
       Height Diff to Ant     : (m)
       Calibration date       : (CCYY-MM-DD)
       Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
       Notes                  : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            "model",
            "manufacturer",
            "serial_number",
            "sampling_interval",
            "accuracy",
            "aspiration",
            "height_diff",
            "calibration_date",
            "effective_dates",
            "notes",
        ]

    @property
    def heading(self):
        return self.model

    @classmethod
    def subsection_number(cls):
        return 3

    model = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Temp. Sensor Model"),
        help_text=_("Enter temperature sensor model"),
        db_index=True,
    )

    sampling_interval = models.PositiveSmallIntegerField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Data Sampling Interval"),
        help_text=_("Enter the sample interval in seconds. Format: (sec)"),
        db_index=True,
    )

    accuracy = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Accuracy (deg C)"),
        help_text=_("Enter the accuracy in degrees Centigrade. Format: (deg C)"),
        db_index=True,
    )

    aspiration = EnumField(
        Aspiration,
        null=True,
        default=None,
        blank=True,
        strict=False,
        max_length=50,
        verbose_name=_("Aspiration"),
        help_text=_(
            "Enter the aspiration type if known. Format: (UNASPIRATED/NATURAL/FAN/etc)"
        ),
        db_index=True,
    )


class SiteWaterVaporRadiometer(MeteorologicalInstrumentation):
    """
    8.4.x Water Vapor Radiometer  :
       Manufacturer           :
       Serial Number          :
       Distance to Antenna    : (m)
       Height Diff to Ant     : (m)
       Calibration date       : (CCYY-MM-DD)
       Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
       Notes                  : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            "model",
            "manufacturer",
            "serial_number",
            "distance_to_antenna",
            "height_diff",
            "calibration_date",
            "effective_dates",
            "notes",
        ]

    @property
    def heading(self):
        return self.model

    @classmethod
    def subsection_number(cls):
        return 4

    model = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Water Vapor Radiometer"),
        help_text=_("Enter water vapor radiometer"),
        db_index=True,
    )

    distance_to_antenna = models.FloatField(
        default=None,
        blank=True,
        null=True,
        verbose_name=_("Distance to Antenna (m)"),
        help_text=_(
            "Enter the horizontal distance between the WVR and the GNSS "
            "antenna to the nearest meter. Format: (m)"
        ),
        db_index=True,
    )


class SiteOtherInstrumentation(SiteSubSection):
    """
    8.5.x Other Instrumentation   : (multiple lines)
    """

    @classproperty
    def valid_time(cls):
        return None

    @classmethod
    def structure(cls):
        return ["instrumentation"]

    @property
    def heading(self):
        return self.instrumentation

    @property
    def effective(self):
        return ""

    @classmethod
    def section_number(cls):
        return 8

    @classmethod
    def subsection_number(cls):
        return 5

    @classmethod
    def section_header(cls):
        return None

    instrumentation = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Other Instrumentation"),
        help_text=_(
            "Enter any other relevant information regarding meteorological "
            "instrumentation near the site. Format: (multiple lines)"
        ),
    )


class Condition(SiteSubSection):
    """
    9.  Local Ongoing Conditions Possibly Affecting Computed Position

       Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
       Additional Information : (multiple lines)
    """

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return (
                f"{date_to_str(self.effective_start)}/{date_to_str(self.effective_end)}"
            )
        elif self.effective_start:
            return f"{date_to_str(self.effective_start)}"
        return ""

    @classmethod
    def section_number(cls):
        return 9

    @classmethod
    def section_header(cls):
        return "Local Ongoing Conditions Possibly Affecting Computed Position"

    effective_start = models.DateField(
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Enter the effective start date for the condition. Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )

    effective_end = models.DateField(
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Enter the effective end date for the condition. Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )

    additional_information = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Additional Information"),
        help_text=_(
            "Enter additional relevant information about any radio "
            "interferences. Format: (multiple lines)"
        ),
    )

    def effective_dates(self):
        return self.effective

    effective_dates.field = (effective_start, effective_end)
    effective_dates.verbose_name = _("Effective Dates")

    class Meta(SiteSubSection.Meta):
        abstract = True
        indexes = [
            models.Index(fields=("site", "subsection", "published", "effective_start")),
            models.Index(fields=("subsection", "published", "effective_start")),
        ]


class SiteRadioInterferences(Condition):
    """
    9.  Local Ongoing Conditions Possibly Affecting Computed Position

    9.1.x Radio Interferences     : (TV/CELL PHONE ANTENNA/RADAR/etc)
           Observed Degradations  : (SN RATIO/DATA GAPS/etc)
           Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
           Additional Information : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            "interferences",
            "degradations",
            "effective_dates",
            "additional_information",
        ]

    @property
    def heading(self):
        return self.interferences

    @classmethod
    def subsection_number(cls):
        return 1

    interferences = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Radio Interferences"),
        help_text=_(
            "Enter all sources of radio interference near the GNSS station. "
            "Format: (TV/CELL PHONE ANTENNA/RADAR/etc)"
        ),
        db_index=True,
    )
    degradations = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Observed Degradations"),
        help_text=_(
            "Describe any observed degradations in the GNSS data that are "
            "presumed to result from radio interference. "
            "Format: (SN RATIO/DATA GAPS/etc)"
        ),
        db_index=True,
    )


class SiteMultiPathSources(Condition):
    """
    9.2.x Multipath Sources       : (METAL ROOF/DOME/VLBI ANTENNA/etc)
           Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
           Additional Information : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return ["sources", "effective_dates", "additional_information"]

    @property
    def heading(self):
        return self.sources

    @classmethod
    def subsection_number(cls):
        return 2

    sources = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Multipath Sources"),
        help_text=_(
            "Describe any potential multipath sources near the GNSS station. "
            "Format: .(METAL ROOF/DOME/VLBI ANTENNA/etc)"
        ),
        db_index=True,
    )


class SiteSignalObstructions(Condition):
    """
    9.3.x Signal Obstructions     : (TREES/BUILDINGS/etc)
       Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
       Additional Information : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return ["obstructions", "effective_dates", "additional_information"]

    @property
    def heading(self):
        return self.obstructions

    @classmethod
    def subsection_number(cls):
        return 3

    obstructions = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Signal Obstructions"),
        help_text=_(
            "Describe any potential signal obstructions near the GNSS station."
            " Format: (TREES/BUILDLINGS/etc)"
        ),
        db_index=True,
    )


class SiteLocalEpisodicEffects(SiteSubSection):
    """
    10.  Local Episodic Effects Possibly Affecting Data Quality

    10.x Date                     : (CCYY-MM-DD/CCYY-MM-DD)
         Event                    : (TREE CLEARING/CONSTRUCTION/etc)
    """

    @classmethod
    def structure(cls):
        return ["date", "event"]

    @property
    def heading(self):
        return self.event

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return (
                f"{date_to_str(self.effective_start)}/{date_to_str(self.effective_end)}"
            )
        elif self.effective_start:
            return f"{date_to_str(self.effective_start)}"
        return ""

    @classmethod
    def section_number(cls):
        return 10

    @classmethod
    def subsection_number(cls):
        return None

    @classmethod
    def section_header(cls):
        return "Local Episodic Effects Possibly Affecting Data Quality"

    event = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Event"),
        help_text=_(
            "Describe any events near the GNSS station that may affect data "
            "quality such as tree clearing, construction, or weather events. "
            "Format: (TREE CLEARING/CONSTRUCTION/etc)"
        ),
    )
    effective_start = models.DateField(
        blank=True,
        default=None,
        null=True,
        help_text=_(
            "Enter the effective start date for the local episodic effect. "
            "Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )

    effective_end = models.DateField(
        blank=True,
        default=None,
        null=True,
        help_text=_(
            "Enter the effective end date for the local episodic effect. "
            "Format: (CCYY-MM-DD)"
        ),
        db_index=True,
    )

    def date(self):
        return self.effective

    date.field = (effective_start, effective_end)
    date.verbose_name = _("Date")

    class Meta(SiteSubSection.Meta):
        indexes = [
            models.Index(fields=("site", "subsection", "published", "effective_start")),
            models.Index(fields=("subsection", "published", "effective_start")),
        ]


class AgencyPOC(SiteSection):
    """
    Agency                   : (multiple lines)
    Preferred Abbreviation   : (A10)
    Mailing Address          : (multiple lines)
    Primary Contact
      Contact Name           :
      Telephone (primary)    :
      Telephone (secondary)  :
      Fax                    :
      E-mail                 :
    Secondary Contact
      Contact Name           :
      Telephone (primary)    :
      Telephone (secondary)  :
      Fax                    :
      E-mail                 :
    Additional Information   : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            "agency",
            "preferred_abbreviation",
            "mailing_address",
            (
                _("Primary Contact (Organization Only)"),
                (
                    "primary_name",
                    "primary_phone1",
                    "primary_phone2",
                    "primary_fax",
                    "primary_email",
                ),
            ),
            (
                _("Secondary Contact"),
                (
                    "secondary_name",
                    "secondary_phone1",
                    "secondary_phone2",
                    "secondary_fax",
                    "secondary_email",
                ),
            ),
            "additional_information",
        ]

    agency = models.TextField(
        max_length=300,
        blank=True,
        default="",
        verbose_name=_("Agency"),
        help_text=_("Enter contact agency name"),
    )
    preferred_abbreviation = models.CharField(
        max_length=50,  # todo A10
        blank=True,
        default="",
        verbose_name=_("Preferred Abbreviation"),
        help_text=_("Enter the contact agency's preferred abbreviation"),
        db_index=True,
    )
    mailing_address = models.TextField(
        max_length=300,
        default="",
        blank=True,
        verbose_name=_("Mailing Address"),
        help_text=_("Enter agency mailing address"),
    )

    primary_name = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Contact Name"),
        help_text=_("Enter primary contact organization name"),
        db_index=True,
    )
    primary_phone1 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Telephone (primary)"),
        help_text=_("Enter primary contact primary phone number"),
        db_index=True,
    )
    primary_phone2 = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Telephone (secondary)"),
        help_text=_("Enter primary contact secondary phone number"),
        db_index=True,
    )
    primary_fax = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Fax"),
        help_text=_("Enter primary contact organization fax number"),
        db_index=True,
    )
    primary_email = models.EmailField(
        blank=True,
        default="",
        verbose_name=_("E-mail"),
        help_text=_(
            "Enter primary contact organization email address. MUST be a "
            "generic email, no personal email addresses."
        ),
        db_index=True,
    )

    secondary_name = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Contact Name"),
        help_text=_("Enter secondary contact name"),
        db_index=True,
    )
    secondary_phone1 = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Telephone (primary)"),
        help_text=_("Enter secondary contact primary phone number"),
        db_index=True,
    )
    secondary_phone2 = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Telephone (secondary)"),
        help_text=_("Enter secondary contact secondary phone number"),
        db_index=True,
    )
    secondary_fax = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name=_("Fax"),
        help_text=_("Enter secondary contact fax number"),
        db_index=True,
    )
    secondary_email = models.EmailField(
        default="",
        blank=True,
        verbose_name=_("E-mail"),
        help_text=_("Enter secondary contact email address"),
        db_index=True,
    )

    additional_information = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Additional Information"),
        help_text=_(
            "Enter additional relevant information regarding operational "
            "contacts. Format: (multiple lines)."
        ),
    )

    class Meta:
        abstract = True


class SiteOperationalContact(AgencyPOC):
    """
    11.   On-Site, Point of Contact Agency Information

         Agency                   : (multiple lines)
         Preferred Abbreviation   : (A10)
         Mailing Address          : (multiple lines)
         Primary Contact
           Contact Name           :
           Telephone (primary)    :
           Telephone (secondary)  :
           Fax                    :
           E-mail                 :
         Secondary Contact
           Contact Name           :
           Telephone (primary)    :
           Telephone (secondary)  :
           Fax                    :
           E-mail                 :
         Additional Information   : (multiple lines)
    """

    @classmethod
    def section_number(cls):
        return 11

    @classmethod
    def section_header(cls):
        return "On-Site, Point of Contact Agency Information"


class SiteResponsibleAgency(AgencyPOC):
    """
    12.  Responsible Agency (if different from 11.)

     Agency                   : (multiple lines)
     Preferred Abbreviation   : (A10)
     Mailing Address          : (multiple lines)
     Primary Contact
       Contact Name           :
       Telephone (primary)    :
       Telephone (secondary)  :
       Fax                    :
       E-mail                 :
     Secondary Contact
       Contact Name           :
       Telephone (primary)    :
       Telephone (secondary)  :
       Fax                    :
       E-mail                 :
     Additional Information   : (multiple lines)
    """

    @classmethod
    def section_number(cls):
        return 12

    @classmethod
    def section_header(cls):
        return "Responsible Agency"


class SiteMoreInformation(SiteSection):
    """
    13.  More Information

     Primary Data Center      : ROB
     Secondary Data Center    : BKG
     URL for More Information :
     Hardcopy on File
       Site Map               : (Y or URL)
       Site Diagram           : (Y or URL)
       Horizon Mask           : (Y or URL)
       Monument Description   : (Y or URL)
       Site Pictures          : (Y or URL)
     Additional Information   : (multiple lines)
     Antenna Graphics with Dimensions
    """

    @classmethod
    def structure(cls):
        return [
            "primary",
            "secondary",
            "more_info",
            (
                _("Hardcopy on File"),
                (
                    "sitemap",
                    "site_diagram",
                    "horizon_mask",
                    "monument_description",
                    "site_picture",
                ),
            ),
            "additional_information",
            # (_('Antenna Graphics with Dimensions'), ('antenna_graphic',))
        ]

    @classmethod
    def section_number(cls):
        return 13

    @classmethod
    def section_header(cls):
        return "More Information"

    primary = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Primary Data Center"),
        help_text=_("Enter the name of the primary operational data center"),
        db_index=True,
    )
    secondary = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Secondary Data Center"),
        help_text=_("Enter the name of the secondary or backup data center"),
        db_index=True,
    )

    more_info = models.URLField(
        default="",
        null=False,
        blank=True,
        verbose_name=_("URL for More Information"),
        db_index=True,
        max_length=8000,
    )

    sitemap = models.CharField(
        max_length=255,
        default="",
        blank=True,
        verbose_name=_("Site Map"),
        help_text=_("Enter the site map URL"),
        db_index=True,
    )
    site_diagram = models.CharField(
        max_length=255,
        default="",
        blank=True,
        verbose_name=_("Site Diagram"),
        help_text=_("Enter URL for site diagram"),
        db_index=True,
    )
    horizon_mask = models.CharField(
        max_length=255,
        default="",
        blank=True,
        verbose_name=_("Horizon Mask"),
        help_text=_("Enter Horizon mask URL"),
        db_index=True,
    )
    monument_description = models.CharField(
        max_length=255,
        default="",
        blank=True,
        verbose_name=_("Monument Description"),
        help_text=_("Enter monument description URL"),
        db_index=True,
    )
    site_picture = models.CharField(
        max_length=255,
        default="",
        blank=True,
        verbose_name=_("Site Pictures"),
        help_text=_("Enter site pictures URL"),
        db_index=True,
    )

    additional_information = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Additional Information"),
        help_text=_("Enter additional relevant information. Format: (multiple lines)"),
    )

    # def antenna_graphic(self):
    #    return self.site.siteantenna_set.first().graphic

    # antenna_graphic.verbose_name = _('')
    # antenna_graphic.no_indent = True
