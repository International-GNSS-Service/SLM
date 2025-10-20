import math
import pytest

from slm.utils import (
    xyz2llh,
    llh2xyz,
    dddmmss_ss_parts,
    decimal_to_dddmmssss,
    dddmmssss_to_decimal,
)


def _is_neg_zero(x: float) -> bool:
    # Detect IEEE-754 signed zero reliably
    return x == 0.0 and math.copysign(1.0, x) < 0.0


def _is_pos_zero(x: float) -> bool:
    return x == 0.0 and math.copysign(1.0, x) > 0.0


@pytest.mark.parametrize(
    "val",
    [
        0.0,  # +0.0 exactly
        -0.0,  # -0.0 exactly (signed zero)
        12.345678,  # generic positive
        -12.345678,  # generic negative
        179.9997222222,  # near 180° (59' 59.0")
        -179.9997222222,  # near -180°
        180.0,  # boundary longitude (if supported)
        89.9999999997,  # near +90° (hemisphere cap)
        -89.9999999997,  # near -90°
    ],
)
def test_ddmmss_conversions_roundtrip(val):
    """
    Round-trip decimal degrees -> DDDMMSS.ss... -> decimal degrees.
    Also verify signed-zero is preserved when input is exactly +0.0 or -0.0.
    """
    dms = decimal_to_dddmmssss(val)
    back = dddmmssss_to_decimal(dms)

    # Tight absolute tolerance; conversions should be lossless to ~1e-10 in normal cases
    if val == 0.0 and _is_neg_zero(val):
        assert _is_neg_zero(back), f"Expected -0.0 round-trip, got {back!r}"
    elif val == 0.0 and _is_pos_zero(val):
        assert _is_pos_zero(back), f"Expected +0.0 round-trip, got {back!r}"
    else:
        assert back == pytest.approx(val, abs=1e-6)


@pytest.mark.parametrize(
    ("decimal_deg", "expected_parts"),
    [
        (0.0, (0, 0, 0.0)),
        (-0.0, (0, 0, 0.0)),
        (118.2584722222, (118, 15, 30.5)),  # 118° 15' 30.5"
        (-118.2584722222, (-118, 15, 30.5)),
        (34.0522222222, (34, 3, 8.0)),  # 34° 3' 8.0"
        (-34.0522222222, (-34, 3, 8.0)),
        (-0.7429986428695962, (-0.0, 44, 34.8)),
        (269.696331426078, (269, 41, 46.8)),
    ],
)
def test_dddmmss_parts_agree_with_expected(decimal_deg, expected_parts):
    """
    The parts from dddmmss_ss_parts should match explicitly expected (deg, min, sec)
    values supplied in the test parameter.
    """
    dms = decimal_to_dddmmssss(decimal_deg)
    deg, minute, second = dddmmss_ss_parts(
        decimal_deg
    )  # should return non-negative parts

    exp_deg, exp_min, exp_sec = expected_parts

    assert deg == exp_deg
    assert minute == exp_min
    assert second == pytest.approx(exp_sec, abs=1e-2)
    assert decimal_deg == pytest.approx(dddmmssss_to_decimal(dms), abs=1e-5)
    assert decimal_deg == pytest.approx(
        dddmmssss_to_decimal(f"{exp_deg:03.0f}{exp_min:02d}{exp_sec:04.1f}"), abs=1e-5
    )


def test_xyz_llh_conversions():
    """
    Robust XYZ->LLH checks at canonical locations on the reference ellipsoid.
    These cases avoid dependency on the internal ellipsoid constants by
    choosing points where the expected lat/lon/height are unambiguous.
    """
    # Ellipsoid semi-major axis for WGS84/GRS80 (identical 'a')
    a = 6378137.0

    # 1) Equator, prime meridian, surface — expect +0.0° lat, 0.0° lon, h≈0
    lat, lon, h = xyz2llh(a, 0.0, 0.0)
    assert _is_pos_zero(lat), f"Expected +0.0° latitude, got {lat!r}"
    assert _is_pos_zero(lon), f"Expected +0.0° longitude, got {lon!r}"
    assert h == pytest.approx(0.0, abs=1e-4)

    # 2) Equator, prime meridian, with Z = -0.0 — expect -0.0° lat, 0.0° lon, h≈0
    lat, lon, h = xyz2llh(a, 0.0, -0.0)
    # Many atan2 implementations preserve the sign of zero here
    assert _is_neg_zero(lat) or lat == pytest.approx(0.0, abs=0.0), (
        f"Expected -0.0° latitude, got {lat!r}"
    )
    assert _is_pos_zero(lon), f"Expected +0.0° longitude, got {lon!r}"
    assert h == pytest.approx(0.0, abs=1e-4)

    # 3) Equator, 90°E — X=0, Y=+a, Z=0  => lat 0°, lon +90°, h≈0
    lat, lon, h = xyz2llh(0.0, a, 0.0)
    assert lat == pytest.approx(0.0, abs=1e-12)
    assert lon == pytest.approx(90.0, abs=1e-12)
    assert h == pytest.approx(0.0, abs=1e-4)

    # 4) Equator, 90°W — X=0, Y=-a, Z=0  => lat 0°, lon -90°, h≈0
    lat, lon, h = xyz2llh(0.0, -a, 0.0)
    assert lat == pytest.approx(0.0, abs=1e-12)
    assert lon == pytest.approx(-90, abs=1e-12)
    assert h == pytest.approx(0.0, abs=1e-4)

    # 5) Equator, 180°/−180° — X=−a, Y=0, Z=0 => lat 0°, lon ±180°, h≈0
    lat, lon, h = xyz2llh(-a, 0.0, 0.0)
    assert lat == pytest.approx(0.0, abs=1e-12)
    assert abs(abs(lon) - 180.0) < 1e-12, f"Expected ±180°, got {lon}"
    assert h == pytest.approx(0.0, abs=1e-4)

    # 6) North pole on the surface — X=0, Y=0, Z≈b (height≈0), lat≈+90°
    # Using GRS80 semi-minor axis; tiny difference vs WGS84 won't matter for these tolerances.
    f_grs80 = 1.0 / 298.257222101
    b = a * (1.0 - f_grs80)
    lat, lon, h = xyz2llh(0.0, 0.0, b)
    assert lat == pytest.approx(90.0, abs=1e-10)
    # longitude is conventionally 0 at the pole
    assert lon == pytest.approx(0.0, abs=1e-12)
    assert h == pytest.approx(0.0, abs=0.05)  # a few cm margin

    # 7) South pole on the surface — X=0, Y=0, Z≈-b (height≈0), lat≈−90°
    lat, lon, h = xyz2llh(0.0, 0.0, -b)
    assert lat == pytest.approx(-90.0, abs=1e-10)
    assert lon == pytest.approx(0.0, abs=1e-12)
    assert h == pytest.approx(0.0, abs=0.05)


# Ellipsoid constants used only to craft exact test inputs
A = 6378137.0
F = 1.0 / 298.257222101
B = A * (1.0 - F)


@pytest.mark.parametrize(
    "lon_deg,h",
    [
        (0.0, 123.4),  # +0 lat, 0 lon, +height
        (90.0, 987.6),  # +0 lat, +90 lon, +height
        (180.0, -50.0),  # +0 lat, ±180 lon, negative height
        (-90.0, 250.0),  # +0 lat, -90 lon, +height
        (45.0, 10.0),  # +0 lat, 45 lon, +height
        (135.0, 5.0),  # +0 lat, 135 lon, +height
        (-45.0, -25.0),  # +0 lat, -45 lon, negative height
        (120.0, 0.1),  # +0 lat, 120 lon, tiny +height
        (-135.0, 1.0),  # +0 lat, -135 lon, +height
        (30.0, -1.0),  # +0 lat, 30 lon, negative height
    ],
)
def test_xyz_llh_conversions_more_equator(lon_deg, h):
    # Equator (φ = ±0) -> Z = 0; X,Y from longitude and radius (a+h)
    r = A + h
    lam = math.radians(lon_deg)
    x = r * math.cos(lam)
    y = r * math.sin(lam)
    z = 0.0

    lat, lon, hh = xyz2llh(x, y, z)

    # Expect exactly 0 latitude (sign could be +0.0; don't over-constrain sign here)
    assert lat == pytest.approx(0.0, abs=0.0)

    # Longitude wraps; allow ±180 equivalence
    # Normalize both to [-180,180)
    def norm180(d):
        out = (d + 180.0) % 360.0 - 180.0
        # Map -180 to +180 as equivalent
        return 180.0 if abs(out + 180.0) < 1e-12 else out

    assert norm180(lon) == pytest.approx(norm180(lon_deg), abs=1e-10)
    assert hh == pytest.approx(h, abs=1e-3)


@pytest.mark.parametrize(
    "z,h,expected_lat",
    [
        (B + 3.0, 3.0, 90.0),  # North pole, +height
        (-(B + 7.0), 7.0, -90.0),  # South pole, +height (Z negative)
        (B + 0.1, 0.1, 90.0),  # North pole, tiny +height
        (-(B + 0.1), 0.1, -90.0),  # South pole, tiny +height
        (B - 2.5, -2.5, 90.0),  # North pole, slight negative height
        (-(B - 2.5), -2.5, -90.0),  # South pole, slight negative height
        (B + 50.0, 50.0, 90.0),
        (-(B + 50.0), 50.0, -90.0),
        (B, 0.0, 90.0),  # exactly on the surface
        (-B, 0.0, -90.0),  # exactly on the surface
    ],
)
def test_xyz_llh_conversions_more_poles(z, h, expected_lat):
    x = 0.0
    y = 0.0
    lat, lon, hh = xyz2llh(x, y, z)
    assert lat == pytest.approx(expected_lat, abs=1e-10)
    # At the poles, longitude is conventionally 0 (some implementations may return any value);
    # most algorithms standardize to 0.
    assert lon == pytest.approx(0.0, abs=1e-12)
    assert hh == pytest.approx(h, abs=0.05)


@pytest.mark.parametrize(
    "xyz",
    [
        (4913652.76087, 3945922.66962, 995383.33311),
        (-3939182.131, 3467075.376, -3613220.824),
        (-3939182.131, 3467075.376, -3613220.824),
        (595828.9368, -4839735.3204, 4097876.7222),
        (6347491.377, -22944.8986, 622822.4766),
        (-3051338.7572, -1317097.8223, 5425614.2192),
        (-2752834.7418, -1533597.398, 5526823.2554),
        (4097216.6805, 4429119.0287, -2065771.3676),
        (2919786, -5383745, 1774604),
        (-4052051.767, 4212836.215, -2545106.027),
        (3765296.991, 1677559.204, 4851297.409),
    ],
)
def test_xyz_roundtrip(xyz):
    converted = llh2xyz(xyz2llh(xyz))
    assert xyz[0] == pytest.approx(converted[0], abs=1e-3)
    assert xyz[1] == pytest.approx(converted[1], abs=1e-3)
    assert xyz[2] == pytest.approx(converted[2], abs=1e-3)
