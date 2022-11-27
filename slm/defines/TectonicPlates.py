from django_enum import TextChoices
from enum_properties import s
from django.utils.translation import gettext as _


class TectonicPlates(TextChoices):
    """
    """

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    AFRICAN        = 'AF', _('African')
    ANTARCTIC      = 'AN', _('Antarctic')
    ARABIAN        = 'AR', _('Arabian')
    AUSTRALIAN     = 'AU', _('Australian')
    CARIBBEAN      = 'CA', _('Caribbean')
    COCOS          = 'CO', _('Cocos')
    EURASIAN       = 'EU', _('Eurasian')
    INDIAN         = 'IN', _('Indian')
    JUAN_DE_FUCA   = 'JU', _('Juan de Fuca')
    NAZCA          = 'NZ', _('Nazca')
    NORTH_AMERICAN = 'NA', _('North American')
    PACIFIC        = 'PA', _('Pacific')
    PHILIPPINE     = 'PH', _('Philippine')
    SCOTIA         = 'SC', _('Scotia')
    SOUTH_AMERICAN = 'SA', _('South American')
    NUBIA          = 'NU', _('Nubia')
    SOMALIA        = 'SO', _('Somalia')
    MARIANA        = 'MA', _('Mariana')
