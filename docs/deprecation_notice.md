# Deprecation Notice

This package (`gf180`) is deprecated and will be removed in a future version. Please use the `gf180mcu` package instead.

## Migration Guide

To migrate from `gf180` to `gf180mcu`:

1. Replace all imports from `gf180` to `gf180mcu`:
   ```python
   # Old import (deprecated)
   import gf180

   # New import (recommended)
   import gf180mcu
   ```

2. Use the equivalent functions from `gf180mcu`:
   ```python
   # Old usage (deprecated)
   c = gf180.some_component(param1=value1)

   # New usage (recommended)
   c = gf180mcu.some_component(param1=value1)
   ```

All components available in `gf180` are available in `gf180mcu` with the same parameters and functionality.
