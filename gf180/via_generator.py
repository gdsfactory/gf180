from math import ceil, floor
from typing import Any

import gdsfactory as gf
from gdsfactory.typings import Float2, LayerSpec, Size, Spacing

from gf180.layers import layer


@gf.cell
def via_generator(
    x_range: Float2 = (0, 1),
    y_range: Float2 = (0, 1),
    via_size: Float2 = (0.17, 0.17),
    via_layer: LayerSpec = (66, 44),
    via_enclosure: Float2 = (0.06, 0.06),
    via_spacing: Float2 = (0.17, 0.17),
) -> gf.Component:
    """Return only vias withen the range xrange and yrange while enclosing by via_enclosure
    and set number of rows and number of columns according to ranges and via size and spacing.

    Args:
        x_range: dx range.
        y_range: dy range.
        via_size: via size.
        via_layer: via layer.
        via_enclosure: via enclosure.
        via_spacing: via spacing.

    """
    c = gf.Component()

    width = x_range[1] - x_range[0]
    length = y_range[1] - y_range[0]
    nr = floor(length / (via_size[1] + via_spacing[1]))
    if (length - nr * via_size[1] - (nr - 1) * via_spacing[1]) / 2 < via_enclosure[1]:
        nr -= 1

    nr = max(nr, 1)
    nc = ceil(width / (via_size[0] + via_spacing[0]))

    if (
        round(width - nc * via_size[0] - (nc - 1) * via_spacing[0], 2)
    ) / 2 < via_enclosure[0]:
        nc -= 1

    nc = max(nc, 1)
    via_sp = (via_size[0] + via_spacing[0], via_size[1] + via_spacing[1])

    rect_via = gf.components.rectangle(size=via_size, layer=via_layer)

    via_arr = c.add_ref(
        rect_via, rows=nr, columns=nc, column_pitch=via_sp[0], row_pitch=via_sp[1]
    )

    via_arr.dmove((x_range[0], y_range[0]))

    via_arr.dmovex((width - nc * via_size[0] - (nc - 1) * via_spacing[0]) / 2)
    via_arr.dmovey((length - nr * via_size[1] - (nr - 1) * via_spacing[1]) / 2)
    return c


@gf.cell
def via_stack(
    x_range: Float2 = (0, 1),
    y_range: Float2 = (0, 1),
    metal_level: int = 1,
    con_size: Size = (0.22, 0.22),
    con_enc: float = 0.07,
    m_enc: float = 0.06,
    con_spacing: Spacing = (0.28, 0.28),
    via_size: Size = (0.22, 0.22),
    via_spacing: Spacing = (0.28, 0.28),
    via_enc: Float2 = (0.06, 0.06),
    base_layer: LayerSpec = layer["metal1"],
    **kwargs: Any,
) -> gf.Component:
    """Returns a via stack withen the range xrange and yrange and expecting the base_layer to be drawen.

    Args:
        x_range: dx range.
        y_range: dy range.
        metal_level: metal level.
        con_size: contact size.
        con_enc: contact enclosure.
        m_enc: metal enclosure.
        con_spacing: contact spacing.
        via_size: via size.
        via_spacing: via spacing.
        via_enc: via enclosure.


    return via stack till the metal level indicated where :
    metal_level 1 : till m1
    metal_level 2 : till m2
    metal_level 3 : till m3
    metal_level 4 : till m4
    metal_level 5 : till m5
    withen the range xrange and yrange and expecting the base_layer to be drawen

    """
    c = gf.Component()
    if metal_level >= 1:
        con_gen = via_generator(
            x_range=x_range,
            y_range=y_range,
            via_size=con_size,
            via_enclosure=(con_enc, con_enc),
            via_layer=layer["contact"],
            via_spacing=con_spacing,
        )
        con = c.add_ref(con_gen)
        m1_x = con.dxsize + 2 * m_enc
        m1_y = con.dysize + 2 * m_enc
        m1 = c.add_ref(gf.components.rectangle(size=(m1_x, m1_y), layer=base_layer))
        m1.dxmin = con.dxmin - m_enc
        m1.dymin = con.dymin - m_enc

    if metal_level >= 2:
        via1_gen = via_generator(
            x_range=(m1.dxmin, m1.dxmax),
            y_range=(m1.dymin, m1.dymax),
            via_size=via_size,
            via_enclosure=via_enc,
            via_layer=layer["via1"],
            via_spacing=via_spacing,
        )
        via1 = c.add_ref(via1_gen)

        if (via1.dxmax - via1.dxmin + 2 * m_enc[0]) < (
            via_size[0] + 2 * via_enc[0]
        ) and metal_level >= 3:
            m2_x = via_size[0] + 2 * via_enc[0]

        else:
            m2_x = via1.dxmax - via1.dxmin + 2 * m_enc[0]

        if (via1.dymax - via1.dymin + 2 * m_enc[1]) < (
            via_size[1] + 2 * via_enc[1]
        ) and metal_level >= 3:
            m2_y = via_size[1] + 2 * via_enc[1]

        else:
            m2_y = via1.dymax - via1.dymin + 2 * m_enc[1]

        m2_mx = (m2_x - (via1.dxmax - via1.dxmin)) / 2
        m2_my = (m2_y - (via1.dymax - via1.dymin)) / 2

        m2 = c.add_ref(
            gf.components.rectangle(size=(m2_x, m2_y), layer=layer["metal2"])
        )
        m2.dmove((via1.dxmin - m2_mx, via1.dymin - m2_my))

    return c


if __name__ == "__main__":
    c = via_stack()
    c.show()
    # c = vias_gen_draw(start_layer="li",end_layer="poly")
    # c.show()
