from datetime import date, datetime, timezone

import pytest

from slm.parsing import _Warning, to_date, to_datetime


def test_to_datetime():
    assert to_datetime("2023-04-18T00:00Z") == datetime(
        2023, 4, 18, tzinfo=timezone.utc
    )


def test_to_date_trailing_junk_warns():
    parsed = to_date("2023-04-18 (approx)")
    assert isinstance(parsed, _Warning)
    assert parsed.value == date(2023, 4, 18)


@pytest.mark.parametrize("value", ["2023-13-45T99:99Z", "not a date"])
def test_invalid_datetime_raises(value):
    with pytest.raises(ValueError):
        to_datetime(value)


@pytest.mark.parametrize("value", ["", "  "])
def test_empty_datetime(value):
    assert to_datetime(value) is None
