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
## FET Pcells Generators for Klayout of GF180MCU
########################################################################################################################

from math import ceil, floor

import gdsfactory as gf
from gdsfactory.typings import Float2, LayerSpec

from .layers_def import layer
from .via_generator import via_generator, via_stack


@gf.cell
def labels_gen(
    label_str: str = "",
    position: Float2 = (0.1, 0.1),
    layer: LayerSpec = layer["metal1_label"],
    label: bool = False,
    label_lst: list = [],
    label_valid_len: int = 1,
    index: int = 0,
) -> gf.Component:
    """Returns labels at given position when label is enabled.

    Args :
        label_str : string of the label
        position : position of the label
        layer : layer of the label
        label : boolean of having the label
        label_lst : list of given labels
        label_valid_len : valid length of labels
    """
    c = gf.Component()

    if label == 1 and len(label_lst) == label_valid_len:
        if label_str == "None":
            c.add_label(label_lst[index], position=position, layer=layer)
        else:
            c.add_label(label_str, position=position, layer=layer)

    return c


def get_patt_label(nl_b, nl, nt, nt_e, g_label, nl_u, nt_o):
    """Returns list of odd,even gate label patterns for alternating gate connection.

    Args :
        nl_b : number of bottom connected gates transistors
        nl : number of transistor
        nt : patterns of tansistor [with out redundancy]
        nt_e : number of transistor with even order
        g_label : list of transistors gate label
        nl_u :  number of upper connected gates transistors
        nt_o : number of transistor with odd order
    """
    g_label_e = []
    g_label_o = []

    if nt == len(g_label):
        for i in range(nl_b):
            g_label_e.extend(g_label[j] for j in range(nl) if nt[j] == nt_e[i])
        for i in range(nl_u):
            g_label_o.extend(g_label[j] for j in range(nl) if nt[j] == nt_o[i])
    return [g_label_e, g_label_o]


def alter_interdig(
    sd_diff,
    pc1,
    pc2,
    poly_con,
    sd_diff_intr,
    l_gate=0.15,
    inter_sd_l=0.15,
    sd_l=0.36,
    nf=1,
    pat="",
    pc_x=0.1,
    pc_spacing=0.1,
    label: bool = False,
    g_label: list = [],
    nl: int = 1,
    patt_label: bool = False,
) -> gf.Component:
    """Returns interdigitation polygons of gate with alternating poly contacts.

    Args :
        sd_diff : source/drain diffusion rectangle
        pc1 : first poly contact array
        pc2 : second poly contact array
        poly_con : component of poly contact
        sd_diff_inter : inter source/drain diffusion rectangle
        l_gate : gate length
        inter_sd_l : inter diffusion length
        nf : number of fingers
        pat : string of the required pattern
    """
    c_inst = gf.Component()

    m2_spacing = 0.28
    via_size = (0.26, 0.26)
    via_enc = (0.06, 0.06)
    via_spacing = (0.26, 0.26)

    pat_o = []
    pat_e = []

    for i in range(int(nf)):
        if i % 2 == 0:
            pat_e.append(pat[i])
        else:
            pat_o.append(pat[i])

    nt = []
    [nt.append(dx) for dx in pat if dx not in nt]

    nt_o = []
    [nt_o.append(dx) for dx in pat_o if dx not in nt_o]

    nt_e = []
    [nt_e.append(dx) for dx in pat_e if dx not in nt_e]

    nl = len(nt)
    nl_b = len(nt_e)
    nl_u = len(nt_o)

    g_label_e, g_label_o = get_patt_label(nl_b, nl, nt, nt_e, g_label, nl_u, nt_o)

    m2_y = via_size[1] + 2 * via_enc[1]
    m2 = gf.components.rectangle(
        size=(sd_diff.dxmax - sd_diff.dxmin, m2_y),
        layer=layer["metal2"],
    )

    m2_arrb = c_inst.add_ref(
        component=m2,
        columns=1,
        rows=nl_b,
        spacing=(0, -m2_y - m2_spacing),
    )
    m2_arrb.dmovey(pc1.dymin - m2_spacing - m2_y)

    m2_arru = c_inst.add_ref(
        component=m2,
        columns=1,
        rows=nl_u,
        spacing=(0, m2_y + m2_spacing),
    )
    m2_arru.dmovey(pc2.dymax + m2_spacing)

    for i in range(nl_u):
        for j in range(floor(nf / 2)):
            if pat_o[j] == nt_o[i]:
                m1 = c_inst.add_ref(
                    gf.components.rectangle(
                        size=(
                            pc_x,
                            ((pc2.dymax + (i + 1) * (m2_spacing + m2_y)) - pc2.dymin),
                        ),
                        layer=layer["metal1"],
                    )
                )
                m1.dxmin = pc2.dxmin + j * (pc_spacing)
                m1.dymin = pc2.dymin

                via1_dr = via_generator(
                    x_range=(m1.dxmin, m1.dxmax),
                    y_range=(
                        m2_arru.dymin + i * (m2_y + m2_spacing),
                        m2_arru.dymin + i * (m2_y + m2_spacing) + m2_y,
                    ),
                    via_enclosure=via_enc,
                    via_layer=layer["via1"],
                    via_size=via_size,
                    via_spacing=via_spacing,
                )
                via1 = c_inst.add_ref(via1_dr)

                c_inst.add_ref(
                    labels_gen(
                        label_str="None",
                        position=(
                            (via1.dxmax + via1.dxmin) / 2,
                            (via1.dymax + via1.dymin) / 2,
                        ),
                        layer=layer["metal2_label"],
                        label=patt_label,
                        label_lst=pat_o,
                        label_valid_len=len(pat_o),
                        index=j,
                    )
                )

                # adding gate_label
                c_inst.add_ref(
                    labels_gen(
                        label_str="None",
                        position=(
                            m1.dxmin + (m1.dxsize / 2),
                            pc2.dymin + (pc2.dysize / 2),
                        ),
                        layer=layer["metal1_label"],
                        label=label,
                        label_lst=g_label_o,
                        label_valid_len=nl_u,
                        index=i,
                    )
                )

    for i in range(nl_b):
        for j in range(ceil(nf / 2)):
            if pat_e[j] == nt_e[i]:
                m1 = c_inst.add_ref(
                    gf.components.rectangle(
                        size=(
                            pc_x,
                            ((pc1.dymax + (i + 1) * (m2_spacing + m2_y)) - pc1.dymin),
                        ),
                        layer=layer["metal1"],
                    )
                )
                m1.dxmin = pc1.dxmin + j * (pc_spacing)
                m1.dymin = -(m1.dymax - m1.dymin) + (pc1.dymax)
                via1_dr = via_generator(
                    x_range=(m1.dxmin, m1.dxmax),
                    y_range=(
                        m2_arrb.dymax - i * (m2_spacing + m2_y) - m2_y,
                        m2_arrb.dymax - i * (m2_spacing + m2_y),
                    ),
                    via_enclosure=via_enc,
                    via_layer=layer["via1"],
                    via_size=via_size,
                    via_spacing=via_spacing,
                )
                via1 = c_inst.add_ref(via1_dr)

                c_inst.add_ref(
                    labels_gen(
                        label_str="None",
                        position=(
                            (via1.dxmax + via1.dxmin) / 2,
                            (via1.dymax + via1.dymin) / 2,
                        ),
                        layer=layer["metal2_label"],
                        label=patt_label,
                        label_lst=pat_e,
                        label_valid_len=len(pat_e),
                        index=j,
                    )
                )

                # adding gate_label
                c_inst.add_ref(
                    labels_gen(
                        label_str="None",
                        position=(
                            m1.dxmin + (m1.dxsize / 2),
                            pc1.dymin + (pc1.dysize / 2),
                        ),
                        layer=layer["metal1_label"],
                        label=label,
                        label_lst=g_label_e,
                        label_valid_len=nl_b,
                        index=i,
                    )
                )

    m3_x = via_size[0] + 2 * via_enc[0]
    m3_spacing = m2_spacing

    for i in range(nl_b):
        for j in range(nl_u):
            if nt_e[i] == nt_o[j]:
                m2_join_b = c_inst.add_ref(
                    gf.components.rectangle(
                        size=(
                            m2_y + sd_l + (i + 1) * (m3_spacing + m3_x),
                            m2_y,
                        ),
                        layer=layer["metal2"],
                    ).dmove(
                        (
                            m2_arrb.dxmin
                            - (m2_y + sd_l + (i + 1) * (m3_spacing + m3_x)),
                            m2_arrb.dymax - i * (m2_spacing + m2_y) - m2_y,
                        )
                    )
                )
                m2_join_u = c_inst.add_ref(
                    gf.components.rectangle(
                        size=(
                            m2_y + sd_l + (i + 1) * (m3_spacing + m3_x),
                            m2_y,
                        ),
                        layer=layer["metal2"],
                    ).dmove(
                        (
                            m2_arru.dxmin
                            - (m2_y + sd_l + (i + 1) * (m3_spacing + m3_x)),
                            m2_arru.dymin + j * (m2_spacing + m2_y),
                        )
                    )
                )
                m3 = c_inst.add_ref(
                    gf.components.rectangle(
                        size=(
                            m3_x,
                            m2_join_u.dymax - m2_join_b.dymin,
                        ),
                        layer=layer["metal1"],
                    )
                )
                m3.dmove((m2_join_b.dxmin, m2_join_b.dymin))
                via2_dr = via_generator(
                    x_range=(m3.dxmin, m3.dxmax),
                    y_range=(m2_join_b.dymin, m2_join_b.dymax),
                    via_enclosure=via_enc,
                    via_size=via_size,
                    via_layer=layer["via1"],
                    via_spacing=via_spacing,
                )
                c_inst.add_ref(
                    component=via2_dr,
                    columns=1,
                    rows=2,
                    spacing=(
                        0,
                        m2_join_u.dymin - m2_join_b.dymin,
                    ),
                )  # via2_draw
    return c_inst


def interdigit(
    sd_diff,
    pc1,
    pc2,
    poly_con,
    sd_diff_intr,
    l_gate: float = 0.15,
    inter_sd_l: float = 0.23,
    sd_l: float = 0.15,
    nf=1,
    patt=[""],
    gate_con_pos="top",
    pc_x=0.1,
    pc_spacing=0.1,
    label: bool = False,
    g_label: list = [],
    patt_label: bool = False,
) -> gf.Component:
    """Returns interdigitation related polygons.

    Args :
        sd_diff : source/drain diffusion rectangle
        pc1 : first poly contact array
        pc2 : second poly contact array
        poly_con : component of poly contact
        sd_diff_inter : inter source/drain diffusion rectangle
        l_gate : gate length
        inter_sd_l : inter diffusion length
        nf : number of fingers
        pat : string of the required pattern
        gate_con_pos : position of gate contact
    """
    c_inst = gf.Component()

    if nf == len(patt):
        pat = list(patt)
        nt = []  # list to store the symbols of transistors and their number nt(number of transistors)
        [nt.append(dx) for dx in pat if dx not in nt]
        nl = len(nt)

        m2_spacing = 0.28
        via_size = (0.26, 0.26)
        via_enc = (0.06, 0.06)
        via_spacing = (0.26, 0.26)

        m2_y = via_size[1] + 2 * via_enc[1]
        m2 = gf.components.rectangle(
            size=(sd_diff.dxmax - sd_diff.dxmin, m2_y), layer=layer["metal2"]
        )

        if gate_con_pos == "alternating":
            c_inst.add_ref(
                alter_interdig(
                    sd_diff=sd_diff,
                    pc1=pc1,
                    pc2=pc2,
                    poly_con=poly_con,
                    sd_diff_intr=sd_diff_intr,
                    l_gate=l_gate,
                    inter_sd_l=inter_sd_l,
                    sd_l=sd_l,
                    nf=nf,
                    pat=pat,
                    pc_x=pc_x,
                    pc_spacing=pc_spacing,
                    label=label,
                    g_label=g_label,
                    nl=nl,
                    patt_label=patt_label,
                )
            )

        elif gate_con_pos == "top":
            m2_arr = c_inst.add_ref(
                component=m2,
                columns=1,
                rows=nl,
                spacing=(0, m2.dymax - m2.dymin + m2_spacing),
            )
            m2_arr.dmovey(pc2.dymax + m2_spacing)

            for i in range(nl):
                for j in range(int(nf)):
                    if pat[j] == nt[i]:
                        m1 = c_inst.add_ref(
                            gf.components.rectangle(
                                size=(
                                    pc_x,
                                    (
                                        (pc2.dymax + (i + 1) * (m2_spacing + m2_y))
                                        - ((1 - j % 2) * pc1.dymin)
                                        - (j % 2) * pc2.dymin
                                    ),
                                ),
                                layer=layer["metal1"],
                            )
                        )
                        m1.dxmin = pc1.dxmin + j * (pc2.dxmin - pc1.dxmin)
                        m1.dymin = pc1.dymin

                        via1_dr = via_generator(
                            x_range=(m1.dxmin, m1.dxmax),
                            y_range=(
                                m2_arr.dymin + i * (m2_spacing + m2_y),
                                m2_arr.dymin + i * (m2_spacing + m2_y) + m2_y,
                            ),
                            via_enclosure=via_enc,
                            via_layer=layer["via1"],
                            via_size=via_size,
                            via_spacing=via_spacing,
                        )
                        via1 = c_inst.add_ref(via1_dr)

                        c_inst.add_ref(
                            labels_gen(
                                label_str="None",
                                position=(
                                    (via1.dxmax + via1.dxmin) / 2,
                                    (via1.dymax + via1.dymin) / 2,
                                ),
                                layer=layer["metal2_label"],
                                label=patt_label,
                                label_lst=pat,
                                label_valid_len=nl,
                                index=j,
                            )
                        )

                        # adding gate_label
                        c_inst.add_ref(
                            labels_gen(
                                label_str="None",
                                position=(
                                    m1.dxmin + (m1.dxsize / 2),
                                    pc1.dymin + (pc1.dysize / 2),
                                ),
                                layer=layer["metal1_label"],
                                label=label,
                                label_lst=g_label,
                                label_valid_len=nl,
                                index=i,
                            )
                        )

        elif gate_con_pos == "bottom":
            m2_arr = c_inst.add_ref(
                component=m2,
                columns=1,
                rows=nl,
                spacing=(0, -m2_y - m2_spacing),
            )
            m2_arr.dmovey(pc2.dymin - m2_spacing - m2_y)

            for i in range(nl):
                for j in range(int(nf)):
                    if pat[j] == nt[i]:
                        m1 = c_inst.add_ref(
                            gf.components.rectangle(
                                size=(
                                    pc_x,
                                    (
                                        (pc1.dymax + (i + 1) * (m2_spacing + m2_y))
                                        - (j % 2) * pc1.dymin
                                        - (1 - j % 2) * pc2.dymin
                                    ),
                                ),
                                layer=layer["metal1"],
                            )
                        )
                        m1.dxmin = pc1.dxmin + j * (pc2.dxmin - pc1.dxmin)
                        m1.dymax = pc1.dymax

                        via1_dr = via_generator(
                            x_range=(m1.dxmin, m1.dxmax),
                            y_range=(
                                m2_arr.dymax - i * (m2_spacing + m2_y) - m2_y,
                                m2_arr.dymax - i * (m2_spacing + m2_y),
                            ),
                            via_enclosure=via_enc,
                            via_layer=layer["via1"],
                            via_size=via_size,
                            via_spacing=via_spacing,
                        )
                        via1 = c_inst.add_ref(via1_dr)

                        c_inst.add_ref(
                            labels_gen(
                                label_str="None",
                                position=(
                                    (via1.dxmax + via1.dxmin) / 2,
                                    (via1.dymax + via1.dymin) / 2,
                                ),
                                layer=layer["metal2_label"],
                                label=patt_label,
                                label_lst=pat,
                                label_valid_len=nl,
                                index=j,
                            )
                        )

                        # adding gate_label
                        c_inst.add_ref(
                            labels_gen(
                                label_str="None",
                                position=(
                                    m1.dxmin + (m1.dxsize / 2),
                                    pc1.dymin + (pc1.dysize / 2),
                                ),
                                layer=layer["metal1_label"],
                                label=label,
                                label_lst=g_label,
                                label_valid_len=nl,
                                index=i,
                            )
                        )

    return c_inst


# @gf.cell
def hv_gen(c, c_inst, volt, dg_encx: float = 0.1, dg_ency: float = 0.1) -> None:
    """Returns high voltage related polygons.

    Args :
        c_inst : dualgate enclosed component
        volt : operating voltage
        dg_encx : dualgate enclosure in x_direction
        dg_ency : dualgate enclosure in y_direction
    """
    # c = gf.Component()

    if volt in ["5V", "6V"]:
        dg = c.add_ref(
            gf.components.rectangle(
                size=(
                    c_inst.dxsize + (2 * dg_encx),
                    c_inst.dysize + (2 * dg_ency),
                ),
                layer=layer["dualgate"],
            )
        )
        dg.dxmin = c_inst.dxmin - dg_encx
        dg.dymin = c_inst.dymin - dg_ency

    if volt == "5V":
        v5x = c.add_ref(
            gf.components.rectangle(size=(dg.dxsize, dg.dysize), layer=layer["v5_xtor"])
        )
        v5x.dxmin = dg.dxmin
        v5x.dymin = dg.dymin

    # return c


# @gf.cell
def bulk_gr_gen(
    c,
    c_inst,
    comp_spacing: float = 0.1,
    poly2_comp_spacing: float = 0.1,
    volt: str = "3.3V",
    grw: float = 0.36,
    l_d: float = 0.1,
    implant_layer: LayerSpec = layer["pplus"],
    label: bool = False,
    sub_label: str = "",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    nw_enc_pcmp: float = 0.1,
    m1_sp: float = 0.1,
) -> None:
    """Returns guardring.

    Args :
        c_inst : component enclosed by guardring
        comp_spacing : spacing between comp polygons
        poly2_comp_spacing : spacing between comp and poly2 polygons
        volt : operating voltage
        grw : guardring width
        l_d : total diffusion length
        implant_layer : layer of comp implant (nplus,pplus)
    """
    # c = gf.Component()

    comp_pp_enc: float = 0.16

    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07
    dg_enc_cmp = 0.24

    c_temp = gf.Component("temp_store")
    rect_bulk_in = c_temp.add_ref(
        gf.components.rectangle(
            size=(
                (c_inst.dxmax - c_inst.dxmin) + 2 * m1_sp,
                (c_inst.dymax - c_inst.dymin) + 2 * m1_sp,
            ),
            layer=layer["comp"],
        )
    )
    rect_bulk_in.dmove((c_inst.dxmin - m1_sp, c_inst.dymin - m1_sp))
    rect_bulk_out = c_temp.add_ref(
        gf.components.rectangle(
            size=(
                (rect_bulk_in.dxmax - rect_bulk_in.dxmin) + 2 * grw,
                (rect_bulk_in.dymax - rect_bulk_in.dymin) + 2 * grw,
            ),
            layer=layer["comp"],
        )
    )
    rect_bulk_out.dmove((rect_bulk_in.dxmin - grw, rect_bulk_in.dymin - grw))
    B = c.add_ref(
        gf.boolean(
            A=rect_bulk_out,
            B=rect_bulk_in,
            operation="A-B",
            layer=layer["comp"],
        )
    )

    psdm_in = c_temp.add_ref(
        gf.components.rectangle(
            size=(
                (rect_bulk_in.dxmax - rect_bulk_in.dxmin) - 2 * comp_pp_enc,
                (rect_bulk_in.dymax - rect_bulk_in.dymin) - 2 * comp_pp_enc,
            ),
            layer=layer["pplus"],
        )
    )
    psdm_in.dmove((rect_bulk_in.dxmin + comp_pp_enc, rect_bulk_in.dymin + comp_pp_enc))
    psdm_out = c_temp.add_ref(
        gf.components.rectangle(
            size=(
                (rect_bulk_out.dxmax - rect_bulk_out.dxmin) + 2 * comp_pp_enc,
                (rect_bulk_out.dymax - rect_bulk_out.dymin) + 2 * comp_pp_enc,
            ),
            layer=layer["pplus"],
        )
    )
    psdm_out.dmove(
        (
            rect_bulk_out.dxmin - comp_pp_enc,
            rect_bulk_out.dymin - comp_pp_enc,
        )
    )
    c.add_ref(
        gf.boolean(A=psdm_out, B=psdm_in, operation="A-B", layer=implant_layer)
    )  # implant_draw(pplus or nplus)

    # generating contacts

    c.add_ref(
        via_generator(
            x_range=(
                rect_bulk_in.dxmin + con_size,
                rect_bulk_in.dxmax - con_size,
            ),
            y_range=(rect_bulk_out.dymin, rect_bulk_in.dymin),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # bottom contact

    c.add_ref(
        via_generator(
            x_range=(
                rect_bulk_in.dxmin + con_size,
                rect_bulk_in.dxmax - con_size,
            ),
            y_range=(rect_bulk_in.dymax, rect_bulk_out.dymax),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # upper contact

    c.add_ref(
        via_generator(
            x_range=(rect_bulk_out.dxmin, rect_bulk_in.dxmin),
            y_range=(
                rect_bulk_in.dymin + con_size,
                rect_bulk_in.dymax - con_size,
            ),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # right contact

    c.add_ref(
        via_generator(
            x_range=(rect_bulk_in.dxmax, rect_bulk_out.dxmax),
            y_range=(
                rect_bulk_in.dymin + con_size,
                rect_bulk_in.dymax - con_size,
            ),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # left contact

    comp_m1_in = c_temp.add_ref(
        gf.components.rectangle(
            size=(
                (l_d) + 2 * comp_spacing,
                (c_inst.dymax - c_inst.dymin) + 2 * poly2_comp_spacing,
            ),
            layer=layer["metal1"],
        )
    )
    comp_m1_in.dmove((-comp_spacing, c_inst.dymin - poly2_comp_spacing))
    comp_m1_out = c_temp.add_ref(
        gf.components.rectangle(
            size=(
                (rect_bulk_in.dxmax - rect_bulk_in.dxmin) + 2 * grw,
                (rect_bulk_in.dymax - rect_bulk_in.dymin) + 2 * grw,
            ),
            layer=layer["metal1"],
        )
    )
    comp_m1_out.dmove((rect_bulk_in.dxmin - grw, rect_bulk_in.dymin - grw))
    c.add_ref(
        gf.boolean(
            A=rect_bulk_out,
            B=rect_bulk_in,
            operation="A-B",
            layer=layer["metal1"],
        )
    )  # metal1_guardring

    hv_gen(c, c_inst=B, volt=volt, dg_encx=dg_enc_cmp, dg_ency=dg_enc_cmp)

    c.add_ref(
        labels_gen(
            label_str=sub_label,
            position=(
                B.dxmin + (grw + 2 * (comp_pp_enc)) / 2,
                B.dymin + (B.dysize / 2),
            ),
            layer=layer["metal1_label"],
            label=label,
            label_lst=[sub_label],
            label_valid_len=1,
        )
    )

    if implant_layer == layer["pplus"]:
        c.add_ref(
            nfet_deep_nwell(
                deepnwell=deepnwell,
                pcmpgr=pcmpgr,
                inst_size=(B.dxsize, B.dysize),
                inst_xmin=B.dxmin,
                inst_ymin=B.dymin,
                grw=grw,
                volt=volt,
            )
        )
    else:
        c.add_ref(
            pfet_deep_nwell(
                deepnwell=deepnwell,
                pcmpgr=pcmpgr,
                enc_size=(B.dxsize, B.dysize),
                enc_xmin=B.dxmin,
                enc_ymin=B.dymin,
                nw_enc_pcmp=nw_enc_pcmp,
                grw=grw,
                volt=volt,
            )
        )

    # return c


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
def nfet_deep_nwell(
    volt="3.3V",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    inst_size: Float2 = (0.1, 0.1),
    inst_xmin: float = 0.1,
    inst_ymin: float = 0.1,
    grw: float = 0.36,
) -> gf.Component:
    """Return nfet deepnwell.

    Args :
        deepnwell : boolean of having deepnwell
        pcmpgr : boolean of having deepnwell guardring
        inst_size : deepnwell enclosed size
        inst_xmin : deepnwell enclosed dxmin
        inst_ymin : deepnwell enclosed dymin
        grw : guardring width
    """
    c = gf.Component()

    if deepnwell == 1:
        lvpwell_enc_ncmp = 0.44
        lvp_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    inst_size[0] + (2 * lvpwell_enc_ncmp),
                    inst_size[1] + (2 * lvpwell_enc_ncmp),
                ),
                layer=layer["lvpwell"],
            )
        )

        lvp_rect.dymin = inst_ymin - lvpwell_enc_ncmp

        dn_enc_lvpwell = 2.5
        lvp_rect.dxmin = inst_xmin - lvpwell_enc_ncmp
        dn_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    lvp_rect.dxsize + (2 * dn_enc_lvpwell),
                    lvp_rect.dysize + (2 * dn_enc_lvpwell),
                ),
                layer=layer["dnwell"],
            )
        )

        dn_rect.dxmin = lvp_rect.dxmin - dn_enc_lvpwell
        dn_rect.dymin = lvp_rect.dymin - dn_enc_lvpwell

        if pcmpgr == 1:
            c.add_ref(pcmpgr_gen(dn_rect=dn_rect, grw=grw))

        if volt in ["5V", "6V"]:
            dg_enc_dn = 0.5
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

    elif volt in ["5V", "6V"]:
        dg_enc_cmp = 0.24
        dg_enc_poly = 0.4

        dg = c.add_ref(
            gf.components.rectangle(
                size=(
                    inst_size[0] + (2 * dg_enc_cmp),
                    inst_size[1] + (2 * dg_enc_poly),
                ),
                layer=layer["dualgate"],
            )
        )
        dg.dxmin = inst_xmin - dg_enc_cmp
        dg.dymin = inst_ymin - dg_enc_poly

    if volt == "5V":
        v5x = c.add_ref(
            gf.components.rectangle(size=(dg.dxsize, dg.dysize), layer=layer["v5_xtor"])
        )
        v5x.dxmin = dg.dxmin
        v5x.dymin = dg.dymin

    return c


def add_inter_sd_labels(
    c, nf, sd_label, poly1, l_gate, inter_sd_l, sd_diff_intr, label, layer, con_bet_fin
) -> None:
    """Adds label to intermediate source/drain diffusion.

    Args :
        c : instance component of the device
        nf : number of fingers
        sd_label : required source and drain labels list
        poly1 : component of poly array
        l_gate : length of fet gate
        inter_sd_l : length of intermediate source/drain diffusion
        sd_diff_inter : component of intermediate source/drain polygon
        label: boolean of having labels
        layer : layer of label
        con_bet_fin : boolean of having contact between fingers
    """
    label_layer = layer["metal1_label"] if con_bet_fin == 1 else layer["comp_label"]
    for i in range(int(nf - 1)):
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(
                    poly1.dxmin + l_gate + (inter_sd_l / 2) + i * (l_gate + inter_sd_l),
                    sd_diff_intr.dymin + (sd_diff_intr.dysize / 2),
                ),
                layer=label_layer,
                label=label,
                label_lst=sd_label,
                label_valid_len=nf + 1,
                index=i + 1,
            )
        )


def add_gate_labels(
    c, g_label, pc1, c_pc, pc_spacing, nc1, nc2, pc2, label, layer, nf
) -> None:
    """Adds gate label when label is enabled.

    Args :
        c : instance component of the device
        g_label : required gate labels list
        pc1 : component of poly array1
        c_pc : component of poly array element
        pc_spacing : float of space between labels
        nc1 : number of columns in poly array1
        nc2 : number of columns in poly array2
        pc2 : component of poly array2
        label : boolean of having labels
        layer : layer of labels
        nf : number of fingers
    """
    for i in range(nc1):
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(
                    pc1.dxmin + (c_pc.dxsize / 2) + i * (pc_spacing),
                    pc1.dymin + (c_pc.dysize / 2),
                ),
                layer=layer["metal1_label"],
                label=label,
                label_lst=g_label,
                label_valid_len=nf,
                index=2 * i,
            )
        )

    for i in range(nc2):
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(
                    pc2.dxmin + (c_pc.dxsize / 2) + i * (pc_spacing),
                    pc2.dymin + (c_pc.dysize / 2),
                ),
                layer=layer["metal1_label"],
                label=label,
                label_lst=g_label,
                label_valid_len=nf,
                index=(2 * i) + 1,
            )
        )


def sd_m1_area_check(
    sd_con_area, m1_area, sd_con, c_inst, sd_l, nf, l_gate, inter_sd_l, pl_cmp_spacing
) -> None:
    if sd_con_area < m1_area:
        sd_con_m1 = gf.components.rectangle(
            size=(sd_con.dxsize, m1_area / sd_con.dysize), layer=layer["metal1"]
        )
        sd_m1_arr = c_inst.add_ref(
            component=sd_con_m1,
            columns=2,
            rows=1,
            spacing=(
                sd_l + nf * l_gate + (nf - 1) * inter_sd_l + 2 * (pl_cmp_spacing),
                0,
            ),
        )
        sd_m1_arr.dxmin = sd_con.dxmin
        sd_m1_arr.dymin = sd_con.dymin - (sd_con_m1.dysize - sd_con.dysize) / 2


def poly_con_m1_check(poly_con_area, m1_area, c_pc, poly_con, c_pl_con) -> None:
    if poly_con_area < m1_area:
        m1_poly = c_pc.add_ref(
            gf.components.rectangle(
                size=(m1_area / poly_con.dxsize, poly_con.dysize),
                layer=layer["metal1"],
            )
        )
        m1_poly.dxmin = c_pl_con.dxmin - (m1_poly.dxsize - poly_con.dxsize) / 2
        m1_poly.dymin = c_pl_con.dymin


def inter_sd_m1_area_check(
    inter_sd_con_area, m1_area, inter_sd_con, c_inst, l_gate, nf, inter_sd_l, sd_con
) -> None:
    if inter_sd_con_area < m1_area:
        inter_sd_con_m1 = gf.components.rectangle(
            size=(inter_sd_con.dxsize, m1_area / inter_sd_con.dysize),
            layer=layer["metal1"],
        )
        inter_sd_m1_arr = c_inst.add_ref(
            component=inter_sd_con_m1,
            columns=nf - 1,
            rows=1,
            spacing=(l_gate + inter_sd_l, 0),
        )
        inter_sd_m1_arr.dxmin = inter_sd_con.dxmin
        inter_sd_m1_arr.dymin = (
            inter_sd_con.dymin - (inter_sd_con_m1.dysize - sd_con.dysize) / 2
        )


def bulk_m1_check(bulk_con_area, m1_area, c_inst, bulk_con) -> None:
    if bulk_con_area < m1_area:
        bulk_m1 = c_inst.add_ref(
            gf.components.rectangle(
                size=(bulk_con.dxsize, m1_area / bulk_con.dysize),
                layer=layer["metal1"],
            )
        )
        bulk_m1.dxmin = bulk_con.dxmin
        bulk_m1.dymin = bulk_con.dymin - (bulk_m1.dysize - bulk_con.dysize) / 2


# @gf.cell
def draw_nfet(
    layout,
    l_gate: float = 0.28,
    w_gate: float = 0.22,
    sd_con_col: int = 1,
    inter_sd_l: float = 0.24,
    nf: int = 1,
    grw: float = 0.22,
    volt: str = "3.3V",
    bulk="None",
    con_bet_fin: int = 1,
    gate_con_pos="alternating",
    interdig: int = 0,
    patt="",
    deepnwell: int = 0,
    pcmpgr: int = 0,
    label: bool = False,
    sd_label: list = [],
    g_label: str = [],
    sub_label: str = "",
    patt_label: bool = False,
) -> gf.Component:
    """Retern nfet.

    Args:
        layout : layout object
        l : Float of gate length
        w : Float of gate width
        sd_l : Float of source and drain diffusion length
        inter_sd_l : Float of source and drain diffusion length between fingers
        nf : integer of number of fingers
        M : integer of number of multipliers
        grw : guard ring width when enabled
        type : string of the device type
        bulk : String of bulk connection type (None, Bulk Tie, Guard Ring)
        con_bet_fin : boolean of having contacts for diffusion between fingers
        gate_con_pos : string of choosing the gate contact position (bottom, top, alternating )

    """
    # used layers and dimensions

    end_cap: float = 0.3
    if volt == "3.3V":
        comp_spacing: float = 0.28
    else:
        comp_spacing: float = 0.36

    gate_np_enc: float = 0.23
    comp_np_enc: float = 0.16
    comp_pp_enc: float = 0.16
    poly2_spacing: float = 0.24
    pc_ext: float = 0.04

    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07
    con_pp_sp = 0.1 - con_comp_enc
    con_pl_enc = 0.07
    pl_cmp_spacing = 0.18
    m1_area = 0.145
    m1_sp = 0.3
    pl_cmpcon_sp = 0.15

    sd_l_con = (
        ((sd_con_col) * con_size)
        + ((sd_con_col - 1) * con_sp)
        + 2 * con_comp_enc
        + 2 * con_pp_sp
    )
    sd_l = sd_l_con

    # gds components to store a single instance and the generated device
    c = gf.Component("sky_nfet_dev")

    c_inst = gf.Component("dev_temp")

    # generating sd diffusion

    if interdig == 1 and nf > 1 and nf != len(patt) and patt != "":
        nf = len(patt)

    l_d = (
        nf * l_gate + (nf - 1) * inter_sd_l + 2 * (pl_cmp_spacing)
    )  # diffution total length
    rect_d_intr = gf.components.rectangle(size=(l_d, w_gate), layer=layer["comp"])
    sd_diff_intr = c_inst.add_ref(rect_d_intr)

    #     # generatin sd contacts

    if w_gate <= con_size + 2 * con_comp_enc:
        cmpc_y = con_comp_enc + con_size + con_comp_enc
        np_cmp_ency = comp_np_enc

    else:
        cmpc_y = w_gate
        np_cmp_ency = gate_np_enc

    cmpc_size = (sd_l_con, cmpc_y)

    sd_diff = c_inst.add_ref(
        component=gf.components.rectangle(size=cmpc_size, layer=layer["comp"]),
        rows=1,
        columns=2,
        spacing=(cmpc_size[0] + sd_diff_intr.dxsize, 0),
    )

    sd_diff.dxmin = sd_diff_intr.dxmin - cmpc_size[0]
    sd_diff.dymin = sd_diff_intr.dymin - (sd_diff.dysize - sd_diff_intr.dysize) / 2

    sd_con = via_stack(
        x_range=(sd_diff.dxmin + con_pp_sp, sd_diff_intr.dxmin - con_pp_sp),
        y_range=(sd_diff.dymin, sd_diff.dymax),
        base_layer=layer["comp"],
        metal_level=1,
    )
    sd_con_arr = c_inst.add_ref(
        component=sd_con,
        columns=2,
        rows=1,
        spacing=(
            sd_l + nf * l_gate + (nf - 1) * inter_sd_l + 2 * (pl_cmp_spacing),
            0,
        ),
    )

    sd_con_area = sd_con.dxsize * sd_con.dysize

    sd_m1_area_check(
        sd_con_area,
        m1_area,
        sd_con,
        c_inst,
        sd_l,
        nf,
        l_gate,
        inter_sd_l,
        pl_cmp_spacing,
    )

    if con_bet_fin == 1 and nf > 1:
        inter_sd_con = via_stack(
            x_range=(
                sd_diff_intr.dxmin + pl_cmp_spacing + l_gate + pl_cmpcon_sp,
                sd_diff_intr.dxmin
                + pl_cmp_spacing
                + l_gate
                + inter_sd_l
                - pl_cmpcon_sp,
            ),
            y_range=(0, w_gate),
            base_layer=layer["comp"],
            metal_level=1,
        )

        c_inst.add_ref(
            component=inter_sd_con,
            columns=nf - 1,
            rows=1,
            spacing=(l_gate + inter_sd_l, 0),
        )

        inter_sd_con_area = inter_sd_con.dxsize * inter_sd_con.dysize
        inter_sd_m1_area_check(
            inter_sd_con_area,
            m1_area,
            inter_sd_con,
            c_inst,
            l_gate,
            nf,
            inter_sd_l,
            sd_con,
        )

    ### adding source/drain labels
    c.add_ref(
        labels_gen(
            label_str="None",
            position=(
                sd_diff.dxmin + (sd_l / 2),
                sd_diff.dymin + (sd_diff.dysize / 2),
            ),
            layer=layer["metal1_label"],
            label=label,
            label_lst=sd_label,
            label_valid_len=nf + 1,
            index=0,
        )
    )

    c.add_ref(
        labels_gen(
            label_str="None",
            position=(
                sd_diff.dxmax - (sd_l / 2),
                sd_diff.dymin + (sd_diff.dysize / 2),
            ),
            layer=layer["metal1_label"],
            label=label,
            label_lst=sd_label,
            label_valid_len=nf + 1,
            index=nf,
        )
    )

    # generating poly

    if l_gate <= con_size + 2 * con_pl_enc:
        pc_x = con_pl_enc + con_size + con_pl_enc

    else:
        pc_x = l_gate

    pc_size = (pc_x, con_pl_enc + con_size + con_pl_enc)

    c_pc = gf.Component("poly con")

    rect_pc = c_pc.add_ref(gf.components.rectangle(size=pc_size, layer=layer["poly2"]))

    poly_con = via_stack(
        x_range=(rect_pc.dxmin, rect_pc.dxmax),
        y_range=(rect_pc.dymin, rect_pc.dymax),
        base_layer=layer["poly2"],
        metal_level=1,
        li_enc_dir="H",
    )
    c_pl_con = c_pc.add_ref(poly_con)

    poly_con_area = poly_con.dxsize * poly_con.dysize

    poly_con_m1_check(poly_con_area, m1_area, c_pc, poly_con, c_pl_con)

    if nf == 1:
        poly = c_inst.add_ref(
            gf.components.rectangle(
                size=(l_gate, w_gate + 2 * end_cap), layer=layer["poly2"]
            )
        )
        poly.dxmin = sd_diff_intr.dxmin + pl_cmp_spacing
        poly.dymin = sd_diff_intr.dymin - end_cap

        if gate_con_pos == "bottom":
            mv = 0
            nr = 1
        elif gate_con_pos == "top":
            mv = pc_size[1] + w_gate + 2 * end_cap
            nr = 1
        else:
            mv = 0
            nr = 2

        pc = c_inst.add_ref(
            component=c_pc,
            rows=nr,
            columns=1,
            spacing=(0, pc_size[1] + w_gate + 2 * end_cap),
        )
        pc.dmove((poly.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv))

        # gate_lablel
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(pc.dxmin + c_pc.dxsize / 2, pc.dymin + c_pc.dysize / 2),
                layer=layer["metal1_label"],
                label=label,
                label_lst=g_label,
                label_valid_len=nf,
                index=0,
            )
        )

    else:
        w_p1 = end_cap + w_gate + end_cap  # poly total width

        if inter_sd_l < (poly2_spacing + 2 * pc_ext):
            if gate_con_pos == "alternating":
                w_p1 += 0.2
                w_p2 = w_p1
                e_c = 0.2
            else:
                w_p2 = w_p1 + con_pl_enc + con_size + con_pl_enc + poly2_spacing + 0.1
                e_c = 0

            if gate_con_pos == "bottom":
                p_mv = -end_cap - (w_p2 - w_p1)
            else:
                p_mv = -end_cap

        else:
            w_p2 = w_p1
            p_mv = -end_cap
            e_c = 0

        rect_p1 = gf.components.rectangle(size=(l_gate, w_p1), layer=layer["poly2"])
        rect_p2 = gf.components.rectangle(size=(l_gate, w_p2), layer=layer["poly2"])
        poly1 = c_inst.add_ref(
            rect_p1,
            rows=1,
            columns=ceil(nf / 2),
            spacing=[2 * (inter_sd_l + l_gate), 0],
        )
        poly1.dxmin = sd_diff_intr.dxmin + pl_cmp_spacing
        poly1.dymin = sd_diff_intr.dymin - end_cap - e_c

        poly2 = c_inst.add_ref(
            rect_p2,
            rows=1,
            columns=floor(nf / 2),
            spacing=[2 * (inter_sd_l + l_gate), 0],
        )
        poly2.dxmin = poly1.dxmin + l_gate + inter_sd_l
        poly2.dymin = p_mv

        # generating poly contacts setups

        if gate_con_pos == "bottom":
            mv_1 = 0
            mv_2 = -(w_p2 - w_p1)
        elif gate_con_pos == "top":
            mv_1 = pc_size[1] + w_p1
            mv_2 = pc_size[1] + w_p2
        else:
            mv_1 = -e_c
            mv_2 = pc_size[1] + w_p2

        nc1 = ceil(nf / 2)
        nc2 = floor(nf / 2)

        pc_spacing = 2 * (inter_sd_l + l_gate)

        # generating poly contacts

        pc1 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc1, spacing=(pc_spacing, 0)
        )
        pc1.dmove((poly1.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv_1))

        pc2 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc2, spacing=(pc_spacing, 0)
        )
        pc2.dmove(
            (
                poly1.dxmin - ((pc_x - l_gate) / 2) + (inter_sd_l + l_gate),
                -pc_size[1] - end_cap + mv_2,
            )
        )

        add_inter_sd_labels(
            c,
            nf,
            sd_label,
            poly1,
            l_gate,
            inter_sd_l,
            sd_diff_intr,
            label,
            layer,
            con_bet_fin,
        )

        if interdig == 1:
            c_inst.add_ref(
                interdigit(
                    sd_diff=sd_diff,
                    pc1=pc1,
                    pc2=pc2,
                    poly_con=poly_con,
                    sd_diff_intr=sd_diff_intr,
                    l_gate=l_gate,
                    inter_sd_l=inter_sd_l,
                    sd_l=sd_l,
                    nf=nf,
                    patt=patt,
                    gate_con_pos=gate_con_pos,
                    pc_x=pc_x,
                    pc_spacing=pc_spacing,
                    label=label,
                    g_label=g_label,
                    patt_label=patt_label,
                )
            )
        else:
            add_gate_labels(
                c, g_label, pc1, c_pc, pc_spacing, nc1, nc2, pc2, label, layer, nf
            )

    # generating bulk
    if bulk == "None":
        nplus = c_inst.add_ref(
            gf.components.rectangle(
                size=(
                    sd_diff.dxsize + 2 * comp_np_enc,
                    sd_diff.dysize + 2 * np_cmp_ency,
                ),
                layer=layer["nplus"],
            )
        )
        nplus.dxmin = sd_diff.dxmin - comp_np_enc
        nplus.dymin = sd_diff.dymin - np_cmp_ency

    elif bulk == "Bulk Tie":
        rect_bulk = c_inst.add_ref(
            gf.components.rectangle(
                size=(sd_l + con_sp, sd_diff.dysize), layer=layer["comp"]
            )
        )
        rect_bulk.dxmin = sd_diff.dxmax
        rect_bulk.dymin = sd_diff.dymin
        nsdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(
                    sd_diff.dxmax - sd_diff.dxmin + comp_np_enc,
                    sd_diff.dysize + (2 * np_cmp_ency),
                ),
                layer=layer["nplus"],
            )
        )
        nsdm.dxmin = sd_diff.dxmin - comp_np_enc
        nsdm.dymin = sd_diff.dymin - np_cmp_ency
        psdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(
                    rect_bulk.dxmax - rect_bulk.dxmin + comp_pp_enc,
                    w_gate + 2 * comp_pp_enc,
                ),
                layer=layer["pplus"],
            )
        )
        psdm.connect("e1", nsdm.ports["e3"])

        bulk_con = via_stack(
            x_range=(sd_con_arr.dxmax + m1_sp, rect_bulk.dxmax),
            y_range=(rect_bulk.dymin, rect_bulk.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(bulk_con)

        bulk_con_area = bulk_con.dxsize * bulk_con.dysize

        bulk_m1_check(bulk_con_area, m1_area, c_inst, bulk_con)

        c.add_ref(
            labels_gen(
                label_str=sub_label,
                position=(
                    bulk_con.dxmin + bulk_con.dxsize / 2,
                    bulk_con.dymin + bulk_con.dysize / 2,
                ),
                layer=layer["metal1_label"],
                label=label,
                label_lst=[sub_label],
                label_valid_len=1,
            )
        )

    if bulk == "Guard Ring":
        nsdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(sd_diff.dxsize + 2 * comp_np_enc, w_gate + 2 * gate_np_enc),
                layer=layer["nplus"],
            )
        )
        nsdm.dxmin = sd_diff.dxmin - comp_np_enc
        nsdm.dymin = sd_diff_intr.dymin - gate_np_enc
        c.add_ref(c_inst)

        bulk_gr_gen(
            c,
            c_inst=c_inst,
            comp_spacing=comp_spacing,
            poly2_comp_spacing=comp_spacing,
            volt=volt,
            grw=grw,
            l_d=l_d,
            implant_layer=layer["pplus"],
            label=label,
            sub_label=sub_label,
            deepnwell=deepnwell,
            pcmpgr=pcmpgr,
            m1_sp=m1_sp,
        )

    else:
        c.add_ref(c_inst)

        inst_size = (c_inst.dxsize, c_inst.dysize)
        inst_xmin = c_inst.dxmin
        inst_ymin = c_inst.dymin

        c.add_ref(
            nfet_deep_nwell(
                deepnwell=deepnwell,
                pcmpgr=pcmpgr,
                inst_size=inst_size,
                inst_xmin=inst_xmin,
                inst_ymin=inst_ymin,
                grw=grw,
                volt=volt,
            )
        )

    # creating layout and cell in klayout
    c.write_gds("nfet_temp.gds")
    layout.read("nfet_temp.gds")
    cell_name = "sky_nfet_dev"

    return layout.cell(cell_name)
    # return c


@gf.cell
def pfet_deep_nwell(
    volt="3.3V",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    enc_size: Float2 = (0.1, 0.1),
    enc_xmin: float = 0.1,
    enc_ymin: float = 0.1,
    nw_enc_pcmp: float = 0.1,
    grw: float = 0.36,
) -> gf.Component:
    """Returns pfet well related polygons.

    Args :
        deepnwell : boolaen of having deepnwell
        pcmpgr : boolean of having deepnwell guardring
        enc_size : enclosed size
        enc_xmin : enclosed dxmin
        enc_ymin : enclosed dymin
        nw_enc_pcmp : nwell enclosure of pcomp
        grw : guardring width
    """
    c = gf.Component()

    dnwell_enc_pcmp = 1.1
    dg_enc_dn = 0.5

    if deepnwell == 1:
        dn_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    enc_size[0] + (2 * dnwell_enc_pcmp),
                    enc_size[1] + (2 * dnwell_enc_pcmp),
                ),
                layer=layer["dnwell"],
            )
        )

        dn_rect.dxmin = enc_xmin - dnwell_enc_pcmp
        dn_rect.dymin = enc_ymin - dnwell_enc_pcmp

        if pcmpgr == 1:
            c.add_ref(pcmpgr_gen(dn_rect=dn_rect, grw=grw))

        if volt == "5V" or volt == "6V":
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

            if volt == "5V":
                v5x = c.add_ref(
                    gf.components.rectangle(
                        size=(dg.dxsize, dg.dysize), layer=layer["v5_xtor"]
                    )
                )
                v5x.dxmin = dg.dxmin
                v5x.dymin = dg.dymin

    else:
        # nwell generation
        nw = c.add_ref(
            gf.components.rectangle(
                size=(
                    enc_size[0] + (2 * nw_enc_pcmp),
                    enc_size[1] + (2 * nw_enc_pcmp),
                ),
                layer=layer["nwell"],
            )
        )
        nw.dxmin = enc_xmin - nw_enc_pcmp
        nw.dymin = enc_ymin - nw_enc_pcmp

        if volt == "5V" or volt == "6V":
            dg = c.add_ref(
                gf.components.rectangle(
                    size=(
                        nw.dxsize + (2 * dg_enc_dn),
                        nw.dysize + (2 * dg_enc_dn),
                    ),
                    layer=layer["dualgate"],
                )
            )
            dg.dxmin = nw.dxmin - dg_enc_dn
            dg.dymin = nw.dymin - dg_enc_dn

            if volt == "5V":
                v5x = c.add_ref(
                    gf.components.rectangle(
                        size=(dg.dxsize, dg.dysize), layer=layer["v5_xtor"]
                    )
                )
                v5x.dxmin = dg.dxmin
                v5x.dymin = dg.dymin

    return c


# @gf.cell
def draw_pfet(
    layout,
    l_gate: float = 0.28,
    w_gate: float = 0.22,
    sd_con_col: int = 1,
    inter_sd_l: float = 0.24,
    nf: int = 1,
    grw: float = 0.22,
    volt: str = "3.3V",
    bulk="None",
    con_bet_fin: int = 1,
    gate_con_pos="alternating",
    interdig: int = 0,
    patt="",
    deepnwell: int = 0,
    pcmpgr: int = 0,
    label: bool = False,
    sd_label: list = [],
    g_label: str = [],
    sub_label: str = "",
    patt_label: bool = False,
) -> gf.Component:
    """Retern pfet.

    Args:
        layout : layout object
        l : Float of gate length
        w : Float of gate width
        sd_l : Float of source and drain diffusion length
        inter_sd_l : Float of source and drain diffusion length between fingers
        nf : integer of number of fingers
        M : integer of number of multipliers
        grw : guard ring width when enabled
        type : string of the device type
        bulk : String of bulk connection type (None, Bulk Tie, Guard Ring)
        con_bet_fin : boolean of having contacts for diffusion between fingers
        gate_con_pos : string of choosing the gate contact position (bottom, top, alternating )

    """
    # used layers and dimensions

    end_cap: float = 0.22
    if volt == "3.3V":
        comp_spacing: float = 0.28
        nw_enc_pcmp = 0.43
    else:
        comp_spacing: float = 0.36
        nw_enc_pcmp = 0.6

    gate_pp_enc: float = 0.23
    comp_np_enc: float = 0.16
    comp_pp_enc: float = 0.16
    poly2_spacing: float = 0.24
    pc_ext: float = 0.04

    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07
    con_pp_sp = 0.1 - con_comp_enc
    pl_cmp_spacing = 0.1
    con_pl_enc = 0.07
    dg_enc_cmp = 0.24
    dg_enc_poly = 0.4
    m1_sp = 0.3
    m1_area = 0.145
    pl_cmpcon_sp = 0.15

    # sd_l_con = (
    #     ((sd_con_col) * con_size) + ((sd_con_col - 1) * con_sp) + 2 * con_comp_enc
    # )
    sd_l_con = (
        ((sd_con_col) * con_size)
        + ((sd_con_col - 1) * con_sp)
        + 2 * con_comp_enc
        + 2 * con_pp_sp
    )
    sd_l = sd_l_con

    # gds components to store a single instance and the generated device
    c = gf.Component("sky_pfet_dev")

    c_inst = gf.Component("dev_temp")

    # generating sd diffusion

    if interdig == 1 and nf > 1 and nf != len(patt) and patt != "":
        nf = len(patt)

    l_d = (
        nf * l_gate + (nf - 1) * inter_sd_l + 2 * (pl_cmp_spacing)
    )  # diffution total length
    rect_d_intr = gf.components.rectangle(size=(l_d, w_gate), layer=layer["comp"])
    sd_diff_intr = c_inst.add_ref(rect_d_intr)

    # generatin sd contacts

    if w_gate <= con_size + 2 * con_comp_enc:
        cmpc_y = con_comp_enc + con_size + con_comp_enc
        pp_cmp_ency = comp_pp_enc

    else:
        cmpc_y = w_gate
        pp_cmp_ency = gate_pp_enc

    cmpc_size = (sd_l_con, cmpc_y)

    sd_diff = c_inst.add_ref(
        component=gf.components.rectangle(size=cmpc_size, layer=layer["comp"]),
        rows=1,
        columns=2,
        spacing=(cmpc_size[0] + sd_diff_intr.dxsize, 0),
    )

    sd_diff.dxmin = sd_diff_intr.dxmin - cmpc_size[0]
    sd_diff.dymin = sd_diff_intr.dymin - (sd_diff.dysize - sd_diff_intr.dysize) / 2

    sd_con = via_stack(
        x_range=(sd_diff.dxmin + con_pp_sp, sd_diff_intr.dxmin - con_pp_sp),
        y_range=(sd_diff.dymin, sd_diff.dymax),
        base_layer=layer["comp"],
        metal_level=1,
    )
    sd_con_arr = c_inst.add_ref(
        component=sd_con,
        columns=2,
        rows=1,
        spacing=(
            sd_l + nf * l_gate + (nf - 1) * inter_sd_l + 2 * (pl_cmp_spacing),
            0,
        ),
    )

    sd_con_area = sd_con.dxsize * sd_con.dysize

    sd_m1_area_check(
        sd_con_area,
        m1_area,
        sd_con,
        c_inst,
        sd_l,
        nf,
        l_gate,
        inter_sd_l,
        pl_cmp_spacing,
    )

    if con_bet_fin == 1 and nf > 1:
        inter_sd_con = via_stack(
            x_range=(
                sd_diff_intr.dxmin + pl_cmp_spacing + l_gate + pl_cmpcon_sp,
                sd_diff_intr.dxmin
                + pl_cmp_spacing
                + l_gate
                + inter_sd_l
                - pl_cmpcon_sp,
            ),
            y_range=(0, w_gate),
            base_layer=layer["comp"],
            metal_level=1,
        )

        c_inst.add_ref(
            component=inter_sd_con,
            columns=nf - 1,
            rows=1,
            spacing=(l_gate + inter_sd_l, 0),
        )

        inter_sd_con_area = inter_sd_con.dxsize * inter_sd_con.dysize
        inter_sd_m1_area_check(
            inter_sd_con_area,
            m1_area,
            inter_sd_con,
            c_inst,
            l_gate,
            nf,
            inter_sd_l,
            sd_con,
        )

    ### adding source/drain labels
    c.add_ref(
        labels_gen(
            label_str="None",
            position=(
                sd_diff.dxmin + (sd_l / 2),
                sd_diff.dymin + (sd_diff.dysize / 2),
            ),
            layer=layer["metal1_label"],
            label=label,
            label_lst=sd_label,
            label_valid_len=nf + 1,
            index=0,
        )
    )

    c.add_ref(
        labels_gen(
            label_str="None",
            position=(
                sd_diff.dxmax - (sd_l / 2),
                sd_diff.dymin + (sd_diff.dysize / 2),
            ),
            layer=layer["metal1_label"],
            label=label,
            label_lst=sd_label,
            label_valid_len=nf + 1,
            index=nf,
        )
    )

    # generating poly

    if l_gate <= con_size + 2 * con_pl_enc:
        pc_x = con_pl_enc + con_size + con_pl_enc

    else:
        pc_x = l_gate

    pc_size = (pc_x, con_pl_enc + con_size + con_pl_enc)

    c_pc = gf.Component("poly con")

    rect_pc = c_pc.add_ref(gf.components.rectangle(size=pc_size, layer=layer["poly2"]))

    poly_con = via_stack(
        x_range=(rect_pc.dxmin, rect_pc.dxmax),
        y_range=(rect_pc.dymin, rect_pc.dymax),
        base_layer=layer["poly2"],
        metal_level=1,
        li_enc_dir="H",
    )
    c_pl_con = c_pc.add_ref(poly_con)

    poly_con_area = poly_con.dxsize * poly_con.dysize

    poly_con_m1_check(poly_con_area, m1_area, c_pc, poly_con, c_pl_con)

    if nf == 1:
        poly = c_inst.add_ref(
            gf.components.rectangle(
                size=(l_gate, w_gate + 2 * end_cap), layer=layer["poly2"]
            )
        )
        poly.dxmin = sd_diff_intr.dxmin + pl_cmp_spacing
        poly.dymin = sd_diff_intr.dymin - end_cap

        if gate_con_pos == "bottom":
            mv = 0
            nr = 1
        elif gate_con_pos == "top":
            mv = pc_size[1] + w_gate + 2 * end_cap
            nr = 1
        else:
            mv = 0
            nr = 2

        pc = c_inst.add_ref(
            component=c_pc,
            rows=nr,
            columns=1,
            spacing=(0, pc_size[1] + w_gate + 2 * end_cap),
        )
        pc.dmove((poly.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv))

        # gate_lablel
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(pc.dxmin + c_pc.dxsize / 2, pc.dymin + c_pc.dysize / 2),
                layer=layer["metal1_label"],
                label=label,
                label_lst=g_label,
                label_valid_len=nf,
                index=0,
            )
        )

    else:
        w_p1 = end_cap + w_gate + end_cap  # poly total width

        if inter_sd_l < (poly2_spacing + 2 * pc_ext):
            if gate_con_pos == "alternating":
                w_p1 += 0.2
                w_p2 = w_p1
                e_c = 0.2
            else:
                w_p2 = w_p1 + con_pl_enc + con_size + con_pl_enc + poly2_spacing + 0.1
                e_c = 0

            if gate_con_pos == "bottom":
                p_mv = -end_cap - (w_p2 - w_p1)
            else:
                p_mv = -end_cap

        else:
            w_p2 = w_p1
            p_mv = -end_cap
            e_c = 0

        rect_p1 = gf.components.rectangle(size=(l_gate, w_p1), layer=layer["poly2"])
        rect_p2 = gf.components.rectangle(size=(l_gate, w_p2), layer=layer["poly2"])
        poly1 = c_inst.add_ref(
            rect_p1,
            rows=1,
            columns=ceil(nf / 2),
            spacing=[2 * (inter_sd_l + l_gate), 0],
        )
        poly1.dxmin = sd_diff_intr.dxmin + pl_cmp_spacing
        poly1.dymin = sd_diff_intr.dymin - end_cap - e_c

        poly2 = c_inst.add_ref(
            rect_p2,
            rows=1,
            columns=floor(nf / 2),
            spacing=[2 * (inter_sd_l + l_gate), 0],
        )
        poly2.dxmin = poly1.dxmin + l_gate + inter_sd_l
        poly2.dymin = p_mv

        # generating poly contacts setups

        if gate_con_pos == "bottom":
            mv_1 = 0
            mv_2 = -(w_p2 - w_p1)
        elif gate_con_pos == "top":
            mv_1 = pc_size[1] + w_p1
            mv_2 = pc_size[1] + w_p2
        else:
            mv_1 = -e_c
            mv_2 = pc_size[1] + w_p2

        nc1 = ceil(nf / 2)
        nc2 = floor(nf / 2)

        pc_spacing = 2 * (inter_sd_l + l_gate)

        # generating poly contacts

        pc1 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc1, spacing=(pc_spacing, 0)
        )
        pc1.dmove((poly1.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv_1))

        pc2 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc2, spacing=(pc_spacing, 0)
        )
        pc2.dmove(
            (
                poly1.dxmin - ((pc_x - l_gate) / 2) + (inter_sd_l + l_gate),
                -pc_size[1] - end_cap + mv_2,
            )
        )

        add_inter_sd_labels(
            c,
            nf,
            sd_label,
            poly1,
            l_gate,
            inter_sd_l,
            sd_diff_intr,
            label,
            layer,
            con_bet_fin,
        )

        add_gate_labels(
            c, g_label, pc1, c_pc, pc_spacing, nc1, nc2, pc2, label, layer, nf
        )

        if interdig == 1:
            c_inst.add_ref(
                interdigit(
                    sd_diff=sd_diff,
                    pc1=pc1,
                    pc2=pc2,
                    poly_con=poly_con,
                    sd_diff_intr=sd_diff_intr,
                    l_gate=l_gate,
                    inter_sd_l=inter_sd_l,
                    sd_l=sd_l,
                    nf=nf,
                    patt=patt,
                    gate_con_pos=gate_con_pos,
                    pc_x=pc_x,
                    pc_spacing=pc_spacing,
                    label=label,
                    g_label=g_label,
                    patt_label=patt_label,
                )
            )

    # generating bulk
    if bulk == "None":
        pplus = c_inst.add_ref(
            gf.components.rectangle(
                size=(sd_diff.dxsize + 2 * comp_pp_enc, w_gate + 2 * gate_pp_enc),
                layer=layer["pplus"],
            )
        )
        pplus.dxmin = sd_diff.dxmin - comp_pp_enc
        pplus.dymin = sd_diff_intr.dymin - gate_pp_enc

        c.add_ref(c_inst)

        # deep nwell and nwell generation

        c.add_ref(
            pfet_deep_nwell(
                deepnwell=deepnwell,
                pcmpgr=pcmpgr,
                enc_size=(sd_diff.dxsize, sd_diff.dysize),
                enc_xmin=sd_diff.dxmin,
                enc_ymin=sd_diff.dymin,
                nw_enc_pcmp=nw_enc_pcmp,
                grw=grw,
                volt=volt,
            )
        )

        hv_gen(c, c_inst=c_inst, volt=volt, dg_encx=dg_enc_cmp, dg_ency=dg_enc_poly)

    elif bulk == "Bulk Tie":
        rect_bulk = c_inst.add_ref(
            gf.components.rectangle(
                size=(sd_l + con_sp, sd_diff.dysize), layer=layer["comp"]
            )
        )
        rect_bulk.dxmin = sd_diff.dxmax
        rect_bulk.dymin = sd_diff.dymin
        psdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(
                    sd_diff.dxmax - sd_diff.dxmin + comp_pp_enc,
                    sd_diff.dysize + (2 * pp_cmp_ency),
                    # w_gate + 2 * gate_pp_enc,
                ),
                layer=layer["pplus"],
            )
        )
        psdm.dxmin = sd_diff.dxmin - comp_pp_enc
        psdm.dymin = sd_diff.dymin - gate_pp_enc
        nsdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(
                    rect_bulk.dxmax - rect_bulk.dxmin + comp_np_enc,
                    w_gate + 2 * comp_np_enc,
                ),
                layer=layer["nplus"],
            )
        )
        nsdm.connect("e1", psdm.ports["e3"])

        bulk_con = via_stack(
            x_range=(sd_con_arr.dxmax + m1_sp, rect_bulk.dxmax),
            y_range=(rect_bulk.dymin, rect_bulk.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(bulk_con)

        bulk_con_area = bulk_con.dxsize * bulk_con.dysize

        bulk_m1_check(bulk_con_area, m1_area, c_inst, bulk_con)

        c.add_ref(c_inst)

        c.add_ref(
            labels_gen(
                label_str=sub_label,
                position=(
                    bulk_con.dxmin + bulk_con.dxsize / 2,
                    bulk_con.dymin + bulk_con.dysize / 2,
                ),
                layer=layer["metal1_label"],
                label=label,
                label_lst=[sub_label],
                label_valid_len=1,
            )
        )

        # deep nwell generation
        nw_enc_pcmp = 0.45 + comp_np_enc + psdm.dymax - nsdm.dymax
        c.add_ref(
            pfet_deep_nwell(
                deepnwell=deepnwell,
                pcmpgr=pcmpgr,
                enc_size=(sd_diff.dxsize + rect_bulk.dxsize, sd_diff.dysize),
                enc_xmin=sd_diff.dxmin,
                enc_ymin=sd_diff.dymin,
                nw_enc_pcmp=nw_enc_pcmp,
                grw=grw,
                volt=volt,
            )
        )

    elif bulk == "Guard Ring":
        psdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(sd_diff.dxsize + 2 * comp_np_enc, w_gate + 2 * gate_pp_enc),
                layer=layer["pplus"],
            )
        )
        psdm.dxmin = sd_diff.dxmin - comp_pp_enc
        psdm.dymin = sd_diff_intr.dymin - gate_pp_enc
        c.add_ref(c_inst)

        bulk_gr_gen(
            c,
            c_inst=c_inst,
            comp_spacing=comp_spacing,
            poly2_comp_spacing=comp_spacing,
            volt=volt,
            grw=grw,
            l_d=l_d,
            implant_layer=layer["nplus"],
            label=label,
            sub_label=sub_label,
            deepnwell=deepnwell,
            pcmpgr=pcmpgr,
            nw_enc_pcmp=nw_enc_pcmp,
            m1_sp=m1_sp,
        )
        # bulk guardring

    # creating layout and cell in klayout
    c.write_gds("pfet_temp.gds")
    layout.read("pfet_temp.gds")
    cell_name = "sky_pfet_dev"

    return layout.cell(cell_name)


def draw_nfet_06v0_nvt(
    layout,
    l_gate: float = 1.8,
    w_gate: float = 0.8,
    sd_con_col: int = 1,
    inter_sd_l: float = 0.24,
    nf: int = 1,
    grw: float = 0.22,
    bulk="None",
    con_bet_fin: int = 1,
    gate_con_pos="alternating",
    interdig: int = 0,
    patt="",
    label: bool = False,
    sd_label: list = [],
    g_label: str = [],
    sub_label: str = "",
    patt_label: bool = False,
) -> gf.Component:
    """Usage:-
     used to draw Native NFET 6V transistor by specifying parameters
    Arguments:-
     layout : Object of layout
     l      : Float of gate length
     w      : Float of gate width
     ld     : Float of diffusion length
     nf     : Integer of number of fingers
     grw    : Float of guard ring width [If enabled]
     bulk   : String of bulk connection type [None, Bulk Tie, Guard Ring].
    """
    # used layers and dimensions

    end_cap: float = 0.22

    comp_spacing: float = 0.36
    poly2_comp_spacing: float = 0.3

    gate_np_enc: float = 0.23
    comp_np_enc: float = 0.16
    comp_pp_enc: float = 0.16
    poly2_spacing: float = 0.24
    pc_ext: float = 0.04

    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07
    con_pp_sp = 0.1 - con_comp_enc
    pl_cmp_spacing = 0.1
    con_pl_enc = 0.07
    pl_cmpcon_sp = 0.15
    nvt_enc_cmp = 2
    m1_sp = 0.3
    m1_area = 0.145

    sd_l_con = (
        ((sd_con_col) * con_size)
        + ((sd_con_col - 1) * con_sp)
        + 2 * con_comp_enc
        + 2 * con_pp_sp
    )
    sd_l = sd_l_con

    # gds components to store a single instance and the generated device
    c = gf.Component("sky_nfet_nvt_dev")

    c_inst = gf.Component("dev_temp")

    # generating sd diffusion

    if interdig == 1 and nf > 1 and nf != len(patt) and patt != "":
        nf = len(patt)

    l_d = (
        nf * l_gate + (nf - 1) * inter_sd_l + 2 * (pl_cmp_spacing)
    )  # diffution total length
    rect_d_intr = gf.components.rectangle(size=(l_d, w_gate), layer=layer["comp"])
    sd_diff_intr = c_inst.add_ref(rect_d_intr)

    # generatin sd contacts

    if w_gate <= con_size + 2 * con_comp_enc:
        cmpc_y = con_comp_enc + con_size + con_comp_enc
        np_cmp_ency = comp_np_enc

    else:
        cmpc_y = w_gate
        np_cmp_ency = gate_np_enc

    cmpc_size = (sd_l_con, cmpc_y)

    sd_diff = c_inst.add_ref(
        component=gf.components.rectangle(size=cmpc_size, layer=layer["comp"]),
        rows=1,
        columns=2,
        spacing=(cmpc_size[0] + sd_diff_intr.dxsize, 0),
    )

    sd_diff.dxmin = sd_diff_intr.dxmin - cmpc_size[0]
    sd_diff.dymin = sd_diff_intr.dymin - (sd_diff.dysize - sd_diff_intr.dysize) / 2

    sd_con = via_stack(
        x_range=(sd_diff.dxmin + con_pp_sp, sd_diff_intr.dxmin - con_pp_sp),
        y_range=(sd_diff.dymin, sd_diff.dymax),
        base_layer=layer["comp"],
        metal_level=1,
    )
    sd_con_arr = c_inst.add_ref(
        component=sd_con,
        columns=2,
        rows=1,
        spacing=(
            sd_l + nf * l_gate + (nf - 1) * inter_sd_l + 2 * (pl_cmp_spacing),
            0,
        ),
    )

    sd_con_area = sd_con.dxsize * sd_con.dysize

    sd_m1_area_check(
        sd_con_area,
        m1_area,
        sd_con,
        c_inst,
        sd_l,
        nf,
        l_gate,
        inter_sd_l,
        pl_cmp_spacing,
    )

    if con_bet_fin == 1 and nf > 1:
        inter_sd_con = via_stack(
            x_range=(
                sd_diff_intr.dxmin + pl_cmp_spacing + l_gate + pl_cmpcon_sp,
                sd_diff_intr.dxmin
                + pl_cmp_spacing
                + l_gate
                + inter_sd_l
                - pl_cmpcon_sp,
            ),
            y_range=(0, w_gate),
            base_layer=layer["comp"],
            metal_level=1,
        )

        c_inst.add_ref(
            component=inter_sd_con,
            columns=nf - 1,
            rows=1,
            spacing=(l_gate + inter_sd_l, 0),
        )

        inter_sd_con_area = inter_sd_con.dxsize * inter_sd_con.dysize
        inter_sd_m1_area_check(
            inter_sd_con_area,
            m1_area,
            inter_sd_con,
            c_inst,
            l_gate,
            nf,
            inter_sd_l,
            sd_con,
        )

    ### adding source/drain labels
    c.add_ref(
        labels_gen(
            label_str="None",
            position=(
                sd_diff.dxmin + (sd_l / 2),
                sd_diff.dymin + (sd_diff.dysize / 2),
            ),
            layer=layer["metal1_label"],
            label=label,
            label_lst=sd_label,
            label_valid_len=nf + 1,
            index=0,
        )
    )

    c.add_ref(
        labels_gen(
            label_str="None",
            position=(
                sd_diff.dxmax - (sd_l / 2),
                sd_diff.dymin + (sd_diff.dysize / 2),
            ),
            layer=layer["metal1_label"],
            label=label,
            label_lst=sd_label,
            label_valid_len=nf + 1,
            index=nf,
        )
    )

    # generating poly

    if l_gate <= con_size + 2 * con_pl_enc:
        pc_x = con_pl_enc + con_size + con_pl_enc

    else:
        pc_x = l_gate

    pc_size = (pc_x, con_pl_enc + con_size + con_pl_enc)

    c_pc = gf.Component("poly con")

    rect_pc = c_pc.add_ref(gf.components.rectangle(size=pc_size, layer=layer["poly2"]))

    poly_con = via_stack(
        x_range=(rect_pc.dxmin, rect_pc.dxmax),
        y_range=(rect_pc.dymin, rect_pc.dymax),
        base_layer=layer["poly2"],
        metal_level=1,
        li_enc_dir="H",
    )
    c_pc.add_ref(poly_con)

    if nf == 1:
        poly = c_inst.add_ref(
            gf.components.rectangle(
                size=(l_gate, w_gate + 2 * end_cap), layer=layer["poly2"]
            )
        )
        poly.dxmin = sd_diff_intr.dxmin + pl_cmp_spacing
        poly.dymin = sd_diff_intr.dymin - end_cap

        if gate_con_pos == "bottom":
            mv = 0
            nr = 1
        elif gate_con_pos == "top":
            mv = pc_size[1] + w_gate + 2 * end_cap
            nr = 1
        else:
            mv = 0
            nr = 2

        pc = c_inst.add_ref(
            component=c_pc,
            rows=nr,
            columns=1,
            spacing=(0, pc_size[1] + w_gate + 2 * end_cap),
        )
        pc.dmove((poly.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv))

        # gate_lablel
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(pc.dxmin + c_pc.dxsize / 2, pc.dymin + c_pc.dysize / 2),
                layer=layer["metal1_label"],
                label=label,
                label_lst=g_label,
                label_valid_len=nf,
                index=0,
            )
        )

    else:
        w_p1 = end_cap + w_gate + end_cap  # poly total width

        if inter_sd_l < (poly2_spacing + 2 * pc_ext):
            if gate_con_pos == "alternating":
                w_p1 += 0.2
                w_p2 = w_p1
                e_c = 0.2
            else:
                w_p2 = w_p1 + con_pl_enc + con_size + con_pl_enc + poly2_spacing + 0.1
                e_c = 0

            if gate_con_pos == "bottom":
                p_mv = -end_cap - (w_p2 - w_p1)
            else:
                p_mv = -end_cap

        else:
            w_p2 = w_p1
            p_mv = -end_cap
            e_c = 0

        rect_p1 = gf.components.rectangle(size=(l_gate, w_p1), layer=layer["poly2"])
        rect_p2 = gf.components.rectangle(size=(l_gate, w_p2), layer=layer["poly2"])
        poly1 = c_inst.add_ref(
            rect_p1,
            rows=1,
            columns=ceil(nf / 2),
            spacing=[2 * (inter_sd_l + l_gate), 0],
        )
        poly1.dxmin = sd_diff_intr.dxmin + pl_cmp_spacing
        poly1.dymin = sd_diff_intr.dymin - end_cap - e_c

        poly2 = c_inst.add_ref(
            rect_p2,
            rows=1,
            columns=floor(nf / 2),
            spacing=[2 * (inter_sd_l + l_gate), 0],
        )
        poly2.dxmin = poly1.dxmin + l_gate + inter_sd_l
        poly2.dymin = p_mv

        # generating poly contacts setups

        if gate_con_pos == "bottom":
            mv_1 = 0
            mv_2 = -(w_p2 - w_p1)
        elif gate_con_pos == "top":
            mv_1 = pc_size[1] + w_p1
            mv_2 = pc_size[1] + w_p2
        else:
            mv_1 = -e_c
            mv_2 = pc_size[1] + w_p2

        nc1 = ceil(nf / 2)
        nc2 = floor(nf / 2)

        pc_spacing = 2 * (inter_sd_l + l_gate)

        # generating poly contacts

        pc1 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc1, spacing=(pc_spacing, 0)
        )
        pc1.dmove((poly1.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv_1))

        pc2 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc2, spacing=(pc_spacing, 0)
        )
        pc2.dmove(
            (
                poly1.dxmin - ((pc_x - l_gate) / 2) + (inter_sd_l + l_gate),
                -pc_size[1] - end_cap + mv_2,
            )
        )

        add_inter_sd_labels(
            c,
            nf,
            sd_label,
            poly1,
            l_gate,
            inter_sd_l,
            sd_diff_intr,
            label,
            layer,
            con_bet_fin,
        )

        add_gate_labels(
            c, g_label, pc1, c_pc, pc_spacing, nc1, nc2, pc2, label, layer, nf
        )

        if interdig == 1:
            c_inst.add_ref(
                interdigit(
                    sd_diff=sd_diff,
                    pc1=pc1,
                    pc2=pc2,
                    poly_con=poly_con,
                    sd_diff_intr=sd_diff_intr,
                    l_gate=l_gate,
                    inter_sd_l=inter_sd_l,
                    sd_l=sd_l,
                    nf=nf,
                    patt=patt,
                    gate_con_pos=gate_con_pos,
                    pc_x=pc_x,
                    pc_spacing=pc_spacing,
                    label=label,
                    g_label=g_label,
                    patt_label=patt_label,
                )
            )

    # generating bulk
    if bulk == "None":
        nplus = c_inst.add_ref(
            gf.components.rectangle(
                size=(sd_diff.dxsize + 2 * comp_np_enc, w_gate + 2 * gate_np_enc),
                layer=layer["nplus"],
            )
        )
        nplus.dxmin = sd_diff.dxmin - comp_np_enc
        nplus.dymin = sd_diff_intr.dymin - gate_np_enc

    elif bulk == "Bulk Tie":
        rect_bulk = c_inst.add_ref(
            gf.components.rectangle(
                size=(sd_l + con_sp, sd_diff.dysize), layer=layer["comp"]
            )
        )
        rect_bulk.dxmin = sd_diff.dxmax
        rect_bulk.dymin = sd_diff.dymin
        nsdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(
                    sd_diff.dxmax - sd_diff.dxmin + comp_np_enc,
                    sd_diff.dysize + (2 * np_cmp_ency),
                ),
                layer=layer["nplus"],
            )
        )
        nsdm.dxmin = sd_diff.dxmin - comp_np_enc
        nsdm.dymin = sd_diff.dymin - np_cmp_ency
        psdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(
                    rect_bulk.dxmax - rect_bulk.dxmin + comp_pp_enc,
                    w_gate + 2 * comp_pp_enc,
                ),
                layer=layer["pplus"],
            )
        )
        psdm.connect("e1", nsdm.ports["e3"])

        bulk_con = via_stack(
            x_range=(sd_con_arr.dxmax + m1_sp, rect_bulk.dxmax),
            y_range=(rect_bulk.dymin, rect_bulk.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(bulk_con)

        bulk_con_area = bulk_con.dxsize * bulk_con.dysize

        bulk_m1_check(bulk_con_area, m1_area, c_inst, bulk_con)

        c.add_ref(
            labels_gen(
                label_str=sub_label,
                position=(
                    bulk_con.dxmin + bulk_con.dxsize / 2,
                    bulk_con.dymin + bulk_con.dysize / 2,
                ),
                layer=layer["metal1_label"],
                label=label,
                label_lst=[sub_label],
                label_valid_len=1,
            )
        )

    elif bulk == "Guard Ring":
        nsdm = c_inst.add_ref(
            gf.components.rectangle(
                size=(sd_diff.dxsize + 2 * comp_np_enc, w_gate + 2 * gate_np_enc),
                layer=layer["nplus"],
            )
        )
        nsdm.dxmin = sd_diff.dxmin - comp_np_enc
        nsdm.dymin = sd_diff_intr.dymin - gate_np_enc
        c.add_ref(c_inst)

        c_temp = gf.Component("temp_store")
        rect_bulk_in = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (c_inst.dxmax - c_inst.dxmin) + 2 * comp_spacing,
                    (c_inst.dymax - c_inst.dymin) + 2 * poly2_comp_spacing,
                ),
                layer=layer["comp"],
            )
        )
        rect_bulk_in.dmove(
            (c_inst.dxmin - comp_spacing, c_inst.dymin - poly2_comp_spacing)
        )
        rect_bulk_out = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_bulk_in.dxmax - rect_bulk_in.dxmin) + 2 * grw,
                    (rect_bulk_in.dymax - rect_bulk_in.dymin) + 2 * grw,
                ),
                layer=layer["comp"],
            )
        )
        rect_bulk_out.dmove((rect_bulk_in.dxmin - grw, rect_bulk_in.dymin - grw))
        c.add_ref(
            gf.boolean(
                A=rect_bulk_out,
                B=rect_bulk_in,
                operation="A-B",
                layer=layer["comp"],
            )
        )

        psdm_in = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_bulk_in.dxmax - rect_bulk_in.dxmin) - 2 * comp_pp_enc,
                    (rect_bulk_in.dymax - rect_bulk_in.dymin) - 2 * comp_pp_enc,
                ),
                layer=layer["pplus"],
            )
        )
        psdm_in.dmove(
            (rect_bulk_in.dxmin + comp_pp_enc, rect_bulk_in.dymin + comp_pp_enc)
        )
        psdm_out = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_bulk_out.dxmax - rect_bulk_out.dxmin) + 2 * comp_pp_enc,
                    (rect_bulk_out.dymax - rect_bulk_out.dymin) + 2 * comp_pp_enc,
                ),
                layer=layer["pplus"],
            )
        )
        psdm_out.dmove(
            (
                rect_bulk_out.dxmin - comp_pp_enc,
                rect_bulk_out.dymin - comp_pp_enc,
            )
        )
        psdm = c.add_ref(
            gf.boolean(A=psdm_out, B=psdm_in, operation="A-B", layer=layer["pplus"])
        )

        # generating contacts

        c.add_ref(
            via_generator(
                x_range=(
                    rect_bulk_in.dxmin + con_size,
                    rect_bulk_in.dxmax - con_size,
                ),
                y_range=(rect_bulk_out.dymin, rect_bulk_in.dymin),
                via_enclosure=(con_comp_enc, con_comp_enc),
                via_layer=layer["contact"],
                via_size=(con_size, con_size),
                via_spacing=(con_sp, con_sp),
            )
        )  # bottom contact

        c.add_ref(
            via_generator(
                x_range=(
                    rect_bulk_in.dxmin + con_size,
                    rect_bulk_in.dxmax - con_size,
                ),
                y_range=(rect_bulk_in.dymax, rect_bulk_out.dymax),
                via_enclosure=(con_comp_enc, con_comp_enc),
                via_layer=layer["contact"],
                via_size=(con_size, con_size),
                via_spacing=(con_sp, con_sp),
            )
        )  # upper contact

        c.add_ref(
            via_generator(
                x_range=(rect_bulk_out.dxmin, rect_bulk_in.dxmin),
                y_range=(
                    rect_bulk_in.dymin + con_size,
                    rect_bulk_in.dymax - con_size,
                ),
                via_enclosure=(con_comp_enc, con_comp_enc),
                via_layer=layer["contact"],
                via_size=(con_size, con_size),
                via_spacing=(con_sp, con_sp),
            )
        )  # right contact

        c.add_ref(
            via_generator(
                x_range=(rect_bulk_in.dxmax, rect_bulk_out.dxmax),
                y_range=(
                    rect_bulk_in.dymin + con_size,
                    rect_bulk_in.dymax - con_size,
                ),
                via_enclosure=(con_comp_enc, con_comp_enc),
                via_layer=layer["contact"],
                via_size=(con_size, con_size),
                via_spacing=(con_sp, con_sp),
            )
        )  # left contact

        comp_m1_in = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (l_d) + 2 * comp_spacing,
                    (c_inst.dymax - c_inst.dymin) + 2 * poly2_comp_spacing,
                ),
                layer=layer["metal1"],
            )
        )
        comp_m1_in.dmove((-comp_spacing, c_inst.dymin - poly2_comp_spacing))
        comp_m1_out = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_bulk_in.dxmax - rect_bulk_in.dxmin) + 2 * grw,
                    (rect_bulk_in.dymax - rect_bulk_in.dymin) + 2 * grw,
                ),
                layer=layer["metal1"],
            )
        )
        comp_m1_out.dmove((rect_bulk_in.dxmin - grw, rect_bulk_in.dymin - grw))
        b_gr = c.add_ref(
            gf.boolean(
                A=rect_bulk_out,
                B=rect_bulk_in,
                operation="A-B",
                layer=layer["metal1"],
            )
        )  # guardring metal1

        c.add_ref(
            labels_gen(
                label_str=sub_label,
                position=(
                    b_gr.dxmin + (grw + 2 * (comp_pp_enc)) / 2,
                    b_gr.dymin + (b_gr.dysize / 2),
                ),
                layer=layer["metal1_label"],
                label=label,
                label_lst=[sub_label],
                label_valid_len=1,
            )
        )

        dg = c.add_ref(
            gf.components.rectangle(
                size=(
                    sd_diff.dxsize + (2 * nvt_enc_cmp),
                    sd_diff.dysize + (2 * nvt_enc_cmp),
                ),
                layer=layer["dualgate"],
            )
        )
        dg.dxmin = sd_diff.dxmin - nvt_enc_cmp
        dg.dymin = sd_diff.dymin - nvt_enc_cmp

    if bulk != "Guard Ring":
        c.add_ref(c_inst)

        dg = c.add_ref(
            gf.components.rectangle(
                size=(
                    c_inst.dxsize + (2 * nvt_enc_cmp),
                    c_inst.dysize + (2 * nvt_enc_cmp),
                ),
                layer=layer["dualgate"],
            )
        )
        dg.dxmin = c_inst.dxmin - nvt_enc_cmp
        dg.dymin = c_inst.dymin - nvt_enc_cmp

    # generating native layer
    nat = c.add_ref(
        gf.components.rectangle(size=(dg.dxsize, dg.dysize), layer=layer["nat"])
    )

    nat.dxmin = dg.dxmin
    nat.dymin = dg.dymin

    # creating layout and cell in klayout

    c.write_gds("nfet_nvt_temp.gds")
    layout.read("nfet_nvt_temp.gds")
    cell_name = "sky_nfet_nvt_dev"

    return layout.cell(cell_name)


if __name__ == "__main__":
    pass
