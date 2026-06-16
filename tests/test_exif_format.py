#!/usr/bin/env python3
from optimize_images.api import format_exif


def test_units_and_enums():
    exif = {
        'image': {'Make': 'ACME', 'Orientation': 6, 'ResolutionUnit': 2},
        'camera': {'FNumber': 1.8, 'FocalLength': 50.0,
                   'FocalLengthIn35mmFilm': 75, 'ExposureTime': 0.004,
                   'ExposureBiasValue': -0.33, 'Flash': 1,
                   'ExposureProgram': 3, 'MeteringMode': 5, 'ColorSpace': 1},
    }
    out = format_exif(exif)
    assert out['image']['Make'] == 'ACME'           # unknown -> passthrough
    assert out['image']['Orientation'] == 'Rotated 90\u00b0 CW'
    assert out['image']['ResolutionUnit'] == 'inches'
    assert out['camera']['FNumber'] == 'f/1.8'
    assert out['camera']['FocalLength'] == '50 mm'
    assert out['camera']['FocalLengthIn35mmFilm'] == '75 mm'
    assert out['camera']['ExposureTime'] == '1/250 s'
    assert out['camera']['ExposureBiasValue'] == '-0.33 EV'
    assert out['camera']['Flash'] == 'Fired'
    assert out['camera']['ExposureProgram'] == 'Aperture priority'
    assert out['camera']['MeteringMode'] == 'Pattern'
    assert out['camera']['ColorSpace'] == 'sRGB'


def test_gps_is_combined():
    exif = {
        'gps': {
            'GPSLatitudeRef': 'N', 'GPSLatitude': (41.0, 33.0, 19.42),
            'GPSLongitudeRef': 'W', 'GPSLongitude': (8.0, 24.0, 10.83),
            'GPSAltitude': 123.0, 'GPSAltitudeRef': 0,
        }
    }
    gps = format_exif(exif)['gps']
    assert gps['Latitude'] == "41\u00b033\u203219.42\u2033 N"
    assert gps['Longitude'] == "8\u00b024\u203210.83\u2033 W"
    assert gps['Altitude'] == '123 m'
    # the raw component/ref tags should have been consumed
    assert 'GPSLatitude' not in gps and 'GPSLatitudeRef' not in gps