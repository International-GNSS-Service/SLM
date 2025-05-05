from django.utils.translation import gettext_lazy as _
from django_enum import IntegerChoices
from enum_properties import p, s


class AntennaReferencePoint(IntegerChoices, p("title")):
    _symmetric_builtins_ = [s("name", case_fold=True)]

    # fmt: off
    #   value              label                                    title
    BAM = 1,  _("BAM (Bottom of Antenna Mount)"),     _("Bottom of Antenna Mount")
    BCR = 2,  _("BCR (Bottom of Chokering)"),         _("Bottom of Chokering")
    BDG = 3,  _("BDG (Bottom of Dome Ground Plane)"), _("Bottom of Dome Ground Plane")
    BGP = 4,  _("BGP (Bottom of Ground Plane)"),      _("Bottom of Ground Plane")
    BPA = 5,  _("BPA (Bottom of Preamplifier)"),      _("Bottom of Preamplifier")
    TCR = 6,  _("TCR (Top of Chokering)"),            _("Top of Chokering")
    TDG = 7,  _("TDG (Top of Dome Ground Plane)"),    _("Top of Dome Ground Plane")
    TGP = 8,  _("TGP (Top of Ground Plane)"),         _("Top of Ground Plane")
    TOP = 9,  _("TOP (Top of Pole)"),                 _("Top of Pole")
    TPA = 10, _("TPA (Top of Preamplifier)"),         _("Top of Preamplifier")
    # fmt: on

    def __str__(self):
        return self.name
