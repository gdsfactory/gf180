from functools import partial
from math import ceil, floor

import gdsfactory as gf
from gdsfactory.typings import Float2, LayerSpec, Strs

from gf180.guardring import pcmpgr_gen
from gf180.layers import layer
from gf180.via_generator import via_generator, via_stack

rectangle = partial(gf.components.rectangle, layer=layer["comp"])
rectangle_array = partial(gf.components.array, component=rectangle)


@gf.cell
def labels_gen(
    label_str: str = "",
    position: Float2 = (0.1, 0.1),
    layer: LayerSpec = layer["metal1_label"],
    label: bool = False,
    labels: Strs | None = None,
    label_valid_len: int = 1,
    index: int = 0,
) -> gf.Component:
    """Returns labels at given position when label is enabled.

    Args :
        label_str : string of the label.
        position : position of the label.
        layer : layer of the label.
        label : boolean of having the label.
        labels : list of given labels.
        label_valid_len : valid length of labels.
    """
    c = gf.Component()

    if label == 1:
        if len(labels) == label_valid_len:
            if label_str == "None":
                c.add_label(labels[index], position=position, layer=layer)
            else:
                c.add_label(label_str, position=position, layer=layer)

    return c


def get_patt_label(nl_b, nl, nt, nt_e, g_label, nl_u, nt_o):
    """Returns list of odd,even gate label patterns for alternating gate connection.

    Args:
        nl_b : number of bottom connected gates transistors.
        nl : number of transistor.
        nt : patterns of tansistor [with out redundancy].
        nt_e : number of transistor with even order.
        g_label : list of transistors gate label.
        nl_u :  number of upper connected gates transistors.
        nt_o : number of transistor with odd order.

    """
    g_label_e = []
    g_label_o = []

    if nt == len(g_label):
        for i in range(nl_b):
            for j in range(nl):
                if nt[j] == nt_e[i]:
                    g_label_e.extend(g_label[j])

        for i in range(nl_u):
            for j in range(nl):
                if nt[j] == nt_o[i]:
                    g_label_o.extend(g_label[j])

    return [g_label_e, g_label_o]


@gf.cell
def alter_interdig(
    sd_diff=rectangle,
    pc1=rectangle_array,
    pc2=rectangle_array,
    sd_l=0.36,
    nf=1,
    pat="",
    pc_x=0.1,
    pc_spacing=0.1,
    label: bool = False,
    g_label: Strs | None = None,
    nl: int = 1,
    patt_label: bool = False,
) -> gf.Component:
    """Returns interdigitation polygons of gate with alternating poly contacts.

    Args :
        sd_diff : source/drain diffusion rectangle.
        pc1 : first poly contact array.
        pc2 : second poly contact array.
        sd_l : source/drain length.
        nf : number of fingers.
        pat: string of the required pattern.
        poly_con : component of poly contact.
        sd_diff_inter : inter source/drain diffusion rectangle.
        l_gate : gate length.
        inter_sd_l : inter diffusion length.
        nf : number of fingers.
    """
    c_inst = gf.Component()
    sd_diff = gf.get_component(sd_diff)
    pc1 = gf.get_component(pc1)
    pc2 = gf.get_component(pc2)

    m2_spacing = 0.28
    via_size = (0.26, 0.26)
    via_enc = (0.06, 0.06)
    via_spacing = (0.26, 0.26)

    pat_o = []
    pat_e = []

    if pat:
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

    if pat:
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
        row_pitch=-m2_y - m2_spacing,
    )
    m2_arrb.dmovey(pc1.dymin - m2_spacing - m2_y)

    m2_arru = c_inst.add_ref(
        component=m2,
        columns=1,
        rows=nl_u,
        row_pitch=m2_y + m2_spacing,
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
                        labels=pat_o,
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
                        labels=g_label_o,
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
                            # poly_con.dxmax - poly_con.dxmin,
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
                        labels=pat_e,
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
                        labels=g_label_e,
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
                    row_pitch=m2_join_u.dymin - m2_join_b.dymin,
                )  # via2_draw
    return c_inst


@gf.cell
def interdigit(
    sd_diff=rectangle,
    pc1=rectangle_array,
    pc2=rectangle_array,
    poly_con=rectangle,
    sd_l: float = 0.15,
    nf=1,
    patt=[""],
    gate_con_pos="top",
    pc_x=0.1,
    pc_spacing=0.1,
    label: bool = False,
    g_label: Strs | None = None,
    patt_label: bool = False,
) -> gf.Component:
    """Returns interdigitation related polygons.

    Args :
        sd_diff : source/drain diffusion rectangle.
        pc1: first poly contact array.
        pc2: second poly contact array.
        poly_con: poly contact.
        sd_diff_inter : inter source/drain diffusion rectangle.
        l_gate : gate length.
        inter_sd_l : inter diffusion length.
        nf : number of fingers.
        pat : string of the required pattern.
        gate_con_pos : position of gate contact.
    """
    c_inst = gf.Component()

    sd_diff = gf.get_component(sd_diff)
    poly_con = gf.get_component(poly_con)
    pc1 = gf.get_component(pc1)
    pc2 = gf.get_component(pc2)

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
                row_pitch=m2.dymax - m2.dymin + m2_spacing,
            )
            m2_arr.dmovey(pc2.dymax + m2_spacing)

            for i in range(nl):
                for j in range(int(nf)):
                    if pat[j] == nt[i]:
                        m1 = c_inst.add_ref(
                            gf.components.rectangle(
                                size=(
                                    pc_x,
                                    # poly_con.dxmax - poly_con.dxmin,
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
                                labels=pat,
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
                                labels=g_label,
                                label_valid_len=nl,
                                index=i,
                            )
                        )

        elif gate_con_pos == "bottom":
            m2_arr = c_inst.add_ref(
                component=m2,
                columns=1,
                rows=nl,
                row_pitch=-m2_y - m2_spacing,
            )
            m2_arr.dmovey(pc2.dymin - m2_spacing - m2_y)

            for i in range(nl):
                for j in range(int(nf)):
                    if pat[j] == nt[i]:
                        m1 = c_inst.add_ref(
                            gf.components.rectangle(
                                size=(
                                    # poly_con.dxmax - poly_con.dxmin,
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
                                labels=pat,
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
                                labels=g_label,
                                label_valid_len=nl,
                                index=i,
                            )
                        )

    return c_inst


def hv_gen(c, c_inst, volt, dg_encx: float = 0.1, dg_ency: float = 0.1) -> None:
    """Returns high voltage related polygons.

    Args :
        c_inst : dualgate enclosed component
        volt : operating voltage
        dg_encx : dualgate enclosure in x_direction
        dg_ency : dualgate enclosure in y_direction
    """
    if volt == "5V" or volt == "6V":
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
                gf.components.rectangle(
                    size=(dg.dxsize, dg.dysize), layer=layer["v5_xtor"]
                )
            )
            v5x.dxmin = dg.dxmin
            v5x.dymin = dg.dymin

    # return c


def bulk_gr_gen(
    c: gf.Component,
    c_inst: gf.Component,
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
                (c_inst.dxmax - c_inst.dxmin) + 2 * comp_spacing,
                (c_inst.dymax - c_inst.dymin) + 2 * poly2_comp_spacing,
            ),
            layer=layer["comp"],
        )
    )
    rect_bulk_in.dmove((c_inst.dxmin - comp_spacing, c_inst.dymin - poly2_comp_spacing))
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

    # c.add_ref(hv_gen(c_inst=B, volt=volt, dg_encx=dg_enc_cmp, dg_ency=dg_enc_cmp))
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
            labels=[sub_label],
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
            )
        )

    # return c


@gf.cell
def nfet_deep_nwell(
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

    dn_enc_lvpwell = 2.5
    lvpwell_enc_ncmp = 0.43

    if deepnwell == 1:
        lvp_rect = c.add_ref(
            gf.components.rectangle(
                size=(
                    inst_size[0] + (2 * lvpwell_enc_ncmp),
                    inst_size[1] + (2 * lvpwell_enc_ncmp),
                ),
                layer=layer["lvpwell"],
            )
        )

        lvp_rect.dxmin = inst_xmin - lvpwell_enc_ncmp
        lvp_rect.dymin = inst_ymin - lvpwell_enc_ncmp

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

    return c


def add_inter_sd_labels(
    c: gf.Component,
    nf: int,
    sd_label: Strs | None,
    poly1: gf.Component,
    l_gate: float,
    inter_sd_l: float,
    sd_diff_intr: gf.Component,
    label: bool,
    layer: LayerSpec,
    con_bet_fin: int,
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
    if con_bet_fin == 1:
        label_layer = layer["metal1_label"]
    else:
        label_layer = layer["comp_label"]

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
                labels=sd_label,
                label_valid_len=nf + 1,
                index=i + 1,
            )
        )


def add_gate_labels(
    c: gf.Component,
    g_label: Strs | None,
    pc1: gf.Component,
    c_pc: gf.Component,
    pc_spacing: float,
    nc1: int,
    nc2: int,
    pc2: gf.Component,
    label: bool,
    layer: LayerSpec,
    nf: int,
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
                labels=g_label,
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
                labels=g_label,
                label_valid_len=nf,
                index=(2 * i) + 1,
            )
        )


@gf.cell
def nfet(
    l_gate: float = 0.28,
    w_gate: float = 0.22,
    sd_con_col: int = 1,
    inter_sd_l: float = 0.24,
    nf: int = 1,
    grw: float = 0.22,
    volt: str = "3.3V",
    bulk: str = "None",
    con_bet_fin: int = 1,
    gate_con_pos: str = "alternating",
    interdig: int = 0,
    patt: str = "",
    deepnwell: int = 0,
    pcmpgr: int = 0,
    label: bool = False,
    sd_label: Strs | None = [],
    g_label: Strs = (),
    sub_label: str = "",
    patt_label: bool = False,
) -> gf.Component:
    """Return nfet.

    Args:
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
    con_pl_enc = 0.07
    dg_enc_cmp = 0.24
    dg_enc_poly = 0.4

    sd_l_con = (
        ((sd_con_col) * con_size) + ((sd_con_col - 1) * con_sp) + 2 * con_comp_enc
    )
    sd_l = sd_l_con

    # gds components to store a single instance and the generated device
    c = gf.Component()

    c_inst = gf.Component()

    # generating sd diffusion

    if interdig == 1 and nf > 1 and nf != len(patt) and patt != "":
        nf = len(patt)

    l_d = (
        nf * l_gate + (nf - 1) * inter_sd_l + 2 * (con_comp_enc)
    )  # diffution total length
    rect_d_intr = gf.components.rectangle(size=(l_d, w_gate), layer=layer["comp"])
    sd_diff_intr = c_inst.add_ref(rect_d_intr)

    #  generating sd contacts

    if w_gate <= con_size + 2 * con_comp_enc:
        cmpc_y = con_comp_enc + con_size + con_comp_enc

    else:
        cmpc_y = w_gate

    cmpc_size = (sd_l_con, cmpc_y)

    sd_diff = c_inst.add_ref(
        component=gf.components.rectangle(size=cmpc_size, layer=layer["comp"]),
        rows=1,
        columns=2,
        column_pitch=(cmpc_size[0] + sd_diff_intr.dxsize),
    )

    sd_diff.dxmin = sd_diff_intr.dxmin - cmpc_size[0]
    sd_diff.dymin = sd_diff_intr.dymin - (sd_diff.dysize - sd_diff_intr.dysize) / 2

    sd_con = via_stack(
        x_range=(sd_diff.dxmin, sd_diff_intr.dxmin),
        y_range=(sd_diff.dymin, sd_diff.dymax),
        base_layer=layer["comp"],
        metal_level=1,
    )
    if (
        column_pitch := sd_l + nf * l_gate + (nf - 1) * inter_sd_l + 2 * (con_comp_enc)
    ) != 0:
        c_inst.add_ref(component=sd_con, columns=2, column_pitch=column_pitch)
    else:
        c_inst.add_ref(component=sd_con)

    if con_bet_fin == 1 and nf > 1:
        inter_sd_con = via_stack(
            x_range=(
                sd_diff_intr.dxmin + con_comp_enc + l_gate,
                sd_diff_intr.dxmin + con_comp_enc + l_gate + inter_sd_l,
            ),
            y_range=(0, w_gate),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(
            component=inter_sd_con,
            columns=nf - 1,
            rows=1,
            column_pitch=(l_gate + inter_sd_l),
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
            labels=sd_label,
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
            labels=sd_label,
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

    c_pc = gf.Component()

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
        poly.dxmin = sd_diff_intr.dxmin + con_comp_enc
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
            component=c_pc, rows=nr, row_pitch=pc_size[1] + w_gate + 2 * end_cap
        )
        pc.dmove((poly.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv))

        # gate_lablel
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(pc.dxmin + c_pc.dxsize / 2, pc.dymin + c_pc.dysize / 2),
                layer=layer["metal1_label"],
                label=label,
                labels=g_label,
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
            column_pitch=2 * (inter_sd_l + l_gate),
        )
        poly1.dxmin = sd_diff_intr.dxmin + con_comp_enc
        poly1.dymin = sd_diff_intr.dymin - end_cap - e_c

        poly2 = c_inst.add_ref(
            rect_p2,
            rows=1,
            columns=floor(nf / 2),
            column_pitch=2 * (inter_sd_l + l_gate),
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
            component=c_pc, rows=1, columns=nc1, column_pitch=pc_spacing
        )
        pc1.dmove((poly1.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv_1))

        pc2 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc2, column_pitch=pc_spacing
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

        # add_gate_labels(c, g_label, pc1, c_pc, pc_spacing, nc1, nc2, pc2, label, layer, nf)

        if interdig == 1:
            c_inst.add_ref(
                interdigit(
                    sd_diff=sd_diff,
                    pc1=pc1,
                    pc2=pc2,
                    poly_con=poly_con,
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
                    w_gate + 2 * gate_np_enc,
                ),
                layer=layer["nplus"],
            )
        )
        nsdm.dxmin = sd_diff.dxmin - comp_np_enc
        nsdm.dymin = sd_diff_intr.dymin - gate_np_enc
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
            x_range=(rect_bulk.dxmin + 0.1, rect_bulk.dxmax - 0.1),
            y_range=(rect_bulk.dymin, rect_bulk.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(bulk_con)

        c.add_ref(
            labels_gen(
                label_str=sub_label,
                position=(
                    bulk_con.dxmin + bulk_con.dxsize / 2,
                    bulk_con.dymin + bulk_con.dysize / 2,
                ),
                layer=layer["metal1_label"],
                label=label,
                labels=[sub_label],
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

        # b_gr = c.add_ref(
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
        )

    # if bulk != "Guard Ring":
    else:
        c.add_ref(c_inst)

        inst_size = (c_inst.dxsize, c_inst.dysize)
        inst_xmin = c_inst.dxmin
        inst_ymin = c_inst.dymin

        # c.add_ref(
        #     hv_gen(c_inst=c_inst, volt=volt, dg_encx=dg_enc_cmp, dg_ency=dg_enc_poly)
        # )
        hv_gen(c, c_inst=c_inst, volt=volt, dg_encx=dg_enc_cmp, dg_ency=dg_enc_poly)

        c.add_ref(
            nfet_deep_nwell(
                deepnwell=deepnwell,
                pcmpgr=pcmpgr,
                inst_size=inst_size,
                inst_xmin=inst_xmin,
                inst_ymin=inst_ymin,
                grw=grw,
            )
        )

    return c


@gf.cell
def pfet_deep_nwell(
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

    return c


@gf.cell
def pfet(
    l_gate: float = 0.28,
    w_gate: float = 0.22,
    sd_con_col: int = 1,
    inter_sd_l: float = 0.24,
    nf: int = 1,
    grw: float = 0.22,
    volt: str = "3.3V",
    bulk: str = "None",
    con_bet_fin: int = 1,
    gate_con_pos: str = "alternating",
    interdig: int = 0,
    patt: str = "",
    deepnwell: int = 0,
    pcmpgr: int = 0,
    label: bool = False,
    sd_label: Strs | None = (),
    g_label: Strs = (),
    sub_label: str = "",
    patt_label: bool = False,
) -> gf.Component:
    """Return pfet.

    Args:
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
    con_pl_enc = 0.07
    dg_enc_cmp = 0.24
    dg_enc_poly = 0.4

    sd_l_con = (
        ((sd_con_col) * con_size) + ((sd_con_col - 1) * con_sp) + 2 * con_comp_enc
    )
    sd_l = sd_l_con

    # gds components to store a single instance and the generated device
    c = gf.Component()

    c_inst = gf.Component()

    # generating sd diffusion

    if interdig == 1 and nf > 1 and nf != len(patt) and patt != "":
        nf = len(patt)

    l_d = (
        nf * l_gate + (nf - 1) * inter_sd_l + 2 * (con_comp_enc)
    )  # diffution total length
    rect_d_intr = gf.components.rectangle(size=(l_d, w_gate), layer=layer["comp"])
    sd_diff_intr = c_inst.add_ref(rect_d_intr)

    # generating sd contacts

    if w_gate <= con_size + 2 * con_comp_enc:
        cmpc_y = con_comp_enc + con_size + con_comp_enc

    else:
        cmpc_y = w_gate

    cmpc_size = (sd_l_con, cmpc_y)

    sd_diff = c_inst.add_ref(
        component=gf.components.rectangle(size=cmpc_size, layer=layer["comp"]),
        rows=1,
        columns=2,
        column_pitch=(cmpc_size[0] + sd_diff_intr.dxsize),
    )
    sd_diff.dxmin = sd_diff_intr.dxmin - cmpc_size[0]
    sd_diff.dymin = sd_diff_intr.dymin - (sd_diff.dysize - sd_diff_intr.dysize) / 2

    sd_con = via_stack(
        x_range=(sd_diff.dxmin, sd_diff_intr.dxmin),
        y_range=(sd_diff.dymin, sd_diff.dymax),
        base_layer=layer["comp"],
        metal_level=1,
    )
    c_inst.add_ref(
        component=sd_con,
        columns=2,
        rows=1,
        column_pitch=sd_l + nf * l_gate + (nf - 1) * inter_sd_l + 2 * (con_comp_enc),
    )

    if con_bet_fin == 1 and nf > 1:
        inter_sd_con = via_stack(
            x_range=(
                sd_diff_intr.dxmin + con_comp_enc + l_gate,
                sd_diff_intr.dxmin + con_comp_enc + l_gate + inter_sd_l,
            ),
            y_range=(0, w_gate),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(
            component=inter_sd_con,
            columns=nf - 1,
            rows=1,
            column_pitch=l_gate + inter_sd_l,
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
            labels=sd_label,
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
            labels=sd_label,
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

    c_pc = gf.Component()

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
        poly.dxmin = sd_diff_intr.dxmin + con_comp_enc
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
            row_pitch=pc_size[1] + w_gate + 2 * end_cap,
        )
        pc.dmove((poly.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv))

        # gate_lablel
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(pc.dxmin + c_pc.dxsize / 2, pc.dymin + c_pc.dysize / 2),
                layer=layer["metal1_label"],
                label=label,
                labels=g_label,
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
            column_pitch=2 * (inter_sd_l + l_gate),
        )
        poly1.dxmin = sd_diff_intr.dxmin + con_comp_enc

        poly2 = c_inst.add_ref(
            rect_p2,
            rows=1,
            columns=floor(nf / 2),
            column_pitch=2 * (inter_sd_l + l_gate),
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
            component=c_pc, rows=1, columns=nc1, column_pitch=pc_spacing
        )
        pc1.dmove((poly1.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv_1))

        pc2 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc2, column_pitch=pc_spacing
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
            )
        )

        # dualgate generation

        # c.add_ref(
        #     hv_gen(c_inst=c_inst, volt=volt, dg_encx=dg_enc_cmp, dg_ency=dg_enc_poly)
        # )
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
                    w_gate + 2 * gate_pp_enc,
                ),
                layer=layer["pplus"],
            )
        )
        psdm.dxmin = sd_diff.dxmin - comp_pp_enc
        psdm.dymin = sd_diff_intr.dymin - gate_pp_enc
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
            x_range=(rect_bulk.dxmin + 0.1, rect_bulk.dxmax - 0.1),
            y_range=(rect_bulk.dymin, rect_bulk.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(bulk_con)

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
                labels=[sub_label],
                label_valid_len=1,
            )
        )

        # deep nwell generation

        c.add_ref(
            pfet_deep_nwell(
                deepnwell=deepnwell,
                pcmpgr=pcmpgr,
                enc_size=(sd_diff.dxsize + rect_bulk.dxsize, sd_diff.dysize),
                enc_xmin=sd_diff.dxmin,
                enc_ymin=sd_diff.dymin,
                nw_enc_pcmp=nw_enc_pcmp,
                grw=grw,
            )
        )

        # dualgate generation
        # c.add_ref(
        #     hv_gen(c_inst=c_inst, volt=volt, dg_encx=dg_enc_cmp, dg_ency=dg_enc_poly)
        # )
        hv_gen(c, c_inst=c_inst, volt=volt, dg_encx=dg_enc_cmp, dg_ency=dg_enc_poly)

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
        )
        # bulk guardring

    return c


@gf.cell
def nfet_06v0_nvt(
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
    sd_label: Strs | None = [],
    g_label: str = [],
    sub_label: str = "",
    patt_label: bool = False,
) -> gf.Component:
    """Draw Native NFET 6V transistor by specifying parameters.

    Arg:
        l      : Float of gate length
        w      : Float of gate width
        ld     : Float of diffusion length
        nf     : Integer of number of fingers
        grw    : Float of guard ring width [If enabled]
        bulk   : String of bulk connection type [None, Bulk Tie, Guard Ring]
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
    con_pl_enc = 0.07
    dg_enc_cmp = 0.24
    dg_enc_poly = 0.4

    sd_l_con = (
        ((sd_con_col) * con_size) + ((sd_con_col - 1) * con_sp) + 2 * con_comp_enc
    )
    sd_l = sd_l_con

    # gds components to store a single instance and the generated device
    c = gf.Component("sky_nfet_nvt_dev")

    c_inst = gf.Component("dev_temp")

    # generating sd diffusion

    if interdig == 1 and nf > 1 and nf != len(patt) and patt != "":
        nf = len(patt)

    l_d = (
        nf * l_gate + (nf - 1) * inter_sd_l + 2 * (con_comp_enc)
    )  # diffution total length
    rect_d_intr = gf.components.rectangle(size=(l_d, w_gate), layer=layer["comp"])
    sd_diff_intr = c_inst.add_ref(rect_d_intr)

    # generatin sd contacts

    if w_gate <= con_size + 2 * con_comp_enc:
        cmpc_y = con_comp_enc + con_size + con_comp_enc

    else:
        cmpc_y = w_gate

    cmpc_size = (sd_l_con, cmpc_y)

    sd_diff = c_inst.add_ref(
        component=gf.components.rectangle(size=cmpc_size, layer=layer["comp"]),
        rows=1,
        columns=2,
        column_pitch=cmpc_size[0] + sd_diff_intr.dxsize,
    )

    sd_diff.dxmin = sd_diff_intr.dxmin - cmpc_size[0]
    sd_diff.dymin = sd_diff_intr.dymin - (sd_diff.dysize - sd_diff_intr.dysize) / 2

    sd_con = via_stack(
        x_range=(sd_diff.dxmin, sd_diff_intr.dxmin),
        y_range=(sd_diff.dymin, sd_diff.dymax),
        base_layer=layer["comp"],
        metal_level=1,
    )
    c_inst.add_ref(
        component=sd_con,
        columns=2,
        rows=1,
        column_pitch=sd_l + nf * l_gate + (nf - 1) * inter_sd_l + 2 * (con_comp_enc),
    )

    if con_bet_fin == 1 and nf > 1:
        inter_sd_con = via_stack(
            x_range=(
                sd_diff_intr.dxmin + con_comp_enc + l_gate,
                sd_diff_intr.dxmin + con_comp_enc + l_gate + inter_sd_l,
            ),
            y_range=(0, w_gate),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(
            component=inter_sd_con,
            columns=nf - 1,
            rows=1,
            column_pitch=l_gate + inter_sd_l,
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
            labels=sd_label,
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
            labels=sd_label,
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
        poly.dxmin = sd_diff_intr.dxmin + con_comp_enc
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
            row_pitch=pc_size[1] + w_gate + 2 * end_cap,
        )
        pc.dmove((poly.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv))

        # gate_lablel
        c.add_ref(
            labels_gen(
                label_str="None",
                position=(pc.dxmin + c_pc.dxsize / 2, pc.dymin + c_pc.dysize / 2),
                layer=layer["metal1_label"],
                label=label,
                labels=g_label,
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
            column_pitch=2 * (inter_sd_l + l_gate),
        )
        poly1.dxmin = sd_diff_intr.dxmin + con_comp_enc
        poly1.dymin = sd_diff_intr.dymin - end_cap - e_c

        poly2 = c_inst.add_ref(
            rect_p2,
            rows=1,
            columns=floor(nf / 2),
            column_pitch=2 * (inter_sd_l + l_gate),
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
            component=c_pc, rows=1, columns=nc1, column_pitch=pc_spacing
        )
        pc1.dmove((poly1.dxmin - ((pc_x - l_gate) / 2), -pc_size[1] - end_cap + mv_1))

        pc2 = c_inst.add_ref(
            component=c_pc, rows=1, columns=nc2, column_pitch=pc_spacing
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
                    w_gate + 2 * gate_np_enc,
                ),
                layer=layer["nplus"],
            )
        )
        nsdm.dxmin = sd_diff.dxmin - comp_np_enc
        nsdm.dymin = sd_diff_intr.dymin - gate_np_enc
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
            x_range=(rect_bulk.dxmin + 0.1, rect_bulk.dxmax - 0.1),
            y_range=(rect_bulk.dymin, rect_bulk.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
        c_inst.add_ref(bulk_con)

        c.add_ref(
            labels_gen(
                label_str=sub_label,
                position=(
                    bulk_con.dxmin + bulk_con.dxsize / 2,
                    bulk_con.dymin + bulk_con.dysize / 2,
                ),
                layer=layer["metal1_label"],
                label=label,
                labels=[sub_label],
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
                labels=[sub_label],
                label_valid_len=1,
            )
        )

        dg = c.add_ref(
            gf.components.rectangle(
                size=(
                    B.dxsize + (2 * dg_enc_cmp),
                    B.dysize + (2 * dg_enc_cmp),
                ),
                layer=layer["dualgate"],
            )
        )
        dg.dxmin = B.dxmin - dg_enc_cmp
        dg.dymin = B.dymin - dg_enc_cmp

    if bulk != "Guard Ring":
        c.add_ref(c_inst)

        dg = c.add_ref(
            gf.components.rectangle(
                size=(
                    c_inst.dxsize + (2 * dg_enc_cmp),
                    c_inst.dysize + (2 * dg_enc_poly),
                ),
                layer=layer["dualgate"],
            )
        )
        dg.dxmin = c_inst.dxmin - dg_enc_cmp
        dg.dymin = c_inst.dymin - dg_enc_poly

    # generating native layer
    nat = c.add_ref(
        gf.components.rectangle(size=(dg.dxsize, dg.dysize), layer=layer["nat"])
    )

    nat.dxmin = dg.dxmin
    nat.dymin = dg.dymin

    return c


if __name__ == "__main__":
    c = pfet()
    # c = nfet()
    # c = nfet_06v0_nvt()
    # c = interdigit()
    # c = alter_interdig()
    c.show()
