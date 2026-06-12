# encoding: utf-8
"""Optional, standards-based formatting of EXIF values.

``inspect_image()`` returns raw EXIF on purpose. This module turns those raw
values into human-readable strings using only standardized EXIF semantics:
units (``f/1.8``, ``50 mm``, ``1/250 s``), the spec's enumerations (Orientation,
Flash, ExposureProgram, ...) and combined GPS coordinates. It is a convenience
for callers that want a ready-to-display view; tag labelling and layout remain
the caller's job. Values without a known standardized representation are passed
through unchanged (as ``str``).
"""
from typing import Dict

# -- Standardized EXIF/TIFF enumerations (value -> meaning) ------------------
_ENUMS = {
    'Orientation': {
        1: 'Normal', 2: 'Mirrored horizontal', 3: 'Rotated 180\u00b0',
        4: 'Mirrored vertical', 5: 'Mirrored, rotated 90\u00b0 CCW',
        6: 'Rotated 90\u00b0 CW', 7: 'Mirrored, rotated 90\u00b0 CW',
        8: 'Rotated 90\u00b0 CCW'},
    'ResolutionUnit': {1: 'None', 2: 'inches', 3: 'cm'},
    'ExposureProgram': {
        0: 'Not defined', 1: 'Manual', 2: 'Normal', 3: 'Aperture priority',
        4: 'Shutter priority', 5: 'Creative', 6: 'Action', 7: 'Portrait',
        8: 'Landscape'},
    'MeteringMode': {
        0: 'Unknown', 1: 'Average', 2: 'Center-weighted', 3: 'Spot',
        4: 'Multi-spot', 5: 'Pattern', 6: 'Partial', 255: 'Other'},
    'LightSource': {
        0: 'Unknown', 1: 'Daylight', 2: 'Fluorescent',
        3: 'Tungsten', 4: 'Flash', 9: 'Fine weather', 10: 'Cloudy',
        11: 'Shade', 17: 'Standard light A', 18: 'Standard light B',
        19: 'Standard light C', 255: 'Other'},
    'WhiteBalance': {0: 'Auto', 1: 'Manual'},
    'ExposureMode': {0: 'Auto', 1: 'Manual', 2: 'Auto bracket'},
    'ColorSpace': {1: 'sRGB', 65535: 'Uncalibrated'},
    'SceneCaptureType': {0: 'Standard', 1: 'Landscape', 2: 'Portrait',
                         3: 'Night'},
    'Contrast': {0: 'Normal', 1: 'Soft', 2: 'Hard'},
    'Saturation': {0: 'Normal', 1: 'Low', 2: 'High'},
    'Sharpness': {0: 'Normal', 1: 'Soft', 2: 'Hard'},
    'SensingMethod': {1: 'Not defined', 2: 'One-chip color area', 3: 'Two-chip '
                      'color area', 4: 'Three-chip color area',
                      5: 'Color sequential area', 7: 'Trilinear',
                      8: 'Color sequential linear'},
}

_FLASH = {
    0x00: 'Did not fire', 0x01: 'Fired',
    0x05: 'Fired, no return', 0x07: 'Fired, return detected',
    0x08: 'On, did not fire', 0x09: 'On, fired',
    0x10: 'Off, did not fire', 0x18: 'Auto, did not fire',
    0x19: 'Auto, fired', 0x1D: 'Auto, fired, no return',
    0x1F: 'Auto, fired, return detected',
}


def format_exif(exif: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, str]]:
    """Return a display-ready copy of grouped EXIF (``ImageMetadata.exif``).

    The structure (sections and order) is preserved; GPS is condensed into
    readable ``Latitude``/``Longitude``/``Altitude`` entries.
    """
    result: Dict[str, Dict[str, str]] = {}
    for section, tags in exif.items():
        formatted = _format_gps(tags) if section == 'gps' else {
            name: _format_value(name, value) for name, value in tags.items()}
        if formatted:
            result[section] = formatted
    return result


def _format_value(name: str, value) -> str:
    if name in _ENUMS:
        try:
            return _ENUMS[name].get(int(value), str(value))
        except (TypeError, ValueError):
            return str(value)
    if name == 'Flash':
        try:
            v = int(value)
            return _FLASH.get(v, 'Fired' if v & 1 else 'Did not fire')
        except (TypeError, ValueError):
            return str(value)
    try:
        if name == 'FNumber':
            return f'f/{float(value):g}'
        if name == 'FocalLength':
            return f'{float(value):g} mm'
        if name == 'FocalLengthIn35mmFilm':
            return f'{int(value)} mm'
        if name == 'ExposureTime':
            v = float(value)
            return f'1/{round(1 / v)} s' if 0 < v < 1 else f'{v:g} s'
        if name == 'ExposureBiasValue':
            return f'{float(value):+g} EV'
    except (TypeError, ValueError, ZeroDivisionError):
        return str(value)
    return str(value)


# -- GPS ---------------------------------------------------------------------
_GPS_CONSUMED = {'GPSLatitude', 'GPSLatitudeRef', 'GPSLongitude',
                 'GPSLongitudeRef', 'GPSAltitude', 'GPSAltitudeRef'}


def _format_gps(gps: Dict[str, object]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    lat = _dms(gps.get('GPSLatitude'), gps.get('GPSLatitudeRef'))
    if lat:
        out['Latitude'] = lat
    lon = _dms(gps.get('GPSLongitude'), gps.get('GPSLongitudeRef'))
    if lon:
        out['Longitude'] = lon
    if gps.get('GPSAltitude') is not None:
        try:
            ref = gps.get('GPSAltitudeRef', 0)
            below = ref in (1, b'\x01', '1')
            out['Altitude'] = f"{'-' if below else ''}{float(gps['GPSAltitude']):g} m"
        except (TypeError, ValueError):
            pass
    # keep any remaining GPS tags (timestamp, direction, ...) as-is
    for name, value in gps.items():
        if name not in _GPS_CONSUMED:
            out[name] = str(value)
    return out


def _dms(coord, ref) -> str:
    if not coord:
        return ''
    try:
        d, m, s = float(coord[0]), float(coord[1]), float(coord[2])
    except (TypeError, ValueError, IndexError):
        return str(coord)
    hemi = ref.strip() if isinstance(ref, str) else str(ref or '')
    return f"{int(d)}\u00b0{int(m)}\u2032{s:g}\u2033 {hemi}".strip()