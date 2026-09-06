"""MIM capacitor pcell matching Magic VLSI geometry exactly.

Implements gf180mcu::cap_mim_2p0fF_draw / cap_device from Magic generators.
Uses MIM-A (metal2/metal3) stack with fusetop cap plate.
"""

from math import floor

import gdsfactory as gf
from gdsfactory.add_pins import add_electrical_pins

from gf180mcu.layers import layer


@gf.cell(tags=["cap_mim"])
def cap_mim(
    mim_option: str = "A",
    metal_level: str = "M4",
    lc: float = 5,
    wc: float = 5,
    label: bool = False,
    top_label: str = "",
    bot_label: str = "",
) -> gf.Component:
    """Return MIM capacitor matching Magic VLSI geometry.

    Args:
        mim_option: MIM-A or MIM-B (only A currently matched).
        metal_level: metal level (ignored for MIM-A).
        lc: cap length (Magic 'l').
        wc: cap width (Magic 'w').
        label: whether to add labels.
        top_label: top label text.
        bot_label: bottom label text.
    """
    c = gf.Component()

    # Magic parameters (from cap_mim_2p0fF_draw, METALS3, non-THICKMET)
    cap_surround = 0.4
    bot_surround = 0.6
    end_surround = 0.31
    end_spacing = 0.60
    contact_size = 0.36
    metal_surround = 0.05
    via_size = 0.26
    diff_surround = 0.065  # from ruleset

    # Layer mapping for MIM-A (METALS3)
    upper_layer = layer["metal3"]
    bottom_layer = layer["metal2"]
    via_layer = layer["via2"]

    hw = wc / 2
    hl = lc / 2

    # Contact column height
    cl = lc + 2 * bot_surround - 2 * end_surround - metal_surround

    # Via pitches
    cap_via_pitch = 0.76  # MIM cap via pitch (observed from Magic output)
    arm_via_pitch = 0.52  # Standard via2 pitch (via_size + 0.26 spacing)

    # --- Cap via cluster (on fusetop) ---
    cap_via_region_hw = hw - cap_surround
    cap_via_region_hl = hl - cap_surround
    cap_ncols = floor((2 * cap_via_region_hw - via_size) / cap_via_pitch) + 1
    cap_nrows = floor((2 * cap_via_region_hl - via_size) / cap_via_pitch) + 1
    cap_array_w = (cap_ncols - 1) * cap_via_pitch + via_size
    cap_array_h = (cap_nrows - 1) * cap_via_pitch + via_size
    cap_via_x0 = -cap_array_w / 2
    cap_via_y0 = -cap_array_h / 2

    # --- Arm via cluster (contact column to the right) ---
    # arm_nrows: fit via array centered in the arm metal3 region with end_surround+diff_surround enclosure
    m3_arm_enc_y = end_surround + diff_surround  # nominal vertical enclosure (0.375)
    arm_nrows = (
        floor((lc + 2 * (bot_surround - m3_arm_enc_y - via_size / 2)) / arm_via_pitch)
        + 1
    )
    arm_ncols = floor(contact_size / via_size) + 2  # 3 for default params

    arm_via_array_w = (arm_ncols - 1) * arm_via_pitch + via_size
    arm_via_array_h = (arm_nrows - 1) * arm_via_pitch + via_size

    # Arm via start position (relative to fusetop center)
    cursor_x = hw + bot_surround + end_spacing
    arm_via_x0 = cursor_x - contact_size / 2 + (arm_via_pitch - end_surround)
    arm_via_y0 = -arm_via_array_h / 2  # centered vertically

    # Arm via center
    arm_via_cx = arm_via_x0 + arm_via_array_w / 2

    # --- Metal3 arm ---
    m3_arm_enc_x = 0.25  # horizontal via enclosure in m3
    # m3_arm_h is derived from cl (arm region height): m3_arm_h = cl + arm_via_pitch - via_size - 2*metal_surround
    m3_arm_w = arm_via_array_w + 2 * m3_arm_enc_x
    m3_arm_h = cl + arm_via_pitch - via_size - 2 * metal_surround
    m3_arm_cx = arm_via_cx
    m3_arm_right = m3_arm_cx + m3_arm_w / 2

    # --- Metal2 extents ---
    m2_xmin = -(hw + bot_surround)
    m2_ymin = -(hl + bot_surround)
    m2_xmax = m3_arm_right + end_surround
    m2_ymax = hl + bot_surround

    # --- GDS shift (Magic cap_draw centering) ---
    shift_x = -(m2_xmax + m2_xmin) / 2
    shift_y = -(m2_ymax + m2_ymin) / 2  # 0 for symmetric

    def gx(x: float) -> float:
        return round(x + shift_x, 4)

    def gy(y: float) -> float:
        return round(y + shift_y, 4)

    # ---- Draw all layers ----

    # Fusetop (cap plate)
    c.add_ref(gf.components.rectangle(size=(wc, lc), layer=layer["fusetop"])).move(
        (gx(-hw), gy(-hl))
    )

    # Cap marker (0.2 larger than fusetop on each side)
    c.add_ref(
        gf.components.rectangle(size=(wc + 0.4, lc + 0.4), layer=layer["cap_mk"])
    ).move((gx(-hw - 0.2), gy(-hl - 0.2)))

    # Metal3 on cap (fusetop shrunk by cap_surround)
    m3_cap_w = 2 * cap_via_region_hw
    m3_cap_h = 2 * cap_via_region_hl
    c.add_ref(
        gf.components.rectangle(size=(m3_cap_w, m3_cap_h), layer=upper_layer)
    ).move((gx(-cap_via_region_hw), gy(-cap_via_region_hl)))

    # Metal3 contact arm
    c.add_ref(
        gf.components.rectangle(size=(m3_arm_w, m3_arm_h), layer=upper_layer)
    ).move((gx(m3_arm_cx - m3_arm_w / 2), gy(-m3_arm_h / 2)))

    # Metal2 frame (4 strips forming a frame around fusetop with right arm)
    # Top strip
    c.add_ref(
        gf.components.rectangle(
            size=(m2_xmax - m2_xmin, m2_ymax - hl), layer=bottom_layer
        )
    ).move((gx(m2_xmin), gy(hl)))
    # Bottom strip
    c.add_ref(
        gf.components.rectangle(
            size=(m2_xmax - m2_xmin, -(m2_ymin + hl)), layer=bottom_layer
        )
    ).move((gx(m2_xmin), gy(m2_ymin)))
    # Left strip (between top and bottom strips, left of fusetop)
    c.add_ref(
        gf.components.rectangle(size=(-(m2_xmin + hw), lc), layer=bottom_layer)
    ).move((gx(m2_xmin), gy(-hl)))
    # Right strip (between top and bottom strips, right of fusetop including arm)
    c.add_ref(
        gf.components.rectangle(size=(m2_xmax - hw, lc), layer=bottom_layer)
    ).move((gx(hw), gy(-hl)))

    # Via2 on cap (left cluster)
    via_rect = gf.components.rectangle(size=(via_size, via_size), layer=via_layer)
    c.add_ref(
        via_rect,
        columns=cap_ncols,
        rows=cap_nrows,
        column_pitch=cap_via_pitch,
        row_pitch=cap_via_pitch,
    ).move((gx(cap_via_x0), gy(cap_via_y0)))

    # Via2 contact arm (right cluster)
    c.add_ref(
        via_rect,
        columns=arm_ncols,
        rows=arm_nrows,
        column_pitch=arm_via_pitch,
        row_pitch=arm_via_pitch,
    ).move((gx(arm_via_x0), gy(arm_via_y0)))

    # Add ports
    c.add_port(
        name="top",
        center=(gx(0), gy(0)),
        width=wc,
        orientation=90,
        layer=upper_layer,
        port_type="electrical",
    )
    c.add_port(
        name="bottom",
        center=(gx(m2_xmin + (m2_xmax - m2_xmin) / 2), gy(0)),
        width=m2_xmax - m2_xmin,
        orientation=90,
        layer=bottom_layer,
        port_type="electrical",
    )

    # VLSIR Simulation Metadata

    add_electrical_pins(c, port_pin_mapping={"top": ["top"], "bottom": ["bottom"]})
    return c
