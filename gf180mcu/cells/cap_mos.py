"""GF180MCU MOS capacitor parametric cells.

Geometry is derived from the open_pdks Magic VLSI generators:
  gf180mcu::nmoscap_3p3_draw / nmoscap_6p0_draw → gf180mcu::mos_draw

The MOS capacitor is a MOSFET varactor:
  - Gate terminal : poly2 over the lc × wc gate area
  - Body terminal : nsd comp strips adjacent to the gate + outer lvpwell guard ring

All geometry is centered at origin and snapped to a 5 nm grid.

Magic ruleset (painted coordinates):
  contact_size     = 0.23  → 0.22 CIF cut  (half-cut = 0.11)
  diff_surround    = 0.065 → 0.07 CIF active surround
  poly_surround    = 0.065 → 0.07 CIF
  metal_surround   = 0.055 → 0.06 CIF
  gate_to_diffcont = 0.26
  gate_to_polycont = 0.28
  metal_spacing    = 0.23
"""

from __future__ import annotations

from math import floor

import gdsfactory as gf
from gdsfactory.add_pins import add_electrical_pins

from gf180mcu.layers import layer

# ---------------------------------------------------------------------------
# Grid snapping — Magic CIF output grid is 5 nm
# ---------------------------------------------------------------------------

_GRID = 0.005


def _snap(v: float) -> float:
    return round(round(v / _GRID) * _GRID, 4)


# ---------------------------------------------------------------------------
# GDS (CIF) physical constants
# ---------------------------------------------------------------------------

_CUT = 0.22  # contact cut size in GDS
_HCUT = 0.11  # half contact cut
_PITCH = 0.47  # contact pitch (0.22 + 0.25)
_CIF_DS = 0.07  # active/poly surround in GDS (painted 0.065 + 0.005 bloat/side)
_CIF_MS = 0.06  # metal1 surround in GDS (painted 0.055 + 0.005 bloat/side)

# Painted constants (used in Magic's geometric formulas)
_CS = 0.23  # contact_size
_DS = 0.065  # diff/poly surround
_MS = 0.055  # metal surround
_HCS = 0.115  # contact_size / 2

# Geometric constant
_DIFFT = _CUT + 2 * _CIF_DS  # comp bar thickness (= 0.36)
_HDIFFT = _DIFFT / 2.0  # = 0.18

# Layer aliases
_L_COMP = layer["comp"]
_L_POLY = layer["poly2"]
_L_NPLUS = layer["nplus"]
_L_PPLUS = layer["pplus"]
_L_CONTACT = layer["contact"]
_L_METAL1 = layer["metal1"]
_L_NWELL = layer["nwell"]
_L_LVPWELL = layer["lvpwell"]
_L_DUALGATE = layer["dualgate"]
_L_MOSCAP = layer["mos_cap_mk"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rect(c, x0, y0, x1, y1, lyr) -> None:
    """Add a snapped rectangle."""
    x0, y0, x1, y1 = _snap(x0), _snap(y0), _snap(x1), _snap(y1)
    if abs(x1 - x0) < 1e-6 or abs(y1 - y0) < 1e-6:
        return
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=lyr)


def _contact_array(c, cx, cy, w_env, h_env) -> None:
    """Place 0.22×0.22 contact cuts within an envelope centered at (cx, cy)."""
    phys_w = max(w_env - 0.01, _CUT)
    phys_h = max(h_env - 0.01, _CUT)
    nx = max(1, floor((phys_w - _CUT) / _PITCH + 1 + 1e-6))
    ny = max(1, floor((phys_h - _CUT) / _PITCH + 1 + 1e-6))
    span_x = (nx - 1) * _PITCH
    span_y = (ny - 1) * _PITCH
    for ix in range(nx):
        for iy in range(ny):
            x = _snap(cx - span_x / 2.0 + ix * _PITCH)
            y = _snap(cy - span_y / 2.0 + iy * _PITCH)
            _rect(c, x - _CUT / 2, y - _CUT / 2, x + _CUT / 2, y + _CUT / 2, _L_CONTACT)


# ---------------------------------------------------------------------------
# draw_contact: place cuts + active surround + metal1
# Replicates gf180mcu::draw_contact in Magic.
#   orient="vert"  → metal grows N/S (y direction), active/metal width = cs min
#   orient="horz"  → metal grows E/W (x direction), active/metal height = cs min
# ---------------------------------------------------------------------------


def _draw_contact(c, cx, cy, w, h, active_layer, orient="vert") -> None:
    """Draw a contact with surrounding active region and metal1."""
    cw = max(w, _CS)
    ch = max(h, _CS)
    hw = cw / 2.0
    hh = ch / 2.0

    # Contact cuts
    _contact_array(c, cx, cy, cw, ch)

    # Active / poly surround
    _rect(c, cx - hw - _DS, cy - hh - _DS, cx + hw + _DS, cy + hh + _DS, active_layer)

    # Metal1 surround (ms applied only along the orientation axis)
    mx0, my0, mx1, my1 = cx - _HCS, cy - _HCS, cx + _HCS, cy + _HCS
    if orient == "vert":
        my0 = cy - hh - _MS
        my1 = cy + hh + _MS
    elif orient == "horz":
        mx0 = cx - hw - _MS
        mx1 = cx + hw + _MS
    _rect(c, mx0, my0, mx1, my1, _L_METAL1)


# ---------------------------------------------------------------------------
# Guard ring: outer lvpwell ring surrounding the nmos cap device.
# Replicates gf180mcu::guard_ring with glc=1, grc=1, gtc=0, gbc=0.
# ---------------------------------------------------------------------------


def _guard_ring(
    c, gx, gy, nwell_x, nwell_y, sub_surround=0.12, metal_spacing=0.23, is_6v=False
) -> None:
    """Draw the source/drain guard ring (lvpwell ring).

    gx, gy        : guard ring size in GDS units (contact-centre to contact-centre).
    nwell_x/y     : nwell half-extents (inner boundary for lvpwell ring).
    sub_surround  : nwell/pwell surround (0.12 for 3p3, 0.16 for 6p0).
    """
    hw = gx / 2.0
    hh = gy / 2.0

    hdiffw = (gx + _DIFFT) / 2.0  # half-width  of top/bottom comp bars
    hdiffh = (gy + _DIFFT) / 2.0  # half-height of left/right comp bars

    # ---- Comp bars (4 bars forming the ring) ----
    _rect(c, -hdiffw, hh - _HDIFFT, hdiffw, hh + _HDIFFT, _L_COMP)  # top
    _rect(c, -hdiffw, -hh - _HDIFFT, hdiffw, -hh + _HDIFFT, _L_COMP)  # bottom
    _rect(c, hw - _HDIFFT, -hdiffh, hw + _HDIFFT, hdiffh, _L_COMP)  # right
    _rect(c, -hw - _HDIFFT, -hdiffh, -hw + _HDIFFT, hdiffh, _L_COMP)  # left

    # ---- Metal1 ring (top, bottom, left, right bars) ----
    hmetw = (gx + _CS) / 2.0
    hmeth = (gy + _CS) / 2.0
    _rect(c, -hmetw, hh - _HCS, hmetw, hh + _HCS, _L_METAL1)  # top
    _rect(c, -hmetw, -hh - _HCS, hmetw, -hh + _HCS, _L_METAL1)  # bottom
    _rect(c, hw - _HCS, -hmeth, hw + _HCS, hmeth, _L_METAL1)  # right
    _rect(c, -hw - _HCS, -hmeth, -hw + _HCS, hmeth, _L_METAL1)  # left

    # ---- Side contacts (left + right only; glc=grc=1, gtc=gbc=0) ----
    # ch uses CIF metal surround (_CIF_MS) in the painted formula
    ch = gy - _CS - 2 * (_CIF_MS + metal_spacing)
    if ch < _CS:
        ch = _CS
    _draw_contact(c, hw, 0, 0, ch, _L_COMP, "vert")
    _draw_contact(c, -hw, 0, 0, ch, _L_COMP, "vert")

    # ---- lvpwell ring: outer lvpwell rectangle minus nwell inner area ----
    # In Magic: pwell painted solid, nwell painted on top. GDS output: 4 bars.
    px_out = hw + _HCUT + _CIF_DS + sub_surround
    py_out = hh + _HCUT + _CIF_DS + sub_surround

    # Top, bottom, left, right lvpwell bars (ring around nwell)
    _rect(c, -px_out, nwell_y, px_out, py_out, _L_LVPWELL)  # top
    _rect(c, -px_out, -py_out, px_out, -nwell_y, _L_LVPWELL)  # bottom
    _rect(c, -px_out, -nwell_y, -nwell_x, nwell_y, _L_LVPWELL)  # left
    _rect(c, nwell_x, -nwell_y, px_out, nwell_y, _L_LVPWELL)  # right

    # ---- pplus guard ring implant ----
    # CIF psd → pplus bloat values derived from Magic GDS reference:
    #   outer bars: enc_outer = +0.02 (x), outer strip: enc_outer_x = -0.10
    #   side bars: inner enc = -0.16, outer enc = +0.03
    #   side_by = ch/2 + _DS  (painted diff surround)
    by_out = hh + _HDIFFT  # outer y of top/bottom comp bars
    by_in = hh - _HDIFFT  # inner y of top/bottom comp bars
    sx_out = hw + _HDIFFT  # outer x of side comp bars
    sx_in = hw - _HDIFFT  # inner x of side comp bars

    side_by = _snap(ch / 2.0 + _DS)

    # For each side (top and bottom):
    #   2 rectangles (3p3) or 2 rectangles (6p0): main body, transition strip
    #   3p3 only: thin outer strip
    # For left/right: 1 rectangle (side bar)
    for sign in (1, -1):
        s = sign  # +1 for top, -1 for bottom
        # thin outer strip — 3p3 only (not 6p0)
        if not is_6v:
            _rect(
                c,
                -(hdiffw - 0.10),
                s * (by_out + 0.02),
                (hdiffw - 0.10),
                s * (by_out + 0.11),
                _L_PPLUS,
            )
        # main body (y: by_in-0.125 to by_out+0.02, wider x)
        _rect(
            c,
            -(hdiffw + 0.02),
            s * (by_in - 0.125),
            (hdiffw + 0.02),
            s * (by_out + 0.02),
            _L_PPLUS,
        )
        # transition strip (y: side_by to by_in-0.125, full x width)
        _rect(
            c,
            -(hdiffw + 0.03),
            s * side_by,
            (hdiffw + 0.03),
            s * (by_in - 0.125),
            _L_PPLUS,
        )

    # side bars (left and right)
    _rect(c, sx_in - 0.16, -side_by, sx_out + 0.03, side_by, _L_PPLUS)  # right
    _rect(c, -sx_out - 0.03, -side_by, -sx_in + 0.16, side_by, _L_PPLUS)  # left


# ---------------------------------------------------------------------------
# Main MOS capacitor generator
# ---------------------------------------------------------------------------


@gf.cell(tags=["cap_mos"])
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
    """MOS capacitor (NMOS/PMOS varactor) matching Magic VLSI reference geometry.

    Centered at origin.  Gate = poly2 over lc × wc area; body = comp ring.

    Args:
        type: "cap_nmos" or "cap_pmos".
        lc: Capacitor gate length (µm).
        wc: Capacitor gate width (µm).
        volt: "3.3V" or "6.0V".
        deepnwell: Unused (reserved).
        pcmpgr: Unused (reserved).
        label: Add metal1 labels.
        g_label: Gate label text.
        sd_label: Source/drain label text.
    """
    c = gf.Component()

    is_nmos = "cap_nmos" in type
    is_6v = volt in ("6.0V", "5/6V", "5.0V")

    hl = lc / 2.0
    hw = wc / 2.0

    # Voltage-specific Magic ruleset parameters
    if is_6v:
        diff_spacing = 0.36
        diff_gate_space = 0.30
        sub_surround = 0.16
        metal_spacing = 0.23
        dev_sub_dist = 0.0
    else:  # 3.3V
        diff_spacing = 0.33
        diff_gate_space = 0.11
        sub_surround = 0.12
        metal_spacing = 0.23
        dev_sub_dist = 0.12

    g2d = 0.26  # gate_to_diffcont
    g2p = 0.28  # gate_to_polycont

    # =========================================================
    # 1. mos_cap_mk marker — exactly lc × wc
    # =========================================================
    _rect(c, -hl, -hw, hl, hw, _L_MOSCAP)

    # =========================================================
    # 2. Poly2 gate  (x = ±hl, y = ±(hw + poly_ext_y))
    #    poly_ext_y = g2p + HCUT + CIF_DS
    #               = 0.28 + 0.11 + 0.07 = 0.46  (matches reference)
    # =========================================================
    poly_ext_y = g2p + _HCUT + _CIF_DS  # = 0.46
    _rect(c, -hl, -(hw + poly_ext_y), hl, hw + poly_ext_y, _L_POLY)

    # =========================================================
    # 3. Inner comp strips (S/D adjacent to gate)
    #    x from ±hl to ±(hl + g2d + HCUT + CIF_DS) = ±(hl + 0.44)
    #    y = ±hw
    #    3p3: two separate bars flanking the poly gate (comp stops at ±hl)
    #    6p0: one solid rectangle spanning full width (comp covers gate area)
    # =========================================================
    inner_comp_outer = _snap(hl + g2d + _HCUT + _CIF_DS)  # hl + 0.44

    if is_6v:
        # Solid comp rectangle covering full device width under gate
        _rect(c, -inner_comp_outer, -hw, inner_comp_outer, hw, _L_COMP)
    else:
        # Two separate bars (poly gate separates them)
        _rect(c, hl, -hw, inner_comp_outer, hw, _L_COMP)  # right
        _rect(c, -inner_comp_outer, -hw, -hl, hw, _L_COMP)  # left

    # S/D contacts on inner comp strips
    cdw = wc - 2 * _DS  # painted contact height
    _draw_contact(c, (hl + g2d), 0, 0, cdw, _L_COMP, "vert")
    _draw_contact(c, -(hl + g2d), 0, 0, cdw, _L_COMP, "vert")

    # =========================================================
    # 4. Poly contacts (top + bottom of gate)
    # =========================================================
    cpl = lc - 2 * _DS  # poly contact width (painted)
    pc_y = hw + g2p  # contact centre y

    _draw_contact(c, 0, pc_y, cpl, 0, _L_POLY, "horz")
    _draw_contact(c, 0, -pc_y, cpl, 0, _L_POLY, "horz")

    if label and g_label:
        c.add_label(g_label, position=(0.0, float(pc_y)), layer=layer["metal1_label"])

    # =========================================================
    # 5. nplus (device implant) — plus/cross shape matching Magic CIF output
    #
    #    The nplus is drawn as 3 rectangles that form a cross shape:
    #      main rect : x=±nplus_x,  y=±nplus_y_inner  (wide, S/D region)
    #      top strip : x=±nplus_px, y=[+nplus_y_inner, +nplus_y] (poly contact area)
    #      bot strip : x=±nplus_px, y=[-nplus_y, -nplus_y_inner]
    #
    #    nplus_x      = hl + 0.60  (S/D enc)
    #    nplus_y      = hw + 0.23  (outer y, covers poly contact)
    #    nplus_y_inner= hw + 0.16  (inner y boundary)
    #    nplus_px     = hl + 0.23  (poly gate enc in x)
    # =========================================================
    nplus_x = _snap(hl + g2d + _HCUT + 0.23)  # = hl + 0.60
    nplus_y = _snap(hw + 0.23)
    nplus_y_inner = _snap(hw + 0.16)
    nplus_px = _snap(hl + 0.23)  # = hl + 0.23

    # Main rect (wide, covers S/D regions)
    _rect(c, -nplus_x, -nplus_y_inner, nplus_x, nplus_y_inner, _L_NPLUS)
    # Top poly-contact strip
    _rect(c, -nplus_px, nplus_y_inner, nplus_px, nplus_y, _L_NPLUS)
    # Bottom poly-contact strip
    _rect(c, -nplus_px, -nplus_y, nplus_px, -nplus_y_inner, _L_NPLUS)

    # =========================================================
    # 6. nwell (dev_sub_type = nwell surrounds mos_device)
    #    nwell_x = hl + g2d + HCUT + CIF_DS + sub_surround  = hl + 0.56 (3p3)
    #    nwell_y = hw + g2p + HCUT + CIF_DS + sub_surround  = hw + 0.58 (3p3)
    # =========================================================
    nwell_x = _snap(hl + g2d + _HCUT + _CIF_DS + sub_surround)
    nwell_y = _snap(hw + g2p + _HCUT + _CIF_DS + sub_surround)
    _rect(c, -nwell_x, -nwell_y, nwell_x, nwell_y, _L_NWELL)

    # =========================================================
    # 7. Guard ring (lvpwell = sub_type pwell)
    #
    #    Magic mos_draw:
    #      gx = fw + 2*(diff_spacing + DS) + CS  [when dsd+sub_surr <= diff_spacing]
    #      gy = fh + 2*(dsd + DS) + CS           [when dsd+sub_surr > diff_gate_space]
    #
    #    fw = 2*nwell_x,  fh = 2*nwell_y   (device bbox)
    # =========================================================
    fw = 2.0 * nwell_x
    fh = 2.0 * nwell_y

    _use_gx_dsd = (dev_sub_dist + sub_surround) > diff_spacing
    _use_gy_dsd = (dev_sub_dist + sub_surround) > diff_gate_space

    if _use_gx_dsd:
        gx = fw + 2 * (dev_sub_dist + _DS) + _CS
    else:
        gx = fw + 2 * (diff_spacing + _DS) + _CS

    if _use_gy_dsd:
        gy = fh + 2 * (dev_sub_dist + _DS) + _CS
    else:
        gy = fh + 2 * (diff_gate_space + _DS) + _CS

    _guard_ring(
        c,
        gx,
        gy,
        nwell_x,
        nwell_y,
        sub_surround=sub_surround,
        metal_spacing=metal_spacing,
        is_6v=is_6v,
    )

    # =========================================================
    # 8. Dualgate (6.0V only)
    # =========================================================
    if is_6v:
        _rect(c, -(hl + 1.56), -(hw + 1.52), (hl + 1.56), (hw + 1.52), _L_DUALGATE)

    # =========================================================
    # 9. Ports
    # =========================================================
    c.add_port(
        name="gate",
        center=(0.0, float(_snap(pc_y))),
        width=float(lc),
        orientation=90,
        layer=_L_METAL1,
        port_type="electrical",
    )
    c.add_port(
        name="source_drain",
        center=(0.0, float(-_snap(pc_y))),
        width=float(lc),
        orientation=270,
        layer=_L_METAL1,
        port_type="electrical",
    )

    # =========================================================
    # 10. VLSIR metadata
    # =========================================================
    prefix = "nmoscap" if is_nmos else "pmoscap"
    voltage = "3p3" if not is_6v else "6p0"
    suffix = "_b" if "_b" in type else ""

    add_electrical_pins(
        c, port_pin_mapping={"gate": ["gate"], "source_drain": ["source_drain"]}
    )
    return c
