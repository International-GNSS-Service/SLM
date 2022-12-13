import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Case, F, Max, Q, Value, When
from django.db.models.functions import (
    Cast,
    Concat,
    ExtractDay,
    ExtractMonth,
    ExtractYear,
    Greatest,
    Lower,
    LPad,
    Substr,
)
from django.utils.functional import cached_property
from django_enum import EnumField
from slm.defines import (
    AntennaReferencePoint,
    Aspiration,
    CollocationStatus,
    FractureSpacing,
    FrequencyStandardType,
    ISOCountry,
    SiteLogStatus,
    TectonicPlates,
)
from slm.models import compat
from slm.utils import date_to_str
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db.models import ExpressionWrapper
from django.utils.timezone import now
from django.utils.translation import gettext as _
from slm import signals as slm_signals
from slm.validators import (
    SLMValidator,
    NULL_TIME,
    get_validators
)


def bool_condition(*args, **kwargs):
    return ExpressionWrapper(
        Q(*args, **kwargs),
        output_field=models.BooleanField()
    )


class DefaultToStrEncoder(json.JSONEncoder):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def default(self, obj):
        return str(obj)


class SiteManager(models.Manager):

    def current(self, epoch=None, published=False):
        """
        if epoch:
            return self.filter(published=True).order_by('-edited').filter(
                edited__lte=epoch
            ).first()
        return self.filter(published=True).order_by('-edited').first()
        """


class SiteQuerySet(models.QuerySet):

    def public(self):
        """
        Return all publicly visible sites.
        :return:
        """
        return self.filter(
            ~Q(status__in=[
                SiteLogStatus.DORMANT,
                SiteLogStatus.PENDING
            ])
            & Q(agencies__public=True)
            & Q(agencies__active=True)
            & Q(last_publish__isnull=False)
        ).distinct()

    def annotate_filenames(
            self,
            published=True,
            name_len=None,
            field_name='filename',
            lower_case=False
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
        name_str = F('name')
        if name_len:
            name_str = Cast(
                Substr('name', 1, length=name_len), models.CharField()
            )

        if lower_case:
            name_str = Lower(name_str)

        timestamp = 'last_update'
        if published:
            timestamp = 'last_publish'

        return self.annotate(
            **{
                field_name: Concat(
                    name_str,
                    Value('_'),
                    Cast(ExtractYear(timestamp), models.CharField()),
                    LPad(
                        Cast(ExtractMonth(timestamp), models.CharField()),
                        2,
                        fill_text=Value('0')
                    ),
                    LPad(
                        Cast(ExtractDay(timestamp), models.CharField()),
                        2,
                        fill_text=Value('0')
                    )
                )
            }
        )

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
            return self.filter(agencies__in=[user.agency])
        return self.none()

    def annotate_review_pending(self):
        return self.annotate(
            _review_pending=bool_condition(
                review_request__isnull=False,
                review_request__timestamp__gte=F('last_publish')
            )
        )

    def meta(self):
        """
        It is expensive to query these normalized values on the fly, so we
        denormalize them onto the Site model. This query can be used to check
        the denormalized data for accuracy and reset it
        """
        qry = self
        for section in self.model.section_fields():
            qry = qry.annotate(**{
                    f'{section}_published': Max(
                        f'{section}__edited',
                        filter=Q(**{f'{section}__published': True})
                    ),
                    f'{section}_modified': Max(f'{section}__edited')
                }
            )
        for section in self.model.subsection_fields():
            qry = qry.annotate(**{
                    f'{section}_published': Max(f'{section}__edited',
                        filter=Q(**{f'{section}__published': True})
                    ),
                    f'{section}_modified': Max(f'{section}__edited')
                }
            )

        for section in self.model.section_fields() + \
                       self.model.subsection_fields():
            qry = qry.annotate(**{
                f'{section}_published': Case(
                    When(
                        Q(**{f'{section}_published__isnull': True}),
                        then=Value(NULL_TIME)
                    ),
                    default=F(f'{section}_published'),
                ),
                f'{section}_modified': Case(
                    When(
                        Q(**{f'{section}_modified__isnull': True}),
                        then=Value(NULL_TIME)
                    ),
                    default=F(f'{section}_modified'),
                )
            })

        qry = qry.annotate(
            _last_published=Greatest(*[
                f'{section}_published'
                for section in self.model.section_fields() +
                               self.model.subsection_fields()
            ]),
            _last_modified=Greatest(*[
                f'{section}_modified'
                for section in self.model.section_fields() +
                               self.model.subsection_fields()
            ])
        )

        return qry.annotate(
            has_updates=Case(
                When(
                    Q(_last_published=F('_last_modified')), then=Value(False)
                ),
                default=Value(True)
            )
        )


class Site(models.Model):
    """
     XXXX Site Information Form (site log)
     International GNSS Service
     See Instructions at:
       https://files.igs.org/pub/station/general/sitelog_instr.txt
    """

    objects = SiteManager.from_queryset(SiteQuerySet)()

    name = models.CharField(
        max_length=9,
        unique=True,
        help_text=_(
            'This is the 9 Character station name (XXXXMRCCC) used in RINEX 3 '
            'filenames Format: (XXXX - existing four character IGS station '
            'name, M - Monument or marker number (0-9), R - Receiver number '
            '(0-9), CCC - Three digit ISO 3166-1 country code)'
        ),
        db_index=True,
        validators=[RegexValidator(r'[\w]{4}[\d]{2}[\w]{3}')]
    )

    # todo can site exist without agency?
    agencies = models.ManyToManyField('slm.Agency', related_name='sites')

    # dormant is now deduplicated into status field
    status = EnumField(
        SiteLogStatus,
        default=SiteLogStatus.PENDING,
        blank=True,
        help_text=_('The current status of the site.')
    )

    owner = models.ForeignKey(
        'slm.User',
        null=True,
        default=None,
        blank=True,
        on_delete=models.SET_NULL
    )

    num_flags = models.PositiveSmallIntegerField(
        default=0,
        blank=True,
        help_text=_(
            'The number of flags the most recent site log version has.'
        ),
        db_index=True
    )

    # todo deprecated
    preferred = models.IntegerField(default=0, blank=True)
    modified_user = models.IntegerField(default=0, blank=True)
    #######

    created = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        help_text=_('The time this site was first registered.'),
        db_index=True
    )

    last_user = models.ForeignKey(
        'slm.User',
        null=True,
        default=None,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recent_sites',
        help_text=_('The last user to make edits to the site log.')
    )

    last_publish = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=_('The publish date of the current log file.'),
        db_index=True
    )

    last_update = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=_('The time of the most recent update to the site log.'),
        db_index=True
    )

    last_recalc = models.DateTimeField(null=True, blank=True, default=None)

    def is_moderator(self, user):
        if user.is_superuser:
            return True
        return self.moderators.filter(pk=user.pk).exists()

    def get_filename(self, log_format, epoch=None):
        if epoch is None:
            epoch = self.last_publish
        return f'{self.name.upper()}_{epoch.year}{epoch.month:02}' \
               f'{epoch.day:02}.{log_format.ext}'

    @cached_property
    def moderators(self):
        """
        Get the users who have moderate permission for this site. Moderators
        are also editors, but are not listed in editors

        :return: A queryset containing users with moderate permission for the
            site
        """
        return get_user_model().objects.filter(is_superuser=True)

    @cached_property
    def editors(self):
        """
        Get the users who have edit permission, but not moderate permission on
        for this site.

        :return: A queryset containing users with edit permissions for the site
        """
        return get_user_model().objects.filter(
            ~Q(pk__in=self.moderators) & (
                Q(agency__in=self.agencies.all()) | Q(pk=self.owner.pk)
            )
        )

    @property
    def review_pending(self):
        """
        Checks if a review is pending.

        :return: True if a review is pending for this site.
        """
        if hasattr(self, '_review_pending'):
            return self._review_pending

        if hasattr(self, 'review_request') and self.review_request:
            return (
                self.last_publish is None or
                self.review_request.timestamp >= self.last_publish
            )
        return False

    @classmethod
    def sections(cls):
        if hasattr(cls, 'sections_'):
            return cls.sections_

        cls.sections_ = {
            section.related_model.section_number(): section.name
            if SiteSubSection not in section.related_model.__mro__
            else {}
            for section in Site._meta.get_fields()
            if section.related_model and
               SiteSection in section.related_model.__mro__
        }

        for subsection in Site._meta.get_fields():
            if (
                subsection.related_model and
                SiteSubSection in subsection.related_model.__mro__
            ):
                cls.sections_[subsection.related_model.section_number()][
                    subsection.related_model.subsection_number()
                ] = subsection.name
        return cls.sections_

    @classmethod
    def section_fields(cls):
        if hasattr(cls, 'section_fields_'):
            return cls.section_fields_

        cls.section_fields_ = [
            section.name for section in Site._meta.get_fields()
            if section.related_model and (
                    SiteSection in section.related_model.__mro__ and
                    SiteSubSection not in section.related_model.__mro__
            )
        ]
        return cls.section_fields_

    @classmethod
    def subsection_fields(cls):
        if hasattr(cls, 'subsection_fields_'):
            return cls.subsection_fields_

        cls.subsection_fields_ = [
            section.name for section in Site._meta.get_fields()
            if section.related_model and
               SiteSubSection in section.related_model.__mro__
        ]
        return cls.subsection_fields_

    @classmethod
    def section_accessors(cls):
        if hasattr(cls, 'section_accessors_'):
            return cls.section_accessors_

        cls.section_accessors_ = [
            section.get_accessor_name() for section in Site._meta.get_fields()
            if section.related_model and (
                    SiteSection in section.related_model.__mro__ and
                    SiteSubSection not in section.related_model.__mro__
            )
        ]
        return cls.section_accessors_

    @classmethod
    def subsection_accessors(cls):
        if hasattr(cls, 'subsection_accessors_'):
            return cls.subsection_accessors_

        cls.subsection_accessors_ = [
            section.get_accessor_name() for section in Site._meta.get_fields()
            if section.related_model and
               SiteSubSection in section.related_model.__mro__
        ]
        return cls.subsection_accessors_

    def can_publish(self, user):
        """
        This is a future hook to use for instances where non-moderators are
        allowed to publish a site log under certain conditions.

        :param user:
        :return:
        """
        if user:
            return self.is_moderator(user)
        return False

    def can_edit(self, user):
        if user and user.is_authenticated:
            if self.is_moderator(user) or self.owner == user:
                return True
            if hasattr(user, 'agency'):
                return user.agency in self.agencies.all()
        return False

    def update_status(self, save=True, head=True, user=None, timestamp=None):
        """
        Update the denormalized data that is too expensive to query on the
        fly. This includes flag count, moderation status and DateTimes.

        :param save:
        :param head: False if status update should be done on the most recent
            published version of the site log.
        :param user: The user responsible for a status update check
        :param timestamp: The time at which the status update is triggered
        :return:
        """
        if head:
            self.head()
        else:
            self.current()

        if not timestamp:
            timestamp = now()

        self.last_update = timestamp

        if user:
            self.last_user = user

        self.num_flags = 0
        status = SiteLogStatus.PUBLISHED
        for section in self.section_fields():
            section_inst = getattr(self, section, None)
            if section_inst:
                self.num_flags += len(getattr(section_inst, '_flags') or {})
                status = status.merge(
                    getattr(
                        section_inst,
                        'mod_status',
                        SiteLogStatus.PUBLISHED
                    )
                )
        for subsections in self.subsection_fields():
            for subsection in getattr(self, subsections):
                if subsection.published and subsection.is_deleted:
                    continue
                self.num_flags += len(subsection._flags or {})
                status = status.merge(subsection.mod_status)

        # if in either of these two states - status update must come from
        # a global publish of the site log, not from this which can be
        # triggered by a section publish
        if self.status not in {SiteLogStatus.DORMANT, SiteLogStatus.PENDING}:
            if status == SiteLogStatus.PUBLISHED:
                self.last_publish = timestamp
            self.status = status
            if (
                self.status == SiteLogStatus.PUBLISHED
                and hasattr(self, 'review_request')
            ):
                self.review_request.delete()
        if save:
            self.save()

    def published(self, epoch=None):
        return self.current(epoch=epoch, published=True)

    def head(self, epoch=None):
        return self.current(epoch=epoch, published=None)

    def current(self, epoch=None, published=None):
        for section in self.section_fields():
            setattr(
                self,
                section,
                getattr(self, f'{section}_set').current(
                    epoch=epoch,
                    published=published
                )
            )
        for subsection in self.subsection_fields():
            setattr(
                self,
                subsection,
                getattr(self, f'{subsection}_set').current(
                    epoch=epoch,
                    published=published
                )
            )

    @property
    def fourid(self):
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

        sections_published = 0
        for section_name in self.section_fields():
            current = getattr(self, f'{section_name}_set').current()
            if current:
                sections_published += int(
                    current.publish(
                        request=request,
                        silent=True,
                        timestamp=timestamp,
                        update_site=False
                    )
                )

        for subsection_name in self.subsection_fields():
            for subsection in getattr(
                self, f'{subsection_name}_set'
            ).current():
                sections_published += int(
                    subsection.publish(
                        request=request,
                        silent=True,
                        timestamp=timestamp,
                        update_site=False
                    )
                )

        # this might be an initial PUBLISH when we're in PENDING or DORMANT
        if sections_published or self.status != SiteLogStatus.PUBLISHED:
            self.status = SiteLogStatus.PUBLISHED
            self.last_publish = timestamp
            self.last_user = request.user if request else None
            self.save()
            if hasattr(self, 'review_request'):
                self.review_request.delete()
            if not silent:
                slm_signals.site_published.send(
                    sender=self,
                    site=self,
                    user=request.user if request else None,
                    timestamp=timestamp,
                    request=request,
                    section=None
                )

        return sections_published

    def __str__(self):
        return self.name


class SiteSectionManager(models.Manager):
    pass


class SiteSectionQueryset(models.QuerySet):

    def editable_by(self, user):
        if user.is_superuser:
            return self
        return self.filter(site__agencies__in=[user.agency])

    def station(self, station):
        if isinstance(station, str):
            return self.filter(site__name=station)
        return self.filter(site=station)

    def published(self, epoch=None):
        return self.current(epoch=epoch, published=True)

    def head(self, epoch=None):
        return self.current(epoch=epoch, published=None)

    def current(self, epoch=None, published=None):
        pub_q = Q()
        if published is not None:
            pub_q = Q(published=published)
        if epoch:
            return self.filter(pub_q).order_by('-edited').filter(
                edited__lte=epoch
            ).first()
        return self.filter(pub_q).order_by('-edited').first()


class SiteSection(models.Model):

    VALIDATORS = []

    site = models.ForeignKey('slm.Site', on_delete=models.CASCADE)
    edited = models.DateTimeField(auto_now_add=True, db_index=True, null=False)
    published = models.BooleanField(default=False, db_index=True)

    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True
    )

    _flags = compat.JSONField(
        null=False,
        blank=True,
        default=dict,
        encoder=DefaultToStrEncoder
    )

    objects = SiteSectionManager.from_queryset(SiteSectionQueryset)()

    def publish(
        self,
        request=None,
        silent=False,
        timestamp=None,
        update_site=True
    ):
        """
        Publish the current HEAD edits on this SiteLog.

        :param request: The request that triggered the publish (optional)
        :param silent: If True, no publish signal will be sent.
        :param timestamp: Timestamp to use for the publish, if none - will
            be the time of this call
        :param update_site: If True, site will be updated with publish
            information (i.e. pass False if this section is being published as
            part of a larger site publish)
        :return: True if a change was published, False otherwise.
        """
        if self.published:
            return False

        if timestamp is None:
            timestamp = now()

        self.published = True
        self.save()

        if update_site:
            self.site.update_status(save=True, timestamp=timestamp)

        if not silent:
            slm_signals.site_published.send(
                sender=self,
                site=self.site,
                user=request.user if request else None,
                timestamp=timestamp,
                request=request,
                section=self
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
        for field in self._meta.fields:
            for validator in get_validators(self._meta.label, field.name):
                try:
                    validator(self, field, getattr(self, field.name, None))
                except ValidationError as val_err:
                    errors[field.name] = val_err.error_list
        if errors:
            raise ValidationError(errors)

    @property
    def num_flags(self):
        if self._flags:
            return len(self._flags)
        return 0

    @property
    def mod_status(self):
        if self.published:
            return SiteLogStatus.PUBLISHED
        return SiteLogStatus.UPDATED

    def published_diff(self, epoch=None):
        """
        Get a dictionary representing the diff with the current published HEAD
        """
        diff = {}
        if getattr(self, 'is_deleted', None):
            return {}
        if isinstance(self, SiteSubSection):
            published = self.__class__.objects.filter(
                site=self.site
            ).published(subsection=self.subsection, epoch=epoch)
        else:
            published = self.__class__.objects.filter(
                site=self.site
            ).published(epoch=epoch)

        if published and published.id == self.id:
            return diff

        def transform(value, field_name):
            if isinstance(value, models.Model):
                return str(value)
            elif isinstance(
                self._meta.get_field(field),
                models.ManyToManyField
            ):
                if value:
                    return '+'.join([str(val) for val in value.all()])
            return value

        for field in self.site_log_fields():
            if getattr(self, field) != getattr(published, field, None):
                diff[field] = {
                    'pub': transform(getattr(published, field, None), field),
                    'head': transform(getattr(self, field), field)
                }
        return diff

    @classmethod
    def section_number(cls):
        raise NotImplementedError(
            f'SiteSection models must implement section_number()'
        )

    @classmethod
    def section_name(cls):
        return cls._meta.verbose_name.replace('site', '').strip().title()

    @classmethod
    def site_log_fields(cls):
        """
        Return the editable fields for the given sitelog section
        """
        return [
            field.name for field in cls._meta.fields if field.name not in {
                'id',
                'site',
                'edited',
                'published',
                'error',
                'subsection',
                'is_deleted',
                'custom_graphic',
                'editor',
                'deleted',
                '_flags',
                'inserted'
            }
        ]

    @classmethod
    def structure(cls):
        """
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
        #raise NotImplementedError(f'SiteSections must implement structure
        # classmethod!')
        return cls.site_log_fields()

    @classmethod
    def legacy_name(cls, field):
        if callable(getattr(cls, field, None)):
            return getattr(cls, field).verbose_name
        return cls._meta.get_field(field).verbose_name

    class Meta:
        abstract = True
        ordering = ('-edited',)
        index_together = [
            ('edited', 'published'),
            ('site', 'edited'),
            ('site', 'edited', 'published'),
        ]


class SiteSubSectionManager(SiteSectionManager):

    def create(self, *args, **kwargs):
        # some DBs only support one auto field per table, so we have to
        # manually increment the subsection identifier for new subsections
        # using select_for_update to avoid race conditions
        if 'subsection' not in kwargs:
            last = self.model.objects.select_for_update().filter(
                site=kwargs.get('site')
            ).aggregate(Max('subsection'))['subsection__max']
            kwargs['subsection'] = last + 1 if last is not None else 0
        return super().create(*args, **kwargs)

    """
    # TODO why doesnt this work?? - should do same thing as subsection_id 
    # property
    def get_queryset(self):
        return super().get_queryset().annotate(
            subsection_id_=Count(
                'subsection',
                filter=(
                    Q(subsection__lt=F('subsection')) & 
                    Q(published=True) & 
                    Q(site=F('site'))
                ),
                distinct=True
            )
        )
    """


class SiteSubSectionQuerySet(SiteSectionQueryset):

    def published(self, subsection=None, epoch=None):
        return self.current(subsection=subsection, epoch=epoch, published=True)

    def head(self, subsection=None, epoch=None):
        return self.current(subsection=subsection, epoch=epoch, published=None)

    def current(self, subsection=None, epoch=None, published=None):
        section_q = Q()
        if published is not None:
            section_q &= Q(published=published)
        if epoch:
            section_q &= Q(edited__lte=epoch)
        if subsection is None:
            sections_q = Q()
            # todo this query could get slow - convert to subquery, though
            #  mysql might not be able to do this
            for subsection, edited in {
                sub[0]: sub[1] for sub in self.filter(
                    section_q
                ).order_by('subsection', 'edited').values_list(
                    'subsection', 'edited'
                )
            }.items():
                sections_q |= (Q(subsection=subsection) & Q(edited=edited))
            if sections_q:
                return self.filter(sections_q).order_by('subsection')
            return self.none()
        else:
            section_q &= Q(subsection=subsection)

        return self.filter(section_q).order_by('-edited').first()


class SiteSubSection(SiteSection):

    subsection = models.PositiveSmallIntegerField()

    is_deleted = models.BooleanField(default=False, null=False, blank=True)

    inserted = models.DateTimeField(default=now)

    objects = SiteSubSectionManager.from_queryset(SiteSubSectionQuerySet)()

    @property
    def heading(self):
        """
        A brief name for this instance useful for UI display.
        """
        raise NotImplementedError(
            f'Site subsection models should implement heading().'
        )

    @cached_property
    def subsection_prefix(self):
        idx = f'{self.section_number()}'
        if self.subsection_number():
            idx += f'.{self.subsection_number()}'
        return idx

    @classmethod
    def subsection_number(cls):
        raise NotImplementedError(
            f'SiteSubSection models must implement subsection_number()'
        )

    @classmethod
    def subsection_name(cls):
        return cls._meta.verbose_name.replace('site', '').strip().title()

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
        ordering = ('-edited',)
        index_together = [
            ('site', 'edited'),
            ('site', 'edited', 'published'),
            ('site', 'edited', 'subsection'),
            ('site', 'edited', 'published', 'subsection')
        ]


class SiteForm(SiteSection):
    """
    TODO - this can be reconstituted on the fly
        (i.e. this is denormalized data - with the exception of prepared by?) - get rid of it?

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
            'prepared_by',
            'date_prepared',
            'report_type',
            (_('If Update'), ('previous_log', 'modified_section')),
        ]

    @classmethod
    def section_number(cls):
        return 0

    @classmethod
    def section_header(cls):
        return 'Form'

    prepared_by = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('Prepared by (full name)'),
        help_text=_('Enter the name of who prepared this site log')
    )
    date_prepared = models.DateField(
        null=True,
        blank=False,
        verbose_name=_('Date Prepared'),
        help_text=_('Enter the date the site log was prepared (CCYY-MM-DD).')
    )

    report_type = models.CharField(
        max_length=50,
        blank=True,
        default=None,
        verbose_name=_('Report Type'),
        help_text=_('Enter type of report. Example: (UPDATE).')
    )
    previous_log = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_('Previous Site Log'),
        help_text=_(
            'Enter previous site log in this format: ssss_CCYYMMDD.log '
            'Format: (ssss = 4 character site name). If the site already has '
            'a log at the IGS Central Bureau, enter the filename currently '
            'found under https://files.igs.org/pub/station/log/'
        )
    )
    modified_section = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Modified/Added Sections'),
        help_text=_(
            'Enter the sections which have changed from the previous version '
            'of the log. Example: (3.2, 4.2)'
        )
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
            'site_name',
            'four_character_id',
            'monument_inscription',
            'iers_domes_number',
            'cdp_number',
            ('monument_description', (
                'monument_height',
                'monument_foundation',
                'foundation_depth'
            )),
            'marker_description',
            'date_installed',
            ('geologic_characteristic', (
                'bedrock_type',
                'bedrock_condition',
                'fracture_spacing',
                ('fault_zones', (
                    'distance',
                ))
            )),
            'additional_information'
        ]

    @classmethod
    def section_number(cls):
        return 1

    @classmethod
    def section_header(cls):
        return 'Site Identification of the GNSS Monument'

    site_name = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_('Site Name'),
        help_text=_('Enter the name of the site.')
    )

    @cached_property
    def four_character_id(self):
        return self.site.name[0:4].upper()

    monument_inscription = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Monument Inscription'),
        help_text=_('Enter what is stamped on the monument')
    )

    iers_domes_number = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('IERS DOMES Number'),
        help_text=_(
            'This is strictly required. '
            'See http://itrf.ensg.ign.fr/domes_request.php to obtain one. '
            'Format: 9 character alphanumeric (A9)'
        )
    )

    cdp_number = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('CDP Number'),
        help_text=_(
            'Enter the NASA CDP identifier if available. '
            'Format: 4 character alphanumeric (A4)'
        )
    )

    date_installed = models.DateTimeField(
        null=True,
        blank=False,
        verbose_name=_('Date Installed'),
        help_text=_(
            'Enter the original date that this site was included in the IGS. '
            'Format: (CCYY-MM-DDThh:mmZ)'
        )
    )

    # Monument fields
    monument_description = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Monument Description'),
        help_text=_(
            'Provide a general description of the GNSS monument. '
            'Format: (PILLAR/BRASS PLATE/STEEL MAST/etc)'
        )
    )

    monument_height = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_('Height of the Monument (m)'),
        help_text=_(
            'Enter the height of the monument above the ground surface in '
            'meters. Units: (m)'
        )
    )
    monument_foundation = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Monument Foundation'),
        help_text=_(
            'Describe how the GNSS monument is attached to the ground. '
            'Format: (STEEL RODS, CONCRETE BLOCK, ROOF, etc)'
        )
    )
    foundation_depth = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_('Foundation Depth (m)'),
        help_text=_(
            'Enter the depth of the monument foundation below the ground '
            'surface in meters. Format: (m)'
        )
    )

    marker_description = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Marker Description'),
        help_text=_(
            'Describe the actual physical marker reference point. '
            'Format: (CHISELLED CROSS/DIVOT/BRASS NAIL/etc)'
        )
    )

    geologic_characteristic = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Geologic Characteristic'),
        help_text=_(
            'Describe the general geologic characteristics of the GNSS site. '
            'Format: (BEDROCK/CLAY/CONGLOMERATE/GRAVEL/SAND/etc)'
        )
    )

    bedrock_type = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Bedrock Type'),
        help_text=_(
            'If the site is located on bedrock, describe the nature of that '
            'bedrock. Format: (IGNEOUS/METAMORPHIC/SEDIMENTARY)'
        )
    )

    bedrock_condition = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Bedrock Condition'),
        help_text=_(
            'If the site is located on bedrock, describe the condition of '
            'that bedrock. Format: (FRESH/JOINTED/WEATHERED)'
        )
    )

    fracture_spacing = EnumField(
        FractureSpacing,
        strict=False,
        max_length=50,
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Fracture Spacing'),
        help_text=_(
            'If known, describe the fracture spacing of the bedrock. '
            'Format: (1-10 cm/11-50 cm/51-200 cm/over 200 cm)'
        )
    )

    fault_zones = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Fault Zones Nearby'),
        help_text=_(
            'Enter the name of any known faults near the site. '
            'Format: (YES/NO/Name of the zone)'
        )
    )

    distance = models.TextField(
        default='',
        blank=True,
        verbose_name=_('Distance/activity'),
        help_text=_(
            'Describe proximity of the site to any known faults. '
            'Format: (multiple lines)'
        )
    )

    additional_information = models.TextField(
        default='',
        blank=True,
        verbose_name=_('Additional Information'),
        help_text=_(
            'Enter any additional information about the geologic '
            'characteristics of the GNSS site. Format: (multiple lines)'
        )
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
    @classmethod
    def structure(cls):
        return [
            'city',
            'state',
            'country',
            'tectonic',
            (_('Approximate Position (ITRF)'), (
                'x',
                'y',
                'z',
                'latitude',
                'longitude',
                'elevation'
            )),
            'additional_information'
        ]

    @classmethod
    def section_number(cls):
        return 2

    @classmethod
    def section_header(cls):
        return 'Site Location Information'

    city = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('City or Town'),
        help_text=_('Enter the city or town the site is located in')
    )
    state = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('State or Province'),
        help_text=_('Enter the state or province the site is located in')
    )

    country = EnumField(
        ISOCountry,
        strict=False,
        max_length=100,
        blank=False,
        null=True,
        verbose_name=_('Country or Region'),
        help_text=_('Enter the country/region the site is located in')
    )

    tectonic = EnumField(
        TectonicPlates,
        strict=False,
        max_length=50,
        null=True,
        default=None,
        blank=True,
        verbose_name=_('Tectonic Plate'),
        help_text=_(
            'Select the primary tectonic plate that the GNSS site occupies'
        )
    )

    x = models.FloatField(
        null=True,
        blank=False,
        verbose_name=_('X Coordinate (m)'),
        help_text=_(
            'Enter the ITRF position to a one meter precision. Format (m)'
        )
    )

    y = models.FloatField(
        null=True,
        blank=False,
        verbose_name=_('Y Coordinate (m)'),
        help_text=_(
            'Enter the ITRF position to a one meter precision. Format (m)'
        )
    )

    z = models.FloatField(
        null=True,
        blank=False,
        verbose_name=_('Z Coordinate (m)'),
        help_text=_(
            'Enter the ITRF position to a one meter precision. Format (m)'
        )
    )

    # todo convert these to geodjango native PointField
    latitude = models.FloatField(
        null=True,
        blank=False,
        verbose_name=_('Latitude (N is +)'),
        help_text=_(
            'Enter the ITRF position to a one meter precision. '
            'Format: (+/-DDMMSS.SS)'
        ),
        db_index=True,
        validators=[MaxValueValidator(900000), MinValueValidator(-900000)]
    )

    longitude = models.FloatField(
        null=True,
        blank=False,
        verbose_name=_('Longitude (E is +)'),
        help_text=_(
            'Enter the ITRF position to a one meter precision. '
            'Format: (+/-DDDMMSS.SS)'
        ),
        db_index=True,
        validators=[MaxValueValidator(1800000), MinValueValidator(-1800000)]
    )

    elevation = models.FloatField(
        null=True,
        verbose_name=_('Elevation (m,ellips.)'),
        help_text=_(
            'Enter the ITRF position to a one meter precision. Format: The '
            'elevation may be given to more decimal places than F7.1. 7.1 is '
            'a minimum for the SINEX format'
        ),
        db_index=True,
        validators=[MaxValueValidator(9000), MinValueValidator(-500)]
    )

    additional_information = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Additional Information'),
        help_text=_(
            'Describe the source of these coordinates or any other relevant '
            'information. Format: (multiple lines)'
        )
    )


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
            'receiver_type',
            'satellite_system',
            'serial_number',
            'firmware',
            'elevation_cutoff',
            'installed',
            'removed',
            'temp',
            'temp_stab',
            'additional_info'
        ]

    @classmethod
    def section_number(cls):
        return 3

    @classmethod
    def section_header(cls):
        return 'GNSS Receiver Information'

    @classmethod
    def subsection_number(cls):
        return None

    @property
    def heading(self):
        return self.receiver_type.model

    @property
    def effective(self):
        if self.installed and self.removed:
            return f'{date_to_str(self.installed)}/{date_to_str(self.removed)}'
        elif self.installed:
            return f'{date_to_str(self.installed)}'
        return ''

    receiver_type = models.ForeignKey(
        'slm.Receiver',
        blank=False,
        verbose_name=_('Receiver Type'),
        help_text=_(
            'Please find your receiver in '
            'https://files.igs.org/pub/station/general/rcvr_ant.tab and use '
            'the official name, taking care to get capital letters, hyphens, '
            'etc. exactly correct. If you do not find a listing for your '
            'receiver, please notify the IGS Central Bureau. '
            'Format: (A20, from rcvr_ant.tab; see instructions)'
        ),
        on_delete=models.PROTECT
    )

    satellite_system = models.ManyToManyField(
        'slm.SatelliteSystem',
        verbose_name=_('Satellite System'),
        blank=False,
        help_text=_('Check all GNSS systems that apply')
    )

    serial_number = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('Serial Number'),
        help_text=_(
            'Enter the receiver serial number. '
            'Format: (A20, but note the first A5 is used in SINEX)'
        )
    )

    firmware = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('Firmware Version'),
        help_text=_('Enter the receiver firmware version. Format: (A11)')
    )

    elevation_cutoff = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Elevation Cutoff Setting (°)'),
        help_text=_(
            'Please respond with the tracking cutoff as set in the receiver, '
            'regardless of terrain or obstructions in the area. Format: (deg)'
        ),
        validators=[
            MinValueValidator(-5),
            MaxValueValidator(15)
        ]
    )

    installed = models.DateTimeField(
        null=True,
        blank=False,
        verbose_name=_('Date Installed'),
        help_text=_(
            'Enter the date and time the receiver was installed. '
            'Format: (CCYY-MM-DDThh:mmZ)'
        )
    )

    removed = models.DateTimeField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_('Date Removed'),
        help_text=_(
            'Enter the date and time the receiver was removed. It is important'
            ' that the date removed is entered BEFORE the addition of a new '
            'receiver. Format: (CCYY-MM-DDThh:mmZ)'
        )
    )

    temp = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Temperature'),
        help_text=_(
            'If the receiver is in a temperature controlled environment, '
            'please enter the approximate temperature of that environment. '
            'Format: (°C)'
        )
    )
    # this field is a string in GeodesyML - therefore leaving it as character
    temp_stab = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Temperature Stabiliz.'),
        help_text=_(
            'If the receiver is in a temperature controlled environment, '
            'please enter the approximate temperature range of that '
            'environment. Format: (± °C)'
        )
    )

    additional_info = models.TextField(
        default='',
        blank=True,
        verbose_name=_('Additional Information'),
        help_text=_(
            'Enter any additional relevant information about the receiver. '
            'Format: (multiple lines)'
        )
    )


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

    @property
    def heading(self):
        return self.antenna_type.model

    @property
    def effective(self):
        if self.installed and self.removed:
            return f'{date_to_str(self.installed)}/{date_to_str(self.removed)}'
        elif self.installed:
            return f'{date_to_str(self.installed)}'
        return ''

    @classmethod
    def section_number(cls):
        return 4

    @classmethod
    def section_header(cls):
        return 'GNSS Antenna Information'

    @classmethod
    def subsection_number(cls):
        return None

    antenna_type = models.ForeignKey(
        'slm.Antenna',
        on_delete=models.PROTECT,
        blank=False,
        verbose_name=_('Antenna Type'),
        help_text=_(
            'Please find your antenna radome type in '
            'https://files.igs.org/pub/station/general/rcvr_ant.tab and use '
            'the official name, taking care to get capital letters, hyphens, '
            'etc. exactly correct. The radome code from rcvr_ant.tab must be '
            'indicated in columns 17-20 of the Antenna Type, use "NONE" if no '
            'radome is installed. The antenna+radome pair must have an entry '
            'in https://files.igs.org/pub/station/general/igs05.atx with '
            'zenith- and azimuth-dependent calibration values down to the '
            'horizon. If not, notify the CB. Format: (A20, from rcvr_ant.tab; '
            'see instructions)'
        ),
        related_name='antennas'
    )

    serial_number = models.CharField(
        max_length=128,
        blank=False,
        verbose_name=_('Serial Number'),
        help_text=_('Only Alpha Numeric Chars and - . Symbols allowed')
    )

    # todo remove this b/c it belongs solely on antenna type?
    reference_point = EnumField(
        AntennaReferencePoint,
        blank=False,
        verbose_name=_('Antenna Reference Point'),
        null=True,
        help_text=_(
            'Locate your antenna in the file '
            'https://files.igs.org/pub/station/general/antenna.gra. Indicate '
            'the three-letter abbreviation for the point which is indicated '
            'equivalent to ARP for your antenna. Contact the Central Bureau if'
            ' your antenna does not appear. Format: (BPA/BCR/XXX from '
            'antenna.gra; see instr.)'
        )
    )

    marker_up = models.FloatField(
        blank=False,
        verbose_name=_('Marker->ARP Up Ecc (m)'),
        help_text=_(
            'Up eccentricity is the antenna height measured to an accuracy of '
            '1mm and defined as the vertical distance of the ARP from the '
            'marker described in section 1. Format: (F8.4) Value 0 is OK'
        )
    )
    marker_north = models.FloatField(
        blank=False,
        verbose_name=_('Marker->ARP North Ecc (m)'),
        help_text=_(
            'North eccentricity is the offset between the ARP and marker '
            'described in section 1 measured to an accuracy of 1mm. '
            'Format: (F8.4)'
        )
    )
    marker_east = models.FloatField(
        blank=False,
        verbose_name=_('Marker->ARP East Ecc (m)'),
        help_text=_(
            'East eccentricity is the offset between the ARP and marker '
            'described in section 1 measured to an accuracy of 1mm. '
            'Format: (F8.4)'
        )
    )

    alignment = models.FloatField(
        blank=False,
        null=True,
        verbose_name=_('Alignment from True N (°)'),
        help_text=_(
            'Enter the clockwise offset from true north in degrees. The '
            'positive direction is clockwise, so that due east would be '
            'equivalent to a response of "+90". '
            'Format: (deg; + is clockwise/east)'
        ),
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )

    radome_type = models.ForeignKey(
        'slm.Radome',
        blank=False,
        verbose_name=_('Antenna Radome Type'),
        help_text=_(
            'Please find your antenna radome type in '
            'https://files.igs.org/pub/station/general/rcvr_ant.tab and use '
            'the official name, taking care to get capital letters, hyphens, '
            'etc. exactly correct. The radome code from rcvr_ant.tab must be '
            'indicated in columns 17-20 of the Antenna Type, use "NONE" if no '
            'radome is installed. The antenna+radome pair must have an entry '
            'in https://files.igs.org/pub/station/general/igs05.atx with '
            'zenith- and azimuth-dependent calibration values down to the '
            'horizon. If not, notify the CB. Format: (A20, from rcvr_ant.tab; '
            'see instructions)'
        ),
        on_delete=models.PROTECT
    )

    radome_serial_number = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_('Radome Serial Number'),
        help_text=_('Enter the serial number of the radome if available')
    )

    cable_type = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Antenna Cable Type'),
        help_text=_(
            'Enter the antenna cable specification if know. '
            'Format: (vendor & type number)'
        )
    )

    cable_length = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_('Antenna Cable Length'),
        help_text=_('Enter the antenna cable length in meters. Format: (m)')
    )

    installed = models.DateTimeField(
        blank=False,
        verbose_name=_('Date Installed'),
        help_text=_(
            'Enter the date the receiver was installed. '
            'Format: (CCYY-MM-DDThh:mmZ)'
        )
    )

    removed = models.DateTimeField(
        default=None,
        blank=True,
        null=True,
        verbose_name=_('Date Removed'),
        help_text=_(
            'Enter the date the receiver was removed. It is important that '
            'the date removed is entered before the addition of a new '
            'receiver. Format: (CCYY-MM-DDThh:mmZ)'
        )
    )

    additional_information = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Additional Information'),
        help_text=_(
            'Enter additional relevant information about the antenna, cable '
            'and radome. Indicate if a signal splitter has been used. '
            'Format: (multiple lines)'
        )
    )

    @property
    def graphic(self):
        if self.custom_graphic:
            return self.custom_graphic
        return self.antenna_type.graphic

    custom_graphic = models.TextField(
        default='',
        blank=True,
        help_text=_('Custom antenna graphic - if different than the default.')
    )


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

    @classmethod
    def structure(cls):
        return [
            'name',
            'usage',
            'cdp_number',
            'domes_number',
            (_(
                'Differential Components from GNSS Marker to the tied '
                'monument (ITRS)'
            ), (
                'dx',
                'dy',
                'dz'
            )),
            'accuracy',
            'survey_method',
            'measured',
            'additional_information'
        ]

    @property
    def heading(self):
        return self.name

    @property
    def effective(self):
        if self.measured:
            return f'{date_to_str(self.measured)}'
        return ''

    @classmethod
    def section_number(cls):
        return 5

    @classmethod
    def section_header(cls):
        return 'Surveyed Local Ties'

    @classmethod
    def subsection_number(cls):
        return None

    name = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Tied Marker Name'),
        help_text=_('Enter name of Tied Marker')
    )
    usage = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Tied Marker Usage'),
        help_text=_(
            'Enter the purpose of the tied marker such as SLR, VLBI, DORIS, '
            'or other. Format: (SLR/VLBI/LOCAL CONTROL/FOOTPRINT/etc)'
        )
    )
    cdp_number = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Tied Marker CDP Number'),
        help_text=_(
            'Enter the NASA CDP identifier if available. Format: (A4)'
        )
    )
    domes_number = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Tied Marker DOMES Number'),
        help_text=_(
            'Enter the tied marker DOMES number if available. Format: (A9)'
        )
    )

    dx = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_('dx (m)'),
        help_text=_(
            'Enter the differential ITRF coordinates to one millimeter '
            'precision. Format: (m)'
        )
    )
    dy = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_('dy (m)'),
        help_text=_(
            'Enter the differential ITRF coordinates to one millimeter '
            'precision. Format: (m)'
        )
    )
    dz = models.FloatField(
        null=True,
        default=None,
        blank=True,
        verbose_name=_('dz (m)'),
        help_text=_(
            'Enter the differential ITRF coordinates to one millimeter '
            'precision. Format: (m)'
        )
    )

    accuracy = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Accuracy (mm)'),
        help_text=_('Enter the accuracy of the tied survey. Format: (mm).')
    )

    survey_method = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Survey method'),
        help_text=_(
            'Enter the source or the survey method used to determine the '
            'differential coordinates, such as GNSS survey, conventional '
            'survey, or other. '
            'Format: (GPS CAMPAIGN/TRILATERATION/TRIANGULATION/etc)'
        )
    )

    measured = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_('Date Measured'),
        help_text=_(
            'Enter the date of the survey local ties measurement. '
            'Format: (CCYY-MM-DDThh:mmZ)'
        )
    )

    additional_information = models.TextField(
        default='',
        blank=True,
        verbose_name=_('Additional Information'),
        help_text=_(
            'Enter any additional information relevant to surveyed local ties.'
            ' Format: (multiple lines)'
        )
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
        return [
            ('standard_type', (
                'input_frequency',
                'effective_dates',
                'notes'
            ))
        ]

    @property
    def heading(self):
        return self.standard_type

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return f'{date_to_str(self.effective_start)}/' \
                   f'{date_to_str(self.effective_end)}'
        elif self.effective_start:
            return f'{date_to_str(self.effective_start)}'
        return ''

    @classmethod
    def section_number(cls):
        return 6

    @classmethod
    def section_header(cls):
        return 'Frequency Standard'

    @classmethod
    def subsection_number(cls):
        return None

    standard_type = EnumField(
        FrequencyStandardType,
        max_length=50,
        strict=False,
        blank=False,
        null=True,
        verbose_name=_('Standard Type'),
        help_text=_(
            'Select whether the frequency standard is INTERNAL or EXTERNAL '
            'and describe the oscillator type. '
            'Format: (INTERNAL or EXTERNAL H-MASER/CESIUM/etc)'
        )
    )

    input_frequency = models.FloatField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_('Input Frequency (MHz)'),
        help_text=_('Enter the input frequency in MHz if known.')
    )

    notes = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Notes'),
        help_text=_(
            'Enter any additional information relevant to frequency standard. '
            'Format: (multiple lines)'
        )
    )

    effective_start = models.DateField(
        blank=False,
        null=True,
        help_text=_(
            'Enter the effective start date for the frequency standard. '
            'Format: (CCYY-MM-DD)'
        )
    )

    effective_end = models.DateField(
        blank=True,
        null=True,
        default=None,
        help_text=_(
            'Enter the effective end date for the frequency standard. '
            'Format: (CCYY-MM-DD)'
        )
    )

    def effective_dates(self):
        return self.effective
    effective_dates.field = (effective_start, effective_end)
    effective_dates.verbose_name = _('Effective Dates')


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
        return [
            ('instrument_type', (
                'status',
                'effective_dates',
                'notes'
            ))
        ]

    @property
    def heading(self):
        return self.instrument_type

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return f'{date_to_str(self.effective_start)}/' \
                   f'{date_to_str(self.effective_end)}'
        elif self.effective_start:
            return f'{date_to_str(self.effective_start)}'
        return ''

    @classmethod
    def section_number(cls):
        return 7

    @classmethod
    def subsection_number(cls):
        return None

    @classmethod
    def section_header(cls):
        return 'Collocation Information'

    instrument_type = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('Instrumentation Type'),
        help_text=_('Select all collocated instrument types that apply')
    )

    status = EnumField(
        CollocationStatus,
        max_length=50,
        strict=False,
        blank=False,
        null=True,
        default=None,
        verbose_name=_('Status'),
        help_text=_('Select appropriate status')
    )

    notes = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Notes'),
        help_text=_(
            'Enter any additional information relevant to collocation. '
            'Format: (multiple lines)'
        )
    )

    # effdate and effstart merged into this field
    effective_start = models.DateField(
        max_length=50,
        blank=False,
        null=True,
        help_text=_(
            'Enter the effective start date of the collocated instrument. '
            'Format: (CCYY-MM-DD)'
        )
    )
    effective_end = models.DateField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_(
            'Enter the effective end date of the collocated instrument. '
            'Format: (CCYY-MM-DD)'
        )
    )

    def effective_dates(self):
        return self.effective
    effective_dates.field = (effective_start, effective_end)
    effective_dates.verbose_name = _('Effective Dates')


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
            'manufacturer',
            'serial_number',
            'height_diff',
            'calibration_date',
            'effective_dates',
            'notes'
        ]

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return f'{date_to_str(self.effective_start)}/' \
                   f'{date_to_str(self.effective_end)}'
        elif self.effective_start:
            return f'{date_to_str(self.effective_start)}'
        return ''

    @classmethod
    def section_number(cls):
        return 8

    @classmethod
    def section_header(cls):
        return 'Meteorological Instrumentation'

    @classmethod
    def section_name(cls):
        return cls.section_header()

    manufacturer = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_('Manufacturer'),
        help_text=_("Enter manufacturer's name")
    )
    serial_number = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_('Serial Number'),
        help_text=_('Enter the serial number of the sensor')
    )

    height_diff = models.FloatField(
        null=True,
        blank=False,
        verbose_name=_('Height Diff to Ant (m)'),
        help_text=_(
            'In meters, enter the difference in height between the sensor and '
            'the GNSS antenna. Positive number indicates the sensor is above '
            'the GNSS antenna. Decimeter accuracy preferred. Format: (m)'
        )
    )

    calibration = models.DateField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_('Calibration Date'),
        help_text=_(
            'Enter the date the sensor was calibrated. Format: (CCYY-MM-DD)'
        )
    )

    def calibration_date(self):
        return date_to_str(self.calibration)
    calibration_date.verbose_name = _('Calibration Date')
    calibration_date.field = calibration

    effective_start = models.DateField(
        blank=False,
        null=True,
        help_text=_(
            'Enter the effective start date for the sensor. '
            'Format: (CCYY-MM-DD)'
        )
    )
    effective_end = models.DateField(
        null=True,
        blank=True,
        default=None,
        help_text=_(
            'Enter the effective end date for the sensor. '
            'Format: (CCYY-MM-DD)'
        )
    )

    notes = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Notes'),
        help_text=_(
            'Enter any additional information relevant to the sensor.'
            ' Format: (multiple lines)'
        )
    )

    def effective_dates(self):
        return self.effective
    effective_dates.field = (effective_start, effective_end)
    effective_dates.verbose_name = _('Effective Dates')

    class Meta:
        abstract = True


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
            'model',
            'manufacturer',
            'serial_number',
            'sampling_interval',
            'accuracy',
            'aspiration',
            'height_diff',
            'calibration_date',
            'effective_dates',
            'notes'
        ]

    @property
    def heading(self):
        return self.model

    @classmethod
    def subsection_number(cls):
        return 1

    model = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_('Humidity Sensor Model'),
        help_text=_('Enter humidity sensor model')
    )

    sampling_interval = models.PositiveSmallIntegerField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Data Sampling Interval (sec)'),
        help_text=_('Enter the sample interval in seconds. Format: (sec)')
    )

    accuracy = models.FloatField(
        default=None,
        blank=True,
        null=True,
        verbose_name=_('Accuracy (% rel h)'),
        help_text=_(
            'Enter the accuracy in % relative humidity. Format: (% rel h)'
        )
    )

    aspiration = EnumField(
        Aspiration,
        null=True,
        default=None,
        blank=True,
        strict=False,
        max_length=50,
        verbose_name=_('Aspiration'),
        help_text=_(
            'Enter the aspiration type if known. '
            'Format: (UNASPIRATED/NATURAL/FAN/etc)'
        )
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
            'model',
            'manufacturer',
            'serial_number',
            'sampling_interval',
            'accuracy',
            'height_diff',
            'calibration_date',
            'effective_dates',
            'notes'
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
        verbose_name=_('Pressure Sensor Model'),
        help_text=_('Enter pressure sensor model')
    )

    sampling_interval = models.PositiveSmallIntegerField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Data Sampling Interval'),
        help_text=_('Enter the sample interval in seconds. Format: (sec)')
    )

    accuracy = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Accuracy (hPa)'),
        help_text=_('Enter the accuracy in hectopascal. Format: (hPa)')
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
            'model',
            'manufacturer',
            'serial_number',
            'sampling_interval',
            'accuracy',
            'aspiration',
            'height_diff',
            'calibration_date',
            'effective_dates',
            'notes'
        ]

    @property
    def heading(self):
        return self.model

    @classmethod
    def subsection_number(cls):
        return 3

    model = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_('Temp. Sensor Model'),
        help_text=_('Enter temperature sensor model')
    )

    sampling_interval = models.PositiveSmallIntegerField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Data Sampling Interval'),
        help_text=_('Enter the sample interval in seconds. Format: (sec)')
    )

    accuracy = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_('Accuracy (deg C)'),
        help_text=_(
            'Enter the accuracy in degrees Centigrade. Format: (deg C)'
        )
    )

    aspiration = EnumField(
        Aspiration,
        null=True,
        default=None,
        blank=True,
        strict=False,
        max_length=50,
        verbose_name=_('Aspiration'),
        help_text=_(
            'Enter the aspiration type if known. '
            'Format: (UNASPIRATED/NATURAL/FAN/etc)'
        )
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
            'model',
            'manufacturer',
            'serial_number',
            'distance_to_antenna',
            'height_diff',
            'calibration_date',
            'effective_dates',
            'notes'
        ]

    @property
    def heading(self):
        return self.model

    @classmethod
    def subsection_number(cls):
        return 4

    model = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_('Water Vapor Radiometer'),
        help_text=_('Enter water vapor radiometer')
    )

    distance_to_antenna = models.FloatField(
        default=None,
        blank=False,
        null=True,
        verbose_name=_('Distance to Antenna (m)'),
        help_text=_(
            'Enter the horizontal distance between the WVR and the GNSS '
            'antenna to the nearest meter. Format: (m)'
        )
    )


class SiteOtherInstrumentation(SiteSubSection):
    """
    8.5.x Other Instrumentation   : (multiple lines)
    """
    @classmethod
    def structure(cls):
        return ['instrumentation']

    @property
    def heading(self):
        return self.instrumentation

    @property
    def effective(self):
        return ''

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
        blank=False,
        verbose_name=_('Other Instrumentation'),
        help_text=_(
            'Enter any other relevant information regarding meteorological '
            'instrumentation near the site. Format: (multiple lines)'
        )
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
            return f'{date_to_str(self.effective_start)}/' \
                   f'{date_to_str(self.effective_end)}'
        elif self.effective_start:
            return f'{date_to_str(self.effective_start)}'
        return ''

    @classmethod
    def section_number(cls):
        return 9

    @classmethod
    def section_header(cls):
        return 'Local Ongoing Conditions Possibly Affecting Computed Position'

    effective_start = models.DateField(
        blank=True,
        null=True,
        default=None,
        help_text=_(
            'Enter the effective start date for the condition. '
            'Format: (CCYY-MM-DD)'
        )
    )

    effective_end = models.DateField(
        blank=True,
        null=True,
        default=None,
        help_text=_(
            'Enter the effective end date for the condition. '
            'Format: (CCYY-MM-DD)'
        )
    )

    additional_information = models.TextField(
        default='',
        blank=True,
        verbose_name=_('Additional Information'),
        help_text=_(
            'Enter additional relevant information about any radio '
            'interferences. Format: (multiple lines)'
        )
    )

    def effective_dates(self):
        return self.effective
    effective_dates.field = (effective_start, effective_end)
    effective_dates.verbose_name = _('Effective Dates')

    class Meta:
        abstract = True


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
            'interferences',
            'degradations',
            'effective_dates',
            'additional_information'
        ]

    @property
    def heading(self):
        return self.interferences

    @classmethod
    def subsection_number(cls):
        return 1

    interferences = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Radio Interferences'),
        help_text=_(
            'Enter all sources of radio interference near the GNSS station. '
            'Format: (TV/CELL PHONE ANTENNA/RADAR/etc)'
        )
    )
    degradations = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Observed Degradations'),
        help_text=_(
            'Describe any observed degradations in the GNSS data that are '
            'presumed to result from radio interference. '
            'Format: (SN RATIO/DATA GAPS/etc)'
        )
    )


class SiteMultiPathSources(Condition):
    """
    9.2.x Multipath Sources       : (METAL ROOF/DOME/VLBI ANTENNA/etc)
           Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
           Additional Information : (multiple lines)
    """

    @classmethod
    def structure(cls):
        return [
            'sources',
            'effective_dates',
            'additional_information'
        ]

    @property
    def heading(self):
        return self.sources

    @classmethod
    def subsection_number(cls):
        return 2

    sources = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Multipath Sources'),
        help_text=_(
            'Describe any potential multipath sources near the GNSS station. '
            'Format: .(METAL ROOF/DOME/VLBI ANTENNA/etc)'
        )
    )


class SiteSignalObstructions(Condition):
    """
    9.3.x Signal Obstructions     : (TREES/BUILDINGS/etc)
       Effective Dates        : (CCYY-MM-DD/CCYY-MM-DD)
       Additional Information : (multiple lines)
    """
    @classmethod
    def structure(cls):
        return [
            'obstructions',
            'effective_dates',
            'additional_information'
        ]

    @property
    def heading(self):
        return self.obstructions

    @classmethod
    def subsection_number(cls):
        return 3

    obstructions = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Signal Obstructions'),
        help_text=_(
            'Describe any potential signal obstructions near the GNSS station.'
            ' Format: (TREES/BUILDLINGS/etc)'
        )
    )


class SiteLocalEpisodicEffects(SiteSubSection):
    """
    10.  Local Episodic Effects Possibly Affecting Data Quality

    10.x Date                     : (CCYY-MM-DD/CCYY-MM-DD)
         Event                    : (TREE CLEARING/CONSTRUCTION/etc)
    """

    @classmethod
    def structure(cls):
        return [
            'date',
            'event'
        ]

    @property
    def heading(self):
        return self.event

    @property
    def effective(self):
        if self.effective_start and self.effective_end:
            return f'{date_to_str(self.effective_start)}/' \
                   f'{date_to_str(self.effective_end)}'
        elif self.effective_start:
            return f'{date_to_str(self.effective_start)}'
        return ''

    @classmethod
    def section_number(cls):
        return 10

    @classmethod
    def subsection_number(cls):
        return None

    @classmethod
    def section_header(cls):
        return 'Local Episodic Effects Possibly Affecting Data Quality'

    event = models.TextField(
        default='',
        blank=True,
        verbose_name=_('Event'),
        help_text=_(
            'Describe any events near the GNSS station that may affect data '
            'quality such as tree clearing, construction, or weather events. '
            'Format: (TREE CLEARING/CONSTRUCTION/etc)'
        )
    )
    effective_start = models.DateField(
        blank=True,
        default=None,
        null=True,
        help_text=_(
            'Enter the effective start date for the local episodic effect. '
            'Format: (CCYY-MM-DD)'
        )
    )

    effective_end = models.DateField(
        blank=True,
        default=None,
        null=True,
        help_text=_(
            'Enter the effective end date for the local episodic effect. '
            'Format: (CCYY-MM-DD)'
        )
    )

    def date(self):
        return self.effective
    date.field = (effective_start, effective_end)
    date.verbose_name = _('Date')


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
            'agency',
            'preferred_abbreviation',
            'mailing_address',
            (_('Primary Contact (Organization Only)'), (
                'primary_name',
                'primary_phone1',
                'primary_phone2',
                'primary_fax',
                'primary_email')
             ),
            (_('Secondary Contact'), (
                'secondary_name',
                'secondary_phone1',
                'secondary_phone2',
                'secondary_fax',
                'secondary_email')
             ),
            'additional_information',
        ]

    agency = models.TextField(
        max_length=300,
        blank=False,
        verbose_name=_('Agency'),
        help_text=_('Enter contact agency name')
    )
    preferred_abbreviation = models.CharField(
        max_length=50,  # todo A10
        blank=False,
        verbose_name=_('Preferred Abbreviation'),
        help_text=_("Enter the contact agency's preferred abbreviation")
    )
    mailing_address = models.TextField(
        max_length=300,
        default='',
        blank=True,
        verbose_name=_('Mailing Address'),
        help_text=_('Enter agency mailing address')
    )

    primary_name = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('Contact Name'),
        help_text=_('Enter primary contact organization name')
    )
    primary_phone1 = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('Telephone (primary)'),
        help_text=_('Enter primary contact primary phone number')
    )
    primary_phone2 = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Telephone (secondary)'),
        help_text=_('Enter primary contact secondary phone number')
    )
    primary_fax = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Fax'),
        help_text=_('Enter primary contact organization fax number')
    )
    primary_email = models.EmailField(
        blank=False,
        verbose_name=_('E-mail'),
        help_text=_(
            'Enter primary contact organization email address. MUST be a '
            'generic email, no personal email addresses.'
        )
    )

    secondary_name = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Contact Name'),
        help_text=_('Enter secondary contact name')
    )
    secondary_phone1 = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Telephone (primary)'),
        help_text=_('Enter secondary contact primary phone number')
    )
    secondary_phone2 = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Telephone (secondary)'),
        help_text=_('Enter secondary contact secondary phone number')
    )
    secondary_fax = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name=_('Fax'),
        help_text=_('Enter secondary contact fax number')
    )
    secondary_email = models.EmailField(
        default='',
        blank=True,
        verbose_name=_('E-mail'),
        help_text=_('Enter secondary contact email address')
    )

    additional_information = models.TextField(
        default='',
        blank=True,
        verbose_name=_('Additional Information'),
        help_text=_(
            'Enter additional relevant information regarding operational '
            'contacts. Format: (multiple lines).'
        )
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
        return 'On-Site, Point of Contact Agency Information'


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
        return 'Responsible Agency'


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
            'primary',
            'secondary',
            'more_info',
            (_('Hardcopy on File'), (
                'sitemap',
                'site_diagram',
                'horizon_mask',
                'monument_description',
                'site_picture')
             ),
            'additional_information',
            #(_('Antenna Graphics with Dimensions'), ('antenna_graphic',))
        ]

    @classmethod
    def section_number(cls):
        return 13

    @classmethod
    def section_header(cls):
        return 'More Information'

    primary = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('Primary Data Center'),
        help_text=_('Enter the name of the primary operational data center')
    )
    secondary = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_('Secondary Data Center'),
        help_text=_('Enter the name of the secondary or backup data center')
    )

    more_info = models.URLField(
        default='',
        null=False,
        blank=True,
        verbose_name=_('URL for More Information')
    )

    sitemap = models.CharField(
        max_length=255,
        default='',
        blank=True,
        verbose_name=_('Site Map'),
        help_text=_('Enter the site map URL')
    )
    site_diagram = models.CharField(
        max_length=255,
        default='',
        blank=True,
        verbose_name=_('Site Diagram'),
        help_text=_('Enter URL for site diagram')
    )
    horizon_mask = models.CharField(
        max_length=255,
        default='',
        blank=True,
        verbose_name=_('Horizon Mask'),
        help_text=_('Enter Horizon mask URL')
    )
    monument_description = models.CharField(
        max_length=255,
        default='',
        blank=True,
        verbose_name=_('Monument Description'),
        help_text=_('Enter monument description URL')
    )
    site_picture = models.CharField(
        max_length=255,
        default='',
        blank=True,
        verbose_name=_('Site Pictures'),
        help_text=_('Enter site pictures URL')
    )

    additional_information = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Additional Information'),
        help_text=_(
            'Enter additional relevant information. Format: (multiple lines)'
        )
    )

    #def antenna_graphic(self):
    #    return self.site.siteantenna_set.first().graphic

    #antenna_graphic.verbose_name = _('')
    #antenna_graphic.no_indent = True

