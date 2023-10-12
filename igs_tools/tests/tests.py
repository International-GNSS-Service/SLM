from igs_tools.file import GNSSDataFile
from igs_tools.defines import (
    RinexVersion,
    DataRate,
    DataSource,
    DataType,
    DataCenter
)
from datetime import datetime, date, timedelta


def test_file():
    """
    Test that GNSSDataFile parses file names correctly.
    """
    for file, properties, overrides in [
        ('NYA100NOR_S_20230700000_01D_30S_MO.crx.sum.gz', {
            'rinex_version': RinexVersion.v3,
            'station': 'NYA100NOR',
            'data_source': DataSource.STREAM,
            'year': 2023,
            'day_of_year': 70,
            'hour': 0,
            'minute': 0,
            'data_span': timedelta(days=1),
            'data_rate': DataRate.DAILY | DataRate.DAILY.period(30),
            'data_type': DataType.MIXED_OBS,
            'file_format': 'crx',
            'aggregation': 'sum',
            'extension': 'gz',
            'datetime': datetime(2023, 3, 11, 0, 0),
            'date': date(2023, 3, 11),
            'mimetype': (None, 'gzip')
        }, {}),
        ('NYA100NOR_U_20210690500_01H_15S_JO.rnx.Z', {
            'rinex_version': RinexVersion.v3,
            'station': 'NYA100NOR',
            'data_source': DataSource.UNKNOWN,
            'year': 2021,
            'day_of_year': 69,
            'hour': 5,
            'minute': 0,
            'data_span': timedelta(hours=1),
            'data_rate': DataRate.HOURLY | DataRate.HOURLY.period(15),
            'data_type': DataType.QZSS_OBS,
            'file_format': 'rnx',
            'aggregation': None,
            'extension': 'Z',
            'datetime': datetime(2021, 3, 10, 5, 0),
            'date': date(2021, 3, 10),
            'mimetype': (None, 'compress')
        }, {}),
        ('NYAL00NOR_R_20230700000_01D_EN.rnx.gz', {
            'rinex_version': RinexVersion.v3,
            'station': 'NYAL00NOR',
            'data_source': DataSource.RECEIVER,
            'year': 2023,
            'day_of_year': 70,
            'hour': 0,
            'minute': 0,
            'data_span': timedelta(days=1),
            'data_rate': DataRate.DAILY,
            'data_type': DataType.GALILEO_NAV,
            'file_format': 'rnx',
            'aggregation': None,
            'extension': 'gz',
            'datetime': datetime(2023, 3, 11, 0, 0),
            'date': date(2023, 3, 11),
            'mimetype': (None, 'gzip')
        }, {}),
        ('trak0700.23s.gz', {
            'rinex_version': RinexVersion.v2,
            'station': 'trak',
            'data_source': None,
            'year': 2023,
            'day_of_year': 70,
            'hour': 0,
            'minute': None,
            'data_span': None,
            'data_rate': None,
            'data_type': DataType.SUMMARY,
            'file_format': None,
            'aggregation': None,
            'extension': 'gz',
            'datetime': datetime(2023, 3, 11, 0, 0),
            'date': date(2023, 3, 11),
            'mimetype': (None, 'gzip')
        }, {}),
        ('tabv069w.21m.Z', {
            'rinex_version': RinexVersion.v2,
            'station': 'tabv',
            'data_source': None,
            'year': 2021,
            'day_of_year': 69,
            'hour': 22,
            'minute': None,
            'data_span': None,
            'data_rate': DataRate.DAILY,
            'data_type': DataType.METEOROLOGY,
            'file_format': None,
            'aggregation': None,
            'extension': 'Z',
            'datetime': datetime(2021, 3, 10, 22, 0),
            'date': date(2021, 3, 10),
            'mimetype': (None, 'compress')
        }, {'data_rate': DataRate.DAILY}),
        ('DJIG00DJI_R_20211300000_01D_01S_RN.rnx.tar', {
            'rinex_version': RinexVersion.v3,
            'station': 'DJIG00DJI',
            'data_source': DataSource.RECEIVER,
            'year': 2021,
            'day_of_year': 130,
            'hour': 0,
            'minute': 0,
            'data_span': timedelta(days=1),
            'data_rate': DataRate.DAILY | DataRate.DAILY.period(1),
            'data_type': DataType.GLONASS_NAV,
            'file_format': 'rnx',
            'aggregation': None,
            'extension': 'tar',
            'datetime': datetime(2021, 5, 10, 0, 0),
            'date': date(2021, 5, 10),
            'mimetype': ('application/x-tar', None)
        }, {})
    ]:
        parsed = GNSSDataFile(file, **overrides)
        for prop, value in properties.items():
            assert getattr(parsed, prop) == value


def test_cddis_dir():

    assert DataCenter.CDDIS.directories(
        rinex_version=RinexVersion.v3,
        data_rate=DataRate.DAILY,
        data_type=DataType.MIXED_OBS,

    )