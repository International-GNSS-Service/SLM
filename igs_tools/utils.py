from datetime import date, datetime
from typing import Union
import re


class classproperty:
    """
    Equivalent to @property but for classes not instances.
    """

    def __init__(self, method=None):
        self.fget = method

    def __get__(self, instance, cls=None):
        return self.fget(cls)

    def getter(self, method):
        self.fget = method
        return self


def gps_week(date: Union[date, datetime]) -> int:
    pass


def day_of_year(date: Union[date, datetime]) -> int:
    return int(date.strftime('%j'))


def get_file_properties(filename):
    """
    Infer properties of a rinex file from its name.
    :param filename:
    :return:
    """
    from igs_tools.defines import RinexVersion
    regexes = [
        (
            re.compile(
                r'^(?P<station>[a-z0-9]{4})'
                r'(?P<gps_day>\d{3})'
                r'(?P<hour>[0a-z]{1})'
                r'[.](?P<year>\d{2})(?P<file_type>[a-z]{1})'
                r'[.](?P<compression>\w*)$'
            ),
            {'rinex_version': RinexVersion.v2}
        ),
        (
            re.compile(
                r'^(?P<station>[A-Z0-9]{9})_(\w{1})_(?P<year>\d{4})'
                r'(?P<gps_day>\d{3})(\d{4})_(\w{3})_((\w{3})_)?'
                r'(?P<constellation>\w{1})(?P<file_type>\w{1})[.]'
                r'(?P<rinex_Format>(crx)|(rnx))[.](?P<compression>\w*)$'
            ),
            {'rinex_version': RinexVersion.v3}
        )
    ]

    for regex in regexes:
        match = re.match(regex[0], filename)
        if match:
            return {
                **match.groupdict(),
                **regex[1]
            }
    return None
