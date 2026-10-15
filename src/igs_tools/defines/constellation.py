from typing import Annotated

from enum_properties import IntFlagProperties, Symmetric


class GNSSConstellation(IntFlagProperties):
    label: Annotated[str, Symmetric()]
    _id: Annotated[str, Symmetric()]
    full_name: Annotated[str, Symmetric()]

    GPS   = 2**0, 'GPS',   'G', 'GPS'
    GLO   = 2**1, 'GLO',   'R', 'GLONASS'
    GAL   = 2**2, 'GAL',   'E', 'Galileo'
    BDS   = 2**3, 'BDS',   'C', 'BeiDou'
    QZSS  = 2**4, 'QZSS',  'J', 'QZSS'
    IRNSS = 2**5, 'IRNSS', 'I', 'IRNSS'
    SBAS  = 2**6, 'SBAS',  'S', 'SBAS'

    def __str__(self):
        return str(self.value)

    @property
    def id(self):
        return self._id or 'M'  # M == Mixed
