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
# # Layout
#
# ## Layout driven flow
#
# You can import the PDK and layout any of the standard cells

# %%
import gf180

# %%
c = gf180.diode_dw2ps()
c.plot()
