# Copyright 2022 GlobalFoundries PDK Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

########################################################################################################################
# Diode Generator for GF180MCU
########################################################################################################################

import pya

from .draw_diode import (
    draw_diode_dw2ps,
    draw_diode_nd2ps,
    draw_diode_nw2ps,
    draw_diode_pd2nw,
    draw_diode_pw2dw,
    draw_sc_diode,
)

np_l = 0.36
np_w = 0.36

pn_l = 0.36
pn_w = 0.36

nwp_l = 0.36
nwp_w = 0.36

diode_pw2dw_l = 0.36
diode_pw2dw_w = 0.36

diode_dw2ps_l = 0.36
diode_dw2ps_w = 0.36

sc_l = 1
sc_w = 0.62


class diode_nd2ps(pya.PCellDeclarationHelper):
    """N+/LVPWELL diode (Outside DNWELL) Generator for GF180MCU."""

    def __init__(self) -> None:
        # Initializing super class.
        super().__init__()

        # ===================== PARAMETERS DECLARATIONS =====================
        self.param("deepnwell", self.TypeBoolean, "Deep NWELL", default=0)
        self.param("pcmpgr", self.TypeBoolean, "Guard Ring", default=0)
        self.Type_handle = self.param("volt", self.TypeList, "Voltage area")
        self.Type_handle.add_choice("3.3V", "3.3V")
        self.Type_handle.add_choice("5/6V", "5/6V")

        self.param("la", self.TypeDouble, "Length", default=np_l, unit="um")
        self.param("wa", self.TypeDouble, "Width", default=np_w, unit="um")
        self.param("cw", self.TypeDouble, "Cathode Width", default=np_w, unit="um")
        self.param("area", self.TypeDouble, "Area", readonly=True, unit="um^2")
        self.param("perim", self.TypeDouble, "Perimeter", readonly=True, unit="um")

        self.param("label", self.TypeBoolean, "Labels", default=0)

        self.param("p_label", self.TypeString, "plus label", default="")

        self.param("n_label", self.TypeString, "minus label", default="")

    def display_text_impl(self) -> str:
        # Provide a descriptive text for the cell
        return f"diode_nd2ps(L={self.la:.3f},W=" + f"{self.wa:.3f}" + ")"

    def coerce_parameters_impl(self) -> None:
        # We employ coerce_parameters_impl to decide whether the handle or the numeric parameter has changed.
        #  We also update the numerical value or the shape, depending on which on has not changed.
        self.area = self.wa * self.la
        self.perim = 2 * (self.wa + self.la)
        # w,l must be larger or equal than min. values.
        self.la = max(self.la, np_l)
        self.wa = max(self.wa, np_w)
        self.cw = max(self.cw, np_w)

    def can_create_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we can use any shape which
        # has a finite bounding box
        return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()

    def parameters_from_shape_impl(self) -> None:
        # Implement the "Create PCell from shape" protocol: we set r and l from the shape's
        # bounding box width and layer
        self.r = self.shape.bbox().width() * self.layout.dbu / 2
        self.la = self.layout.get_info(self.laayer)

    def transformation_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we use the dcenter of the shape's
        # bounding box to determine the transformation
        return pya.Trans(self.shape.bbox().dcenter())

    def produce_impl(self) -> None:
        np_instance = draw_diode_nd2ps(
            self.layout,
            la=self.la,
            wa=self.wa,
            cw=self.cw,
            volt=self.volt,
            deepnwell=self.deepnwell,
            pcmpgr=self.pcmpgr,
            label=self.label,
            p_label=self.p_label,
            n_label=self.n_label,
        )
        write_cells = pya.CellInstArray(
            np_instance.cell_index(),
            pya.Trans(pya.Point(0, 0)),
            pya.Vector(0, 0),
            pya.Vector(0, 0),
            1,
            1,
        )

        self.cell.insert(write_cells)
        self.cell.flatten(1)


class diode_pd2nw(pya.PCellDeclarationHelper):
    """P+/Nwell diode (Outside DNWELL) Generator for GF180MCU."""

    def __init__(self) -> None:
        # Initializing super class.
        super().__init__()

        # ===================== PARAMETERS DECLARATIONS =====================
        self.param("deepnwell", self.TypeBoolean, "Deep NWELL", default=0)
        self.param("pcmpgr", self.TypeBoolean, "Guard Ring", default=0)
        self.Type_handle = self.param("volt", self.TypeList, "Voltage area")
        self.Type_handle.add_choice("3.3V", "3.3V")
        self.Type_handle.add_choice("5/6V", "5/6V")

        self.param("la", self.TypeDouble, "Length", default=pn_l, unit="um")
        self.param("wa", self.TypeDouble, "Width", default=pn_w, unit="um")
        self.param("cw", self.TypeDouble, "Cathode Width", default=np_w, unit="um")
        self.param("area", self.TypeDouble, "Area", readonly=True, unit="um^2")
        self.param("perim", self.TypeDouble, "Perimeter", readonly=True, unit="um")

        self.param("label", self.TypeBoolean, "Labels", default=0)

        self.param("p_label", self.TypeString, "plus label", default="")

        self.param("n_label", self.TypeString, "minus label", default="")

    def display_text_impl(self) -> str:
        # Provide a descriptive text for the cell
        return f"diode_pd2nw(L={self.la:.3f},W=" + f"{self.wa:.3f}" + ")"

    def coerce_parameters_impl(self) -> None:
        # We employ coerce_parameters_impl to decide whether the handle or the numeric parameter has changed.
        #  We also update the numerical value or the shape, depending on which on has not changed.
        self.area = self.wa * self.la
        self.perim = 2 * (self.wa + self.la)
        # w,l must be larger or equal than min. values.
        self.la = max(self.la, pn_l)
        self.wa = max(self.wa, pn_w)

    def can_create_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we can use any shape which
        # has a finite bounding box
        return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()

    def parameters_from_shape_impl(self) -> None:
        # Implement the "Create PCell from shape" protocol: we set r and l from the shape's
        # bounding box width and layer
        self.r = self.shape.bbox().width() * self.layout.dbu / 2
        self.la = self.layout.get_info(self.laayer)

    def transformation_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we use the dcenter of the shape's
        # bounding box to determine the transformation
        return pya.Trans(self.shape.bbox().dcenter())

    def produce_impl(self) -> None:
        np_instance = draw_diode_pd2nw(
            self.layout,
            la=self.la,
            wa=self.wa,
            cw=self.cw,
            volt=self.volt,
            deepnwell=self.deepnwell,
            pcmpgr=self.pcmpgr,
            label=self.label,
            p_label=self.p_label,
            n_label=self.n_label,
        )
        write_cells = pya.CellInstArray(
            np_instance.cell_index(),
            pya.Trans(pya.Point(0, 0)),
            pya.Vector(0, 0),
            pya.Vector(0, 0),
            1,
            1,
        )

        self.cell.insert(write_cells)
        self.cell.flatten(1)


class diode_nw2ps(pya.PCellDeclarationHelper):
    """Nwell/Psub diode Generator for GF180MCU."""

    def __init__(self) -> None:
        # Initializing super class.
        super().__init__()

        # ===================== PARAMETERS DECLARATIONS =====================
        self.Type_handle = self.param("volt", self.TypeList, "Voltage area")
        self.Type_handle.add_choice("3.3V", "3.3V")
        self.Type_handle.add_choice("5/6V", "5/6V")

        self.param("la", self.TypeDouble, "Length", default=nwp_l, unit="um")
        self.param("wa", self.TypeDouble, "Width", default=nwp_w, unit="um")
        self.param("cw", self.TypeDouble, "Cathode Width", default=np_w, unit="um")
        self.param("area", self.TypeDouble, "Area", readonly=True, unit="um^2")
        self.param("perim", self.TypeDouble, "Perimeter", readonly=True, unit="um")

        self.param("label", self.TypeBoolean, "Labels", default=0)

        self.param("p_label", self.TypeString, "plus label", default="")

        self.param("n_label", self.TypeString, "minus label", default="")

    def display_text_impl(self) -> str:
        # Provide a descriptive text for the cell
        return f"diode_nw2ps(L={self.la:.3f},W=" + f"{self.wa:.3f}" + ")"

    def coerce_parameters_impl(self) -> None:
        # We employ coerce_parameters_impl to decide whether the handle or the numeric parameter has changed.
        #  We also update the numerical value or the shape, depending on which on has not changed.
        self.area = self.wa * self.la
        self.perim = 2 * (self.wa + self.la)
        # w,l must be larger or equal than min. values.
        self.la = max(self.la, nwp_l)
        self.wa = max(self.wa, nwp_w)
        self.cw = max(self.cw, nwp_w)

    def can_create_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we can use any shape which
        # has a finite bounding box
        return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()

    def parameters_from_shape_impl(self) -> None:
        # Implement the "Create PCell from shape" protocol: we set r and l from the shape's
        # bounding box width and layer
        self.r = self.shape.bbox().width() * self.layout.dbu / 2
        self.la = self.layout.get_info(self.laayer)

    def transformation_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we use the dcenter of the shape's
        # bounding box to determine the transformation
        return pya.Trans(self.shape.bbox().dcenter())

    def produce_impl(self) -> None:
        nwp_instance = draw_diode_nw2ps(
            self.layout,
            la=self.la,
            wa=self.wa,
            cw=self.cw,
            volt=self.volt,
            label=self.label,
            p_label=self.p_label,
            n_label=self.n_label,
        )
        write_cells = pya.CellInstArray(
            nwp_instance.cell_index(),
            pya.Trans(pya.Point(0, 0)),
            pya.Vector(0, 0),
            pya.Vector(0, 0),
            1,
            1,
        )

        self.cell.insert(write_cells)
        self.cell.flatten(1)


class diode_pw2dw(pya.PCellDeclarationHelper):
    """LVPWELL/DNWELL diode Generator for GF180MCU."""

    def __init__(self) -> None:
        # Initializing super class.
        super().__init__()

        # ===================== PARAMETERS DECLARATIONS =====================
        self.param("pcmpgr", self.TypeBoolean, "Guard Ring", default=0)
        self.Type_handle = self.param("volt", self.TypeList, "Voltage area")
        self.Type_handle.add_choice("3.3V", "3.3V")
        self.Type_handle.add_choice("5/6V", "5/6V")

        self.param("la", self.TypeDouble, "Length", default=diode_pw2dw_l, unit="um")
        self.param("wa", self.TypeDouble, "Width", default=diode_pw2dw_w, unit="um")
        self.param("cw", self.TypeDouble, "Cathode Width", default=np_w, unit="um")
        self.param("area", self.TypeDouble, "Area", readonly=True, unit="um^2")
        self.param("perim", self.TypeDouble, "Perimeter", readonly=True, unit="um")

        self.param("label", self.TypeBoolean, "Labels", default=0)

        self.param("p_label", self.TypeString, "plus label", default="")

        self.param("n_label", self.TypeString, "minus label", default="")

    def display_text_impl(self) -> str:
        # Provide a descriptive text for the cell
        return f"diode_pw2dw(L={self.la:.3f},W=" + f"{self.wa:.3f}" + ")"

    def coerce_parameters_impl(self) -> None:
        # We employ coerce_parameters_impl to decide whether the handle or the numeric parameter has changed.
        #  We also update the numerical value or the shape, depending on which on has not changed.
        self.area = self.wa * self.la
        self.perim = 2 * (self.wa + self.la)
        # w,l must be larger or equal than min. values.
        self.la = max(self.la, diode_pw2dw_l)
        self.wa = max(self.wa, diode_pw2dw_w)
        self.cw = max(self.cw, diode_pw2dw_w)

    def can_create_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we can use any shape which
        # has a finite bounding box
        return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()

    def parameters_from_shape_impl(self) -> None:
        # Implement the "Create PCell from shape" protocol: we set r and l from the shape's
        # bounding box width and layer
        self.r = self.shape.bbox().width() * self.layout.dbu / 2
        self.la = self.layout.get_info(self.laayer)

    def transformation_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we use the dcenter of the shape's
        # bounding box to determine the transformation
        return pya.Trans(self.shape.bbox().dcenter())

    def produce_impl(self) -> None:
        diode_pw2dw_instance = draw_diode_pw2dw(
            self.layout,
            la=self.la,
            wa=self.wa,
            cw=self.cw,
            volt=self.volt,
            pcmpgr=self.pcmpgr,
            label=self.label,
            p_label=self.p_label,
            n_label=self.n_label,
        )
        write_cells = pya.CellInstArray(
            diode_pw2dw_instance.cell_index(),
            pya.Trans(pya.Point(0, 0)),
            pya.Vector(0, 0),
            pya.Vector(0, 0),
            1,
            1,
        )

        self.cell.insert(write_cells)
        self.cell.flatten(1)


class diode_dw2ps(pya.PCellDeclarationHelper):
    """LVPWELL/DNWELL diode Generator for GF180MCU."""

    def __init__(self) -> None:
        # Initializing super class.
        super().__init__()

        # ===================== PARAMETERS DECLARATIONS =====================
        self.param("pcmpgr", self.TypeBoolean, "Guard Ring", default=0)
        self.Type_handle = self.param("volt", self.TypeList, "Voltage area")
        self.Type_handle.add_choice("3.3V", "3.3V")
        self.Type_handle.add_choice("5/6V", "5/6V")

        self.param("la", self.TypeDouble, "Length", default=diode_dw2ps_l, unit="um")
        self.param("wa", self.TypeDouble, "Width", default=diode_dw2ps_w, unit="um")
        self.param("cw", self.TypeDouble, "Cathode Width", default=np_w, unit="um")
        self.param("area", self.TypeDouble, "Area", readonly=True, unit="um^2")
        self.param("perim", self.TypeDouble, "Perimeter", readonly=True, unit="um")

        self.param("label", self.TypeBoolean, "Labels", default=0)

        self.param("p_label", self.TypeString, "plus label", default="")

        self.param("n_label", self.TypeString, "minus label", default="")

    def display_text_impl(self) -> str:
        # Provide a descriptive text for the cell
        return f"diode_dw2ps(L={self.la:.3f},W=" + f"{self.wa:.3f}" + ")"

    def coerce_parameters_impl(self) -> None:
        # We employ coerce_parameters_impl to decide whether the handle or the numeric parameter has changed.
        #  We also update the numerical value or the shape, depending on which on has not changed.
        self.area = self.wa * self.la
        self.perim = 2 * (self.wa + self.la)
        # w,l must be larger or equal than min. values.
        self.la = max(self.la, diode_dw2ps_l)
        self.wa = max(self.wa, diode_dw2ps_w)
        self.cw = max(self.cw, diode_dw2ps_w)

    def can_create_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we can use any shape which
        # has a finite bounding box
        return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()

    def parameters_from_shape_impl(self) -> None:
        # Implement the "Create PCell from shape" protocol: we set r and l from the shape's
        # bounding box width and layer
        self.r = self.shape.bbox().width() * self.layout.dbu / 2
        self.la = self.layout.get_info(self.laayer)

    def transformation_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we use the dcenter of the shape's
        # bounding box to determine the transformation
        return pya.Trans(self.shape.bbox().dcenter())

    def produce_impl(self) -> None:
        diode_dw2ps_instance = draw_diode_dw2ps(
            self.layout,
            la=self.la,
            wa=self.wa,
            cw=self.cw,
            volt=self.volt,
            pcmpgr=self.pcmpgr,
            label=self.label,
            p_label=self.p_label,
            n_label=self.n_label,
        )
        write_cells = pya.CellInstArray(
            diode_dw2ps_instance.cell_index(),
            pya.Trans(pya.Point(0, 0)),
            pya.Vector(0, 0),
            pya.Vector(0, 0),
            1,
            1,
        )

        self.cell.insert(write_cells)
        self.cell.flatten(1)


class sc_diode(pya.PCellDeclarationHelper):
    """N+/LVPWELL diode (Outside DNWELL) Generator for GF180MCU."""

    def __init__(self) -> None:
        # Initializing super class.
        super().__init__()

        # ===================== PARAMETERS DECLARATIONS =====================
        self.param("pcmpgr", self.TypeBoolean, "Guard Ring", default=0)
        self.param("la", self.TypeDouble, "Length", default=sc_l, unit="um")
        self.param(
            "wa", self.TypeDouble, "Width", default=sc_w, unit="um", readonly=True
        )
        self.param("cw", self.TypeDouble, "Cathode Width", default=np_w, unit="um")
        self.param("m", self.TypeDouble, "no. of fingers", default=4)
        self.param("area", self.TypeDouble, "Area", readonly=True, unit="um^2")
        self.param("perim", self.TypeDouble, "Perimeter", readonly=True, unit="um")

        self.param("label", self.TypeBoolean, "Labels", default=0)

        self.param("p_label", self.TypeString, "plus label", default="")

        self.param("n_label", self.TypeString, "minus label", default="")

    def display_text_impl(self) -> str:
        # Provide a descriptive text for the cell
        return f"sc_diode(L={self.la:.3f},W=" + f"{self.wa:.3f}" + ")"

    def coerce_parameters_impl(self) -> None:
        # We employ coerce_parameters_impl to decide whether the handle or the numeric parameter has changed.
        #  We also update the numerical value or the shape, depending on which on has not changed.
        self.area = self.wa * self.la
        self.perim = 2 * (self.wa + self.la)
        # w,l must be larger or equal than min. values.
        self.la = max(self.la, sc_l)
        if (self.wa) != sc_w:
            self.wa = sc_w

    def can_create_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we can use any shape which
        # has a finite bounding box
        return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()

    def parameters_from_shape_impl(self) -> None:
        # Implement the "Create PCell from shape" protocol: we set r and l from the shape's
        # bounding box width and layer
        self.r = self.shape.bbox().width() * self.layout.dbu / 2
        self.la = self.layout.get_info(self.laayer)

    def transformation_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we use the dcenter of the shape's
        # bounding box to determine the transformation
        return pya.Trans(self.shape.bbox().dcenter())

    def produce_impl(self) -> None:
        sc_instance = draw_sc_diode(
            self.layout,
            la=self.la,
            wa=self.wa,
            cw=self.cw,
            m=self.m,
            pcmpgr=self.pcmpgr,
            label=self.label,
            p_label=self.p_label,
            n_label=self.n_label,
        )
        write_cells = pya.CellInstArray(
            sc_instance.cell_index(),
            pya.Trans(pya.Point(0, 0)),
            pya.Vector(0, 0),
            pya.Vector(0, 0),
            1,
            1,
        )

        self.cell.insert(write_cells)
        self.cell.flatten(1)
