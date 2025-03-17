import gdsfactory as gf

from gf180.layers import layer
from gf180.via_generator import via_generator


@gf.cell
def cap_mim(
    mim_option: str = "A",
    metal_level: str = "M4",
    lc: float = 2,
    wc: float = 2,
    label: bool = False,
    top_label: str = "",
    bot_label: str = "",
) -> gf.Component:
    """Return mim cap.

    Args:
        min_option: MIM-A or MIM-B.
        metal_level: metal level. M4, M5, M6.
        lc: cap length.
        wc: cap width.
        label: 1 to add labels.
        top_label: top label.
        bot_label: bottom label.

    """
    c = gf.Component("mim_cap_dev")
    # used dimensions and layers

    # MIM Option selection
    if mim_option == "MIM-A":
        upper_layer = layer["metal3"]
        bottom_layer = layer["metal2"]
        via_layer = layer["via2"]
        up_label_layer = layer["metal3_label"]
        bot_label_layer = layer["metal2_label"]

    elif mim_option == "MIM-B":
        if metal_level == "M4":
            upper_layer = layer["metal4"]
            bottom_layer = layer["metal3"]
            via_layer = layer["via3"]
            up_label_layer = layer["metal4_label"]
            bot_label_layer = layer["metal3_label"]
        elif metal_level == "M5":
            upper_layer = layer["metal5"]
            bottom_layer = layer["metal4"]
            via_layer = layer["via4"]
            up_label_layer = layer["metal5_label"]
            bot_label_layer = layer["metal4_label"]
        elif metal_level == "M6":
            upper_layer = layer["metaltop"]
            bottom_layer = layer["metal5"]
            via_layer = layer["via5"]
            up_label_layer = layer["metaltop_label"]
            bot_label_layer = layer["metal5_label"]
    else:
        upper_layer = layer["metal3"]
        bottom_layer = layer["metal2"]
        via_layer = layer["via2"]
        up_label_layer = layer["metal3_label"]
        bot_label_layer = layer["metal2_label"]

    via_size = (0.22, 0.22)
    via_spacing = (0.5, 0.5)
    via_enc = (0.4, 0.4)

    bot_enc_top = 0.6
    l_mk_w = 0.1

    # drawing cap identifier and bottom , upper layers

    m_up = c.add_ref(
        gf.components.rectangle(
            size=(wc, lc),
            layer=upper_layer,
        )
    )

    fusetop = c.add_ref(
        gf.components.rectangle(size=(m_up.dxsize, m_up.dysize), layer=layer["fusetop"])
    )
    fusetop.dxmin = m_up.dxmin
    fusetop.dymin = m_up.dymin

    mim_l_mk = c.add_ref(
        gf.components.rectangle(size=(fusetop.dxsize, l_mk_w), layer=layer["mim_l_mk"])
    )
    mim_l_mk.dxmin = fusetop.dxmin
    mim_l_mk.dymin = fusetop.dymin

    m_dn = c.add_ref(
        gf.components.rectangle(
            size=(m_up.dxsize + (2 * bot_enc_top), m_up.dysize + (2 * bot_enc_top)),
            layer=bottom_layer,
        )
    )
    m_dn.dxmin = m_up.dxmin - bot_enc_top
    m_dn.dymin = m_up.dymin - bot_enc_top

    cap_mk = c.add_ref(
        gf.components.rectangle(size=(m_dn.dxsize, m_dn.dysize), layer=layer["cap_mk"])
    )
    cap_mk.dxmin = m_dn.dxmin
    cap_mk.dymin = m_dn.dymin

    # generating labels
    if label == 1:
        c.add_label(
            top_label,
            position=(m_up.dxmin + (m_up.dxsize / 2), m_dn.dxmin + (m_dn.dysize / 2)),
            layer=up_label_layer,
        )

        c.add_label(
            bot_label,
            position=(
                m_dn.dxmin + (m_dn.dxsize / 2),
                m_dn.dymin + (m_up.dymin - m_dn.dymin) / 2,
            ),
            layer=bot_label_layer,
        )

    # generating vias
    via = via_generator(
        x_range=(m_up.dxmin, m_up.dxmax),
        y_range=(m_up.dymin, m_up.dymax),
        via_enclosure=via_enc,
        via_layer=via_layer,
        via_size=via_size,
        via_spacing=via_spacing,
    )
    c.add_ref(via)
    return c


if __name__ == "__main__":
    c = cap_mim()
    c.show()
