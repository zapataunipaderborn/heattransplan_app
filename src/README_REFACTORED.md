# Heat Integration Analysis App - Refactored Structure

This directory contains the refactored Heat Integration Analysis application, organized into logical modules for better maintainability and code organization.

## File Structure

### Core Application
- **`app_refactored.py`** - Main Streamlit application entry point
- **`app.py`** - Original monolithic application (kept for reference)

### Configuration & Constants
- **`config.py`** - Application configuration, constants, and settings
  - Map dimensions and tile templates
  - Default coordinates and addresses
  - UI configuration constants

### Session State Management
- **`session_state.py`** - Session state initialization and management
  - Initialize all session variables
  - State cleanup utilities
  - State validation helpers

### Geographic & Coordinate Utils
- **`geo_utils.py`** - Geographic coordinate transformations
  - Web Mercator projection utilities
  - Pixel to lat/lon conversions
  - Haversine distance calculations

### Map Functionality
- **`map_utils.py`** - Map creation and rendering utilities
  - Folium map creation with different base layers
  - Address geocoding
  - Static map snapshot capture
  - Map rendering with process markers

### User Interface Components
- **`ui_components.py`** - Reusable UI components and styling
  - Custom CSS application
  - Base layer selectors
  - Status bars and headers
  - Process control widgets

### Process Management
- **`process_interface.py`** - Process management UI components
  - Process group rendering
  - Process editor interface
  - Stream management
  - Process connection handling

- **`process_utils.py`** - Process data utilities (existing)
  - Process CRUD operations
  - CSV import/export
  - Data validation

### Visualization
- **`visualization.py`** - Image rendering and process visualization
  - Process box drawing
  - Stream visualization
  - Arrow and connection rendering
  - Image overlay composition

## Key Improvements

### 1. **Separation of Concerns**
- Configuration separated from logic
- UI components isolated from business logic
- Geographic calculations in dedicated module
- Clear separation between data and presentation

### 2. **Modularity**
- Each module has a single, well-defined responsibility
- Functions are focused and reusable
- Easy to test individual components
- Simplified debugging and maintenance

### 3. **Code Organization**
- Related functionality grouped together
- Consistent naming conventions
- Clear module dependencies
- Reduced code duplication

### 4. **Maintainability**
- Easier to locate and modify specific functionality
- Changes in one area don't affect unrelated components
- Clear interfaces between modules
- Better error handling and logging

## Usage

To run the refactored application:

```bash
streamlit run app_refactored.py
```

The refactored version maintains full compatibility with the original functionality while providing a much cleaner and more maintainable codebase.

## Migration Notes

- All original functionality is preserved
- Session state structure remains the same
- UI behavior is identical to the original
- Performance improvements through better code organization
- Easier to extend with new features

## Module Dependencies

```
app_refactored.py
├── config.py
├── session_state.py
│   └── process_utils.py
├── ui_components.py
│   └── config.py
├── map_utils.py
│   └── config.py
├── process_interface.py
│   ├── ui_components.py
│   └── process_utils.py
├── visualization.py
│   ├── config.py
│   └── geo_utils.py
└── geo_utils.py
```

This structure makes it easy to understand the relationships between different parts of the application and ensures clean, maintainable code.
