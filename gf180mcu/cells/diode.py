"""Diode pcells matching Magic VLSI geometry exactly.

Implements gf180mcu::diode_nd2ps and diode_pd2nw from Magic generators.

All geometry derived from XOR regression against Magic VLSI reference GDS files.

Key geometry rules (from reference analysis):
  nd2ps 03v3: guard_inner = wa/2+0.300, guard_outer = wa/2+0.680 (strip=0.380)
  nd2ps 06v0: guard_inner = wa/2+0.400, guard_outer = wa/2+0.760 (strip=0.360)
  pd2nw 03v3 inner: same as nd2ps 03v3
  pd2nw 06v0 inner: guard_inner = wa/2+0.360, guard_outer = wa/2+0.720 (strip=0.360)
  pd2nw 03v3 outer: inner_outer+0.450 to inner_outer+0.810
  pd2nw 06v0 outer: inner_outer+0.520 to inner_outer+0.880

Contact rules:
  nc_x = floor((wa+0.15)/0.50), pitch_x = 0.47 if nc_x==2 else 0.50
  Guard ring side: nc_guard(nc, volt), pitch = 0.47 always
  Contact inset from guard comp outer: 0.190 (03v3), 0.180 (06v0 or outer guard)
"""

import gdsfactory as gf
from gdsfactory.add_pins import add_electrical_pins
from gdsfactory.typings import Float2

from gf180mcu.cells.via_generator import via_generator, via_stack
from gf180mcu.layers import layer

# ---------------------------------------------------------------------------
# Helper: exact rectangle placement (bypasses gdsfactory snap_to_grid2x)
# ---------------------------------------------------------------------------


def _add_rect(
    c: gf.Component, x0: float, y0: float, x1: float, y1: float, lyr: str
) -> None:
    """Add an exact rectangle polygon directly, avoiding snap-to-grid rounding."""
    c.add_polygon([(x0, y0), (x0, y1), (x1, y1), (x1, y0)], layer=layer[lyr])


# ---------------------------------------------------------------------------
# Helper: contact position generation
# ---------------------------------------------------------------------------


def _positions(nc: int, pitch: float) -> list:
    """nc contact centre positions centred on zero."""
    if nc == 1:
        return [0.0]
    start = -(nc - 1) / 2.0 * pitch
    return [round(start + i * pitch, 4) for i in range(nc)]


def _nc_inner(w: float) -> int:
    """Number of inner device contacts in dimension w."""
    return int((w + 0.15) / 0.50)


def _nc_guard(nc: int, volt: str) -> int:
    """Number of guard ring side contacts given inner contact count."""
    if volt == "3.3V":
        return nc + (1 if nc >= 4 and nc % 2 == 0 else 0)
    else:  # 6.0V
        return nc + 1


def _inner_pitch(nc: int) -> float:
    """Pitch for nc inner contacts."""
    return 0.47 if nc == 2 else 0.50


def _nc_outer_guard_side(og_inner_y: float) -> int:
    """nc for outer guard ring side contacts (left/right columns).

    Contact centres must satisfy: center_y ≤ og_inner_y - 0.340.
    (Empirically derived from reference GDS: 0.340 = contact_half + 0.230 rule.)
    """
    max_y = og_inner_y - 0.340
    odd_nc = 0
    for n in range(500):
        if n * 0.47 <= max_y + 1e-9:
            odd_nc = 2 * n + 1
        else:
            break
    even_nc = 0
    for n in range(1, 500):
        if (n - 0.5) * 0.47 <= max_y + 1e-9:
            even_nc = 2 * n
        else:
            break
    return max(odd_nc, even_nc)


def _place_contacts(c: gf.Component, xs: list, ys: list) -> None:
    """Place 0.22x0.22 contacts at all (x,y) combinations."""
    size = 0.22
    con_rect = gf.components.rectangle(size=(size, size), layer=layer["contact"])
    for x in xs:
        for y in ys:
            c.add_ref(con_rect).move((x - size / 2, y - size / 2))


def _guard_ring_comp(
    c: gf.Component,
    guard_inner_x: float,
    guard_inner_y: float,
    guard_outer_x: float,
    guard_outer_y: float,
    lyr: str = "comp",
) -> None:
    """Draw guard ring comp as 4 strips (ring shape, no overlap with inner device comp)."""
    # Top strip: from y=guard_inner_y to y=guard_outer_y, x=-guard_outer to +guard_outer
    c.add_ref(
        gf.components.rectangle(
            size=(2 * guard_outer_x, guard_outer_y - guard_inner_y), layer=layer[lyr]
        )
    ).move((-guard_outer_x, guard_inner_y))
    # Bottom strip
    c.add_ref(
        gf.components.rectangle(
            size=(2 * guard_outer_x, guard_outer_y - guard_inner_y), layer=layer[lyr]
        )
    ).move((-guard_outer_x, -guard_outer_y))
    # Left strip: x=-guard_outer to x=-guard_inner, y=-guard_inner to y=+guard_inner
    c.add_ref(
        gf.components.rectangle(
            size=(guard_outer_x - guard_inner_x, 2 * guard_inner_y), layer=layer[lyr]
        )
    ).move((-guard_outer_x, -guard_inner_y))
    # Right strip
    c.add_ref(
        gf.components.rectangle(
            size=(guard_outer_x - guard_inner_x, 2 * guard_inner_y), layer=layer[lyr]
        )
    ).move((guard_inner_x, -guard_inner_y))


def _pplus_ring(
    c: gf.Component,
    guard_inner_x: float,
    guard_inner_y: float,
    guard_outer_x: float,
    guard_outer_y: float,
    outer_enc: float = 0.030,
    inner_enc: float = 0.030,
    cap_thickness: float = 0.010,
    lyr: str = "pplus",
) -> None:
    """Draw a pplus/nplus ring matching Magic VLSI decomposition (nd2ps style).

    Outer boundary: guard_outer + outer_enc, with thin caps protruding at
    centre of each edge (half-width = guard_inner - 0.125).
    Inner hole: guard_inner - inner_enc.
    Uses direct polygon placement to avoid snap_to_grid2x rounding.
    """
    pp_outer_x = round(guard_outer_x + outer_enc, 4)
    pp_outer_y = round(guard_outer_y + outer_enc, 4)
    main_outer_x = round(pp_outer_x - cap_thickness, 4)
    main_outer_y = round(pp_outer_y - cap_thickness, 4)
    pp_inner_x = round(guard_inner_x - inner_enc, 4)
    pp_inner_y = round(guard_inner_y - inner_enc, 4)
    cap_half_x = round(guard_inner_x - 0.125, 4)
    cap_half_y = round(guard_inner_y - 0.125, 4)

    # Main top band: x=[-main_outer_x, main_outer_x], y=[pp_inner_y, main_outer_y]
    _add_rect(c, -main_outer_x, pp_inner_y, main_outer_x, main_outer_y, lyr)
    # Main bottom band
    _add_rect(c, -main_outer_x, -main_outer_y, main_outer_x, -pp_inner_y, lyr)
    # Main left strip: x=[-main_outer_x, -pp_inner_x], y=[-pp_inner_y, pp_inner_y]
    _add_rect(c, -main_outer_x, -pp_inner_y, -pp_inner_x, pp_inner_y, lyr)
    # Main right strip
    _add_rect(c, pp_inner_x, -pp_inner_y, main_outer_x, pp_inner_y, lyr)
    # Thin top cap: x=[-cap_half_x, cap_half_x], y=[main_outer_y, pp_outer_y]
    _add_rect(c, -cap_half_x, main_outer_y, cap_half_x, pp_outer_y, lyr)
    # Thin bottom cap
    _add_rect(c, -cap_half_x, -pp_outer_y, cap_half_x, -main_outer_y, lyr)
    # Thin left cap: x=[-pp_outer_x, -main_outer_x], y=[-cap_half_y, cap_half_y]
    _add_rect(c, -pp_outer_x, -cap_half_y, -main_outer_x, cap_half_y, lyr)
    # Thin right cap
    _add_rect(c, main_outer_x, -cap_half_y, pp_outer_x, cap_half_y, lyr)


def _pplus_ring_outer(
    c: gf.Component,
    og_inner_x: float,
    og_inner_y: float,
    og_outer_x: float,
    og_outer_y: float,
    lyr: str = "pplus",
) -> None:
    """Draw pd2nw outer guard ring pplus matching Magic VLSI decomposition.

    Outer extent: og_outer_x+0.030 (x), og_outer_y+0.020 (y, asymmetric).
    Inner hole: og_inner - 0.160.
    Thin inner-transition strips at og_inner - 0.125 (connect sides to top/bottom).
    """
    opp_outer_x = round(og_outer_x + 0.030, 4)
    opp_outer_y = round(og_outer_y + 0.020, 4)
    main_outer_x = round(opp_outer_x - 0.010, 4)  # = og_outer + 0.020
    opp_inner_x = round(og_inner_x - 0.160, 4)
    opp_inner_y = round(og_inner_y - 0.160, 4)
    transition_y = round(og_inner_y - 0.125, 4)  # = opp_inner_y + 0.035

    # Main top: x=[-main_outer_x, main_outer_x], y=[transition_y, opp_outer_y]
    _add_rect(c, -main_outer_x, transition_y, main_outer_x, opp_outer_y, lyr)
    # Thin top transition: x=[-opp_outer_x, opp_outer_x], y=[opp_inner_y, transition_y]
    _add_rect(c, -opp_outer_x, opp_inner_y, opp_outer_x, transition_y, lyr)
    # Left side: x=[-opp_outer_x, -opp_inner_x], y=[-opp_inner_y, opp_inner_y]
    _add_rect(c, -opp_outer_x, -opp_inner_y, -opp_inner_x, opp_inner_y, lyr)
    # Right side
    _add_rect(c, opp_inner_x, -opp_inner_y, opp_outer_x, opp_inner_y, lyr)
    # Thin bottom transition
    _add_rect(c, -opp_outer_x, -transition_y, opp_outer_x, -opp_inner_y, lyr)
    # Main bottom
    _add_rect(c, -main_outer_x, -opp_outer_y, main_outer_x, -transition_y, lyr)


def _guard_contacts(
    c: gf.Component,
    guard_contact_x: float,
    guard_contact_y: float,
    nc_gx: int,
    nc_gy: int,
) -> None:
    """Place guard ring contacts on all four sides.

    Left/right cols at x=±guard_contact_x, y positions from nc_gy.
    Top/bottom rows at y=±guard_contact_y, x positions from nc_gx.
    """
    gy_pos = _positions(nc_gy, 0.47)
    gx_pos = _positions(nc_gx, 0.47)
    _place_contacts(c, [-guard_contact_x], gy_pos)
    _place_contacts(c, [guard_contact_x], gy_pos)
    _place_contacts(c, gx_pos, [guard_contact_y])
    _place_contacts(c, gx_pos, [-guard_contact_y])


def _guard_metal1(
    c: gf.Component,
    guard_inner_x: float,
    guard_inner_y: float,
    guard_comp_outer_x: float,
    guard_comp_outer_y: float,
    diff_surround: float = 0.065,
) -> None:
    """Draw guard ring metal1 as a ring (4 strips).

    Outer edge: guard_comp_outer - diff_surround.
    Inner edge: guard_inner + diff_surround.
    """
    m1_outer_x = round(guard_comp_outer_x - diff_surround, 4)
    m1_outer_y = round(guard_comp_outer_y - diff_surround, 4)
    m1_inner_x = round(guard_inner_x + diff_surround, 4)
    m1_inner_y = round(guard_inner_y + diff_surround, 4)
    # Top strip
    c.add_ref(
        gf.components.rectangle(
            size=(2 * m1_outer_x, m1_outer_y - m1_inner_y), layer=layer["metal1"]
        )
    ).move((-m1_outer_x, m1_inner_y))
    # Bottom strip
    c.add_ref(
        gf.components.rectangle(
            size=(2 * m1_outer_x, m1_outer_y - m1_inner_y), layer=layer["metal1"]
        )
    ).move((-m1_outer_x, -m1_outer_y))
    # Left strip
    c.add_ref(
        gf.components.rectangle(
            size=(m1_outer_x - m1_inner_x, 2 * m1_inner_y), layer=layer["metal1"]
        )
    ).move((-m1_outer_x, -m1_inner_y))
    # Right strip
    c.add_ref(
        gf.components.rectangle(
            size=(m1_outer_x - m1_inner_x, 2 * m1_inner_y), layer=layer["metal1"]
        )
    ).move((m1_inner_x, -m1_inner_y))


def _inner_metal1(c: gf.Component, wa: float, la: float) -> None:
    """Draw inner device metal1 rectangle.

    Long dimension gets half-0.010 extent; short dimension gets half-0.065.
    Square devices: wa (x) is treated as "long" → x gets -0.010.
    """
    if la > wa:
        m1_hx = round(wa / 2 - 0.065, 4)
        m1_hy = round(la / 2 - 0.010, 4)
    else:
        m1_hx = round(wa / 2 - 0.010, 4)
        m1_hy = round(la / 2 - 0.065, 4)
    c.add_ref(
        gf.components.rectangle(size=(2 * m1_hx, 2 * m1_hy), layer=layer["metal1"])
    ).move((-m1_hx, -m1_hy))


# ---------------------------------------------------------------------------
# diode_nd2ps
# ---------------------------------------------------------------------------


@gf.cell(tags=["diode"])
def diode_nd2ps(
    la: float = 0.45,
    wa: float = 0.45,
    volt: str = "3.3V",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    label: bool = False,
    p_label: str = "",
    n_label: str = "",
) -> gf.Component:
    """Draw N+/LVPWELL diode matching Magic VLSI geometry.

    Args:
        la: diffusion length (anode).
        wa: diffusion width (anode).
        volt: operating voltage ("3.3V" or "6.0V").
        deepnwell: use Deep NWELL device (not implemented).
        pcmpgr: use P+ Guard Ring for DNWELL (not implemented).
        label: add labels (not implemented).
        p_label: p terminal label.
        n_label: n terminal label.
    """
    c = gf.Component()

    diff_surround = 0.065
    lvpwell_enc = 0.12

    # Voltage-dependent geometry constants (all from reference GDS analysis)
    if volt == "3.3V":
        dev_spacing = 0.300  # gap between inner comp and guard ring comp inner edge
        guard_inner_offset = 0.300  # guard_inner = wa/2 + this
        guard_outer_offset = 0.680  # guard_outer = wa/2 + this (strip = 0.380)
        contact_inset = 0.190  # guard contact center to guard comp outer edge
        nplus_enc = 0.16
        dg_enc = 0.24
    else:  # 6.0V
        dev_spacing = 0.400
        guard_inner_offset = 0.400
        guard_outer_offset = 0.760
        contact_inset = 0.180
        nplus_enc = 0.16
        dg_enc = 0.24

    hw = wa / 2
    hl = la / 2

    # Guard ring comp geometry
    guard_inner_x = round(hw + guard_inner_offset, 4)
    guard_inner_y = round(hl + guard_inner_offset, 4)
    guard_outer_x = round(hw + guard_outer_offset, 4)
    guard_outer_y = round(hl + guard_outer_offset, 4)

    # Guard ring contact centre positions
    guard_contact_x = round(guard_outer_x - contact_inset, 4)
    guard_contact_y = round(guard_outer_y - contact_inset, 4)

    # Contact counts
    nc_x = _nc_inner(wa)
    nc_y = _nc_inner(la)
    nc_gx = _nc_guard(nc_x, volt)
    nc_gy = _nc_guard(nc_y, volt)
    pitch_x = _inner_pitch(nc_x)
    pitch_y = _inner_pitch(nc_y)

    # --- Inner device ---
    # Comp
    c.add_ref(gf.components.rectangle(size=(wa, la), layer=layer["comp"])).move(
        (-hw, -hl)
    )

    # Diode marker
    c.add_ref(gf.components.rectangle(size=(wa, la), layer=layer["diode_mk"])).move(
        (-hw, -hl)
    )

    # N+ implant (solid rect enclosing inner comp)
    nplus_hw = round(hw + nplus_enc, 4)
    nplus_hl = round(hl + nplus_enc, 4)
    c.add_ref(
        gf.components.rectangle(size=(2 * nplus_hw, 2 * nplus_hl), layer=layer["nplus"])
    ).move((-nplus_hw, -nplus_hl))

    # Inner contacts
    inner_xs = _positions(nc_x, pitch_x)
    inner_ys = _positions(nc_y, pitch_y)
    _place_contacts(c, inner_xs, inner_ys)

    # Inner metal1
    _inner_metal1(c, wa, la)

    # --- Guard ring (P+ comp ring) ---
    # Guard ring comp: 4 strips (ring shape)
    _guard_ring_comp(c, guard_inner_x, guard_inner_y, guard_outer_x, guard_outer_y)

    # P+ implant: ring with notched corners matching Magic VLSI decomposition
    _pplus_ring(
        c, guard_inner_x, guard_inner_y, guard_outer_x, guard_outer_y, lyr="pplus"
    )

    # Guard ring metal1 (ring: 4 strips)
    _guard_metal1(
        c, guard_inner_x, guard_inner_y, guard_outer_x, guard_outer_y, diff_surround
    )

    # Guard ring contacts
    _guard_contacts(c, guard_contact_x, guard_contact_y, nc_gx, nc_gy)

    # LVPWELL
    lvp_hx = round(guard_outer_x + lvpwell_enc, 4)
    lvp_hy = round(guard_outer_y + lvpwell_enc, 4)
    c.add_ref(
        gf.components.rectangle(size=(2 * lvp_hx, 2 * lvp_hy), layer=layer["lvpwell"])
    ).move((-lvp_hx, -lvp_hy))

    # Dualgate for 6.0V
    if volt == "6.0V":
        dg_hx = round(guard_outer_x + dg_enc, 4)
        dg_hy = round(guard_outer_y + dg_enc, 4)
        c.add_ref(
            gf.components.rectangle(
                size=(2 * dg_hx, 2 * dg_hy), layer=layer["dualgate"]
            )
        ).move((-dg_hx, -dg_hy))

    # Ports
    c.add_port(
        name="anode",
        center=(0, 0),
        width=wa,
        orientation=0,
        layer=layer["metal1"],
        port_type="electrical",
    )
    c.add_port(
        name="cathode",
        center=(0, guard_contact_y),
        width=2 * guard_outer_x,
        orientation=90,
        layer=layer["metal1"],
        port_type="electrical",
    )

    add_electrical_pins(
        c, port_pin_mapping={"anode": ["anode"], "cathode": ["cathode"]}
    )
    return c


# ---------------------------------------------------------------------------
# diode_pd2nw
# ---------------------------------------------------------------------------


@gf.cell(tags=["diode"])
def diode_pd2nw(
    la: float = 0.45,
    wa: float = 0.45,
    volt: str = "3.3V",
    deepnwell: bool = False,
    pcmpgr: bool = False,
    label: bool = False,
    p_label: str = "",
    n_label: str = "",
) -> gf.Component:
    """Draw P+/Nwell diode matching Magic VLSI geometry.

    Args:
        la: diffusion length.
        wa: diffusion width.
        volt: operating voltage ("3.3V" or "6.0V").
        deepnwell: use Deep NWELL device (not implemented).
        pcmpgr: use P+ Guard Ring for DNWELL (not implemented).
        label: add labels (not implemented).
        p_label: p terminal label.
        n_label: n terminal label.
    """
    c = gf.Component()

    diff_surround = 0.065
    lvpwell_enc = 0.12

    if volt == "3.3V":
        # Inner guard ring
        ig_inner_offset = 0.300  # guard_inner = wa/2 + this
        ig_outer_offset = 0.680  # guard_outer = wa/2 + this
        ig_contact_inset = 0.190
        nw_enc = 0.12
        nplus_enc_out = 0.16  # nplus outer enc on ig_outer
        nplus_enc_in = 0.090  # nplus inner enc on ig_inner (inward)
        lvpwell_enc = 0.12
        # Outer guard ring (relative to inner guard outer)
        og_inner_gap = 0.450  # outer_guard_inner = inner_guard_outer + this
        og_strip = 0.360  # outer_guard_outer = outer_guard_inner + this
        # outer_guard_outer = inner_guard_outer + 0.450 + 0.360 = inner_guard_outer + 0.810
        og_contact_inset = 0.180
        dg_enc = 0.24
    else:  # 6.0V
        ig_inner_offset = 0.360
        ig_outer_offset = 0.720
        ig_contact_inset = 0.180
        nw_enc = 0.16
        nplus_enc_out = 0.16
        nplus_enc_in = 0.070  # nplus inner enc (inward) for 6.0V
        lvpwell_enc = 0.16
        og_inner_gap = 0.520
        og_strip = 0.360
        og_contact_inset = 0.180
        dg_enc = 0.24

    hw = wa / 2
    hl = la / 2

    # Inner guard ring geometry
    ig_inner_x = round(hw + ig_inner_offset, 4)
    ig_inner_y = round(hl + ig_inner_offset, 4)
    ig_outer_x = round(hw + ig_outer_offset, 4)
    ig_outer_y = round(hl + ig_outer_offset, 4)
    ig_contact_x = round(ig_outer_x - ig_contact_inset, 4)
    ig_contact_y = round(ig_outer_y - ig_contact_inset, 4)

    # Outer guard ring geometry
    og_inner_x = round(ig_outer_x + og_inner_gap, 4)
    og_inner_y = round(ig_outer_y + og_inner_gap, 4)
    og_outer_x = round(og_inner_x + og_strip, 4)
    og_outer_y = round(og_inner_y + og_strip, 4)
    og_contact_x = round(og_outer_x - og_contact_inset, 4)
    og_contact_y = round(og_outer_y - og_contact_inset, 4)

    # Contact counts
    nc_x = _nc_inner(wa)
    nc_y = _nc_inner(la)
    nc_gx = _nc_guard(nc_x, volt)
    nc_gy = _nc_guard(nc_y, volt)
    pitch_x = _inner_pitch(nc_x)
    pitch_y = _inner_pitch(nc_y)

    # Outer guard ring side nc: side contacts are in y direction, constrained by og_inner_y
    nc_outer_side_y = _nc_outer_guard_side(og_inner_y)

    # --- Inner device (P+ diffusion) ---
    c.add_ref(gf.components.rectangle(size=(wa, la), layer=layer["comp"])).move(
        (-hw, -hl)
    )

    c.add_ref(gf.components.rectangle(size=(wa, la), layer=layer["diode_mk"])).move(
        (-hw, -hl)
    )

    # P+ implant on inner device
    pplus_hw = round(hw + 0.16, 4)
    pplus_hl = round(hl + 0.16, 4)
    c.add_ref(
        gf.components.rectangle(size=(2 * pplus_hw, 2 * pplus_hl), layer=layer["pplus"])
    ).move((-pplus_hw, -pplus_hl))

    # Inner contacts
    inner_xs = _positions(nc_x, pitch_x)
    inner_ys = _positions(nc_y, pitch_y)
    _place_contacts(c, inner_xs, inner_ys)

    # Inner metal1
    _inner_metal1(c, wa, la)

    # --- Inner guard ring (N+ comp ring = cathode) ---
    _guard_ring_comp(c, ig_inner_x, ig_inner_y, ig_outer_x, ig_outer_y)

    # N+ implant: ring (annular) matching inner guard ring comp
    np_outer_x = round(ig_outer_x + nplus_enc_out, 4)
    np_outer_y = round(ig_outer_y + nplus_enc_out, 4)
    np_inner_x = round(ig_inner_x - nplus_enc_in, 4)
    np_inner_y = round(ig_inner_y - nplus_enc_in, 4)
    _guard_ring_comp(c, np_inner_x, np_inner_y, np_outer_x, np_outer_y, lyr="nplus")

    # Inner guard ring metal1 (ring: 4 strips)
    _guard_metal1(c, ig_inner_x, ig_inner_y, ig_outer_x, ig_outer_y, diff_surround)

    # Inner guard ring contacts
    _guard_contacts(c, ig_contact_x, ig_contact_y, nc_gx, nc_gy)

    # Nwell
    nw_hx = round(ig_outer_x + nw_enc, 4)
    nw_hy = round(ig_outer_y + nw_enc, 4)
    c.add_ref(
        gf.components.rectangle(size=(2 * nw_hx, 2 * nw_hy), layer=layer["nwell"])
    ).move((-nw_hx, -nw_hy))

    # --- Outer guard ring (P+ comp = LVPWELL ground) ---
    _guard_ring_comp(c, og_inner_x, og_inner_y, og_outer_x, og_outer_y)

    # Outer pplus: ring with asymmetric outer (x:+0.030, y:+0.020) matching Magic decomposition
    _pplus_ring_outer(c, og_inner_x, og_inner_y, og_outer_x, og_outer_y, lyr="pplus")

    # Outer guard ring metal1 (ring: 4 strips)
    _guard_metal1(c, og_inner_x, og_inner_y, og_outer_x, og_outer_y, diff_surround)

    # Outer guard ring contacts (left/right columns only, no top/bottom rows)
    og_gy_positions = _positions(nc_outer_side_y, 0.47)
    _place_contacts(c, [-og_contact_x], og_gy_positions)
    _place_contacts(c, [og_contact_x], og_gy_positions)

    # LVPWELL: ring (outer guard ring to nwell boundary)
    lvp_outer_x = round(og_outer_x + lvpwell_enc, 4)
    lvp_outer_y = round(og_outer_y + lvpwell_enc, 4)
    lvp_inner_x = round(nw_hx, 4)
    lvp_inner_y = round(nw_hy, 4)
    _guard_ring_comp(
        c, lvp_inner_x, lvp_inner_y, lvp_outer_x, lvp_outer_y, lyr="lvpwell"
    )

    # Dualgate for 6.0V
    if volt == "6.0V":
        dg_hx = round(og_outer_x + dg_enc, 4)
        dg_hy = round(og_outer_y + dg_enc, 4)
        c.add_ref(
            gf.components.rectangle(
                size=(2 * dg_hx, 2 * dg_hy), layer=layer["dualgate"]
            )
        ).move((-dg_hx, -dg_hy))

    # Ports
    c.add_port(
        name="anode",
        center=(0, 0),
        width=wa,
        orientation=0,
        layer=layer["metal1"],
        port_type="electrical",
    )
    c.add_port(
        name="cathode",
        center=(0, ig_contact_y),
        width=2 * ig_outer_x,
        orientation=90,
        layer=layer["metal1"],
        port_type="electrical",
    )

    add_electrical_pins(
        c, port_pin_mapping={"anode": ["anode"], "cathode": ["cathode"]}
    )
    return c


# ---------------------------------------------------------------------------
# diode_nw2ps  (ported from KLayout draw_diode_nw2ps)
# ---------------------------------------------------------------------------


@gf.cell(tags=["diode"])
def diode_nw2ps(
    la: float = 0.1,
    wa: float = 0.1,
    cw: float = 0.1,
    volt: str = "3.3V",
    label: bool = False,
    p_label: str = "",
    n_label: str = "",
) -> gf.Component:
    """Draw 3.3V Nwell/Psub diode.

    Args:
        la: diffusion length (anode).
        wa: diffusion width (anode).
        cw: cathode width.
        volt: operating voltage ("3.3V" or "5/6V").
        label: add labels.
        p_label: p terminal label text.
        n_label: n terminal label text.
    """
    c = gf.Component()

    comp_spacing: float = 0.48
    np_enc_comp: float = 0.16
    pp_enc_comp: float = 0.16

    dg_enc_cmp = 0.24

    nwell_ncmp_enc = 0.16

    # n generation
    ncmp = c.add_ref(gf.components.rectangle(size=(wa, la), layer=layer["comp"]))
    nplus = c.add_ref(
        gf.components.rectangle(
            size=(
                ncmp.dxsize + (2 * np_enc_comp),
                ncmp.dysize + (2 * np_enc_comp),
            ),
            layer=layer["nplus"],
        )
    )
    nplus.dxmin = ncmp.dxmin - np_enc_comp
    nplus.dymin = ncmp.dymin - np_enc_comp
    diode_mk = c.add_ref(
        gf.components.rectangle(
            size=(ncmp.dxsize, ncmp.dysize), layer=layer["diode_mk"]
        )
    )
    diode_mk.dxmin = ncmp.dxmin
    diode_mk.dymin = ncmp.dymin

    nwell = c.add_ref(
        gf.components.rectangle(
            size=(
                ncmp.dxsize + (2 * nwell_ncmp_enc),
                ncmp.dysize + (2 * nwell_ncmp_enc),
            ),
            layer=layer["nwell"],
        )
    )
    nwell.dxmin = ncmp.dxmin - nwell_ncmp_enc
    nwell.dymin = ncmp.dymin - nwell_ncmp_enc

    n_con = c.add_ref(
        via_stack(
            x_range=(ncmp.dxmin, ncmp.dxmax),
            y_range=(ncmp.dymin, ncmp.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
    )  # ncomp contact

    # p generation
    pcmp = c.add_ref(gf.components.rectangle(size=(cw, la), layer=layer["comp"]))
    pcmp.dxmax = ncmp.dxmin - comp_spacing
    pplus = c.add_ref(
        gf.components.rectangle(
            size=(
                pcmp.dxsize + (2 * pp_enc_comp),
                pcmp.dysize + (2 * pp_enc_comp),
            ),
            layer=layer["pplus"],
        )
    )
    pplus.dxmin = pcmp.dxmin - pp_enc_comp
    pplus.dymin = pcmp.dymin - pp_enc_comp

    p_con = c.add_ref(
        via_stack(
            x_range=(pcmp.dxmin, pcmp.dxmax),
            y_range=(pcmp.dymin, pcmp.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
    )  # pcmp contact

    # labels generation
    if label == 1:
        c.add_label(
            n_label,
            position=(
                n_con.dxmin + (n_con.dxsize / 2),
                n_con.dymin + (n_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

        c.add_label(
            p_label,
            position=(
                p_con.dxmin + (p_con.dxsize / 2),
                p_con.dymin + (p_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    if volt == "5/6V":
        dg = c.add_ref(
            gf.components.rectangle(
                size=(
                    ncmp.dxmax - pcmp.dxmin + (2 * dg_enc_cmp),
                    ncmp.dysize + (2 * dg_enc_cmp),
                ),
                layer=layer["dualgate"],
            )
        )
        dg.dxmin = pcmp.dxmin - dg_enc_cmp
        dg.dymin = pcmp.dymin - dg_enc_cmp

    c.add_port(
        name="cathode",
        center=(
            n_con.dx + n_con.dxsize / 2,
            n_con.dy + n_con.dysize / 2,
        ),
        width=wa,
        orientation=0,
        layer=layer["metal1"],
        port_type="electrical",
    )
    c.add_port(
        name="anode",
        center=(
            p_con.dx + p_con.dxsize / 2,
            p_con.dy + p_con.dysize / 2,
        ),
        width=cw,
        orientation=0,
        layer=layer["metal1"],
        port_type="electrical",
    )

    add_electrical_pins(
        c, port_pin_mapping={"cathode": ["cathode"], "anode": ["anode"]}
    )
    return c


# ---------------------------------------------------------------------------
# diode_pw2dw  (ported from KLayout draw_diode_pw2dw)
# ---------------------------------------------------------------------------


@gf.cell(tags=["diode"])
def diode_pw2dw(
    la: float = 0.1,
    wa: float = 0.1,
    cw: float = 0.1,
    volt: str = "3.3V",
    pcmpgr: bool = False,
    label: bool = False,
    p_label: str = "",
    n_label: str = "",
) -> gf.Component:
    """Draw LVPWELL/DNWELL diode.

    Args:
        la: diffusion length (anode).
        wa: diffusion width (anode).
        cw: cathode width.
        volt: operating voltage ("3.3V" or "5/6V").
        pcmpgr: use P+ Guard Ring.
        label: add labels.
        p_label: p terminal label text.
        n_label: n terminal label text.
    """
    c = gf.Component()

    comp_spacing: float = 0.48
    np_enc_comp: float = 0.16
    pp_enc_comp: float = 0.16

    dg_enc_dn = 0.5

    lvpwell_enc_pcmp = 0.16
    dn_enc_lvpwell = 2.5

    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07

    pcmpgr_enc_dn = 2.5

    # p generation
    pcmp = c.add_ref(gf.components.rectangle(size=(wa, la), layer=layer["comp"]))
    pplus = c.add_ref(
        gf.components.rectangle(
            size=(
                pcmp.dxsize + (2 * pp_enc_comp),
                pcmp.dysize + (2 * pp_enc_comp),
            ),
            layer=layer["pplus"],
        )
    )
    pplus.dxmin = pcmp.dxmin - pp_enc_comp
    pplus.dymin = pcmp.dymin - pp_enc_comp
    diode_mk = c.add_ref(
        gf.components.rectangle(
            size=(pcmp.dxsize, pcmp.dysize), layer=layer["diode_mk"]
        )
    )
    diode_mk.dxmin = pcmp.dxmin
    diode_mk.dymin = pcmp.dymin

    lvpwell = c.add_ref(
        gf.components.rectangle(
            size=(
                pcmp.dxsize + (2 * lvpwell_enc_pcmp),
                pcmp.dysize + (2 * lvpwell_enc_pcmp),
            ),
            layer=layer["lvpwell"],
        )
    )
    lvpwell.dxmin = pcmp.dxmin - lvpwell_enc_pcmp
    lvpwell.dymin = pcmp.dymin - lvpwell_enc_pcmp

    p_con = c.add_ref(
        via_stack(
            x_range=(pcmp.dxmin, pcmp.dxmax),
            y_range=(pcmp.dymin, pcmp.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
    )  # pcomp_contact

    # n generation
    ncmp = c.add_ref(gf.components.rectangle(size=(cw, la), layer=layer["comp"]))
    ncmp.dxmax = pcmp.dxmin - comp_spacing
    nplus = c.add_ref(
        gf.components.rectangle(
            size=(
                ncmp.dxsize + (2 * np_enc_comp),
                ncmp.dysize + (2 * np_enc_comp),
            ),
            layer=layer["nplus"],
        )
    )
    nplus.dxmin = ncmp.dxmin - np_enc_comp
    nplus.dymin = ncmp.dymin - np_enc_comp

    n_con = c.add_ref(
        via_stack(
            x_range=(ncmp.dxmin, ncmp.dxmax),
            y_range=(ncmp.dymin, ncmp.dymax),
            base_layer=layer["comp"],
            metal_level=1,
        )
    )  # ncomp contact

    # labels generation
    if label == 1:
        c.add_label(
            n_label,
            position=(
                n_con.dxmin + (n_con.dxsize / 2),
                n_con.dymin + (n_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

        c.add_label(
            p_label,
            position=(
                p_con.dxmin + (p_con.dxsize / 2),
                p_con.dymin + (p_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

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
                    (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) + 2 * cw,
                    (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) + 2 * cw,
                ),
                layer=layer["comp"],
            )
        )
        rect_pcmpgr_out.dmove((rect_pcmpgr_in.dxmin - cw, rect_pcmpgr_in.dymin - cw))
        c.add_ref(
            gf.boolean(
                A=rect_pcmpgr_out,
                B=rect_pcmpgr_in,
                operation="A-B",
                layer=layer["comp"],
            )
        )  # guardring Bulk

        psdm_in = c_temp_gr.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) - 2 * pp_enc_comp,
                    (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) - 2 * pp_enc_comp,
                ),
                layer=layer["pplus"],
            )
        )
        psdm_in.dmove(
            (
                rect_pcmpgr_in.dxmin + pp_enc_comp,
                rect_pcmpgr_in.dymin + pp_enc_comp,
            )
        )
        psdm_out = c_temp_gr.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_pcmpgr_out.dxmax - rect_pcmpgr_out.dxmin) + 2 * pp_enc_comp,
                    (rect_pcmpgr_out.dymax - rect_pcmpgr_out.dymin) + 2 * pp_enc_comp,
                ),
                layer=layer["pplus"],
            )
        )
        psdm_out.dmove(
            (
                rect_pcmpgr_out.dxmin - pp_enc_comp,
                rect_pcmpgr_out.dymin - pp_enc_comp,
            )
        )
        c.add_ref(
            gf.boolean(A=psdm_out, B=psdm_in, operation="A-B", layer=layer["pplus"])
        )  # guardring psdm

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
                    (comp_m1_in.dxsize) + 2 * cw,
                    (comp_m1_in.dysize) + 2 * cw,
                ),
                layer=layer["metal1"],
            )
        )
        comp_m1_out.dmove((rect_pcmpgr_in.dxmin - cw, rect_pcmpgr_in.dymin - cw))
        c.add_ref(
            gf.boolean(
                A=rect_pcmpgr_out,
                B=rect_pcmpgr_in,
                operation="A-B",
                layer=layer["metal1"],
            )
        )  # guardring metal1

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

    c.add_port(
        name="anode",
        center=(
            p_con.dx + p_con.dxsize / 2,
            p_con.dy + p_con.dysize / 2,
        ),
        width=wa,
        orientation=0,
        layer=layer["metal1"],
        port_type="electrical",
    )
    c.add_port(
        name="cathode",
        center=(
            n_con.dx + n_con.dxsize / 2,
            n_con.dy + n_con.dysize / 2,
        ),
        width=cw,
        orientation=0,
        layer=layer["metal1"],
        port_type="electrical",
    )

    add_electrical_pins(
        c, port_pin_mapping={"anode": ["anode"], "cathode": ["cathode"]}
    )
    return c


# ---------------------------------------------------------------------------
# diode_dw2ps  (ported from KLayout draw_diode_dw2ps)
# ---------------------------------------------------------------------------


@gf.cell(tags=["diode"])
def diode_dw2ps(
    la: float = 0.1,
    wa: float = 0.1,
    cw: float = 0.1,
    volt: str = "3.3V",
    pcmpgr: bool = False,
    label: bool = False,
    p_label: str = "",
    n_label: str = "",
) -> gf.Component:
    """Draw DNWELL/Psub diode.

    Args:
        la: diffusion length (anode).
        wa: diffusion width (anode).
        cw: contact width (ring width for annular cathode).
        volt: operating voltage ("3.3V" or "5/6V").
        pcmpgr: use P+ Guard Ring.
        label: add labels.
        p_label: p terminal label text.
        n_label: n terminal label text.
    """
    c = gf.Component()

    if volt == "5/6V":
        dn_enc_ncmp = 0.66
    else:
        dn_enc_ncmp = 0.62

    comp_spacing = 0.32
    np_enc_comp: float = 0.16
    pp_enc_comp: float = 0.16

    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07

    dg_enc_dn = 0.5

    pcmpgr_enc_dn = 2.5

    if (wa < ((2 * cw) + comp_spacing)) or (la < ((2 * cw) + comp_spacing)):
        ncmp = c.add_ref(gf.components.rectangle(size=(wa, la), layer=layer["comp"]))

        n_con = c.add_ref(
            via_stack(
                x_range=(ncmp.dxmin, ncmp.dxmax),
                y_range=(ncmp.dymin, ncmp.dymax),
                base_layer=layer["comp"],
                metal_level=1,
            )
        )  # ncomp_contact

        nplus = c.add_ref(
            gf.components.rectangle(
                size=(
                    ncmp.dxsize + (2 * np_enc_comp),
                    ncmp.dysize + (2 * np_enc_comp),
                ),
                layer=layer["nplus"],
            )
        )
        nplus.dxmin = ncmp.dxmin - np_enc_comp
        nplus.dymin = ncmp.dymin - np_enc_comp
    else:
        c_temp = gf.Component("temp_store guard ring")
        ncmp_in = c_temp.add_ref(
            gf.components.rectangle(
                size=(wa - (2 * cw), la - (2 * cw)),
                layer=layer["comp"],
            )
        )
        ncmp_out = c_temp.add_ref(
            gf.components.rectangle(
                size=(wa, la),
                layer=layer["comp"],
            )
        )
        ncmp_out.dmove((ncmp_in.dxmin - cw, ncmp_in.dymin - cw))
        ncmp = c.add_ref(
            gf.boolean(
                A=ncmp_out,
                B=ncmp_in,
                operation="A-B",
                layer=layer["comp"],
            )
        )

        pplus_in = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (ncmp_in.dxmax - ncmp_in.dxmin) - 2 * pp_enc_comp,
                    (ncmp_in.dymax - ncmp_in.dymin) - 2 * pp_enc_comp,
                ),
                layer=layer["pplus"],
            )
        )
        pplus_in.dmove(
            (
                ncmp_in.dxmin + pp_enc_comp,
                ncmp_in.dymin + pp_enc_comp,
            )
        )
        pplus_out = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (ncmp_out.dxmax - ncmp_out.dxmin) + 2 * pp_enc_comp,
                    (ncmp_out.dymax - ncmp_out.dymin) + 2 * pp_enc_comp,
                ),
                layer=layer["pplus"],
            )
        )
        pplus_out.dmove(
            (
                ncmp_out.dxmin - pp_enc_comp,
                ncmp_out.dymin - pp_enc_comp,
            )
        )
        c.add_ref(
            gf.boolean(A=pplus_out, B=pplus_in, operation="A-B", layer=layer["nplus"])
        )  # nplus

        c.add_ref(
            via_generator(
                x_range=(
                    ncmp_in.dxmin + con_size,
                    ncmp_in.dxmax - con_size,
                ),
                y_range=(ncmp_out.dymin, ncmp_in.dymin),
                via_enclosure=(con_comp_enc, con_comp_enc),
                via_layer=layer["contact"],
                via_size=(con_size, con_size),
                via_spacing=(con_sp, con_sp),
            )
        )  # bottom contact

        c.add_ref(
            via_generator(
                x_range=(
                    ncmp_in.dxmin + con_size,
                    ncmp_in.dxmax - con_size,
                ),
                y_range=(ncmp_in.dymax, ncmp_out.dymax),
                via_enclosure=(con_comp_enc, con_comp_enc),
                via_layer=layer["contact"],
                via_size=(con_size, con_size),
                via_spacing=(con_sp, con_sp),
            )
        )  # upper contact

        n_con = c.add_ref(
            via_generator(
                x_range=(ncmp_out.dxmin, ncmp_in.dxmin),
                y_range=(
                    ncmp_in.dymin + con_size,
                    ncmp_in.dymax - con_size,
                ),
                via_enclosure=(con_comp_enc, con_comp_enc),
                via_layer=layer["contact"],
                via_size=(con_size, con_size),
                via_spacing=(con_sp, con_sp),
            )
        )  # left contact

        c.add_ref(
            via_generator(
                x_range=(ncmp_in.dxmax, ncmp_out.dxmax),
                y_range=(
                    ncmp_in.dymin + con_size,
                    ncmp_in.dymax - con_size,
                ),
                via_enclosure=(con_comp_enc, con_comp_enc),
                via_layer=layer["contact"],
                via_size=(con_size, con_size),
                via_spacing=(con_sp, con_sp),
            )
        )  # right contact

        comp_m1_in = c_temp.add_ref(
            gf.components.rectangle(
                size=(ncmp_in.dxsize, ncmp_in.dysize),
                layer=layer["metal1"],
            )
        )

        comp_m1_out = c_temp.add_ref(
            gf.components.rectangle(
                size=(
                    (comp_m1_in.dxsize) + 2 * cw,
                    (comp_m1_in.dxsize) + 2 * cw,
                ),
                layer=layer["metal1"],
            )
        )
        comp_m1_out.dmove((ncmp_in.dxmin - cw, ncmp_in.dymin - cw))
        c.add_ref(
            gf.boolean(
                A=ncmp_out,
                B=ncmp_in,
                operation="A-B",
                layer=layer["metal1"],
            )
        )  # guardring metal1

    # labels generation
    if label == 1:
        c.add_label(
            n_label,
            position=(
                n_con.dxmin + (n_con.dxsize / 2),
                n_con.dymin + (n_con.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    # generate dnwell

    dn_rect = c.add_ref(
        gf.components.rectangle(
            size=(
                ncmp.dxsize + (2 * dn_enc_ncmp),
                ncmp.dysize + (2 * dn_enc_ncmp),
            ),
            layer=layer["dnwell"],
        )
    )
    dn_rect.dxmin = ncmp.dxmin - dn_enc_ncmp
    dn_rect.dymin = ncmp.dymin - dn_enc_ncmp

    diode_mk = c.add_ref(
        gf.components.rectangle(
            size=(dn_rect.dxsize, dn_rect.dysize), layer=layer["diode_mk"]
        )
    )
    diode_mk.dxmin = dn_rect.dxmin
    diode_mk.dymin = dn_rect.dymin

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
                    (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) + 2 * cw,
                    (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) + 2 * cw,
                ),
                layer=layer["comp"],
            )
        )
        rect_pcmpgr_out.dmove((rect_pcmpgr_in.dxmin - cw, rect_pcmpgr_in.dymin - cw))
        c.add_ref(
            gf.boolean(
                A=rect_pcmpgr_out,
                B=rect_pcmpgr_in,
                operation="A-B",
                layer=layer["comp"],
            )
        )  # guardring Bulk

        psdm_in = c_temp_gr.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) - 2 * pp_enc_comp,
                    (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) - 2 * pp_enc_comp,
                ),
                layer=layer["pplus"],
            )
        )
        psdm_in.dmove(
            (
                rect_pcmpgr_in.dxmin + pp_enc_comp,
                rect_pcmpgr_in.dymin + pp_enc_comp,
            )
        )
        psdm_out = c_temp_gr.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_pcmpgr_out.dxmax - rect_pcmpgr_out.dxmin) + 2 * pp_enc_comp,
                    (rect_pcmpgr_out.dymax - rect_pcmpgr_out.dymin) + 2 * pp_enc_comp,
                ),
                layer=layer["pplus"],
            )
        )
        psdm_out.dmove(
            (
                rect_pcmpgr_out.dxmin - pp_enc_comp,
                rect_pcmpgr_out.dymin - pp_enc_comp,
            )
        )
        c.add_ref(
            gf.boolean(A=psdm_out, B=psdm_in, operation="A-B", layer=layer["pplus"])
        )  # psdm

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

        p_con = c.add_ref(
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
        )  # left contact

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
        )  # right contact

        # labels generation
        if label == 1:
            c.add_label(
                p_label,
                position=(
                    p_con.dxmin + (p_con.dxsize / 2),
                    p_con.dymin + (p_con.dysize / 2),
                ),
                layer=layer["metal1_label"],
            )

        comp_m1_in = c_temp_gr.add_ref(
            gf.components.rectangle(
                size=(rect_pcmpgr_in.dxsize, rect_pcmpgr_in.dysize),
                layer=layer["metal1"],
            )
        )

        comp_m1_out = c_temp_gr.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) + 2 * cw,
                    (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) + 2 * cw,
                ),
                layer=layer["metal1"],
            )
        )
        comp_m1_out.dmove((rect_pcmpgr_in.dxmin - cw, rect_pcmpgr_in.dymin - cw))
        c.add_ref(
            gf.boolean(
                A=rect_pcmpgr_out,
                B=rect_pcmpgr_in,
                operation="A-B",
                layer=layer["metal1"],
            )
        )  # guardring metal1

    # generate dualgate

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

    c.add_port(
        name="cathode",
        center=(
            n_con.dx + n_con.dxsize / 2,
            n_con.dy + n_con.dysize / 2,
        ),
        width=wa,
        orientation=0,
        layer=layer["metal1"],
        port_type="electrical",
    )

    pin_mapping: dict[str, list[str]] = {"cathode": ["cathode"]}
    if pcmpgr == 1:
        c.add_port(
            name="anode",
            center=(
                p_con.dx + p_con.dxsize / 2,
                p_con.dy + p_con.dysize / 2,
            ),
            width=cw,
            orientation=0,
            layer=layer["metal1"],
            port_type="electrical",
        )
        pin_mapping["anode"] = ["anode"]

    add_electrical_pins(c, port_pin_mapping=pin_mapping)
    return c


# ---------------------------------------------------------------------------
# sc_diode  (ported from KLayout draw_sc_diode)
# ---------------------------------------------------------------------------


@gf.cell(tags=["diode"])
def sc_diode(
    la: float = 0.1,
    wa: float = 0.1,
    cw: float = 0.1,
    m: int = 1,
    pcmpgr: bool = False,
    label: bool = False,
    p_label: str = "",
    n_label: str = "",
) -> gf.Component:
    """Draw Schottky diode with interdigitated cathode/anode array.

    Args:
        la: diffusion length (anode).
        wa: diffusion width (anode).
        cw: cathode width.
        m: number of anode fingers.
        pcmpgr: use P+ Guard Ring.
        label: add labels.
        p_label: p terminal label text.
        n_label: n terminal label text.
    """
    c = gf.Component()

    sc_enc_comp = 0.16
    sc_comp_spacing = 0.28
    dn_enc_sc_an = 1.4
    np_enc_comp = 0.03
    m1_w = 0.23
    pcmpgr_enc_dn = 2.5
    pp_enc_comp: float = 0.16

    con_size = 0.22
    con_sp = 0.28
    con_comp_enc = 0.07

    @gf.cell(tags=["diode"])
    def sc_cathode_strap(size: Float2 = (0.1, 0.1)) -> gf.Component:
        """Return sc_diode cathode array element."""
        c = gf.Component()

        ncmp = c.add_ref(gf.components.rectangle(size=size, layer=layer["comp"]))

        nplus = c.add_ref(
            gf.components.rectangle(
                size=(
                    ncmp.dxsize + (2 * np_enc_comp),
                    ncmp.dysize + (2 * np_enc_comp),
                ),
                layer=layer["nplus"],
            )
        )
        nplus.dxmin = ncmp.dxmin - np_enc_comp
        nplus.dymin = ncmp.dymin - np_enc_comp

        c.add_ref(
            via_stack(
                x_range=(ncmp.dxmin, ncmp.dxmax),
                y_range=(ncmp.dymin, ncmp.dymax),
                base_layer=layer["comp"],
                metal_level=1,
            )
        )  # ncomp contact

        return c

    @gf.cell(tags=["diode"])
    def sc_anode_strap(size: Float2 = (0.1, 0.1)) -> gf.Component:
        """Return sc_diode anode array element."""
        c = gf.Component()

        cmp = c.add_ref(gf.components.rectangle(size=size, layer=layer["comp"]))

        c.add_ref(
            via_stack(
                x_range=(cmp.dxmin, cmp.dxmax),
                y_range=(cmp.dymin, cmp.dymax),
                base_layer=layer["comp"],
                metal_level=1,
            )
        )  # comp contact

        return c

    sc_an = sc_anode_strap(size=(wa, la))
    sc_cath = sc_cathode_strap(size=(cw, la))

    sc_cathode = c.add_ref(
        sc_cath,
        rows=1,
        columns=(m + 1),
        column_pitch=(cw + wa + (2 * sc_comp_spacing)),
    )

    # Metal1 bounds of one cathode strap (relative to strap origin at 0,0).
    # via_stack places metal on base_layer with: xmin = con.xmin - m_enc, xmax = xmin + (con.xsize + 2*m_enc)
    # For a (0, cw) range with 1 contact centred: con.xmin = (0 + cw)/2 - 0.11 - cw/2 = -0.06 (from via_generator centering)
    # m_enc = 0.06, con_enc = 0.07  → metal.xmin = con.xmin - m_enc = -0.06 - 0.06 = -0.12
    # Use via_stack bbox which is the actual metal extent
    cath_m1_xmin = sc_cath.dxmin
    cath_m1_ymin = sc_cath.dymin
    cath_m1_xmax = sc_cath.dxmax

    cath_m1_v = c.add_ref(
        gf.components.rectangle(
            size=(
                cath_m1_xmax - cath_m1_xmin,
                cath_m1_ymin - sc_cathode.dymin + m1_w,
            ),
            layer=layer["metal1"],
        ),
        rows=1,
        columns=(m + 1),
        column_pitch=(cw + wa + (2 * sc_comp_spacing)),
    )

    cath_m1_v.dxmin = cath_m1_xmin
    cath_m1_v.dymax = cath_m1_ymin

    cath_m1_h = c.add_ref(
        gf.components.rectangle(size=(cath_m1_v.dxsize, m1_w), layer=layer["metal1"])
    )
    cath_m1_h.dxmin = cath_m1_v.dxmin
    cath_m1_h.dymax = cath_m1_v.dymin

    # cathode label generation
    if label == 1:
        c.add_label(
            n_label,
            position=(
                cath_m1_h.dxmin + (cath_m1_h.dxsize / 2),
                cath_m1_h.dymin + (cath_m1_h.dysize / 2),
            ),
            layer=layer["metal1_label"],
        )

    sc_anode = c.add_ref(
        sc_an,
        rows=1,
        columns=m,
        column_pitch=(wa + cw + (2 * sc_comp_spacing)),
    )

    sc_anode.dxmin = sc_cathode.dxmin + (cw + sc_comp_spacing)

    # Metal1 bounds of one anode strap in c coordinate system.
    # sc_an.dxmin/dymin already accounts for via_stack enclosure.
    # sc_anode.dxmin = position where first strap's component origin lands (including metal offset)
    an_m1_xmin = sc_anode.dxmin  # = placement_x + sc_an.dxmin
    an_m1_ymin = sc_anode.dymin
    an_m1_xmax = sc_anode.dxmin + (sc_an.dxmax - sc_an.dxmin)  # width of one strap
    an_m1_ymax = sc_anode.dymin + (sc_an.dymax - sc_an.dymin)  # height of one strap

    if m > 1:
        an_m1_v = c.add_ref(
            gf.components.rectangle(
                size=(
                    an_m1_xmax - an_m1_xmin,
                    cath_m1_ymin - sc_an.dymin + m1_w,
                ),
                layer=layer["metal1"],
            ),
            rows=1,
            columns=m,
            column_pitch=(cw + wa + (2 * sc_comp_spacing)),
        )

        an_m1_v.dxmin = an_m1_xmin
        an_m1_v.dymin = an_m1_ymax

        an_m1_h = c.add_ref(
            gf.components.rectangle(size=(an_m1_v.dxsize, m1_w), layer=layer["metal1"])
        )
        an_m1_h.dxmin = an_m1_v.dxmin
        an_m1_h.dymin = an_m1_v.dymax

        # anode label generation
        if label == 1:
            c.add_label(
                p_label,
                position=(
                    an_m1_h.dxmin + (an_m1_h.dxsize / 2),
                    an_m1_h.dymin + (an_m1_h.dysize / 2),
                ),
                layer=layer["metal1_label"],
            )

    else:
        # anode label generation
        if label == 1:
            c.add_label(
                p_label,
                position=(
                    an_m1_xmin + ((an_m1_xmax - an_m1_xmin) / 2),
                    an_m1_ymin + ((an_m1_ymax - an_m1_ymin) / 2),
                ),
                layer=layer["metal1_label"],
            )

    # schottky_diode marker
    diode_mk = c.add_ref(
        gf.components.rectangle(
            size=(
                sc_cathode.dxsize + (2 * sc_enc_comp),
                sc_cathode.dysize + (2 * sc_enc_comp),
            ),
            layer=layer["schottky_diode"],
        )
    )
    diode_mk.dxmin = sc_cathode.dxmin - sc_enc_comp
    diode_mk.dymin = sc_cathode.dymin - sc_enc_comp

    # dnwell
    dn_rect = c.add_ref(
        gf.components.rectangle(
            size=(
                sc_anode.dxsize + (2 * dn_enc_sc_an),
                sc_anode.dysize + (2 * dn_enc_sc_an),
            ),
            layer=layer["dnwell"],
        )
    )
    dn_rect.dxmin = sc_anode.dxmin - dn_enc_sc_an
    dn_rect.dymin = sc_anode.dymin - dn_enc_sc_an

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
                    (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) + 2 * cw,
                    (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) + 2 * cw,
                ),
                layer=layer["comp"],
            )
        )
        rect_pcmpgr_out.dmove((rect_pcmpgr_in.dxmin - cw, rect_pcmpgr_in.dymin - cw))
        c.add_ref(
            gf.boolean(
                A=rect_pcmpgr_out,
                B=rect_pcmpgr_in,
                operation="A-B",
                layer=layer["comp"],
            )
        )  # guardring Bulk

        psdm_in = c_temp_gr.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_pcmpgr_in.dxmax - rect_pcmpgr_in.dxmin) - 2 * pp_enc_comp,
                    (rect_pcmpgr_in.dymax - rect_pcmpgr_in.dymin) - 2 * pp_enc_comp,
                ),
                layer=layer["pplus"],
            )
        )
        psdm_in.dmove(
            (
                rect_pcmpgr_in.dxmin + pp_enc_comp,
                rect_pcmpgr_in.dymin + pp_enc_comp,
            )
        )
        psdm_out = c_temp_gr.add_ref(
            gf.components.rectangle(
                size=(
                    (rect_pcmpgr_out.dxmax - rect_pcmpgr_out.dxmin) + 2 * pp_enc_comp,
                    (rect_pcmpgr_out.dymax - rect_pcmpgr_out.dymin) + 2 * pp_enc_comp,
                ),
                layer=layer["pplus"],
            )
        )
        psdm_out.dmove(
            (
                rect_pcmpgr_out.dxmin - pp_enc_comp,
                rect_pcmpgr_out.dymin - pp_enc_comp,
            )
        )
        c.add_ref(
            gf.boolean(A=psdm_out, B=psdm_in, operation="A-B", layer=layer["pplus"])
        )  # psdm

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
                    (comp_m1_in.dxsize) + 2 * cw,
                    (comp_m1_in.dysize) + 2 * cw,
                ),
                layer=layer["metal1"],
            )
        )
        comp_m1_out.dmove((rect_pcmpgr_in.dxmin - cw, rect_pcmpgr_in.dymin - cw))
        c.add_ref(
            gf.boolean(
                A=rect_pcmpgr_out,
                B=rect_pcmpgr_in,
                operation="A-B",
                layer=layer["metal1"],
            )
        )  # guardring metal1

    c.add_port(
        name="cathode",
        center=(
            cath_m1_h.dx + cath_m1_h.dxsize / 2,
            cath_m1_h.dy + cath_m1_h.dysize / 2,
        ),
        width=cath_m1_h.dxsize,
        orientation=270,
        layer=layer["metal1"],
        port_type="electrical",
    )
    if m > 1:
        c.add_port(
            name="anode",
            center=(
                an_m1_h.dx + an_m1_h.dxsize / 2,
                an_m1_h.dy + an_m1_h.dysize / 2,
            ),
            width=an_m1_h.dxsize,
            orientation=90,
            layer=layer["metal1"],
            port_type="electrical",
        )
    else:
        c.add_port(
            name="anode",
            center=(
                an_m1_xmin + (an_m1_xmax - an_m1_xmin) / 2,
                an_m1_ymin + (an_m1_ymax - an_m1_ymin) / 2,
            ),
            width=an_m1_xmax - an_m1_xmin,
            orientation=90,
            layer=layer["metal1"],
            port_type="electrical",
        )

    add_electrical_pins(
        c, port_pin_mapping={"cathode": ["cathode"], "anode": ["anode"]}
    )
    return c
