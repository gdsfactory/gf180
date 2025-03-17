import gdsfactory as gf
import numpy as np
from gdsfactory.typings import Float2, LayerSpec

from gf180.layers import layer
from gf180.via_generator import via_generator, via_stack


@gf.cell
def cap_mos_inst(
    lc: float = 0.1,
    wc: float = 0.1,
    cmp_w: float = 0.1,
    con_w: float = 0.1,
    pl_l: float = 0.1,
    cmp_ext: float = 0.1,
    pl_ext: float = 0.1,
    implant_layer: LayerSpec = layer["nplus"],
    implant_enc: Float2 = (0.1, 0.1),
    label: bool = False,
    g_label: str = "",
) -> gf.Component:
    """Returns mos cap simple instance.

    Args:
        lc : length of mos_cap.
        ws : width of mos_cap.
        cmp_w : width of layer["comp"].
        con_w : min width of comp contain contact.
        pl_l : length od layer["poly2"].
        cmp_ext : comp extension beyond poly2.
        pl_ext : poly2 extension beyond comp.
        implant_layer : Layer of implant [nplus,pplus].
        implant_enc : enclosure of implant_layer to comp.
        label : 1 to add labels.
        g_label : gate label.

    """
    c_inst = gf.Component()

    cmp = c_inst.add_ref(gf.components.rectangle(size=(cmp_w, wc), layer=layer["comp"]))

    cap_mk = c_inst.add_ref(
        gf.components.rectangle(
            size=(cmp.dxsize, cmp.dysize), layer=layer["mos_cap_mk"]
        )
    )
    cap_mk.dxmin = cmp.dxmin
    cap_mk.dymin = cmp.dymin

    if (column_pitch := cmp_w - con_w) != 0:
        c_inst.add_ref(
            component=via_stack(
                x_range=(cmp.dxmin, cmp.dxmin + con_w),
                y_range=(cmp.dymin, cmp.dymax),
                base_layer=layer["comp"],
                metal_level=1,
            ),
            columns=2,
            column_pitch=column_pitch,
        )  # comp contact
    else:
        c_inst.add_ref(
            component=via_stack(
                x_range=(cmp.dxmin, cmp.dxmin + con_w),
                y_range=(cmp.dymin, cmp.dymax),
                base_layer=layer["comp"],
                metal_level=1,
            )
        )

    imp_rect = c_inst.add_ref(
        gf.components.rectangle(
            size=(
                cmp.dxsize + (2 * implant_enc[0]),
                cmp.dysize + (2 * implant_enc[1]),
            ),
            layer=implant_layer,
        )
    )
    imp_rect.dxmin = cmp.dxmin - implant_enc[0]
    imp_rect.dymin = cmp.dymin - implant_enc[1]

    poly = c_inst.add_ref(
        gf.components.rectangle(size=(lc, pl_l), layer=layer["poly2"])
    )

    poly.dxmin = cmp.dxmin + cmp_ext
    poly.dymin = cmp.dymin - pl_ext

    pl_con_el = via_stack(
        x_range=(poly.dxmin, poly.dxmax),
        y_range=(poly.dymin, poly.dymin + con_w),
        base_layer=layer["poly2"],
        metal_level=1,
    )

    if (column_pitch := pl_l - con_w) != 0:
        pl_con = c_inst.add_ref(component=pl_con_el, rows=2, row_pitch=pl_l - con_w)
    else:
        pl_con = c_inst.add_ref(component=pl_con_el)

    # Gate labels_generation

    if label == 1:
        c_inst.add_label(
            g_label,
            position=(
                pl_con.dxmin + (pl_con.dxsize / 2),
                pl_con.dymin + (pl_con_el.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    pl_m1 = c_inst.add_ref(
        gf.components.rectangle(
            size=(pl_con.dxsize, pl_con.dysize), layer=layer["metal1"]
        )
    )
    pl_m1.dxmin = pl_con.dxmin
    pl_m1.dymin = pl_con.dymin

    return c_inst


@gf.cell
def cap_mos(
    type: str = "cap_nmos",
    lc: float = 0.1,
    wc: float = 0.1,
    volt: str = "3.3V",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    label: bool = False,
    g_label: str = "",
    sd_label: str = "",
) -> gf.Component:
    """Usage:-
     used to draw NMOS capacitor (Outside DNWELL) by specifying parameters
    Arguments:-
     l      : Float of diff length
     w      : Float of diff width.
    """
    c = gf.Component("cap_mos_dev")

    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07
    con_pl_enc = 0.07
    cmp_ext = 0.15 - con_comp_enc
    pl_ext = 0.17 - con_pl_enc

    np_enc_gate: float = 0.23
    np_enc_cmp: float = 0.16

    dg_enc_cmp = 0.24
    dg_enc_poly = 0.4
    lvpwell_enc_ncmp = 0.43
    dn_enc_lvpwell = 2.5

    grw = 0.36

    m1_w = 1
    pcmpgr_enc_dn = 2.5
    m1_ext = 0.82
    comp_pp_enc: float = 0.16
    dnwell_enc_pcmp = 1.1

    # end_cap: float = 0.22

    cmp_ed_w = con_size + (2 * con_comp_enc)
    cmp_w = (2 * (cmp_ed_w + cmp_ext)) + lc
    end_cap = pl_ext + cmp_ed_w

    pl_l = wc + (2 * end_cap)

    if "cap_nmos" in type:
        implant_layer = layer["nplus"]
    else:
        implant_layer = layer["pplus"]

    c_inst = c.add_ref(
        cap_mos_inst(
            cmp_w=cmp_w,
            lc=lc,
            wc=wc,
            pl_l=pl_l,
            cmp_ext=cmp_ed_w + cmp_ext,
            con_w=cmp_ed_w,
            pl_ext=end_cap,
            implant_layer=implant_layer,
            implant_enc=(np_enc_cmp, np_enc_gate),
            label=label,
            g_label=g_label,
        )
    )

    cmp_m1_polys = gf.Component(base=c_inst.cell.base).get_polygons_points()[
        layer["metal1"]
    ]
    cmp_m1_xmin = np.min(cmp_m1_polys[0][:, 0])
    cmp_m1_xmax = np.max(cmp_m1_polys[0][:, 0])
    cmp_m1_ymax = np.max(cmp_m1_polys[0][:, 1])

    # cmp_m1 = c.add_ref(gf.components.rectangle(size=(m1_w,w+m1_ext),layer=layer["metal1"]))
    cmp_m1_v = c.add_ref(
        component=gf.components.rectangle(
            size=(m1_w, wc + m1_ext), layer=layer["metal1"]
        ),
        rows=1,
        columns=2,
        column_pitch=m1_w + cmp_w - 2 * cmp_ed_w,
    )
    cmp_m1_v.dxmin = cmp_m1_xmin - (m1_w - (cmp_m1_xmax - cmp_m1_xmin))
    cmp_m1_v.dymax = cmp_m1_ymax

    cmp_m1_h = c.add_ref(
        gf.components.rectangle(size=(cmp_m1_v.dxsize, m1_w), layer=layer["metal1"])
    )
    cmp_m1_h.dxmin = cmp_m1_v.dxmin
    cmp_m1_h.dymax = cmp_m1_v.dymin

    # sd labels generation
    if label == 1:
        c.add_label(
            sd_label,
            position=(
                cmp_m1_h.dxmin + (cmp_m1_h.dxsize / 2),
                cmp_m1_h.dymin + (cmp_m1_h.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    # dualgate

    if volt == "5/6V":
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

    cmp_polys = gf.Component(base=c_inst.cell.base).get_polygons_points()[layer["comp"]]
    cmp_xmin = np.min(cmp_polys[0][:, 0])
    cmp_ymin = np.min(cmp_polys[0][:, 1])
    cmp_xmax = np.max(cmp_polys[0][:, 0])
    cmp_ymax = np.max(cmp_polys[0][:, 1])

    if "_b" in type:
        if "cap_nmos" in type:
            nwell = c.add_ref(
                gf.components.rectangle(
                    size=(
                        cmp_xmax - cmp_xmin + (2 * np_enc_cmp),
                        cmp_ymax - cmp_ymin + (2 * np_enc_gate),
                    ),
                    layer=layer["nwell"],
                )
            )
            nwell.dxmin = cmp_xmin - np_enc_cmp
            nwell.dymin = cmp_ymin - np_enc_gate
        else:
            lvpwell = c.add_ref(
                gf.components.rectangle(
                    size=(
                        cmp_xmax - cmp_xmin + (2 * np_enc_cmp),
                        cmp_ymax - cmp_ymin + (2 * np_enc_gate),
                    ),
                    layer=layer["lvpwell"],
                )
            )

            lvpwell.dxmin = cmp_xmin - np_enc_cmp
            lvpwell.dymin = cmp_ymin - np_enc_gate

    if deepnwell == 1:
        if type == "cap_nmos":
            lvp_rect = c.add_ref(
                gf.components.rectangle(
                    size=(
                        c_inst.dxsize + (2 * lvpwell_enc_ncmp),
                        c_inst.dysize + (2 * lvpwell_enc_ncmp),
                    ),
                    layer=layer["lvpwell"],
                )
            )

            lvp_rect.dxmin = c_inst.dxmin - lvpwell_enc_ncmp
            lvp_rect.dymin = c_inst.dymin - lvpwell_enc_ncmp

            dn_rect = c.add_ref(
                gf.components.rectangle(
                    size=(
                        lvp_rect.dxsize + (2 * dn_enc_lvpwell),
                        lvp_rect.dysize + (2 * dn_enc_lvpwell),
                    ),
                    layer=layer["nwell"],
                )
            )

            dn_rect.dxmin = lvp_rect.dxmin - dn_enc_lvpwell
            dn_rect.dymin = lvp_rect.dymin - dn_enc_lvpwell

        else:
            dn_rect = c.add_ref(
                gf.components.rectangle(
                    size=(
                        c_inst.dxsize + (2 * dnwell_enc_pcmp),
                        c_inst.dysize + (2 * dnwell_enc_pcmp),
                    ),
                    layer=layer["nwell"],
                )
            )

            dn_rect.dxmin = c_inst.dxmin - dnwell_enc_pcmp
            dn_rect.dymin = c_inst.dymin - dnwell_enc_pcmp

        if pcmpgr == 1:
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
            rect_pcmpgr_in.dmove(
                (dn_rect.dxmin - pcmpgr_enc_dn, dn_rect.dymin - pcmpgr_enc_dn)
            )
            rect_pcmpgr_out = c_temp_gr.add_ref(
                gf.components.rectangle(
                    size=(
                        (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) + 2 * grw,
                        (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) + 2 * grw,
                    ),
                    layer=layer["comp"],
                )
            )
            rect_pcmpgr_out.dmove(
                (rect_pcmpgr_in.dxmin - grw, rect_pcmpgr_in.dymin - grw)
            )
            c.add_ref(
                gf.boolean(
                    A=rect_pcmpgr_out,
                    B=rect_pcmpgr_in,
                    operation="A-B",
                    layer=layer["comp"],
                )
            )  # guardring Bullk

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
                        (rect_pcmpgr_out.dxmax - rect_pcmpgr_out.dxmin)
                        + 2 * comp_pp_enc,
                        (rect_pcmpgr_out.dymax - rect_pcmpgr_out.dymin)
                        + 2 * comp_pp_enc,
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
            )  # psdm

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
            )  # guardring metal1

    return c


if __name__ == "__main__":
    c = cap_mos()
    c.show()
