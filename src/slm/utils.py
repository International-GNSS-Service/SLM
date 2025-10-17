import json
import re
import typing as t
from datetime import date, datetime, timedelta
from math import atan2, copysign, cos, floor, sin, sqrt

from dateutil import parser as date_parser
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from PIL import ExifTags, Image

PROTOCOL = getattr(settings, "SLM_HTTP_PROTOCOL", None)
GPS_EPOCH = date(year=1980, month=1, day=6)

_site_record = None


def get_record_model():
    global _site_record
    if _site_record is not None:
        return _site_record

    from django.apps import apps

    slm_site_record = getattr(settings, "SLM_SITE_RECORD", "slm.DefaultSiteRecord")
    try:
        app_label, model_class = slm_site_record.split(".")
        _site_record = apps.get_app_config(app_label).get(model_class.lower(), None)
        if not _site_record:
            raise ImproperlyConfigured(
                f'SLM_SITE_RECORD "{slm_site_record}" is not a registered model'
            )
        return _site_record
    except ValueError as ve:
        raise ImproperlyConfigured(
            f"SLM_SITE_RECORD value {slm_site_record} is invalid, must be "
            f'"app_label.ModelClass"'
        ) from ve


def dddmmssss_to_decimal(
    dddmmssss: t.Optional[t.Union[float, str, int]], sec_digits: int = 6
) -> t.Optional[float]:
    """
    Convert DDDMMSS.ss composite to decimal degrees.
    Preserves -0.0 and normalizes 60s/60m carries.

    :param dddmmssss: latitude or longitude in DDDMMSS.SS format
    :return: the coordinate in decimal degrees
    """
    if dddmmssss is None:
        return None
    if isinstance(dddmmssss, str):
        dddmmssss = float(dddmmssss)

    sgn = copysign(1.0, dddmmssss)
    v = abs(dddmmssss)

    # Extract D, M, S from DDDMMSS.ss
    degrees = int(v // 10000)
    remainder = v - degrees * 10000
    minutes = int(remainder // 100)
    seconds = remainder - minutes * 100

    # Clean up float noise and normalize carries
    seconds = round(seconds, sec_digits)
    if seconds >= 60.0:
        seconds = 0.0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        degrees += 1

    dec = degrees + minutes / 60.0 + seconds / 3600.0
    return copysign(dec, sgn)


def decimal_to_dddmmssss(
    dec: t.Optional[t.Union[str, float]], sec_digits: int = 2
) -> t.Optional[float]:
    """
    Convert decimal degrees to DDDMMSS.SS... as a float.
    Preserves the sign of -0.0 and normalizes carry (sec/min -> min/deg).

    :param: dec: string or float of decimal degrees of either latitude or longitude
    :return: floating point lat or lon in DDDMMSS.SS format
    """
    if dec is None:
        return None
    if isinstance(dec, str):
        dec = float(dec)

    # Work with absolute value; keep original sign with copysign at the end
    a = abs(dec)

    degrees = int(a)
    minutes_full = (a - degrees) * 60.0
    minutes = int(minutes_full)
    seconds = (minutes_full - minutes) * 60.0

    # Round seconds, then normalize carries (60s -> +1m, 60m -> +1d)
    seconds = round(seconds, sec_digits)
    if seconds >= 60.0:
        seconds = 0.0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        degrees += 1

    # Compose as DDDMMSS.ss (minutes and seconds are non-negative)
    composite = degrees * 10000 + minutes * 100 + seconds
    return copysign(composite, dec)


def dddmmss_ss_parts(
    dec: t.Optional[t.Union[str, float, int]], sec_digits: int = 2
) -> t.Tuple[t.Optional[float], t.Optional[int], t.Optional[float]]:
    """
    Return (degrees, minutes, seconds) from decimal degrees
    :param dec: Decimal degrees lat or lon
    :return: a 3-tuple of degrees, minutes seconds components. The degrees component will be a
      whole number, but is a float so that it may contain the sign.
    """
    if dec is None:
        return None, None, None
    if isinstance(dec, str):
        dec = float(dec)

    sign = int(copysign(1, dec))
    v = abs(dec)

    degrees = floor(v)
    minutes_full = (v - degrees) * 60
    minutes = floor(minutes_full)
    seconds = (minutes_full - minutes) * 60

    seconds = round(seconds, sec_digits)

    # Handle rounding overflow (e.g. 59.9999 → 60.0)
    if seconds >= 60.0:
        seconds = 0.0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        degrees += 1

    return (sign * float(degrees), minutes, seconds)


def lon_180_to_360(lon):
    return lon % 360.0


def lon_360_to_180(lon):
    return ((lon + 180) % 360) - 180


def set_protocol(request):
    global PROTOCOL
    if not PROTOCOL:
        PROTOCOL = "https" if request.is_secure() else "http"


def get_protocol():
    global PROTOCOL
    if PROTOCOL is not None:
        return PROTOCOL
    return "https" if getattr(settings, "SECURE_SSL_REDIRECT", False) else "http"


def build_absolute_url(path, request=None):
    if path.startswith("mailto:"):
        return path
    if request:
        return request.build_absolute_uri(path)
    return f"{get_url()}/{path.lstrip('/')}"


def get_url():
    from django.contrib.sites.models import Site

    return f"{get_protocol()}://{Site.objects.get_current().domain}"


def from_email():
    from django.contrib.sites.models import Site

    return getattr(
        settings, "SERVER_EMAIL", f"noreply@{Site.objects.get_current().domain}"
    )


def clear_caches():
    from slm.models import Site, User

    User.is_moderator.cache_clear()
    Site.is_moderator.cache_clear()


def to_bool(bool_str):
    if bool_str is None:
        return None
    if isinstance(bool_str, str):
        return bool_str.lower() not in ["0", "no", "false"]
    return bool(bool_str)


def to_snake_case(string):
    snake = string
    if string:
        snake = string[0].lower()
        new = False
        for char in string[1:]:
            if char == " ":
                new = True
            elif char.isupper() or new:
                snake += f"_{char.lower()}"
                new = False
            elif char.isalnum():
                snake += char
    return snake


def date_to_str(date_obj):
    if date_obj:
        return f"{date_obj.year}-{date_obj.month:02}-{date_obj.day:02}"
    return ""


def gps_week(date_obj=datetime.now()):
    """
    Return GPS week number for a given datetime, date or date string
    :param date_obj: Date object, datetime object or date string
    :return: 2-tuple: GPS week number, GPS day of week
    :raises ValueError: If date_obj is earlier than the GPS epoch
    """
    # todo move this to igs_tools
    if date_obj is None:
        date_obj = datetime.now().date()
    if isinstance(date_obj, str):
        date_obj = date_parser.parse(date_obj)
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    delta = date_obj - GPS_EPOCH
    if delta.days >= 0:
        return delta.days // 7, delta.days % 7
    raise ValueError(f"{date_obj} is earlier than the GPS epoch {GPS_EPOCH}.")


def date_from_gps_week(gps_week, day_of_week=0):
    """
    Return a date object for a given GPS week number and day of week
    :param gps_week: GPS week number
    :param day_of_week: GPS day of week, 0-6
    :return: Date object
    """
    # todo move this to igs_tools
    return GPS_EPOCH + timedelta(days=gps_week * 7 + day_of_week)


def day_of_year(date_obj=datetime.now()):
    """
    Return the day of the year for the given object representing a date.

    :param date_obj: Date object, datetime object or date string
    :return: integer day of year
    """
    # todo move this to igs_tools
    if isinstance(date_obj, str):
        date_obj = date_parser.parse(date_obj)
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    return (date_obj - date(date_obj.year, 1, 1) + timedelta(days=1)).days


def http_accepts(accepted_types, mimetype):
    if "*/*" in accepted_types:
        return True
    if mimetype in accepted_types:
        return True
    typ, sub_type = mimetype.split("/")
    if f"{typ}/*" in accepted_types:
        return True
    if f"*/{sub_type}" in accepted_types:
        return True
    return False


class SectionEncoder(json.JSONEncoder):
    def default(self, obj):
        from django.db.models import Manager, Model, QuerySet

        from slm.models import Equipment, Manufacturer, SiteSection

        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if isinstance(obj, SiteSection):
            return {field: getattr(obj, field) for field in obj.site_log_fields()}
        if isinstance(obj, Equipment):
            return {field: getattr(obj, field) for field in ["model", "manufacturer"]}
        if isinstance(obj, Manufacturer):
            return {field: getattr(obj, field) for field in ["name"]}

        if isinstance(obj, Model):
            # catch-all
            return json.loads(serializers.serialize("json", [obj]))[0]

        if isinstance(obj, (Manager, QuerySet)):
            return [related for related in obj.all()]

        if isinstance(obj, Point):
            return obj.coords
        return json.JSONEncoder.default(self, obj)


def get_exif_tags(file_path):
    # not all images have exif, (e.g. gifs)
    image_exif = getattr(Image.open(file_path), "_getexif", lambda: None)()
    if image_exif:
        exif = {
            ExifTags.TAGS[k]: v
            for k, v in image_exif.items()
            if k in ExifTags.TAGS and not isinstance(v, bytes)
        }
        return exif
    return {}


def xyz2llh(*xyz, geodetic=True) -> t.Tuple[float, float, float]:
    """
    Convert ECEF to LLH using ITRF2020 Ellipsoid.

    :param xyz: A 3-tuple or 3 xyz parameters, e.g. xyz2llh(x,y,z) or xyz2llh((x,y,z))
    :return: A 3-tuple of latitude, longitude, height. Longitude is geodetic (+/-180) by default and height is in meters.
    """
    a_e = 6378.137e3  # meters
    f_e = 1 / 298.257222101  # ITRF2020 flattening
    radians2degree = 45 / atan2(1, 1)

    # allow xyz2llh(x,y,z) or xyz2llh((x,y,z))
    xyz = xyz[0] if len(xyz) == 1 else xyz

    xyz_array = [v / a_e for v in xyz]
    (x, y, z) = (xyz_array[0], xyz_array[1], xyz_array[2])
    e2 = f_e * (2 - f_e)
    z2 = z**2
    p2 = x**2 + y**2
    p = sqrt(p2)
    r = sqrt(p2 + z2)
    mu = atan2(z * (1 - f_e + e2 / r), p)
    phi = atan2(
        z * (1 - f_e) + e2 * (sin(mu)) ** 3, (1 - f_e) * (p - e2 * (cos(mu)) ** 3)
    )
    lat = phi * radians2degree
    lon = atan2(y, x) * radians2degree
    if lon < 0:
        lon = lon + 360
    h = a_e * (p * cos(phi) + z * sin(phi) - sqrt(1 - e2 * (sin(phi)) ** 2))

    return lat, lon_360_to_180(lon) if geodetic else lon, h


def llh2xyz(*llh) -> t.Tuple[float, float, float]:
    """
    Convert LLH (latitude, longitude, height) to ECEF (X, Y, Z)
    using ITRF2020 Ellipsoid.

    :param llh: A 3-tuple or 3 separate parameters, e.g. llh2xyz(lat, lon, h) or llh2xyz((lat, lon, h))
    :returns: (x, y, z) in meters
    """
    a_e = 6378.137e3  # semi-major axis in meters
    f_e = 1 / 298.257222101  # flattening (ITRF2020)
    radians_per_degree = atan2(1, 1) / 45  # inverse of your radians2degree

    # allow llh2xyz(lat, lon, h) or llh2xyz((lat, lon, h))
    llh = llh[0] if len(llh) == 1 else llh
    lat, lon, h = llh

    # convert to radians
    phi = lat * radians_per_degree
    lam = lon * radians_per_degree

    e2 = f_e * (2 - f_e)
    sin_phi = sin(phi)
    cos_phi = cos(phi)
    sin_lam = sin(lam)
    cos_lam = cos(lam)

    # prime vertical radius of curvature
    N = a_e / sqrt(1 - e2 * sin_phi**2)

    # ECEF coordinates
    x = (N + h) * cos_phi * cos_lam
    y = (N + h) * cos_phi * sin_lam
    z = ((1 - e2) * N + h) * sin_phi

    return x, y, z


def convert_9to4(text: str, name: str) -> str:
    """
    In any text convert the 9 character string to the equivalent 4 character site name.
    """
    return re.compile(re.escape(name), re.IGNORECASE).sub(
        lambda match: match.group(0)[0:4], text
    )


def convert_4to9(text: str, name: str) -> str:
    """
    In any text convert the 4 character string to the equivalent 9 character site name.
    """

    def match_case(match: str) -> str:
        if match.isupper():
            return name.upper()
        elif match.islower():
            return name.lower()
        return name

    return re.compile(re.escape(name[0:4]), re.IGNORECASE).sub(match_case, text)


def transliterate(unicode_str: str) -> str:
    """
    Transliterate a string that potentially contains multi-byte ASCII characters to its closest
    ASCII equivalent if one exists.
    """
    import unicodedata

    return unicodedata.normalize("NFKD", unicode_str).encode("ascii", "ignore").decode()
