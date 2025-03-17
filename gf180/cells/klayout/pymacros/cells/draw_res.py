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
## Resistor Pcells Generators for Klayout of GF180MCU
########################################################################################################################

import gdsfactory as gf
from gdsfactory.typings import Float2, LayerSpec

from .layers_def import layer
from .via_generator import via_generator, via_stack


def draw_metal_res(
    layout,
    l_res: float = 0.1,
    w_res: float = 0.1,
    res_type: str = "rm1",
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
) -> gf.Component:
    """Usage:-
     used to draw 2-terminal Metal resistor by specifying parameters
    Arguments:-
     layout : Object of layout
     l      : Float of diff length
     w      : Float of diff width.
    """
    c = gf.Component("res_dev")

    m_ext = 0.28

    if res_type == "rm1":
        m_layer = layer["metal1"]
        res_layer = layer["metal1_res"]
        m_label_layer = layer["metal1_label"]
    elif res_type == "rm2":
        m_layer = layer["metal2"]
        res_layer = layer["metal2_res"]
        m_label_layer = layer["metal2_label"]
    elif res_type == "rm3":
        m_layer = layer["metal3"]
        res_layer = layer["metal3_res"]
        m_label_layer = layer["metal3_label"]
    else:
        m_layer = layer["metaltop"]
        res_layer = layer["metal6_res"]
        m_label_layer = layer["metaltop_label"]

    res_mk = c.add_ref(gf.components.rectangle(size=(l_res, w_res), layer=res_layer))

    m_rect = c.add_ref(
        gf.components.rectangle(size=(l_res + (2 * m_ext), w_res), layer=m_layer)
    )
    m_rect.dxmin = res_mk.dxmin - m_ext
    m_rect.dymin = res_mk.dymin

    # labels generation
    if label == 1:
        c.add_label(
            r0_label,
            position=(
                res_mk.dxmin + (res_mk.dxsize / 2),
                res_mk.dymin + (res_mk.dysize / 2),
            ),
            layer=m_label_layer,
        )
        c.add_label(
            r1_label,
            position=(
                m_rect.dxmin + (res_mk.dxmin - m_rect.dxmin) / 2,
                m_rect.dymin + (m_rect.dysize / 2),
            ),
            layer=m_label_layer,
        )

    # creating layout and cell in klayout
    c.write_gds("res_temp.gds")
    layout.read("res_temp.gds")
    cell_name = "res_dev"

    return layout.cell(cell_name)


@gf.cell
def pcmpgr_gen(dn_rect, grw: float = 0.36) -> gf.Component:
    """Return deepnwell guardring.

    Args :
        dn_rect : deepnwell polygon
        grw : guardring width
    """
    c = gf.Component()

    comp_pp_enc: float = 0.16
    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07
    pcmpgr_enc_dn = 2.5

    c_temp_gr = gf.Component("temp_store guard ring")
    rect_pcmpgr_in = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (dn_rect.dxmax - dn_rect.dxmin) + 2 * pcmpgr_enc_dn,
                (dn_rect.dymax - dn_rect.dymin) + 2 * pcmpgr_enc_dn,
            ),
            layer=layer["comp"],
        )
    )
    rect_pcmpgr_in.dmove((dn_rect.dxmin - pcmpgr_enc_dn, dn_rect.dymin - pcmpgr_enc_dn))
    rect_pcmpgr_out = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) + 2 * grw,
                (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) + 2 * grw,
            ),
            layer=layer["comp"],
        )
    )
    rect_pcmpgr_out.dmove((rect_pcmpgr_in.dxmin - grw, rect_pcmpgr_in.dymin - grw))
    c.add_ref(
        gf.boolean(
            A=rect_pcmpgr_out,
            B=rect_pcmpgr_in,
            operation="A-B",
            layer=layer["comp"],
        )
    )  # guardring bulk

    psdm_in = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) - 2 * comp_pp_enc,
                (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) - 2 * comp_pp_enc,
            ),
            layer=layer["pplus"],
        )
    )
    psdm_in.dmove(
        (
            rect_pcmpgr_in.dxmin + comp_pp_enc,
            rect_pcmpgr_in.dymin + comp_pp_enc,
        )
    )
    psdm_out = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (rect_pcmpgr_out.dxmax - rect_pcmpgr_out.dxmin) + 2 * comp_pp_enc,
                (rect_pcmpgr_out.dymax - rect_pcmpgr_out.dymin) + 2 * comp_pp_enc,
            ),
            layer=layer["pplus"],
        )
    )
    psdm_out.dmove(
        (
            rect_pcmpgr_out.dxmin - comp_pp_enc,
            rect_pcmpgr_out.dymin - comp_pp_enc,
        )
    )
    c.add_ref(
        gf.boolean(A=psdm_out, B=psdm_in, operation="A-B", layer=layer["pplus"])
    )  # pplus_draw

    # generating contacts

    c.add_ref(
        via_generator(
            x_range=(
                rect_pcmpgr_in.dxmin + con_size,
                rect_pcmpgr_in.dxmax - con_size,
            ),
            y_range=(rect_pcmpgr_out.dymin, rect_pcmpgr_in.dymin),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # bottom contact

    c.add_ref(
        via_generator(
            x_range=(
                rect_pcmpgr_in.dxmin + con_size,
                rect_pcmpgr_in.dxmax - con_size,
            ),
            y_range=(rect_pcmpgr_in.dymax, rect_pcmpgr_out.dymax),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # upper contact

    c.add_ref(
        via_generator(
            x_range=(rect_pcmpgr_out.dxmin, rect_pcmpgr_in.dxmin),
            y_range=(
                rect_pcmpgr_in.dymin + con_size,
                rect_pcmpgr_in.dymax - con_size,
            ),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # right contact

    c.add_ref(
        via_generator(
            x_range=(rect_pcmpgr_in.dxmax, rect_pcmpgr_out.dxmax),
            y_range=(
                rect_pcmpgr_in.dymin + con_size,
                rect_pcmpgr_in.dymax - con_size,
            ),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # left contact

    comp_m1_in = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(rect_pcmpgr_in.dxsize, rect_pcmpgr_in.dysize),
            layer=layer["metal1"],
        )
    )

    comp_m1_out = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (comp_m1_in.dxsize) + 2 * grw,
                (comp_m1_in.dysize) + 2 * grw,
            ),
            layer=layer["metal1"],
        )
    )
    comp_m1_out.dmove((rect_pcmpgr_in.dxmin - grw, rect_pcmpgr_in.dymin - grw))
    c.add_ref(
        gf.boolean(
            A=rect_pcmpgr_out,
            B=rect_pcmpgr_in,
            operation="A-B",
            layer=layer["metal1"],
        )
    )  # metal1 guardring

    return c


@gf.cell
def plus_res_inst(
    l_res: float = 0.1,
    w_res: float = 0.1,
    res_type: str = "nplus_s",
    sub: bool = False,
    cmp_res_ext: float = 0.1,
    con_enc: float = 0.1,
    cmp_imp_layer: LayerSpec = layer["nplus"],
    sub_imp_layer: LayerSpec = layer["pplus"],
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
    sub_label: str = "",
) -> gf.Component:
    c = gf.Component()

    np_enc_cmp: float = 0.16
    res_mk = c.add_ref(
        gf.components.rectangle(size=(l_res, w_res), layer=layer["res_mk"])
    )

    if "plus_u" in res_type:
        sab_res_ext = 0.22

        sab_rect = c.add_ref(
            gf.components.rectangle(
                size=(res_mk.dxsize, res_mk.dysize + (2 * sab_res_ext)),
                layer=layer["sab"],
            )
        )
        sab_rect.dxmin = res_mk.dxmin
        sab_rect.dymin = res_mk.dymin - sab_res_ext

    cmp = c.add_ref(
        gf.components.rectangle(
            size=(res_mk.dxsize + (2 * cmp_res_ext), res_mk.dysize),
            layer=layer["comp"],
        )
    )
    cmp.dxmin = res_mk.dxmin - cmp_res_ext
    cmp.dymin = res_mk.dymin

    cmp_con = via_stack(
        x_range=(cmp.dxmin, res_mk.dxmin + con_enc),
        y_range=(cmp.dymin, cmp.dymax),
        base_layer=layer["comp"],
        metal_level=1,
    )

    cmp_con_arr = c.add_ref(
        component=cmp_con,
        rows=1,
        columns=2,
        spacing=(cmp_res_ext - con_enc + res_mk.dxsize, 0),
    )  # comp contact array

    # labels generation
    if label == 1:
        c.add_label(
            r0_label,
            position=(
                cmp_con_arr.dxmin + (cmp_con.dxsize / 2),
                cmp_con_arr.dymin + (cmp_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )
        c.add_label(
            r1_label,
            position=(
                cmp_con_arr.dxmax - (cmp_con.dxsize / 2),
                cmp_con_arr.dymin + (cmp_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    cmp_imp = c.add_ref(
        gf.components.rectangle(
            size=(cmp.dxsize + (2 * np_enc_cmp), cmp.dysize + (2 * np_enc_cmp)),
            layer=cmp_imp_layer,
        )
    )
    cmp_imp.dxmin = cmp.dxmin - np_enc_cmp
    cmp_imp.dymin = cmp.dymin - np_enc_cmp

    if sub == 1:
        sub_w: float = 0.36
        sub_rect = c.add_ref(
            gf.components.rectangle(size=(sub_w, w_res), layer=layer["comp"])
        )
        comp_spacing: float = 0.72
        sub_rect.dxmax = cmp.dxmin - comp_spacing
        sub_rect.dymin = cmp.dymin

        # sub_rect contact
        sub_con = c.add_ref(
            via_stack(
                x_range=(sub_rect.dxmin, sub_rect.dxmax),
                y_range=(sub_rect.dymin, sub_rect.dymax),
                base_layer=layer["comp"],
                metal_level=1,
            )
        )

        pp_enc_cmp: float = 0.16
        sub_imp = c.add_ref(
            gf.components.rectangle(
                size=(
                    sub_rect.dxsize + (2 * pp_enc_cmp),
                    cmp.dysize + (2 * pp_enc_cmp),
                ),
                layer=sub_imp_layer,
            )
        )
        sub_imp.dxmin = sub_rect.dxmin - pp_enc_cmp
        sub_imp.dymin = sub_rect.dymin - pp_enc_cmp

        # label generation
        if label == 1:
            c.add_label(
                sub_label,
                position=(
                    sub_con.dxmin + (sub_con.dxsize / 2),
                    sub_con.dymin + (sub_con.dysize / 2),
                ),
                layer=layer["metal1_label"],
            )

    return c


def draw_nplus_res(
    layout,
    l_res: float = 0.1,
    w_res: float = 0.1,
    res_type: str = "nplus_s",
    sub: bool = False,
    deepnwell: bool = False,
    pcmpgr: bool = False,
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
    sub_label: str = "",
) -> gf.Component:
    c = gf.Component("res_dev")

    if res_type == "nplus_s":
        cmp_res_ext = 0.29
        con_enc = 0.07
    else:
        cmp_res_ext = 0.44
        con_enc = 0.0

    # adding res inst
    r_inst = c.add_ref(
        plus_res_inst(
            l_res=l_res,
            w_res=w_res,
            res_type=res_type,
            sub=sub,
            cmp_res_ext=cmp_res_ext,
            con_enc=con_enc,
            cmp_imp_layer=layer["nplus"],
            sub_imp_layer=layer["pplus"],
            label=label,
            r0_label=r0_label,
            r1_label=r1_label,
            sub_label=sub_label,
        )
    )

    if deepnwell == 1:
        lvpwell_enc_cmp = 0.43
        lvpwell = c.add_ref(
            gf.components.rectangle(
                size=(
                    r_inst.dxsize + (2 * lvpwell_enc_cmp),
                    r_inst.dysize + (2 * lvpwell_enc_cmp),
                ),
                layer=layer["lvpwell"],
            )
        )
        lvpwell.dxmin = r_inst.dxmin - lvpwell_enc_cmp
        lvpwell.dymin = r_inst.dymin - lvpwell_enc_cmp

        dn_enc_lvpwell = 2.5
        dn_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    lvpwell.dxsize + (2 * dn_enc_lvpwell),
                    lvpwell.dysize + (2 * dn_enc_lvpwell),
                ),
                layer=layer["dnwell"],
            )
        )
        dn_rect.dxmin = lvpwell.dxmin - dn_enc_lvpwell
        dn_rect.dymin = lvpwell.dymin - dn_enc_lvpwell

        if pcmpgr == 1:
            sub_w = 0.36

            c.add_ref(pcmpgr_gen(dn_rect=dn_rect, grw=sub_w))

    c.write_gds("res_temp.gds")
    layout.read("res_temp.gds")
    cell_name = "res_dev"

    return layout.cell(cell_name)


def draw_pplus_res(
    layout,
    l_res: float = 0.1,
    w_res: float = 0.1,
    res_type: str = "pplus_s",
    sub: bool = False,
    deepnwell: bool = False,
    pcmpgr: bool = False,
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
    sub_label: str = "",
) -> gf.Component:
    c = gf.Component("res_dev")

    if res_type == "pplus_s":
        cmp_res_ext = 0.29
        con_enc = 0.07
    else:
        cmp_res_ext = 0.44
        con_enc = 0.0

    # adding res inst
    r_inst = c.add_ref(
        plus_res_inst(
            l_res=l_res,
            w_res=w_res,
            res_type=res_type,
            sub=1,
            cmp_res_ext=cmp_res_ext,
            con_enc=con_enc,
            cmp_imp_layer=layer["pplus"],
            sub_imp_layer=layer["nplus"],
            label=label,
            r0_label=r0_label,
            r1_label=r1_label,
            sub_label=sub_label,
        )
    )

    if deepnwell == 1:
        dn_enc_ncmp = 0.66
        dn_enc_pcmp = 1.02
        dn_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    r_inst.dxsize + (dn_enc_pcmp + dn_enc_ncmp),
                    r_inst.dysize + (2 * dn_enc_pcmp),
                ),
                layer=layer["dnwell"],
            )
        )
        dn_rect.dxmax = r_inst.dxmax + dn_enc_pcmp
        dn_rect.dymin = r_inst.dymin - dn_enc_pcmp

        if pcmpgr == 1:
            sub_w = 0.36

            c.add_ref(pcmpgr_gen(dn_rect=dn_rect, grw=sub_w))

    else:
        nw_enc_pcmp = 0.6
        nw_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    r_inst.dxsize + (2 * nw_enc_pcmp),
                    r_inst.dysize + (2 * nw_enc_pcmp),
                ),
                layer=layer["nwell"],
            )
        )
        nw_rect.dxmin = r_inst.dxmin - nw_enc_pcmp
        nw_rect.dymin = r_inst.dymin - nw_enc_pcmp

    c.write_gds("res_temp.gds")
    layout.read("res_temp.gds")
    cell_name = "res_dev"

    return layout.cell(cell_name)


@gf.cell
def polyf_res_inst(
    l_res: float = 0.1,
    w_res: float = 0.1,
    res_type: str = "npolyf_s",
    pl_res_ext: float = 0.1,
    con_enc: float = 0.1,
    pl_imp_layer: LayerSpec = layer["nplus"],
    sub_imp_layer: LayerSpec = layer["pplus"],
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
    sub_label: str = "",
) -> gf.Component:
    c = gf.Component()

    sub_w: float = 0.36
    np_enc_poly2 = 0.3
    pp_enc_cmp: float = 0.16
    comp_spacing: float = 0.72
    res_mk = c.add_ref(
        gf.components.rectangle(size=(l_res, w_res), layer=layer["res_mk"])
    )

    if "polyf_u" in res_type:
        sab_res_ext = 0.28

        sab_rect = c.add_ref(
            gf.components.rectangle(
                size=(res_mk.dxsize, res_mk.dysize + (2 * sab_res_ext)),
                layer=layer["sab"],
            )
        )
        sab_rect.dxmin = res_mk.dxmin
        sab_rect.dymin = res_mk.dymin - sab_res_ext

    pl = c.add_ref(
        gf.components.rectangle(
            size=(res_mk.dxsize + (2 * pl_res_ext), res_mk.dysize),
            layer=layer["poly2"],
        )
    )
    pl.dxmin = res_mk.dxmin - pl_res_ext
    pl.dymin = res_mk.dymin

    pl_con = via_stack(
        x_range=(pl.dxmin, res_mk.dxmin + con_enc),
        y_range=(pl.dymin, pl.dymax),
        base_layer=layer["poly2"],
        metal_level=1,
    )

    pl_con_arr = c.add_ref(
        component=pl_con,
        rows=1,
        columns=2,
        spacing=(pl_res_ext - con_enc + res_mk.dxsize, 0),
    )  # comp contact array

    pl_imp = c.add_ref(
        gf.components.rectangle(
            size=(pl.dxsize + (2 * np_enc_poly2), pl.dysize + (2 * np_enc_poly2)),
            layer=pl_imp_layer,
        )
    )
    pl_imp.dxmin = pl.dxmin - np_enc_poly2
    pl_imp.dymin = pl.dymin - np_enc_poly2

    sub_rect = c.add_ref(
        gf.components.rectangle(size=(sub_w, w_res), layer=layer["comp"])
    )
    sub_rect.dxmax = pl.dxmin - comp_spacing
    sub_rect.dymin = pl.dymin

    # sub_rect contact
    sub_con = c.add_ref(
        via_stack(
            x_range=(sub_rect.dxmin, sub_rect.dxmax),
            y_range=(sub_rect.dymin, sub_rect.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
    )

    sub_imp = c.add_ref(
        gf.components.rectangle(
            size=(
                sub_rect.dxsize + (2 * pp_enc_cmp),
                pl.dysize + (2 * pp_enc_cmp),
            ),
            layer=sub_imp_layer,
        )
    )
    sub_imp.dxmin = sub_rect.dxmin - pp_enc_cmp
    sub_imp.dymin = sub_rect.dymin - pp_enc_cmp

    # labels generation
    if label == 1:
        c.add_label(
            r0_label,
            position=(
                pl_con_arr.dxmin + (pl_con.dxsize / 2),
                pl_con_arr.dymin + (pl_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )
        c.add_label(
            r1_label,
            position=(
                pl_con_arr.dxmax - (pl_con.dxsize / 2),
                pl_con_arr.dymin + (pl_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

        c.add_label(
            sub_label,
            position=(
                sub_con.dxmin + (sub_con.dxsize / 2),
                sub_con.dymin + (sub_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    return c


def draw_npolyf_res(
    layout,
    l_res: float = 0.1,
    w_res: float = 0.1,
    res_type: str = "npolyf_s",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
    sub_label: str = "",
) -> gf.Component:
    c = gf.Component("res_dev")

    if res_type == "npolyf_s":
        pl_res_ext = 0.29
        con_enc = 0.07
    else:
        pl_res_ext = 0.44
        con_enc = 0.0

    # adding res inst
    r_inst = c.add_ref(
        polyf_res_inst(
            l_res=l_res,
            w_res=w_res,
            res_type=res_type,
            pl_res_ext=pl_res_ext,
            con_enc=con_enc,
            pl_imp_layer=layer["nplus"],
            sub_imp_layer=layer["pplus"],
            label=label,
            r0_label=r0_label,
            r1_label=r1_label,
            sub_label=sub_label,
        )
    )

    if deepnwell == 1:
        lvpwell_enc_cmp = 0.43
        lvpwell = c.add_ref(
            gf.components.rectangle(
                size=(
                    r_inst.dxsize + (2 * lvpwell_enc_cmp),
                    r_inst.dysize + (2 * lvpwell_enc_cmp),
                ),
                layer=layer["lvpwell"],
            )
        )
        lvpwell.dxmin = r_inst.dxmin - lvpwell_enc_cmp
        lvpwell.dymin = r_inst.dymin - lvpwell_enc_cmp

        dn_enc_lvpwell = 2.5
        dn_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    lvpwell.dxsize + (2 * dn_enc_lvpwell),
                    lvpwell.dysize + (2 * dn_enc_lvpwell),
                ),
                layer=layer["dnwell"],
            )
        )
        dn_rect.dxmin = lvpwell.dxmin - dn_enc_lvpwell
        dn_rect.dymin = lvpwell.dymin - dn_enc_lvpwell

        if pcmpgr == 1:
            sub_w = 0.36

            c.add_ref(pcmpgr_gen(dn_rect=dn_rect, grw=sub_w))

    c.write_gds("res_temp.gds")
    layout.read("res_temp.gds")
    cell_name = "res_dev"

    return layout.cell(cell_name)


def draw_ppolyf_res(
    layout,
    l_res: float = 0.1,
    w_res: float = 0.1,
    res_type: str = "ppolyf_s",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
    sub_label: str = "",
) -> gf.Component:
    c = gf.Component("res_dev")

    if res_type == "ppolyf_s":
        pl_res_ext = 0.29
        con_enc = 0.07
    else:
        pl_res_ext = 0.44
        con_enc = 0.0

    sub_layer = layer["nplus"] if deepnwell == 1 else layer["pplus"]
    # adding res inst
    r_inst = c.add_ref(
        polyf_res_inst(
            l_res=l_res,
            w_res=w_res,
            res_type=res_type,
            pl_res_ext=pl_res_ext,
            con_enc=con_enc,
            pl_imp_layer=layer["pplus"],
            sub_imp_layer=sub_layer,
            label=label,
            r0_label=r0_label,
            r1_label=r1_label,
            sub_label=sub_label,
        )
    )

    if deepnwell == 1:
        dn_enc_ncmp = 0.66
        dn_enc_poly2 = 1.34

        dn_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    r_inst.dxsize + (dn_enc_poly2 + dn_enc_ncmp),
                    r_inst.dysize + (2 * dn_enc_poly2),
                ),
                layer=layer["dnwell"],
            )
        )
        dn_rect.dxmax = r_inst.dxmax + dn_enc_poly2
        dn_rect.dymin = r_inst.dymin - dn_enc_poly2

        if pcmpgr == 1:
            sub_w = 0.36
            c.add_ref(pcmpgr_gen(dn_rect=dn_rect, grw=sub_w))

    c.write_gds("res_temp.gds")
    layout.read("res_temp.gds")
    cell_name = "res_dev"

    return layout.cell(cell_name)


def draw_ppolyf_u_high_Rs_res(
    layout,
    l_res: float = 0.42,
    w_res: float = 0.42,
    volt: str = "3.3V",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
    sub_label: str = "",
) -> gf.Component:
    c = gf.Component("res_dev")

    dn_enc_ncmp = 0.62
    dn_enc_poly2 = 1.34

    pl_res_ext = 0.64

    sub_w: float = 0.42
    pp_enc_poly2 = 0.18
    pp_enc_cmp: float = 0.02
    comp_spacing: float = 0.7
    sab_res_ext = (0.1, 0.28)
    con_size = 0.36
    resis_enc = (1.04, 0.4)
    dg_enc_dn = 0.5

    res_mk = c.add_ref(
        gf.components.rectangle(size=(l_res, w_res), layer=layer["res_mk"])
    )

    resis_mk = c.add_ref(
        gf.components.rectangle(
            size=(
                res_mk.dxsize + (2 * resis_enc[0]),
                res_mk.dysize + (2 * resis_enc[1]),
            ),
            layer=layer["resistor"],
        )
    )

    resis_mk.dxmin = res_mk.dxmin - resis_enc[0]
    resis_mk.dymin = res_mk.dymin - resis_enc[1]

    sab_rect = c.add_ref(
        gf.components.rectangle(
            size=(
                res_mk.dxsize + (2 * sab_res_ext[0]),
                res_mk.dysize + (2 * sab_res_ext[1]),
            ),
            layer=layer["sab"],
        )
    )
    sab_rect.dxmin = res_mk.dxmin - sab_res_ext[0]
    sab_rect.dymin = res_mk.dymin - sab_res_ext[1]

    pl = c.add_ref(
        gf.components.rectangle(
            size=(res_mk.dxsize + (2 * pl_res_ext), res_mk.dysize),
            layer=layer["poly2"],
        )
    )
    pl.dxmin = res_mk.dxmin - pl_res_ext
    pl.dymin = res_mk.dymin

    pl_con = via_stack(
        x_range=(pl.dxmin, pl.dxmin + con_size),
        y_range=(pl.dymin, pl.dymax),
        base_layer=layer["poly2"],
        metal_level=1,
    )

    pl_con_arr = c.add_ref(
        component=pl_con,
        rows=1,
        columns=2,
        spacing=(pl.dxsize - con_size, 0),
    )  # comp contact array

    pplus = gf.components.rectangle(
        size=(pl_res_ext + pp_enc_poly2, pl.dysize + (2 * pp_enc_poly2)),
        layer=layer["pplus"],
    )

    pplus_arr = c.add_ref(
        component=pplus, rows=1, columns=2, spacing=(pplus.dxsize + res_mk.dxsize, 0)
    )

    pplus_arr.dxmin = pl.dxmin - pp_enc_poly2
    pplus_arr.dymin = pl.dymin - pp_enc_poly2

    sub_rect = c.add_ref(
        gf.components.rectangle(size=(sub_w, w_res), layer=layer["comp"])
    )
    sub_rect.dxmax = pl.dxmin - comp_spacing
    sub_rect.dymin = pl.dymin

    # sub_rect contact
    sub_con = c.add_ref(
        via_stack(
            x_range=(sub_rect.dxmin, sub_rect.dxmax),
            y_range=(sub_rect.dymin, sub_rect.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
    )

    # labels generation
    if label == 1:
        c.add_label(
            r0_label,
            position=(
                pl_con_arr.dxmin + (pl_con.dxsize / 2),
                pl_con_arr.dymin + (pl_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )
        c.add_label(
            r1_label,
            position=(
                pl_con_arr.dxmax - (pl_con.dxsize / 2),
                pl_con_arr.dymin + (pl_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

        c.add_label(
            sub_label,
            position=(
                sub_con.dxmin + (sub_con.dxsize / 2),
                sub_con.dymin + (sub_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    if deepnwell == 1:
        sub_layer = layer["nplus"]
    else:
        sub_layer = layer["pplus"]

    sub_imp = c.add_ref(
        gf.components.rectangle(
            size=(
                sub_rect.dxsize + (2 * pp_enc_cmp),
                pl.dysize + (2 * pp_enc_cmp),
            ),
            layer=sub_layer,
        )
    )
    sub_imp.dxmin = sub_rect.dxmin - pp_enc_cmp
    sub_imp.dymin = sub_rect.dymin - pp_enc_cmp

    if deepnwell == 1:
        dn_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    (pl.dxmax - sub_rect.dxmin) + (dn_enc_poly2 + dn_enc_ncmp),
                    pl.dysize + (2 * dn_enc_poly2),
                ),
                layer=layer["dnwell"],
            )
        )
        dn_rect.dxmax = pl.dxmax + dn_enc_poly2
        dn_rect.dymin = pl.dymin - dn_enc_poly2

        if volt == "5/6V":
            dg = c.add_ref(
                gf.components.rectangle(
                    size=(
                        dn_rect.dxsize + (2 * dg_enc_dn),
                        dn_rect.dysize + (2 * dg_enc_dn),
                    ),
                    layer=layer["dualgate"],
                )
            )

            dg.dxmin = dn_rect.dxmin - dg_enc_dn
            dg.dymin = dn_rect.dymin - dg_enc_dn

        if pcmpgr == 1:
            c.add_ref(pcmpgr_gen(dn_rect=dn_rect, grw=sub_w))

    else:
        if volt == "5/6V":
            dg = c.add_ref(
                gf.components.rectangle(
                    size=(resis_mk.dxsize, resis_mk.dysize), layer=layer["dualgate"]
                )
            )

            dg.dxmin = resis_mk.dxmin
            dg.dymin = resis_mk.dymin

    c.write_gds("res_temp.gds")
    layout.read("res_temp.gds")
    cell_name = "res_dev"

    return layout.cell(cell_name)


def draw_well_res(
    layout,
    l_res: float = 0.42,
    w_res: float = 0.42,
    res_type: str = "nwell",
    pcmpgr: bool = False,
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
    sub_label: str = "",
) -> gf.Component:
    c = gf.Component("res_dev")

    nw_res_ext = 0.48
    nw_res_enc = 0.5
    nw_enc_cmp = 0.12

    sub_w: float = 0.36
    pp_enc_cmp: float = 0.16
    nw_comp_spacing: float = 0.72
    dn_enc_lvpwell = 2.5

    if res_type == "pwell":
        cmp_imp_layer = layer["pplus"]
        sub_imp_layer = layer["nplus"]
        well_layer = layer["lvpwell"]
    else:
        cmp_imp_layer = layer["nplus"]
        sub_imp_layer = layer["pplus"]
        well_layer = layer["nwell"]

    res_mk = c.add_ref(
        gf.components.rectangle(
            size=(l_res, w_res + (2 * nw_res_enc)), layer=layer["res_mk"]
        )
    )

    well_rect = c.add_ref(
        gf.components.rectangle(
            size=(res_mk.dxsize + (2 * nw_res_ext), w_res), layer=well_layer
        )
    )
    well_rect.dxmin = res_mk.dxmin - nw_res_ext
    well_rect.dymin = res_mk.dymin + nw_res_enc

    @gf.cell
    def comp_related_gen(size: Float2 = (0.42, 0.42)) -> gf.Component:
        c = gf.Component()

        cmp = c.add_ref(gf.components.rectangle(size=size, layer=layer["comp"]))
        cmp.dxmin = well_rect.dxmin + nw_enc_cmp
        cmp.dymin = well_rect.dymin + nw_enc_cmp

        c.add_ref(
            via_stack(
                x_range=(cmp.dxmin, cmp.dxmax),
                y_range=(cmp.dymin, cmp.dymax),
                base_layer=layer["comp"],
                metal_level=1,
            )
        )  # contact

        return c

    con_polys = comp_related_gen(
        size=(
            res_mk.dxmin - well_rect.dxmin - nw_enc_cmp,
            well_rect.dysize - (2 * nw_enc_cmp),
        )
    )

    con_polys_arr = c.add_ref(
        component=con_polys,
        rows=1,
        columns=2,
        spacing=(well_rect.dxsize - (2 * nw_enc_cmp) - con_polys.dxsize, 0),
    )  # comp and its related contact array

    nplus_rect = gf.components.rectangle(
        size=(
            con_polys.dxsize + (2 * pp_enc_cmp),
            con_polys.dysize + (2 * pp_enc_cmp),
        ),
        layer=cmp_imp_layer,
    )
    nplus_arr = c.add_ref(
        component=nplus_rect,
        rows=1,
        columns=2,
        spacing=(well_rect.dxsize - (2 * nw_enc_cmp) - con_polys.dxsize, 0),
    )
    nplus_arr.dxmin = con_polys.dxmin - pp_enc_cmp
    nplus_arr.dymin = con_polys.dymin - pp_enc_cmp

    sub_rect = c.add_ref(
        gf.components.rectangle(size=(sub_w, well_rect.dysize), layer=layer["comp"])
    )
    sub_rect.dxmax = well_rect.dxmin - nw_comp_spacing
    sub_rect.dymin = well_rect.dymin

    # sub_rect contact
    sub_con = c.add_ref(
        via_stack(
            x_range=(sub_rect.dxmin, sub_rect.dxmax),
            y_range=(sub_rect.dymin, sub_rect.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
    )

    sub_imp = c.add_ref(
        gf.components.rectangle(
            size=(
                sub_rect.dxsize + (2 * pp_enc_cmp),
                well_rect.dysize + (2 * pp_enc_cmp),
            ),
            layer=sub_imp_layer,
        )
    )
    sub_imp.dxmin = sub_rect.dxmin - pp_enc_cmp
    sub_imp.dymin = sub_rect.dymin - pp_enc_cmp

    if res_type == "pwell":
        dn_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    well_rect.dxsize + (2 * dn_enc_lvpwell),
                    well_rect.dysize + (2 * dn_enc_lvpwell),
                ),
                layer=layer["dnwell"],
            )
        )
        dn_rect.dxmin = well_rect.dxmin - dn_enc_lvpwell
        dn_rect.dymin = well_rect.dymin - dn_enc_lvpwell

        if pcmpgr == 1:
            c.add_ref(pcmpgr_gen(dn_rect=dn_rect, grw=sub_w))

    # labels generation
    if label == 1:
        c.add_label(
            r0_label,
            position=(
                con_polys_arr.dxmin + (con_polys.dxsize / 2),
                con_polys_arr.dymin + (con_polys.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )
        c.add_label(
            r1_label,
            position=(
                con_polys_arr.dxmax - (con_polys.dxsize / 2),
                con_polys_arr.dymin + (con_polys.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

        c.add_label(
            sub_label,
            position=(
                sub_con.dxmin + (sub_con.dxsize / 2),
                sub_con.dymin + (sub_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    c.write_gds("res_temp.gds")
    layout.read("res_temp.gds")
    cell_name = "res_dev"

    return layout.cell(cell_name)
