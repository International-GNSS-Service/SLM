from enum_properties import EnumProperties, IntFlagProperties, p, s


class DataType(
    IntFlagProperties, s('r2codes'), s('label'), s('description')
):

    MIXED_OBS    = 2**0,  ['o'],      'MO', 'Mixed observation data'
    MIXED_NAV    = 2**1,  ['p'],      'MN', 'Navigation data (All GNSS Constellations)'
    COMBINED_NAV = 2**2,  ['b'],      'MN', 'Combined broadcast ephemeris data'
    HATANAKA_OBS = 2**3,  ['d'],      'MO', 'Hatanaka-compressed mixed observation data'
    BEIDOU_NAV   = 2**4,  ['f'],      'CN', 'BDS Navigation data'
    GLONASS_NAV  = 2**5,  ['g'],      'RN', 'GLONASS Navigation data'
    SBAS_NAV     = 2**6,  ['h'],      'SN', 'SBAS Navigation data'
    IRNSS_NAV    = 2**7,  ['i'],      'IN', 'IRNSS Navigation data'
    GALILEO_NAV  = 2**8,  ['l'],      'EN', 'Galileo Navigation data'
    METEOROLOGY  = 2**9,  ['m'],      'MM', 'Meteorological Observation'
    GPS_NAV      = 2**10, ['n'],      'GN', 'GPS Navigation data'
    QZSS_NAV     = 2**11, ['q'],      'JN', 'QZSS Navigation data'
    SUMMARY      = 2**12, ['s'],      'MO', 'Observation summary files'
    MIXED_EPH    = 2**13, ['x'],      'MN', 'Mixed broadcast ephemeris data'
    GPS_OBS      = 2**14, ['o', 'd'], 'GO', 'GPS Observation data'
    GLONASS_OBS  = 2**15, ['o', 'd'], 'RO', 'GLONASS Observation data'
    GALILEO_OBS  = 2**16, ['o', 'd'], 'EO', 'Galileo Observation data'
    QZSS_OBS     = 2**17, ['o', 'd'], 'JO', 'QZSS Observation data'
    BEIDOU_OBS   = 2**18, ['o', 'd'], 'CO', 'BDS Observation data'
    IRNSS_OBS    = 2**19, ['o', 'd'], 'IO', 'IRNSS Observation data'
    SBAS_OBS     = 2**20, ['o', 'd'], 'SO', 'SBAS Observation data'

    OBSERVABLES = (
        MIXED_OBS | HATANAKA_OBS | GPS_OBS | GLONASS_OBS |
        GALILEO_OBS | QZSS_OBS | BEIDOU_OBS | IRNSS_OBS |
        SBAS_OBS
    ), None, 'OBS', 'All Observation data'

    NAVIGATION = (
        MIXED_NAV | COMBINED_NAV | BEIDOU_NAV |
        GLONASS_NAV | SBAS_NAV | IRNSS_NAV | GALILEO_NAV |
        GPS_NAV | QZSS_NAV | MIXED_EPH
    ), None, 'NAV', 'All Navigation data'

    @property
    def r2code(self):
        if self.rt2codes:
            return self.r2codes[0]
        return None


class DataSource(EnumProperties, s('label'), p('description')):

    RECEIVER = 'R', 'Receiver', 'From Receiver data using vendor or other software.'
    STREAM   = 'S', 'Stream',   'From data stream (RTCM or other)'
    UNKNOWN  = 'U', 'Unknown',  'Unknown source'
