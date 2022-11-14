from django.contrib.auth.models import UserManager as DjangoUserManager
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
from django.db import models
from django.contrib.auth.hashers import make_password
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
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields['is_staff'] = True
        extra_fields['is_superuser'] = True
        return self._create_user(email, password, **extra_fields)


class UserQueryset(models.QuerySet):

    def emails_ok(self):
        return self.filter(silence_emails=False)


class UserProfile(models.Model):

    # contact
    phone1 = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('Primary Phone Number'),
        #help_text=_('Your primary contact phone number.')
    )
    phone2 = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('Secondary Phone Number')
    )
    address1 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('Address Line 1')
    )
    address2 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('Address Line 2')
    )
    address3 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('Address Line 3')
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('City')
    )
    state_province = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('State/Province')
    )
    country = models.CharField(
        max_length=75,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('Country')
    )
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_('Postal Code')
    )

    # affiliation
    registration_agency = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        default=None,
        verbose_name=_('Registration Agency')
    )

    # preferences
    html_emails = models.BooleanField(
        default=True,
        verbose_name=_('HTML Emails'),
        help_text=_('Receive HTML in email communications.')
    )


class User(AbstractBaseUser, PermissionsMixin):
    """
    Stub out a custom user model now in case we want them later - its way easier to add stuff to
    a custom user model later rather than having to migrate off of django's native user model
    """
    email = models.EmailField(
        verbose_name=_('Email Address'),
        max_length=255,
        null=True,
        unique=True
    )

    first_name = models.CharField(max_length=255, null=True, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=255, null=True, verbose_name=_('Last Name'))

    is_superuser = models.BooleanField(
        _('Superuser'),
        default=False,
        help_text=_('Designates whether the user has unlimited access.'),
    )

    is_staff = models.BooleanField(
        _('Staff'),
        default=True,
        help_text=_('Designates if the user is staff.'),
    )

    is_active = models.BooleanField(
        _('Active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name=_('Date Joined'))

    agency = models.ForeignKey(
        'slm.Agency',
        null=True,
        default=None,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('Agency')
    )

    profile = models.OneToOneField(
        UserProfile,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None
    )

    silence_emails = models.BooleanField(
        null=False,
        default=False,
        blank=True,
        help_text=_(
            'If set to true this user will not be sent any emails by the '
            'system. Note: this does not apply to account related emails '
            '(i.e. password resets).'
        )
    )

    def is_moderator(self, station):
        return station.is_moderator(self)

    @property
    def name(self):
        if self.first_name or self.last_name:
            return f'{self.first_name} {self.last_name}'
        elif self.email:
            return self.email
        return None

    def __str__(self):
        if self.name:
            return f'{self.email} | {self.name}'
        return self.email

    objects = UserManager.from_queryset(UserQueryset)()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
