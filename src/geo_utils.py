"""
Coordinate transformation utilities for map functionality.
Web Mercator projection helpers for converting between pixel coordinates and lat/lon.
"""

import math


def snapshot_pixel_to_lonlat(px, py, center_ll, z_level, img_w, img_h):
    """
    Convert pixel coordinates (relative to center) in snapshot to lon/lat using Web Mercator math.
    
    Args:
        px, py: Pixel coordinates
        center_ll: Center coordinates [lat, lon]
        z_level: Zoom level
        img_w, img_h: Image dimensions
        
    Returns:
        tuple: (longitude, latitude)
    """
    def lonlat_to_xy(lon_val, lat_val, z_val):
        lat_rad = math.radians(lat_val)
        n_val = 2.0 ** z_val
        xtile = (lon_val + 180.0) / 360.0 * n_val
        ytile = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n_val
        return xtile, ytile
    
    def xy_to_lonlat(xtile_v, ytile_v, z_val):
        n_val = 2.0 ** z_val
        lon_val = xtile_v / n_val * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile_v / n_val)))
        lat_val = math.degrees(lat_rad)
        return lon_val, lat_val
    
    lon0, lat0 = center_ll
    xtile0, ytile0 = lonlat_to_xy(lon0, lat0, z_level)
    px_per_tile = 256
    dx = px - img_w / 2
    dy = py - img_h / 2
    dxtile = dx / px_per_tile
    dytile = dy / px_per_tile
    xtile = xtile0 + dxtile
    ytile = ytile0 + dytile
    lon_val, lat_val = xy_to_lonlat(xtile, ytile, z_level)
    return lon_val, lat_val


def snapshot_lonlat_to_pixel(lon_val_in, lat_val_in, center_ll, z_level, img_w, img_h):
    """
    Convert lon/lat coordinates to snapshot pixel coordinates.
    
    Args:
        lon_val_in, lat_val_in: Longitude and latitude
        center_ll: Center coordinates [lat, lon]
        z_level: Zoom level
        img_w, img_h: Image dimensions
        
    Returns:
        tuple: (pixel_x, pixel_y)
    """
    def lonlat_to_xy(lon_inner, lat_inner, z_val):
        lat_rad = math.radians(lat_inner)
        n_val = 2.0 ** z_val
        xtile = (lon_inner + 180.0) / 360.0 * n_val
        ytile = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n_val
        return xtile, ytile
    
    lon0, lat0 = center_ll
    xtile0, ytile0 = lonlat_to_xy(lon0, lat0, z_level)
    xtile, ytile = lonlat_to_xy(lon_val_in, lat_val_in, z_level)
    dxtile = xtile - xtile0
    dytile = ytile - ytile0
    px_per_tile = 256
    snapshot_px = img_w / 2 + dxtile * px_per_tile
    snapshot_py = img_h / 2 + dytile * px_per_tile
    return snapshot_px, snapshot_py


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        float: Distance in meters
    """
    R = 6371000  # Earth radius in meters
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c
