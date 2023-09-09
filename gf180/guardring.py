from functools import partial

import gdsfactory as gf

from gf180.layers import LAYER, layer
from gf180.via_generator import via_generator

dn_rect = partial(gf.components.rectangle, layer=LAYER.dnwell)


@gf.cell
def pcmpgr_gen(dn_rect=dn_rect, grw: float = 0.36) -> gf.Component:
    """Return deepnwell guardring

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
                (dn_rect.xmax - dn_rect.xmin) + 2 * pcmpgr_enc_dn,
                (dn_rect.ymax - dn_rect.ymin) + 2 * pcmpgr_enc_dn,
            ),
            layer=layer["comp"],
        )
    )
    rect_pcmpgr_in.move((dn_rect.xmin - pcmpgr_enc_dn, dn_rect.ymin - pcmpgr_enc_dn))
    rect_pcmpgr_out = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (rect_pcmpgr_in.xmax - rect_pcmpgr_in.xmin) + 2 * grw,
                (rect_pcmpgr_in.ymax - rect_pcmpgr_in.ymin) + 2 * grw,
            ),
            layer=layer["comp"],
        )
    )
    rect_pcmpgr_out.move((rect_pcmpgr_in.xmin - grw, rect_pcmpgr_in.ymin - grw))
    c.add_ref(
        gf.geometry.boolean(
            A=rect_pcmpgr_out,
            B=rect_pcmpgr_in,
            operation="A-B",
            layer=layer["comp"],
        )
    )  # guardring bulk

    psdm_in = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (rect_pcmpgr_in.xmax - rect_pcmpgr_in.xmin) - 2 * comp_pp_enc,
                (rect_pcmpgr_in.ymax - rect_pcmpgr_in.ymin) - 2 * comp_pp_enc,
            ),
            layer=layer["pplus"],
        )
    )
    psdm_in.move(
        (
            rect_pcmpgr_in.xmin + comp_pp_enc,
            rect_pcmpgr_in.ymin + comp_pp_enc,
        )
    )
    psdm_out = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (rect_pcmpgr_out.xmax - rect_pcmpgr_out.xmin) + 2 * comp_pp_enc,
                (rect_pcmpgr_out.ymax - rect_pcmpgr_out.ymin) + 2 * comp_pp_enc,
            ),
            layer=layer["pplus"],
        )
    )
    psdm_out.move(
        (
            rect_pcmpgr_out.xmin - comp_pp_enc,
            rect_pcmpgr_out.ymin - comp_pp_enc,
        )
    )
    c.add_ref(
        gf.geometry.boolean(
            A=psdm_out, B=psdm_in, operation="A-B", layer=layer["pplus"]
        )
    )  # pplus_draw

    # generating contacts

    c.add_ref(
        via_generator(
            x_range=(
                rect_pcmpgr_in.xmin + con_size,
                rect_pcmpgr_in.xmax - con_size,
            ),
            y_range=(rect_pcmpgr_out.ymin, rect_pcmpgr_in.ymin),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # bottom contact

    c.add_ref(
        via_generator(
            x_range=(
                rect_pcmpgr_in.xmin + con_size,
                rect_pcmpgr_in.xmax - con_size,
            ),
            y_range=(rect_pcmpgr_in.ymax, rect_pcmpgr_out.ymax),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # upper contact

    c.add_ref(
        via_generator(
            x_range=(rect_pcmpgr_out.xmin, rect_pcmpgr_in.xmin),
            y_range=(
                rect_pcmpgr_in.ymin + con_size,
                rect_pcmpgr_in.ymax - con_size,
            ),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # right contact

    c.add_ref(
        via_generator(
            x_range=(rect_pcmpgr_in.xmax, rect_pcmpgr_out.xmax),
            y_range=(
                rect_pcmpgr_in.ymin + con_size,
                rect_pcmpgr_in.ymax - con_size,
            ),
            via_enclosure=(con_comp_enc, con_comp_enc),
            via_layer=layer["contact"],
            via_size=(con_size, con_size),
            via_spacing=(con_sp, con_sp),
        )
    )  # left contact

    comp_m1_in = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(rect_pcmpgr_in.size[0], rect_pcmpgr_in.size[1]),
            layer=layer["metal1"],
        )
    )

    comp_m1_out = c_temp_gr.add_ref(
        gf.components.rectangle(
            size=(
                (comp_m1_in.size[0]) + 2 * grw,
                (comp_m1_in.size[1]) + 2 * grw,
            ),
            layer=layer["metal1"],
        )
    )
    comp_m1_out.move((rect_pcmpgr_in.xmin - grw, rect_pcmpgr_in.ymin - grw))
    c.add_ref(
        gf.geometry.boolean(
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
