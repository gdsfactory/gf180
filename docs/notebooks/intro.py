# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Layout (DEPRECATED)
#
# > **DEPRECATION NOTICE**: The `gf180` package is deprecated and will be removed in a future version. Please use the `gf180mcu` package instead.
# > 
# > This notebook is kept for reference only and may contain outdated information.
# >
# > **Please visit the [gf180mcu documentation](https://gdsfactory.github.io/gf180mcu/) for up-to-date notebooks.**
# 
# ## Layout driven flow using gf180mcu (recommended)
#
# You should import the PDK from gf180mcu and layout any of the standard cells

# %%
# Recommended approach using gf180mcu directly
import gf180mcu

# Create components using gf180mcu
c = gf180mcu.diode_dw2ps()
c.plot()

# %% [markdown]
# ## Legacy approach using gf180 (deprecated)
#
# While still supported for backwards compatibility, this approach is deprecated and will show warnings:

# %%
# Legacy/deprecated approach (generates deprecation warning)
import gf180

# This still works but is redirected to gf180mcu internally
c = gf180.diode_dw2ps()
c.plot()
