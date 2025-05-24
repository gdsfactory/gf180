import inspect
import pathlib

from gdsfactory.serialization import clean_value_json

# Import directly from gf180mcu since gf180 is now just a wrapper
import gf180mcu
from gf180mcu import cells

filepath = pathlib.Path(__file__).parent.absolute() / "cells.rst"

skip = {
    "LIBRARY",
    "circuit_names",
    "component_factory",
    "component_names",
    "container_names",
    "component_names_test_ports",
    "component_names_skip_test",
    "component_names_skip_test_ports",
    "dataclasses",
    "library",
    "waveguide_template",
}

skip_plot: tuple[str, ...] = ("add_fiber_array_siepic",)
skip_settings: tuple[str, ...] = ("flatten", "safe_cell_names")


with open(filepath, "w+") as f:
    f.write(
        """
.. warning::
   **DEPRECATION NOTICE**: The ``gf180`` package is deprecated and will be removed in a future version. Please use the ``gf180mcu`` package instead. All cells and functionality shown here are available in the ``gf180mcu`` package.

.. danger::
   This cell documentation is outdated. Please see the up-to-date cell documentation in the `gf180mcu documentation <https://gdsfactory.github.io/gf180mcu/cells.html>`_.

**This page has been replaced by the equivalent page in the gf180mcu documentation:**

`gf180mcu Cell Documentation <https://gdsfactory.github.io/gf180mcu/cells.html>`_

Please update your bookmarks and references to point to the new cell documentation page.

Here are the parametric cells available in the PDK (via the gf180mcu package)


Cells
=============================
"""
    )

    for name in sorted(cells.keys()):
        if name in skip or name.startswith("_"):
            continue
        print(name)
        sig = inspect.signature(cells[name])
        kwargs = ", ".join(
            [
                f"{p}={clean_value_json(sig.parameters[p].default)!r}"
                for p in sig.parameters
                if isinstance(sig.parameters[p].default, int | float | str | tuple)
                and p not in skip_settings
            ]
        )
        f.write(
            f"""

{name}
----------------------------------------------------

.. admonition:: DEPRECATED
   :class: danger

   This component documentation is deprecated.
   Please use the equivalent component in the gf180mcu package.
   
   See the equivalent component in gf180mcu documentation:
   `gf180mcu.{name} <https://gdsfactory.github.io/gf180mcu/autoapi/gf180mcu/index.html#{name}>`_

"""
        )
