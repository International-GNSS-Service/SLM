from functools import lru_cache

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission, PermissionsMixin
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _


class UserManager(DjangoUserManager):
    use_in_migrations = False

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        email = self.normalize_email(email)
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.pop("is_staff", None)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault(
            "silence_alerts", getattr(settings, "SLM_EMAILS_REQUIRE_LOGIN", True)
        )
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.pop("is_staff", None)
        extra_fields["is_superuser"] = True
        extra_fields.setdefault(
            "silence_alerts", getattr(settings, "SLM_EMAILS_REQUIRE_LOGIN", True)
        )
        return self._create_user(email, password, **extra_fields)


class UserQueryset(models.QuerySet):
    def emails_ok(self, html=None):
        if html is None:
            return self.filter(silence_alerts=False)
        return self.filter(silence_alerts=False, html_emails=html)

    def annotate_moderator_status(self):
        perm = Permission.objects.get_by_natural_key("moderate_sites", "slm", "user")
        return self.annotate(
            moderator=models.Case(
                models.When(
                    Q(groups__permissions=perm)
                    | Q(user_permissions=perm)
                    | Q(is_superuser=True),
                    then=True,
                ),
                default=False,
                output_field=models.BooleanField(),
            )
        )


class UserProfile(models.Model):
    # contact
    phone1 = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Primary Phone Number"),
        # help_text=_('Your primary contact phone number.')
    )
    phone2 = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Secondary Phone Number"),
    )
    address1 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Address Line 1"),
    )
    address2 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Address Line 2"),
    )
    address3 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Address Line 3"),
    )
    city = models.CharField(
        max_length=100, blank=True, null=True, default=None, verbose_name=_("City")
    )
    state_province = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("State/Province"),
    )
    country = models.CharField(
        max_length=75, blank=True, null=True, default=None, verbose_name=_("Country")
    )
    postal_code = models.CharField(
        max_length=10, blank=True, null=True, verbose_name=_("Postal Code")
    )

    # affiliation
    registration_agency = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Registration Agency"),
    )

    user = models.OneToOneField(
        "slm.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        related_name="profile",
    )

    def __str__(self):
        return self.user.name


class User(AbstractBaseUser, PermissionsMixin):
    """
    Stub out a custom user model now in case we want them later - its way
    easier to add stuff to a custom user model later rather than having to
    migrate off of django's native user model
    """

    email = models.EmailField(
        verbose_name=_("Email Address"), max_length=255, null=True, unique=True
    )

    first_name = models.CharField(
        max_length=255, null=True, blank=True, default="", verbose_name=_("First Name")
    )
    last_name = models.CharField(
        max_length=255, null=True, blank=True, default="", verbose_name=_("Last Name")
    )

    is_superuser = models.BooleanField(
        _("Superuser"),
        default=False,
        help_text=_("Designates whether the user has unlimited access."),
        db_index=True,
    )

    @property
    def is_staff(self):
        """
        Django users typically have an is_staff flag which allows access
        to sub-superusers to the admin. This seems like an unnecessary layer of
        complexity for SLM use cases. Only superusers should be able to see the
        admin. If necessary in the future - this could be converted into a
        database field.
        """
        return self.is_superuser

    is_active = models.BooleanField(
        _("Active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
        db_index=True,
    )

    date_joined = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Date Joined"), db_index=True
    )

    last_activity = models.DateTimeField(
        verbose_name=_("Last Activity"),
        editable=False,
        null=True,
        blank=True,
        default=None,
        db_index=True,
    )

    agencies = models.ManyToManyField(
        "slm.Agency",
        blank=True,
        verbose_name=_("Agency"),
        help_text=_(
            "The agencies this user is a member of. At bare minimum this user "
            "will have edit permissions for all these agency sites."
        ),
        related_name="users",
    )

    silence_alerts = models.BooleanField(
        null=False,
        default=True,
        blank=True,
        help_text=_(
            "If set to true this user will not be sent any alert emails by "
            "the system. Note: this does not apply to account related emails "
            "(i.e. password resets)."
        ),
        db_index=True,
    )

    # preferences
    html_emails = models.BooleanField(
        default=True,
        blank=True,
        verbose_name=_("HTML Emails"),
        help_text=_("Receive HTML in email communications."),
        db_index=True,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not hasattr(self, "profile") or not self.profile:
            UserProfile.objects.create(user=self)

    @lru_cache(maxsize=32)
    def is_moderator(self, station=None):
        if self.is_superuser:
            return True
        if station:
            return station.is_moderator(self)
        elif hasattr(self, "moderator"):
            return self.moderator

        moderate_perm = Permission.objects.get_by_natural_key(
            "moderate_sites", "slm", "user"
        )
        return (
            self.user_permissions.filter(pk=moderate_perm.pk).exists()
            or self.groups.filter(permissions__in=[moderate_perm]).exists()
        )

    def can_propose_site(self, agencies=None):
        """
        Superusers can propose any site, otherwise the user must have the
        slm.propose_sites permission and they must be a member of every
        agency the proposed site is a member of.

        :param agencies: A QuerySet of Agencies the proposed site will be a
            member of
        :return: True if this user can propose the site, false otherwise.
        """
        if self.is_superuser:
            return True
        if not self.has_perm("slm.propose_sites"):
            return False
        if agencies is None:
            from slm.models import Agency

            agencies = Agency.objects.none()
        return not agencies.filter(~Q(pk__in=self.agencies.all())).exists()

    @property
    def name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.email:
            return self.email
        return None

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def __str__(self):
        if self.name:
            return f"{self.email} | {self.name}"
        return self.email

    objects = UserManager.from_queryset(UserQueryset)()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"

    class Meta:
        permissions = [
            ("propose_sites", _("May propose new sites for their agencies.")),
            ("moderate_sites", _("May publish logs for sites in their agencies.")),
        ]
