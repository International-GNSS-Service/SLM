from datetime import date, datetime
from typing import Union
from functools import reduce
from datetime import timedelta
from itertools import chain, islice


def all_flags(flags):
    return reduce(lambda x, y: x | y, [flg for flg in flags])


def str_to_timedelta(time_delta_str):
    """
    Convert a standard string GNSS time period string to a python timedelta.
    These strings are ofr the format ##(S|M|H|D) where ## is the number of
    units and the letter is the unit (seconds, minutes, hours, days).

    :param time_delta_str: string in the format
    :return: timedelta object
    """
    if time_delta_str[-1].upper() == 'S':
        return timedelta(seconds=int(time_delta_str[:-1]))
    elif time_delta_str[-1].upper() == 'M':
        return timedelta(minutes=int(time_delta_str[:-1]))
    elif time_delta_str[-1].upper() == 'H':
        return timedelta(hours=int(time_delta_str[:-1]))
    elif time_delta_str[-1].upper() == 'D':
        return timedelta(days=int(time_delta_str[:-1]))
    raise ValueError(f'Invalid timedelta: {time_delta_str}')


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


def chunks(iterable, size=10):
    """
    Read size elements from a generator at a time without pre-walking the
    entire generator.
    :param iterable: The generator to read from
    :param size: The maximum number of elements to read
    :return: A generator that yields size elements at a time
    """
    iterator = iter(iterable)
    for first in iterator:
        yield chain([first], islice(iterator, size - 1))
