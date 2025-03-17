from functools import partial

import gdsfactory as gf

from gf180.layers import LAYER, layer
from gf180.via_generator import via_generator

dn_rect = partial(gf.components.rectangle, layer=LAYER.dnwell)


@gf.cell
def pcmpgr_gen(dn_rect=dn_rect, grw: float = 0.36) -> gf.Component:
    """Return deepnwell guardring.

    Args:
        dn_rect : deepnwell polygon.
        grw : guardring width.

    """
    c = gf.Component()

    dn_rect = gf.get_component(dn_rect)

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


if __name__ == "__main__":
    c = pcmpgr_gen()
    c.show()
