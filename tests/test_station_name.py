"""
StationNameField must reject names that are unsafe to use as filesystem path
components or URL segments, regardless of whether a deployment configures
SLM_STATION_NAME_REGEX.
"""

import pytest
from django.core.exceptions import ValidationError

from slm.models import Site


@pytest.mark.parametrize(
    "name",
    [
        "AAA200USA",
        "aaa200usa",
        "ABCD",
        "my-station",
        "station_1",
    ],
)
def test_safe_station_names_are_accepted(name):
    Site._meta.get_field("name").run_validators(name)


@pytest.mark.parametrize(
    "name",
    [
        "..",
        ".",
        "../AAA200USA",
        "AAA200USA/..",
        "a/b",
        "a\\b",
        "/absolute",
        "AAA200.USA",
        "AAA 200USA",
        "AAA200USA\n",
        "AAA\x00USA",
    ],
)
def test_unsafe_station_names_are_rejected(name):
    with pytest.raises(ValidationError):
        Site._meta.get_field("name").run_validators(name)


def test_model_clean_rejects_unsafe_name(db):
    site = Site(name="../escape")
    with pytest.raises(ValidationError) as excinfo:
        site.full_clean(exclude=["agencies"], validate_unique=False)
    assert "name" in excinfo.value.error_dict
