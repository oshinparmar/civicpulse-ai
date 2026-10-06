"""
CivicPulse AI - Utility Functions
- EXIF GPS metadata extractor
- Haversine distance calculator for 50m spatial clustering
- Base64 image encoding for reliable cross-platform display (SQLite + Streamlit Cloud)
- Indore landmark coordinates
"""

import io
import math
import base64
from typing import Optional, Tuple
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# Default Center Coordinates for Indore, India
INDORE_CENTER = (22.7196, 75.8577)

# Prominent Indore Localities and Landmarks for quick selection
INDORE_LANDMARKS = {
    "Vijay Nagar Square": (22.7533, 75.8937),
    "Rajwada Palace": (22.7186, 75.8554),
    "56 Dukan (Chappan)": (22.7244, 75.8839),
    "Palasia Square": (22.7258, 75.8893),
    "Bhawarkua Square (Student Hub)": (22.6926, 75.8672),
    "Super Corridor (TCS/Infosys)": (22.7820, 75.8280),
    "Khajrana Temple Road": (22.7302, 75.9085),
    "Annapurna Road": (22.6985, 75.8361),
    "Bengali Square (Ring Road)": (22.7135, 75.9110),
    "Geeta Bhawan Square": (22.7169, 75.8856),
    "LIG Colony / AB Road": (22.7380, 75.8920),
    "Airport Road (Devi Ahilya)": (22.7275, 75.8080),
    "Rau Circle (Bypass)": (22.6394, 75.8038),
    "Malwa Mill Square": (22.7305, 75.8715),
    "Bhanwarkuan - IT Park": (22.6830, 75.8690),
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in meters.
    Used to detect duplicate reports within ~50 meters.
    """
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def _convert_to_degrees(value) -> float:
    """Helper function to convert GPS coordinates stored in EXIF format to degrees."""
    d0 = value[0]
    d1 = value[1]
    d2 = value[2]

    deg = float(d0[0]) / float(d0[1]) if isinstance(d0, tuple) else float(d0)
    minute = float(d1[0]) / float(d1[1]) if isinstance(d1, tuple) else float(d1)
    sec = float(d2[0]) / float(d2[1]) if isinstance(d2, tuple) else float(d2)

    return deg + (minute / 60.0) + (sec / 3600.0)


def extract_exif_gps(image: Image.Image) -> Optional[Tuple[float, float]]:
    """
    Extract GPS Latitude and Longitude from image EXIF metadata if present.
    Returns (lat, lon) tuple in decimal degrees, or None.
    """
    try:
        exif_raw = image._getexif()
        if not exif_raw:
            return None

        gps_info = {}
        for tag_id, value in exif_raw.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == "GPSInfo":
                for key in value:
                    sub_tag = GPSTAGS.get(key, key)
                    gps_info[sub_tag] = value[key]

        if not gps_info:
            return None

        lat_raw = gps_info.get("GPSLatitude")
        lat_ref = gps_info.get("GPSLatitudeRef")
        lon_raw = gps_info.get("GPSLongitude")
        lon_ref = gps_info.get("GPSLongitudeRef")

        if lat_raw and lat_ref and lon_raw and lon_ref:
            lat = _convert_to_degrees(lat_raw)
            if lat_ref.upper() != "N":
                lat = -lat

            lon = _convert_to_degrees(lon_raw)
            if lon_ref.upper() != "E":
                lon = -lon

            return round(lat, 6), round(lon, 6)

    except Exception:
        pass

    return None


def image_to_base64_data_uri(image: Image.Image, max_dim: int = 800, quality: int = 85) -> str:
    """
    Resizes image and converts to a compressed JPEG Base64 Data URI string.
    Ensures safe persistence in SQLite and instant inline rendering in Streamlit/Folium.
    """
    img = image.copy()
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize if larger than max_dim to keep DB lightweight and fast
    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"
