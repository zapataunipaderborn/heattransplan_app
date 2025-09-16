"""
Configuration constants and settings for the Heat Integration Analysis app.
"""

# Map dimensions
MAP_WIDTH = 1500  # widened map (extends to the right)
MAP_HEIGHT = 860  # taller snapshot for more vertical space

# Tile templates for snapshot capture (static)
TILE_TEMPLATES = {
    'OpenStreetMap': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    'Positron': 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    'Satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
}

# Default start location (Universität Paderborn, Warburger Str. 100, 33098 Paderborn)
DEFAULT_START_ADDRESS = "Universität Paderborn, Warburger Str. 100, 33098 Paderborn"
# Approximate coordinates (lat, lon)
DEFAULT_START_COORDS = [51.70814085564164, 8.772155163087213]

# UI Configuration
BOX_FONT_SIZE = 20

# Base layer options
BASE_OPTIONS = ["OpenStreetMap", "Positron", "Satellite", "Blank"]
ANALYZE_OPTIONS = ["OpenStreetMap", "Positron", "Satellite", "Blank"]
