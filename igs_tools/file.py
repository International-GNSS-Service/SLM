from igs_tools.defines import (
    RinexVersion,
    DataRate,
    DataSource,
    DataType
)
from mimetypes import guess_type
from datetime import datetime, timedelta
from igs_tools.utils import all_flags, str_to_timedelta
from typing import Optional
import re


class GNSSDataFile(str):

    regexes = [
        (
            # XXXXMRCCC_K_YYYYDDDHHMM_01D_30S_tt.FFF.gz
            re.compile(
                r'^(?P<station>[A-Z0-9]{9})_(?P<data_source>\w{1})_'
                r'(?P<year>\d{4})(?P<day_of_year>\d{3})(?P<hour>\d{2})'
                r'(?P<minute>\d{2})_((?P<data_span>\w{3})_)?'
                r'((?P<data_rate>\w{3})_)?(?P<data_type>\w{2})[.]'
                r'(?P<file_format>\w+)[.]((?P<aggregation>\w+)[.])?'
                r'(?P<extension>\w*)$'
            ), {'rinex_version': RinexVersion.v3}
        ),
        (
            # mmmmDDD#.YYt.gz
            re.compile(
                r'^(?P<station>[a-z0-9]{4})'
                r'(?P<day_of_year>\d{3})'
                r'(?P<hour>[0a-z]{1})'
                r'[.](?P<year>\d{2})(?P<data_type>[a-z]{1})'
                r'[.](?P<extension>\w*)$'
            ), {'rinex_version': RinexVersion.v2}
        )
    ]

    _station_: Optional[str] = None
    _rinex_version_: Optional[RinexVersion] = None
    _data_rate_: Optional[DataRate] = None
    _data_type_: Optional[DataType] = None
    _data_source_: Optional[DataSource] = None
    _data_span_: Optional[timedelta] = None
    _mimetype_: Optional[str] = None
    _year_: Optional[int] = None
    _day_of_year_: Optional[int] = None
    _hour_: Optional[int] = None
    _minute_: Optional[int] = None
    _extension_: Optional[str] = None
    _file_format_: Optional[str] = None
    _aggregation_: Optional[str] = None

    @property
    def station(self):
        return self._station_

    @station.setter
    def station(self, value):
        self._station_ = value

    @property
    def rinex_version(self):
        return self._rinex_version_

    @rinex_version.setter
    def rinex_version(self, value):
        if value is not None:
            self._rinex_version_ = RinexVersion(value)
        else:
            self._rinex_version_ = None

    @property
    def data_span(self):
        return self._data_span_

    @data_span.setter
    def data_span(self, value):
        if value is not None:
            self._data_span_ = str_to_timedelta(value)
            if self._data_span_.total_seconds() >= 86400:
                self._data_rate_ = DataRate.DAILY
            elif self._data_span_.total_seconds() >= 3600:
                self._data_rate_ = DataRate.HOURLY
            else:
                self._data_rate_ = DataRate.HIGH_RATE
        else:
            self._data_span_ = None
            self._data_rate_ = None

    @property
    def file_cadence(self):
        return self._data_rate_ & all_flags(DataRate)

    @property
    def data_rate(self):
        return self._data_rate_

    @data_rate.setter
    def data_rate(self, value):
        """
        Set the full data_rate, or the period in seconds for the already set
        file cadence, or a timedelta string (e.g. '15M') representing the data
        rate at the already set file cadence.

        :param value:
        :return:
        """
        if value is not None:
            if isinstance(value, DataRate):
                self._data_rate_ = value
            else:
                if not hasattr(self._data_rate_, 'period'):
                    raise ValueError('Must set data_span before data_rate')
                if isinstance(value, str) and not value.isdigit():
                    self._data_rate_ |= self._data_rate_.period(
                        int(str_to_timedelta(value).total_seconds())
                    )
                else:
                    self._data_rate_ |= self._data_rate_.period(int(value))
        else:
            self._data_rate_ &= all_flags(DataRate)

    @property
    def data_type(self):
        return self._data_type_

    @data_type.setter
    def data_type(self, value):
        if value is not None:
            self._data_type_ = DataType(value)
        else:
            self._data_type_ = None

    @property
    def data_source(self):
        return self._data_source_

    @data_source.setter
    def data_source(self, value):
        if value is not None:
            self._data_source_ = DataSource(value)
        else:
            self._data_source_ = None

    @property
    def year(self):
        return self._year_

    @year.setter
    def year(self, value):
        if value is not None:
            self._year_ = int(value)
            if 70 < self._year_ < 100:
                self._year_ += 1900
            elif 0 < self._year_ < 70:
                self._year_ += 2000
        else:
            self._year_ = None

    @property
    def day_of_year(self):
        return self._day_of_year_

    @day_of_year.setter
    def day_of_year(self, value):
        if value is not None:
            self._day_of_year_ = int(value)
        else:
            self._day_of_year_ = None

    @property
    def hour(self):
        return self._hour_

    @hour.setter
    def hour(self, value):
        if value is not None:
            if value.isalpha() and len(value) == 1:
                self._hour_ = int(ord(value.lower()) - ord('a'))
            else:
                self._hour_ = int(value)
        else:
            self._hour_ = None

    @property
    def minute(self):
        return self._minute_

    @minute.setter
    def minute(self, value):
        if value is not None:
            self._minute_ = int(value)
        else:
            self._minute_ = None

    @property
    def extension(self):
        return self._extension_

    @extension.setter
    def extension(self, value):
        self._extension_ = value

    @property
    def file_format(self):
        return self._file_format_

    @file_format.setter
    def file_format(self, value):
        self._file_format_ = value

    @property
    def aggregation(self):
        return self._aggregation_

    @aggregation.setter
    def aggregation(self, value):
        self._aggregation_ = value

    @property
    def datetime(self):
        if self.year is not None and self.day_of_year is not None:
            return datetime(self.year, 1, 1) + \
                timedelta(
                    days=self.day_of_year - 1,
                    hours=self.hour,
                    minutes=self.minute or 0
                )
        return None

    @property
    def date(self):
        if self.datetime:
            return self.datetime.date()
        return None

    @property
    def mimetype(self):
        return self._mimetype_

    @mimetype.setter
    def mimetype(self, value):
        if value is not None:
            self._mimetype_ = guess_type(value)
        else:
            self._mimetype_ = None

    def __new__(cls, path, **kwargs):
        path = path.split('/')[-1]
        match = None
        for regex, props in cls.regexes:
            match = regex.match(path)
            if match:
                for prop, value in props.items():
                    kwargs.setdefault(prop, value)
                break

        if match is None:
            raise ValueError(f'Unrecognized RINEX file name: {path}')

        instance = super().__new__(cls, path)
        for prop, value in {**match.groupdict(), **kwargs}.items():
            setattr(instance, prop, value)

        instance.mimetype = path
        return instance

    # @staticmethod
    # def from_params():
    #     pass
