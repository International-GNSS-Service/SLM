from enum import nonmember

from enum_properties import StrEnumProperties, s


class TectonicPlates(StrEnumProperties, s("label", case_fold=True)):
    _symmetric_builtins_ = [s("name", case_fold=True)]
    do_not_call_in_templates = nonmember(True)

    # fmt: off
    AFRICAN        = "AF", "African"
    ANTARCTIC      = "AN", "Antarctic"
    ARABIAN        = "AR", "Arabian"
    AUSTRALIAN     = "AU", "Australian"
    CARIBBEAN      = "CA", "Caribbean"
    COCOS          = "CO", "Cocos"
    EURASIAN       = "EU", "Eurasian"
    INDIAN         = "IN", "Indian"
    JUAN_DE_FUCA   = "JU", "Juan de Fuca"
    NAZCA          = "NZ", "Nazca"
    NORTH_AMERICAN = "NA", "North American"
    PACIFIC        = "PA", "Pacific"
    PHILIPPINE     = "PH", "Philippine"
    SCOTIA         = "SC", "Scotia"
    SOUTH_AMERICAN = "SA", "South American"
    NUBIA          = "NU", "Nubia"
    SOMALIA        = "SO", "Somalia"
    MARIANA        = "MA", "Mariana"
    # fmt: on

    def __str__(self):
        return str(self.label)
