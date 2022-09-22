from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class TectonicPlates(IntegerChoices):
    """
    <enumeration value="African"/>
    <enumeration value="African Indian/Australia"/>
    <enumeration value="African Eurasian"/>
    <enumeration value="Antarctic"/>
    <enumeration value="Arabian"/>
    <enumeration value="Caribbean"/>
    <enumeration value="Cocos"/>
    <enumeration value="Eurasian"/>
    <enumeration value="Indian/Australian"/>
    <enumeration value="Nazca"/>
    <enumeration value="North America"/>
    <enumeration value="North America Pacific"/>
    <enumeration value="Pacific"/>
    <enumeration value="Phillipine"/>
    <enumeration value="South American"/>
    <enumeration value="South American African"/>
    <enumeration value="Juan De Fuca"/>
    <enumeration value="Scotia"/>
    """

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    AFRICAN        = 1, _('African')
    ANTARCTIC      = 2, _('Antarctic')
    ARABIAN        = 3, _('Arabian')
    AUSTRALIAN     = 4, _('Australian')
    CARIBBEAN      = 5, _('Caribbean')
    COCOS          = 6, _('Cocos')
    EURASIAN       = 7, _('Eurasian')
    INDIAN         = 8, _('Indian')
    JUAN_DE_FUCA   = 9, _('Juan de Fuca')
    NAZCA          = 10, _('Nazca')
    NORTH_AMERICAN = 11, _('North American')
    PACIFIC        = 12, _('Pacific')
    PHILIPPINE     = 13, _('Philippine')
    SCOTIA         = 14, _('Scotia')
    SOUTH_AMERICAN = 15, _('South American')
    NUBIA          = 17, _('Nubia')
    SOMALIA        = 18, _('Somalia')
    MARIANA        = 19, _('Mariana')
