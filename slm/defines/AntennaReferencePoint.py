from django_enum import IntegerChoices
from enum_properties import s
from django.utils.translation import gettext as _


class AntennaReferencePoint(IntegerChoices, s('title')):

    __symmetric_builtins__ = [
        s('name', case_fold=True),
        s('label', case_fold=True)
    ]

    #   value              label                                    title
    BAM = 1,  f'BAM ({_("Bottom of Antenna Mount")})',     _("Bottom of Antenna Mount")
    BCR = 2,  f'BCR ({_("Bottom of Chokering")})',         _('Bottom of Chokering')
    BDG = 3,  f'BDG ({_("Bottom of Dome Ground Plane")})', _('Bottom of Dome Ground Plane')
    BGP = 4,  f'BGP ({_("Bottom of Ground Plane")})',      _('Bottom of Ground Plane')
    BPA = 5,  f'BPA ({_("Bottom of Preamplifier")})',      _('Bottom of Preamplifier')
    TCR = 6,  f'TCR ({_("Top of Chokering")})',            _('Top of Chokering')
    TDG = 7,  f'TDG ({_("Top of Dome Ground Plane")})',    _('Top of Dome Ground Plane')
    TGP = 8,  f'TGP ({_("Top of Ground Plane")})',         _('Top of Ground Plane')
    TOP = 9,  f'TOP ({_("Top of Pole")})',                 _('Top of Pole')
    TPA = 10, f'TPA ({_("Top of Preamplifier")})',         _('Top of Preamplifier')

    def __str__(self):
        return self.name
