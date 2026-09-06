"""GF180MCU MOSFET parametric cells — rewritten to match Magic VLSI geometry.

This module implements nfet(), pfet(), and nfet_06v0_nvt() generators that
produce layout geometry matching the open_pdks Magic VLSI generators
polygon-for-polygon.

The algorithm faithfully replicates the Magic Tcl procedures:
  - gf180mcu::mos_device   (single finger drawing)
  - gf180mcu::mos_draw     (tiling + guard ring)
  - gf180mcu::draw_contact (contact + surround + metal)
  - gf180mcu::guard_ring   (substrate guard ring)

All geometric computations use Magic's "painted" dimension values (contact_size
= 0.23, diff_surround = 0.065, etc.).  At the point of polygon output, these
are converted to physical GDS dimensions:
  - contact cut = 0.22 (painted 0.23 shrunk by 0.005/side in CIF)
  - active surround = 0.07 (painted 0.065 grown by 0.005/side in CIF)
  - metal surround  = 0.06 (painted 0.055 grown by 0.005/side in CIF)

The total envelope is conserved (0.23/2 + 0.065 = 0.22/2 + 0.07 = 0.18).
"""

# TODO: Replace hard coded DRC rules by proper DRC rule dictionaries to build the components.

from __future__ import annotations

from math import floor

import gdsfactory as gf
from gdsfactory.add_pins import add_electrical_pins
from gdsfactory.typings import Strs

from gf180mcu.layers import layer

# ---------------------------------------------------------------------------
# Grid snapping — Magic CIF output grid is 5 nm
# ---------------------------------------------------------------------------

_GRID = 0.005  # 5 nm


def _snap(v: float) -> float:
    """Round *v* to the nearest 5 nm grid point."""
    return round(round(v / _GRID) * _GRID, 4)


# ---------------------------------------------------------------------------
# Magic ruleset (from gf180mcu::ruleset in open_pdks gf180mcu.tcl)
# These are the "painted" values used for all geometric computations.
# ---------------------------------------------------------------------------

_RULES = dict(
    contact_size=0.23,
    poly_surround=0.065,
    diff_surround=0.065,
    gate_to_diffcont=0.26,
    gate_to_polycont=0.28,
    gate_extension=0.22,
    diff_extension=0.23,
    metal_surround=0.055,
    sub_surround=0.12,
    diff_spacing=0.33,
    poly_spacing=0.24,
    diff_poly_space=0.10,
    diff_gate_space=0.11,
    metal_spacing=0.23,
)

# Physical GDS dimensions (after CIF conversion)
_CIF_CONTACT_CUT = 0.22  # contact cut on GDS layer 33
_CIF_DIFF_SURROUND = 0.07  # active/poly surround in GDS
_CIF_POLY_SURROUND = 0.07  # poly surround in GDS
_CIF_METAL_SURROUND = 0.06  # metal1 surround in GDS
_CIF_CONTACT_GAP = 0.25  # min gap between contact cuts
_CIF_CONTACT_PITCH = 0.47  # _CIF_CONTACT_CUT + _CIF_CONTACT_GAP

# Layer aliases
_L_COMP = layer["comp"]
_L_POLY = layer["poly2"]
_L_PPLUS = layer["pplus"]
_L_NPLUS = layer["nplus"]
_L_CONTACT = layer["contact"]
_L_METAL1 = layer["metal1"]
_L_NWELL = layer["nwell"]
_L_LVPWELL = layer["lvpwell"]
_L_DUALGATE = layer["dualgate"]
_L_V5XTOR = layer["v5_xtor"]
_L_SAB = layer["sab"]
_L_RESMK = layer["res_mk"]
_L_NAT = layer["nat"]
_L_MVSD = layer["mvsd"]
_L_MVPSD = layer["mvpsd"]
_L_PR_BNDRY = layer["pr_bndry"]


# ---------------------------------------------------------------------------
# Helper: add a snapped rectangle
# ---------------------------------------------------------------------------


def _rect(c, x0, y0, x1, y1, layer_spec):
    x0, y0, x1, y1 = _snap(x0), _snap(y0), _snap(x1), _snap(y1)
    if abs(x1 - x0) < 1e-6 or abs(y1 - y0) < 1e-6:
        return
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=layer_spec)


# ---------------------------------------------------------------------------
# Contact cut array — places 0.22 x 0.22 cuts with 0.47 pitch
# ---------------------------------------------------------------------------


def _contact_cuts(c, cx, cy, w_envelope, h_envelope):
    """Place contact cuts within an envelope of size (w_envelope, h_envelope)
    centered at (cx, cy).

    The envelope is the painted region size (using Magic's contact_size).
    Physical cuts are 0.22x0.22 within this envelope.
    """
    cut = _CIF_CONTACT_CUT
    pitch = _CIF_CONTACT_PITCH

    # Available space for cuts (envelope minus the 0.005 CIF shrink per side)
    # The envelope matches the painted contact region. Within it, cuts are placed.
    # Number of cuts based on the envelope size converted to physical space.
    # Effective size = envelope (which is already the physical contact extent)
    # Actually, the envelope equals the painted size, and in the CIF output,
    # the contact region shrinks by 0.005/side. So physical contact region
    # = envelope - 2*0.005 per axis. For a single contact:
    # painted 0.23 -> physical 0.22 cut. For larger regions, multiple cuts
    # are placed within the physical area.

    # For a region painted as contact_size x H:
    # If H = 0.23, one cut of 0.22 fits.
    # If H > 0.23, multiple cuts of 0.22 with 0.25 gap.
    # Physical area = H - 0.01 (0.005 shrink per side)
    # Number of cuts = floor((phys_H - cut) / pitch) + 1

    phys_w = max(w_envelope - 0.01, cut)
    phys_h = max(h_envelope - 0.01, cut)

    nx = max(1, floor((phys_w - cut) / pitch + 1 + 1e-6))
    ny = max(1, floor((phys_h - cut) / pitch + 1 + 1e-6))

    span_x = (nx - 1) * pitch
    span_y = (ny - 1) * pitch

    for ix in range(nx):
        for iy in range(ny):
            x = _snap(cx - span_x / 2.0 + ix * pitch)
            y = _snap(cy - span_y / 2.0 + iy * pitch)
            _rect(c, x - cut / 2, y - cut / 2, x + cut / 2, y + cut / 2, _L_CONTACT)


# ---------------------------------------------------------------------------
# draw_contact — replicates gf180mcu::draw_contact
# ---------------------------------------------------------------------------


def _draw_contact(c, cx, cy, w, h, rules, active_layer, orient="vert", no_cuts=False):
    """Draw contact with surrounding active/poly and metal1.

    w, h: requested contact area size (painted dimensions).
    cx, cy: center position.
    orient: "vert" (metal grows N/S), "horz" (metal grows E/W).
    no_cuts: if True, skip contact cut placement (for DSS/asymmetric).

    Returns (ax0, ay0, ax1, ay1): active/poly surround bounding box.
    """
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    metal_surround = rules["metal_surround"]

    # Enforce minimum painted size
    cw = max(w, contact_size)
    ch = max(h, contact_size)

    hw = cw / 2.0
    hh = ch / 2.0

    # Contact cuts (physical 0.22 within the painted region)
    if not no_cuts:
        _contact_cuts(c, cx, cy, cw, ch)

    # Active/poly surround (CIF bloats painted diff_surround to physical)
    # The total extent = hw + diff_surround (painted) stays the same.
    # But in GDS, the active extends to the same boundary.
    ds = diff_surround
    ax0 = _snap(cx - hw - ds)
    ay0 = _snap(cy - hh - ds)
    ax1 = _snap(cx + hw + ds)
    ay1 = _snap(cy + hh + ds)
    _rect(c, ax0, ay0, ax1, ay1, active_layer)

    # Metal1 surround
    ms = metal_surround
    mx0, my0, mx1, my1 = cx - hw, cy - hh, cx + hw, cy + hh
    if orient in ("vert", "full"):
        my0 = cy - hh - ms
        my1 = cy + hh + ms
    if orient in ("horz", "full"):
        mx0 = cx - hw - ms
        mx1 = cx + hw + ms
    _rect(c, mx0, my0, mx1, my1, _L_METAL1)

    return (ax0, ay0, ax1, ay1)


# ---------------------------------------------------------------------------
# Guard ring — replicates gf180mcu::guard_ring
# ---------------------------------------------------------------------------


def _guard_ring(
    c,
    gx,
    gy,
    rules,
    sub_layer,
    full_metal=True,
    glc=True,
    grc=True,
    gtc=False,
    gbc=False,
):
    """Draw guard ring centered at origin.

    gx, gy: guard ring size measured to contact centers (painted coords).
    """
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    metal_surround = rules["metal_surround"]
    metal_spacing = rules["metal_spacing"]
    sub_surround = rules["sub_surround"]

    hx = contact_size / 2.0
    hw = gx / 2.0
    hh = gy / 2.0

    difft = contact_size + 2 * diff_surround
    hdifft = difft / 2.0
    hdiffw = (gx + difft) / 2.0
    hdiffh = (gy + difft) / 2.0

    # Guard ring diffusion (comp layer) — 4 bars forming a ring
    _rect(c, -hdiffw, hh - hdifft, hdiffw, hh + hdifft, _L_COMP)  # top
    _rect(c, -hdiffw, -hh - hdifft, hdiffw, -hh + hdifft, _L_COMP)  # bottom
    _rect(c, hw - hdifft, -hdiffh, hw + hdifft, hdiffh, _L_COMP)  # right
    _rect(c, -hw - hdifft, -hdiffh, -hw + hdifft, hdiffh, _L_COMP)  # left

    # Full metal ring
    if full_metal:
        hmetw = (gx + contact_size) / 2.0
        hmeth = (gy + contact_size) / 2.0
        _rect(c, -hmetw, hh - hx, hmetw, hh + hx, _L_METAL1)  # top
        _rect(c, -hmetw, -hh - hx, hmetw, -hh + hx, _L_METAL1)  # bottom
        _rect(c, hw - hx, -hmeth, hw + hx, hmeth, _L_METAL1)  # right
        _rect(c, -hw - hx, -hmeth, -hw + hx, hmeth, _L_METAL1)  # left

    # Contact height/width for side/top-bottom contacts
    ch = gy - contact_size - 2 * (metal_surround + metal_spacing)
    if ch < contact_size:
        ch = contact_size
    cw = gx - contact_size - 2 * (metal_surround + metal_spacing)
    if cw < contact_size:
        cw = contact_size

    # Side contacts
    if grc:
        _draw_contact(c, hw, 0, 0, ch, rules, _L_COMP, "vert")
    if glc:
        _draw_contact(c, -hw, 0, 0, ch, rules, _L_COMP, "vert")
    if gtc:
        _draw_contact(c, 0, hh, cw, 0, rules, _L_COMP, "horz")
    if gbc:
        _draw_contact(c, 0, -hh, cw, 0, rules, _L_COMP, "horz")

    # Substrate/well layer
    sub_ext = hx + diff_surround + sub_surround
    _rect(c, -hw - sub_ext, -hh - sub_ext, hw + sub_ext, hh + sub_ext, sub_layer)

    return (-hw - sub_ext, -hh - sub_ext, hw + sub_ext, hh + sub_ext)


# ---------------------------------------------------------------------------
# Guard ring implant
# ---------------------------------------------------------------------------


def _guard_ring_implant(c, gx, gy, implant_layer, rules):
    """Draw implant for the guard ring.

    Magic's CIF output generates implant shapes around the guard ring
    diffusion with technology-specific bloat/shrink rules.

    For pplus (NFET guard ring): 8 rectangles with ~0.02/0.03 bloat
    For nplus (PFET guard ring): 4 rectangles with ~0.16 bloat
    """
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    metal_surround = rules["metal_surround"]
    metal_spacing = rules["metal_spacing"]

    hw = gx / 2.0
    hh = gy / 2.0
    difft = contact_size + 2 * diff_surround
    hdifft = difft / 2.0
    hdiffw = (gx + difft) / 2.0
    hdiffh = (gy + difft) / 2.0

    # GR comp bar extents
    bar_outer_x = _snap(hdiffw)
    bar_outer_y = _snap(hh + hdifft)
    bar_inner_y = _snap(hh - hdifft)
    side_outer_x = _snap(hw + hdifft)
    side_inner_x = _snap(hw - hdifft)

    # Guard ring side contact height (from guard_ring function)
    ch = gy - contact_size - 2 * (metal_surround + metal_spacing)
    if ch < contact_size:
        ch = contact_size
    # Contact painted region half-height
    ch_actual = max(ch, contact_size)
    # Side bar implant Y extent = contact surround + CIF bloat
    # The psd/nsd painted region extends ch_actual/2 + diff_surround from center
    # Plus the CIF implant bloat
    side_bloat_y = 0.03  # CIF Y-direction bloat for side bars
    side_impl_half_y = _snap(ch_actual / 2.0 + diff_surround + side_bloat_y)

    if implant_layer == _L_PPLUS:
        # NFET guard ring: pplus with small CIF bloat (~0.02-0.03)
        enc_tb = 0.02  # top/bottom bar bloat
        enc_side_x = 0.03  # side bar X bloat

        # Top bar
        _rect(
            c,
            -bar_outer_x - enc_tb,
            bar_inner_y - enc_tb,
            bar_outer_x + enc_tb,
            bar_outer_y + enc_tb,
            implant_layer,
        )
        # Bottom bar
        _rect(
            c,
            -bar_outer_x - enc_tb,
            -bar_outer_y - enc_tb,
            bar_outer_x + enc_tb,
            -bar_inner_y + enc_tb,
            implant_layer,
        )
        # Left side bar (main body)
        _rect(
            c,
            -side_outer_x - enc_side_x,
            -side_impl_half_y,
            -side_inner_x + enc_side_x,
            side_impl_half_y,
            implant_layer,
        )
        # Right side bar (main body)
        _rect(
            c,
            side_inner_x - enc_side_x,
            -side_impl_half_y,
            side_outer_x + enc_side_x,
            side_impl_half_y,
            implant_layer,
        )
        # Corner pieces (bridge between bars and side bars)
        # Top-left corner
        _rect(
            c,
            -bar_outer_x - enc_tb,
            side_impl_half_y,
            -side_inner_x + enc_side_x,
            bar_inner_y - enc_tb,
            implant_layer,
        )
        # Top-right corner
        _rect(
            c,
            side_inner_x - enc_side_x,
            side_impl_half_y,
            bar_outer_x + enc_tb,
            bar_inner_y - enc_tb,
            implant_layer,
        )
        # Bottom-left corner
        _rect(
            c,
            -bar_outer_x - enc_tb,
            -bar_inner_y + enc_tb,
            -side_inner_x + enc_side_x,
            -side_impl_half_y,
            implant_layer,
        )
        # Bottom-right corner
        _rect(
            c,
            side_inner_x - enc_side_x,
            -bar_inner_y + enc_tb,
            bar_outer_x + enc_tb,
            -side_impl_half_y,
            implant_layer,
        )

    else:
        # PFET guard ring: nplus with outer bloat 0.16, inner bloat varies
        enc_out = 0.16
        # Inner bloat depends on voltage variant (from CIF rules)
        volt = rules.get("volt", "3.3V")
        if volt in ("5.0V", "6.0V", "10.0V"):
            enc_in = 0.07
        else:
            enc_in = 0.11

        # Inner boundary of the nplus ring
        inner_x = _snap(side_inner_x - enc_in)  # inner X
        inner_y = _snap(bar_inner_y - enc_in)  # inner Y

        # Top bar (full width, from inner_y to outer top)
        _rect(
            c,
            -bar_outer_x - enc_out,
            inner_y,
            bar_outer_x + enc_out,
            bar_outer_y + enc_out,
            implant_layer,
        )
        # Bottom bar
        _rect(
            c,
            -bar_outer_x - enc_out,
            -bar_outer_y - enc_out,
            bar_outer_x + enc_out,
            -inner_y,
            implant_layer,
        )
        # Left side bar (between inner_y bounds)
        _rect(c, -side_outer_x - enc_out, -inner_y, -inner_x, inner_y, implant_layer)
        # Right side bar
        _rect(c, inner_x, -inner_y, side_outer_x + enc_out, inner_y, implant_layer)


# ---------------------------------------------------------------------------
# Device implant
# ---------------------------------------------------------------------------


def _device_implant_region(
    finger_results, bloat, channel_bloat=None, gate_bloat=0.23, use_gate=True
):
    """Build a kdb.Region for the device implant or v5_xtor.

    For each finger, creates the typed-diffusion shape:
    - Channel region (hw in Y, full X extent)
    - Dogbone extensions (cdwmin/2 in Y, only at S/D contact positions)
    Then bloats by the specified amount.

    The gate region is computed as the UNION of all fingers' gates, then bloated
    once (not per-finger) to avoid artifacts at finger boundaries.
    """
    import klayout.db as kdb

    def um(v):
        return round(v * 1000)

    region = kdb.Region()

    for r in finger_results:
        # Channel extent (hw in Y, full X)
        cx0, cy0, cx1, cy1 = r["channel"]
        cb = channel_bloat if channel_bloat is not None else bloat
        region.insert(kdb.Box(um(cx0 - cb), um(cy0 - cb), um(cx1 + cb), um(cy1 + cb)))

        # Dogbone tabs (individual rectangles, not bounding box)
        for tab in r.get("dogbone_tabs", []):
            t0, t1, t2, t3 = tab
            region.insert(
                kdb.Box(um(t0 - bloat), um(t1 - bloat), um(t2 + bloat), um(t3 + bloat))
            )

    # Gate region: for dogbone devices (w < cdwmin), add each finger's gate
    # individually so the gap between fingers is preserved (nplus notch at
    # shared contacts). For non-dogbone, use bounding box of all gates.
    if use_gate and finger_results:
        # Detect dogbone: channel Y extent < active Y extent
        r0 = finger_results[0]
        is_dogbone = (
            abs(r0["channel"][3] - r0["channel"][1])
            < abs(r0["active"][3] - r0["active"][1]) - 0.001
        )
        if is_dogbone and len(finger_results) > 1:
            for r in finger_results:
                gx0, gy0, gx1, gy1 = r["gate"]
                region.insert(
                    kdb.Box(
                        um(gx0 - gate_bloat),
                        um(gy0 - gate_bloat),
                        um(gx1 + gate_bloat),
                        um(gy1 + gate_bloat),
                    )
                )
        else:
            gate_x0 = min(r["gate"][0] for r in finger_results)
            gate_y0 = min(r["gate"][1] for r in finger_results)
            gate_x1 = max(r["gate"][2] for r in finger_results)
            gate_y1 = max(r["gate"][3] for r in finger_results)
            region.insert(
                kdb.Box(
                    um(gate_x0 - gate_bloat),
                    um(gate_y0 - gate_bloat),
                    um(gate_x1 + gate_bloat),
                    um(gate_y1 + gate_bloat),
                )
            )

    return region.merged()


def _draw_region(c, region, layer_spec):
    """Draw a kdb.Region as polygons on the given layer."""
    for poly in region.each():
        points = [
            (_snap(p.x / 1000.0), _snap(p.y / 1000.0)) for p in poly.each_point_hull()
        ]
        if len(points) >= 3:
            c.add_polygon(points, layer=layer_spec)


# ---------------------------------------------------------------------------
# Single MOS device geometry computation
# ---------------------------------------------------------------------------


def _mos_geometry(w, l, rules, topc=True, botc=True):
    """Compute geometry for one MOS finger using Magic's algorithm.

    Returns dict with all coordinates needed for drawing and tiling.
    All values in Magic's "painted" coordinate space.
    """
    eps = 0.0005
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    poly_surround = rules["poly_surround"]
    metal_surround = rules["metal_surround"]
    gate_to_diffcont = rules["gate_to_diffcont"]
    gate_to_polycont = rules["gate_to_polycont"]
    gate_extension = rules["gate_extension"]
    diff_extension = rules["diff_extension"]
    diff_poly_space = rules["diff_poly_space"]

    hw = w / 2.0
    hl = l / 2.0

    # --- Dogbone Rule 1: diffusion contact ---
    cdwmin = contact_size + 2 * diff_surround
    cstem = gate_to_diffcont - cdwmin / 2.0
    cgrow = diff_poly_space - cstem
    diffcont_orient = "vert"
    ddover = 0.0

    if (w + eps) < cdwmin:
        if cgrow > 0:
            gate_to_diffcont += cgrow
            diffcont_orient = "horz"
        ddover = (cdwmin - w) / 2.0

    # --- Rule 2: poly contact dogbone ---
    cplmin = contact_size + 2 * poly_surround
    cstem_p = gate_to_polycont - cplmin / 2.0
    cgrow_p = diff_poly_space - cstem_p
    if (l + eps) < cplmin:
        if cgrow_p > 0:
            gate_to_polycont += cgrow_p

    # --- Rule 3: both dogbone ---
    if (w + eps) < cdwmin and (l + eps) < cplmin:
        cgrow3 = (cplmin - w) / 2.0
        gate_to_polycont += cgrow3

    # --- Contact dimensions ---
    cdw = w - 2 * diff_surround
    cpl = l - 2 * poly_surround

    # --- Diffusion extent from gate edge ---
    hc = contact_size / 2.0
    if diff_extension > gate_to_diffcont:
        diff_grow_d = diff_extension  # drain side
        diff_grow_s = diff_extension  # source side
    else:
        diff_grow_d = gate_to_diffcont + hc
        diff_grow_s = gate_to_diffcont + hc

    # --- Poly extent ---
    if gate_extension > gate_to_polycont:
        poly_ext_top = gate_extension
        poly_ext_bot = gate_extension
    else:
        poly_ext_top = gate_to_polycont if topc else gate_extension
        poly_ext_bot = gate_to_polycont if botc else gate_extension

    # --- Single device bounding box (used for tiling) ---
    # fw and fh are the bounding box extents returned by mos_device (cext).
    # They include all drawn elements: diffusion + contact surround + poly pads.
    #
    # fw: The diffusion contact's active surround extends diff_surround beyond
    # the painted contact region. So the total X extent from gate center is:
    #   hl + diff_grow + diff_surround
    # where diff_grow includes gate_to_diffcont + contact_size/2.
    fw = 2 * (hl + max(diff_grow_d, diff_grow_s) + diff_surround)

    # fh: From the max of (poly gate extent) and (poly contact pad extent).
    # Poly gate: hw + poly_ext_top (= gate_extension or gate_to_polycont)
    # Contact pad: hw + gate_to_polycont + poly_surround + contact_size/2
    if topc:
        top_ext = max(
            poly_ext_top, gate_to_polycont + poly_surround + contact_size / 2.0
        )
    else:
        top_ext = poly_ext_top
    if botc:
        bot_ext = max(
            poly_ext_bot, gate_to_polycont + poly_surround + contact_size / 2.0
        )
    else:
        bot_ext = poly_ext_bot
    fh = hw + top_ext + hw + bot_ext

    # But we also need to account for diffusion contact extent in Y
    # When dogbone, the contact extent in Y = cdwmin/2 + diff_surround
    # When not dogbone, it's hw + diff_surround? No...
    # Actually fh in Magic is computed from cext which is the union of all drawn elements
    # The critical Y extents come from:
    # 1. Poly contact pads: hw + gate_to_polycont + poly_surround + contact_size/2
    # 2. Diffusion contacts (if dogbone): ddover + diff_surround (above/below gate center)
    #    = cdwmin/2 + diff_surround
    # These are typically smaller than the poly extent, so fh is dominated by poly pads.

    return dict(
        w=w,
        l=l,
        hw=hw,
        hl=hl,
        gate_to_diffcont=gate_to_diffcont,
        gate_to_polycont=gate_to_polycont,
        gate_extension=gate_extension,
        diff_grow_d=diff_grow_d,
        diff_grow_s=diff_grow_s,
        poly_ext_top=poly_ext_top,
        poly_ext_bot=poly_ext_bot,
        diffcont_orient=diffcont_orient,
        ddover=ddover,
        cdw=cdw,
        cpl=cpl,
        fw=fw,
        fh=fh,
        cdwmin=cdwmin,
        cplmin=cplmin,
    )


# ---------------------------------------------------------------------------
# Draw single MOS device finger
# ---------------------------------------------------------------------------


def _draw_mos_finger(
    c, cx, cy, geom, rules, evens=1, topc=True, botc=True, dss=False, asym=False
):
    """Draw one MOS finger at (cx, cy). Returns device extents."""
    w = geom["w"]
    l = geom["l"]
    hw = geom["hw"]
    hl = geom["hl"]
    gate_to_diffcont = geom["gate_to_diffcont"]
    gate_to_polycont = geom["gate_to_polycont"]
    gate_extension = geom["gate_extension"]
    diff_grow_d = geom["diff_grow_d"]
    diff_grow_s = geom["diff_grow_s"]
    diffcont_orient = geom["diffcont_orient"]
    cdw = geom["cdw"]
    cpl = geom["cpl"]
    cdwmin = geom["cdwmin"]

    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    poly_surround = rules["poly_surround"]

    # Drain/source sides
    if evens == 1:
        dside = -1  # drain left
    else:
        dside = 1  # drain right
    sside = -dside

    # --- Diffusion (comp) painting ---
    # Magic paints drain diff and source diff separately
    # Drain side
    if dside == -1:
        drain_left = cx - hl - diff_grow_d
        drain_right = cx + hl
    else:
        drain_left = cx - hl
        drain_right = cx + hl + diff_grow_d

    if sside == -1:
        source_left = cx - hl - diff_grow_s
        source_right = cx + hl
    else:
        source_left = cx - hl
        source_right = cx + hl + diff_grow_s

    comp_left = min(drain_left, source_left)
    comp_right = max(drain_right, source_right)

    # Main comp (device active)
    if asym:
        # Asymmetric: source side comp extends from -(hl - sub_surround)
        # to source contact outer. Drain comp is only from draw_contact.
        sub_surround_v = rules.get("sub_surround", 0.12)
        if sside == -1:
            # Source on left, drain on right
            _rect(c, source_left, cy - hw, cx + hl - sub_surround_v, cy + hw, _L_COMP)
        else:
            # Source on right, drain on left
            _rect(c, cx - hl + sub_surround_v, cy - hw, source_right, cy + hw, _L_COMP)
    else:
        _rect(c, comp_left, cy - hw, comp_right, cy + hw, _L_COMP)

    # Dogbone extensions for diffusion contacts
    if w < cdwmin - 0.0001:
        dog_hw = cdwmin / 2.0
        # The dogbone is created by the draw_contact's active surround
        # extending beyond the device channel width.
        # We paint the comp extension here as separate rectangles
        # for the parts that extend beyond the channel.
        drain_cx = cx + dside * (hl + gate_to_diffcont)
        source_cx = cx + sside * (hl + gate_to_diffcont)

        # Drain dogbone comp extension (above and below channel)
        d_ext_left = drain_cx - contact_size / 2 - diff_surround
        d_ext_right = drain_cx + contact_size / 2 + diff_surround
        _rect(c, d_ext_left, cy + hw, d_ext_right, cy + dog_hw, _L_COMP)
        _rect(c, d_ext_left, cy - dog_hw, d_ext_right, cy - hw, _L_COMP)

        # Source dogbone comp extension
        s_ext_left = source_cx - contact_size / 2 - diff_surround
        s_ext_right = source_cx + contact_size / 2 + diff_surround
        _rect(c, s_ext_left, cy + hw, s_ext_right, cy + dog_hw, _L_COMP)
        _rect(c, s_ext_left, cy - dog_hw, s_ext_right, cy - hw, _L_COMP)

    # --- Poly gate ---
    poly_top = cy + hw + geom["poly_ext_top"]
    poly_bot = cy - hw - geom["poly_ext_bot"]
    _rect(c, cx - hl, poly_bot, cx + hl, poly_top, _L_POLY)

    # --- Diffusion contacts ---
    drain_cx = cx + dside * (hl + gate_to_diffcont)
    source_cx = cx + sside * (hl + gate_to_diffcont)

    # DSS: skip all S/D contact cuts (keep metal and comp surround)
    # Asymmetric: skip drain contact cuts, use L-shaped drain comp
    drain_no_cuts = dss or asym
    source_no_cuts = dss

    if asym:
        # Asymmetric drain: L-shaped comp (ldndiffc CIF output)
        # Outer part (metal surround area): full hw
        # Inner part (contact cut area): hw - diff_surround
        metal_surround = rules["metal_surround"]
        cw_d = max(0, contact_size)
        ch_d = max(cdw, contact_size)
        ms_phys = _CIF_METAL_SURROUND  # 0.06
        hc_half = contact_size / 2.0

        # Draw the L-shaped drain comp
        # Outer: from drain outer surround to drain center + metal_surround_phys
        # at ±hw
        d_outer_edge = _snap(drain_cx - hc_half - diff_surround)  # outer
        d_mid_edge = _snap(drain_cx + ms_phys)  # metal surround boundary
        d_inner_edge = _snap(drain_cx + hc_half)  # contact right edge
        hw_reduced = _snap(hw - diff_surround)
        if dside == -1:
            # Drain on left
            _rect(c, d_outer_edge, cy - hw, d_mid_edge, cy + hw, _L_COMP)
            _rect(
                c, d_mid_edge, cy - hw_reduced, d_inner_edge, cy + hw_reduced, _L_COMP
            )
        else:
            # Drain on right
            d_outer_edge = _snap(drain_cx + hc_half + diff_surround)
            d_mid_edge = _snap(drain_cx - ms_phys)
            d_inner_edge = _snap(drain_cx - hc_half)
            _rect(
                c, d_inner_edge, cy - hw_reduced, d_mid_edge, cy + hw_reduced, _L_COMP
            )
            _rect(c, d_mid_edge, cy - hw, d_outer_edge, cy + hw, _L_COMP)
        # Still draw drain metal (no comp from draw_contact for asym drain)
        cw_m = max(0, contact_size)
        ch_m = max(cdw, contact_size)
        _rect(
            c,
            drain_cx - cw_m / 2,
            cy - ch_m / 2 - metal_surround,
            drain_cx + cw_m / 2,
            cy + ch_m / 2 + metal_surround,
            _L_METAL1,
        )
    else:
        _draw_contact(
            c,
            drain_cx,
            cy,
            0,
            cdw,
            rules,
            _L_COMP,
            diffcont_orient,
            no_cuts=drain_no_cuts,
        )
    _draw_contact(
        c,
        source_cx,
        cy,
        0,
        cdw,
        rules,
        _L_COMP,
        diffcont_orient,
        no_cuts=source_no_cuts,
    )

    # --- Poly contacts ---
    if topc:
        pc_cy = cy + hw + gate_to_polycont
        _draw_contact(c, cx, pc_cy, cpl, 0, rules, _L_POLY, "horz")
    if botc:
        pc_cy = cy - hw - gate_to_polycont
        _draw_contact(c, cx, pc_cy, cpl, 0, rules, _L_POLY, "horz")

    # --- Compute TWO extents: ---
    # 1. cext: full bounding box including poly pads (for tiling computation)
    # 2. active_ext: only the active diffusion area (for device implant)

    # Active area extent for device implant.
    # The implant is based on the total typed-diffusion (ndiff/pdiff) extent,
    # which includes: gate painting + contact's active surround.
    # X: hl + gate_to_diffcont + contact_size/2 + diff_surround
    # Y: max(hw, cdwmin/2) — the max of gate height and contact dogbone height
    act_half_x = hl + gate_to_diffcont + contact_size / 2.0 + diff_surround
    act_left = cx - act_half_x
    act_right = cx + act_half_x

    # Y extent: the typed diffusion height
    if w < cdwmin - 0.0001:
        act_half_y = cdwmin / 2.0  # dogbone height
    else:
        act_half_y = hw  # device width
    act_bot = cy - act_half_y
    act_top = cy + act_half_y

    # Full extent including poly pads
    ext_left = act_left
    ext_right = act_right
    ext_bot = act_bot
    ext_top = act_top

    if topc:
        pad_top = cy + hw + gate_to_polycont + contact_size / 2 + poly_surround
        ext_top = max(ext_top, pad_top)
    if botc:
        pad_bot = cy - hw - gate_to_polycont - contact_size / 2 - poly_surround
        ext_bot = min(ext_bot, pad_bot)

    # Gate extent (just the gate polygon area, for implant gate bloat)
    gate_left = cx - hl
    gate_right = cx + hl
    gate_bot = cy - hw
    gate_top = cy + hw

    # Channel extent (just the gate channel, hw in Y)
    chan_left = act_left
    chan_right = act_right
    chan_bot = cy - hw
    chan_top = cy + hw

    # Dogbone tab rectangles (for v5_xtor cross-shape construction)
    dogbone_tabs = []
    if w < cdwmin - 0.0001:
        dog_hw = cdwmin / 2.0
        drain_cx = cx + dside * (hl + gate_to_diffcont)
        source_cx = cx + sside * (hl + gate_to_diffcont)
        d_left = _snap(drain_cx - contact_size / 2 - diff_surround)
        d_right = _snap(drain_cx + contact_size / 2 + diff_surround)
        s_left = _snap(source_cx - contact_size / 2 - diff_surround)
        s_right = _snap(source_cx + contact_size / 2 + diff_surround)
        # Top and bottom tabs for each S/D contact
        for left, right in [(d_left, d_right), (s_left, s_right)]:
            dogbone_tabs.append((left, _snap(cy + hw), right, _snap(cy + dog_hw)))
            dogbone_tabs.append((left, _snap(cy - dog_hw), right, _snap(cy - hw)))

    return dict(
        cext=(_snap(ext_left), _snap(ext_bot), _snap(ext_right), _snap(ext_top)),
        active=(_snap(act_left), _snap(act_bot), _snap(act_right), _snap(act_top)),
        channel=(_snap(chan_left), _snap(chan_bot), _snap(chan_right), _snap(chan_top)),
        gate=(_snap(gate_left), _snap(gate_bot), _snap(gate_right), _snap(gate_top)),
        dogbone_tabs=dogbone_tabs,
        drain_cx=_snap(drain_cx),
        source_cx=_snap(source_cx),
    )


# ---------------------------------------------------------------------------
# Main MOS drawing — replicates gf180mcu::mos_draw
# ---------------------------------------------------------------------------


def _mos_draw(
    c,
    w,
    l,
    nf,
    rules,
    is_nfet=True,
    topc=True,
    botc=True,
    guard=True,
    full_metal=True,
    dss=False,
    asym=False,
):
    """Draw complete MOSFET with guard ring."""
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    diff_spacing = rules["diff_spacing"]
    diff_gate_space = rules["diff_gate_space"]
    gate_extension = rules["gate_extension"]

    geom = _mos_geometry(w, l, rules, topc, botc)
    fw = geom["fw"]
    fh = geom["fh"]

    # Tiling pitch (doverlap=1): overlap diffusion contacts
    dx = fw - (diff_surround * 2 + contact_size)

    # Core dimensions
    corex = (nf - 1) * dx + fw
    corey = fh

    # Guard ring adjustments for dogbone
    cdwmin = contact_size + 2 * diff_surround
    if guard and (w + 0.0005) < cdwmin:
        inset = (contact_size + 2 * diff_surround - w) / 2.0
        sdiff = inset + diff_spacing - (gate_extension + diff_gate_space)
        if sdiff > 0:
            if not topc:
                corey += sdiff
            if not botc:
                corey += sdiff

    # Guard ring size (to contact centers)
    gx = corex + 2 * (diff_spacing + diff_surround) + contact_size
    gy = corey + 2 * (diff_gate_space + diff_surround) + contact_size

    # Layer configuration
    if is_nfet:
        gr_implant = _L_PPLUS
        dev_implant = _L_NPLUS
        sub_layer = _L_LVPWELL
    else:
        gr_implant = _L_NPLUS
        dev_implant = _L_PPLUS
        sub_layer = _L_NWELL

    # Draw guard ring
    if guard:
        _guard_ring(c, gx, gy, rules, sub_layer, full_metal)
        _guard_ring_implant(c, gx, gy, gr_implant, rules)

    # Draw device fingers
    start_x = -(nf - 1) * dx / 2.0
    evens = 1
    all_finger_results = []
    for i in range(nf):
        fx = start_x + i * dx
        result = _draw_mos_finger(
            c, fx, 0, geom, rules, evens=evens, topc=topc, botc=botc, dss=dss, asym=asym
        )
        all_finger_results.append(result)
        evens = 1 - evens

    # Device implant
    volt = rules.get("volt", "3.3V")
    if dss and volt in ("3.3V",) and all_finger_results:
        # 3.3V DSS (ndiffres/pdiffres): implant is active bbox bloated by 0.18.
        act_x0 = min(r["active"][0] for r in all_finger_results)
        act_y0 = min(r["active"][1] for r in all_finger_results)
        act_x1 = max(r["active"][2] for r in all_finger_results)
        act_y1 = max(r["active"][3] for r in all_finger_results)
        _rect(
            c, act_x0 - 0.18, act_y0 - 0.18, act_x1 + 0.18, act_y1 + 0.18, dev_implant
        )
    elif asym and all_finger_results:
        # 10V asymmetric: gate region bloated by 0.23 (bounding box)
        # + source side channel bloated by 0.16 (no drain channel contribution).
        import klayout.db as kdb

        def um(v):
            return round(v * 1000)

        impl_region = kdb.Region()
        hw_v = geom["hw"]
        # Gate region: bounding box of all gates, bloated by 0.23
        gate_x0 = min(r["gate"][0] for r in all_finger_results)
        gate_y0 = min(r["gate"][1] for r in all_finger_results)
        gate_x1 = max(r["gate"][2] for r in all_finger_results)
        gate_y1 = max(r["gate"][3] for r in all_finger_results)
        impl_region.insert(
            kdb.Box(
                um(gate_x0 - 0.23),
                um(gate_y0 - 0.23),
                um(gate_x1 + 0.23),
                um(gate_y1 + 0.23),
            )
        )
        # Source side channel: bloated by 0.16
        for r in all_finger_results:
            scx = r["source_cx"]
            dcx = r["drain_cx"]
            cx0, cy0, cx1, cy1 = r["channel"]
            # Source channel region: from gate edge to source outer
            if scx > dcx:
                # Source on right
                s_x0 = (cx0 + cx1) / 2 - geom["hl"]  # gate left edge
                s_x1 = cx1  # source outer
            else:
                # Source on left
                s_x0 = cx0  # source outer
                s_x1 = (cx0 + cx1) / 2 + geom["hl"]  # gate right edge
            impl_region.insert(
                kdb.Box(
                    um(s_x0 - 0.16), um(-hw_v - 0.16), um(s_x1 + 0.16), um(hw_v + 0.16)
                )
            )
        impl_region = impl_region.merged()
        _draw_region(c, impl_region, dev_implant)
    elif all_finger_results:
        # Normal and 6V DSS (mvndiffres/mvpdiffres): standard implant computation.
        impl_region = _device_implant_region(all_finger_results, bloat=0.16)
        _draw_region(c, impl_region, dev_implant)

    # --- DSS: add SAB layer ---
    # SAB = device comp shape bloated by gate_extension (0.22), with
    # morphological closing to fill tiny CIF notches (matching Magic output).
    if dss and all_finger_results:
        import klayout.db as kdb

        def um(v):
            return round(v * 1000)

        sab_enc = rules["gate_extension"]
        sab_region = kdb.Region()
        hw_v = geom["hw"]
        cdwmin_v = geom["cdwmin"]
        # Main comp rect: full active X extent at ±hw
        act_x0 = min(r["active"][0] for r in all_finger_results)
        act_x1 = max(r["active"][2] for r in all_finger_results)
        sab_region.insert(kdb.Box(um(act_x0), um(-hw_v), um(act_x1), um(hw_v)))
        # Dogbone contact surrounds at ±cdwmin/2
        if w < cdwmin_v - 0.0001:
            dog_half = cdwmin_v / 2.0
            for r in all_finger_results:
                # Drain contact surround
                dcx = r["drain_cx"]
                ds_hw = contact_size / 2.0 + diff_surround
                sab_region.insert(
                    kdb.Box(
                        um(dcx - ds_hw), um(-dog_half), um(dcx + ds_hw), um(dog_half)
                    )
                )
                # Source contact surround
                scx = r["source_cx"]
                sab_region.insert(
                    kdb.Box(
                        um(scx - ds_hw), um(-dog_half), um(scx + ds_hw), um(dog_half)
                    )
                )
        sab_region = sab_region.merged()
        sab_region = sab_region.sized(round(sab_enc * 1000))
        # Morphological closing: fill tiny CIF notches (< 0.10 um)
        sab_region = sab_region.sized(50).sized(-50)
        _draw_region(c, sab_region, _L_SAB)

    # --- 10V asymmetric: MVSD ---
    volt = rules.get("volt", "3.3V")

    if asym and all_finger_results:
        import klayout.db as kdb

        def um(v):
            return round(v * 1000)

        # MVSD/MVPSD layer: L-shaped region covering drain side.
        # Derived from reference analysis across multiple parameter combinations.
        hw_v = geom["hw"]
        gate_to_diffcont_v = geom["gate_to_diffcont"]
        hl_v = geom["hl"]
        diff_poly_space_v = rules.get("diff_poly_space", 0.10)
        gy_half = gy / 2.0
        gx_half = gx / 2.0
        sub_surround_v = rules["sub_surround"]
        mvsd_layer = _L_MVSD if is_nfet else _L_MVPSD

        # Y outer extent: gy/2 - 0.14 (constant for 10V process rules)
        mvsd_y_outer = _snap(gy_half - 0.14)
        # Y inner step: hw - 0.865 (empirically derived from references)
        inner_y = _snap(hw_v - 0.865)

        mvsd_region = kdb.Region()
        for r in all_finger_results:
            dcx = r["drain_cx"]
            scx = r["source_cx"]
            finger_cx = (r["channel"][0] + r["channel"][2]) / 2.0

            # X outer: -(gx/2 + gate_to_diffcont) on drain side
            # X right: gate_to_diffcont - hl + diff_poly_space from finger center
            x1_rel = gate_to_diffcont_v - hl_v + diff_poly_space_v
            x_step_rel = x1_rel - diff_surround - _CIF_DIFF_SURROUND

            if dcx < scx:
                # Drain left, source right
                x0 = _snap(-gx_half - gate_to_diffcont_v)
                x_step = _snap(finger_cx + x_step_rel)
                x1 = _snap(finger_cx + x1_rel)
            else:
                # Drain right, source left
                x1 = _snap(gx_half + gate_to_diffcont_v)
                x_step = _snap(finger_cx - x_step_rel)
                x0 = _snap(finger_cx - x1_rel)

            if dcx < scx:
                # Drain left: main body from x0 (outer left) to x_step
                mvsd_region.insert(
                    kdb.Box(um(x0), um(-mvsd_y_outer), um(x_step), um(mvsd_y_outer))
                )
                # Wings from x_step to x1
                mvsd_region.insert(
                    kdb.Box(um(x_step), um(-mvsd_y_outer), um(x1), um(-inner_y))
                )
                mvsd_region.insert(
                    kdb.Box(um(x_step), um(inner_y), um(x1), um(mvsd_y_outer))
                )
            else:
                # Drain right: main body from x_step to x1 (outer right)
                mvsd_region.insert(
                    kdb.Box(um(x_step), um(-mvsd_y_outer), um(x1), um(mvsd_y_outer))
                )
                # Wings from x0 to x_step
                mvsd_region.insert(
                    kdb.Box(um(x0), um(-mvsd_y_outer), um(x_step), um(-inner_y))
                )
                mvsd_region.insert(
                    kdb.Box(um(x0), um(inner_y), um(x_step), um(mvsd_y_outer))
                )

        mvsd_region = mvsd_region.merged()
        _draw_region(c, mvsd_region, mvsd_layer)

    # Dualgate and V5_XTOR for 5V/6V/10V
    if volt in ("5.0V", "6.0V", "10.0V"):
        sub_surround = rules["sub_surround"]
        hx_c = contact_size / 2.0
        sub_ext = hx_c + diff_surround + sub_surround
        dg_enc = 0.08
        _rect(
            c,
            -(gx / 2 + sub_ext + dg_enc),
            -(gy / 2 + sub_ext + dg_enc),
            gx / 2 + sub_ext + dg_enc,
            gy / 2 + sub_ext + dg_enc,
            _L_DUALGATE,
        )

    if volt in ("5.0V", "10.0V") and all_finger_results:
        import klayout.db as kdb

        def um(v):
            return round(v * 1000)

        v5_region = kdb.Region()
        if asym:
            # 10V asymmetric: v5_xtor covers source side only
            # Source active: from -hl to source contact outer, at ±hw
            hw_v = geom["hw"]
            for r in all_finger_results:
                scx = r["source_cx"]
                dcx = r["drain_cx"]
                finger_cx = (r["channel"][0] + r["channel"][2]) / 2.0
                hl_v = geom["hl"]
                if scx > dcx:
                    # Source right: from gate left edge to source outer
                    src_x0 = finger_cx - hl_v
                    src_x1 = _snap(scx + contact_size / 2 + diff_surround)
                else:
                    # Source left
                    src_x0 = _snap(scx - contact_size / 2 - diff_surround)
                    src_x1 = finger_cx + hl_v
                v5_region.insert(kdb.Box(um(src_x0), um(-hw_v), um(src_x1), um(hw_v)))
        else:
            for r in all_finger_results:
                # Channel comp (main body)
                cx0, cy0, cx1, cy1 = r["channel"]
                v5_region.insert(kdb.Box(um(cx0), um(cy0), um(cx1), um(cy1)))
                # Dogbone tabs (if any)
                for tab in r.get("dogbone_tabs", []):
                    t0, t1, t2, t3 = tab
                    v5_region.insert(kdb.Box(um(t0), um(t1), um(t2), um(t3)))
        v5_region = v5_region.merged().sized(100)  # bloat 0.10 um = 100 nm
        _draw_region(c, v5_region, _L_V5XTOR)

    # NVT: nat and dualgate layers
    if volt == "nvt" and all_finger_results:
        # NAT layer = channel extent bloated by 0.26 (simple rectangle)
        chan_x0 = min(r["channel"][0] for r in all_finger_results)
        chan_y0 = min(r["channel"][1] for r in all_finger_results)
        chan_x1 = max(r["channel"][2] for r in all_finger_results)
        chan_y1 = max(r["channel"][3] for r in all_finger_results)
        _rect(c, chan_x0 - 0.26, chan_y0 - 0.26, chan_x1 + 0.26, chan_y1 + 0.26, _L_NAT)

        # Dualgate for NVT
        sub_surround = rules["sub_surround"]
        hx_c = contact_size / 2.0
        sub_ext = hx_c + diff_surround + sub_surround
        dg_enc = 0.08
        _rect(
            c,
            -(gx / 2 + sub_ext + dg_enc),
            -(gy / 2 + sub_ext + dg_enc),
            gx / 2 + sub_ext + dg_enc,
            gy / 2 + sub_ext + dg_enc,
            _L_DUALGATE,
        )

    # prBoundary removed — Magic's 10x FIXED_BBOX is unnecessarily large

    # -----------------------------------------------------------------
    # Collect port metadata for Source, Drain, Gate, Bulk
    # -----------------------------------------------------------------
    drain_xs = sorted({r["drain_cx"] for r in all_finger_results})
    source_xs = sorted({r["source_cx"] for r in all_finger_results})

    sd_port_width = max(geom["cdw"], contact_size)

    gate_poly_centers = []
    gate_contacts = []
    gate_to_polycont = geom["gate_to_polycont"]
    hw = geom["hw"]
    for i in range(nf):
        fx = start_x + i * dx
        gate_poly_centers.append((_snap(fx), 0.0))
        if topc:
            gate_contacts.append((_snap(fx), _snap(hw + gate_to_polycont)))
        if botc:
            gate_contacts.append((_snap(fx), _snap(-(hw + gate_to_polycont))))

    gate_contact_width = max(geom["cpl"], contact_size)

    bulk_contacts = []
    if guard:
        bulk_contacts = [
            (0.0, _snap(gy / 2.0)),
            (0.0, _snap(-gy / 2.0)),
            (_snap(-gx / 2.0), 0.0),
            (_snap(gx / 2.0), 0.0),
        ]

    bulk_port_width = contact_size + 2 * diff_surround

    return dict(
        drain_xs=drain_xs,
        source_xs=source_xs,
        sd_port_width=sd_port_width,
        gate_poly_centers=gate_poly_centers,
        gate_poly_width=l,
        gate_contacts=gate_contacts,
        gate_contact_width=gate_contact_width,
        bulk_contacts=bulk_contacts,
        bulk_port_width=bulk_port_width,
        has_guard=guard,
    )


# ---------------------------------------------------------------------------
# Port / pin helper
# ---------------------------------------------------------------------------


def _add_mos_ports(c, port_data):
    """Add electrical ports and logical pins to a MOSFET component."""
    drain_ports = []
    for i, dx in enumerate(port_data["drain_xs"]):
        name = f"Drain_{i}"
        c.add_port(
            name=name,
            center=(float(dx), 0.0),
            width=float(port_data["sd_port_width"]),
            orientation=90,
            layer=_L_METAL1,
            port_type="electrical",
        )
        drain_ports.append(name)

    source_ports = []
    for i, sx in enumerate(port_data["source_xs"]):
        name = f"Source_{i}"
        c.add_port(
            name=name,
            center=(float(sx), 0.0),
            width=float(port_data["sd_port_width"]),
            orientation=90,
            layer=_L_METAL1,
            port_type="electrical",
        )
        source_ports.append(name)

    gate_ports = []
    idx = 0
    for gx, gy in port_data["gate_poly_centers"]:
        name = f"Gate_{idx}"
        c.add_port(
            name=name,
            center=(float(gx), float(gy)),
            width=float(port_data["gate_poly_width"]),
            orientation=90,
            layer=_L_POLY,
            port_type="electrical",
        )
        gate_ports.append(name)
        idx += 1
    for gx, gy in port_data["gate_contacts"]:
        name = f"Gate_{idx}"
        c.add_port(
            name=name,
            center=(float(gx), float(gy)),
            width=float(port_data["gate_contact_width"]),
            orientation=90,
            layer=_L_METAL1,
            port_type="electrical",
        )
        gate_ports.append(name)
        idx += 1

    bulk_ports = []
    if port_data["has_guard"]:
        for i, (bx, by) in enumerate(port_data["bulk_contacts"]):
            name = f"Bulk_{i}"
            c.add_port(
                name=name,
                center=(float(bx), float(by)),
                width=float(port_data["bulk_port_width"]),
                orientation=90,
                layer=_L_METAL1,
                port_type="electrical",
            )
            bulk_ports.append(name)

    pin_mapping = {
        "Drain": drain_ports,
        "Source": source_ports,
        "Gate": gate_ports,
    }
    if bulk_ports:
        pin_mapping["Bulk"] = bulk_ports

    add_electrical_pins(c, port_pin_mapping=pin_mapping)


# ---------------------------------------------------------------------------
# nfet
# ---------------------------------------------------------------------------


@gf.cell(tags=["fet"])
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
    dss: bool = False,
    asym: bool = False,
) -> gf.Component:
    """Return NFET transistor matching Magic VLSI geometry.

    Args:
        l_gate: gate length in microns.
        w_gate: gate width in microns.
        sd_con_col: number of source/drain contact columns.
        inter_sd_l: inter source/drain length.
        nf: number of gate fingers.
        grw: guard-ring width; set to 0 to disable the guard ring.
        volt: voltage rating ("3.3V", "5.0V", "6.0V", "10.0V").
        bulk: bulk connection option.
        con_bet_fin: contacts between fingers.
        gate_con_pos: gate contact position ("alternating", "top", "bottom").
        interdig: interdigitated layout toggle.
        patt: gate pattern option.
        deepnwell: deep N-well toggle.
        pcmpgr: P-comp guard-ring toggle.
        label: add text labels.
        sd_label: per-terminal source/drain label strings.
        g_label: gate label strings.
        sub_label: substrate label string.
        patt_label: enable pattern labels.
        dss: drain-side symmetric spacing.
        asym: asymmetric layout.
    """
    c = gf.Component()
    rules = dict(_RULES)
    rules["volt"] = volt

    if volt in ("5.0V", "6.0V", "10.0V"):
        rules["diff_poly_space"] = 0.30
        rules["diff_gate_space"] = 0.30
        rules["diff_spacing"] = 0.36
        rules["sub_surround"] = 0.16

    port_data = _mos_draw(
        c, w_gate, l_gate, nf, rules, is_nfet=True, guard=grw > 0, dss=dss, asym=asym
    )
    _add_mos_ports(c, port_data)
    return c


@gf.cell(tags=["fet"])
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
    dss: bool = False,
    asym: bool = False,
) -> gf.Component:
    """Return PFET transistor matching Magic VLSI geometry.

    Args:
        l_gate: gate length in microns.
        w_gate: gate width in microns.
        sd_con_col: number of source/drain contact columns.
        inter_sd_l: inter source/drain length.
        nf: number of gate fingers.
        grw: guard-ring width; set to 0 to disable the guard ring.
        volt: voltage rating ("3.3V", "5.0V", "6.0V", "10.0V").
        bulk: bulk connection option.
        con_bet_fin: contacts between fingers.
        gate_con_pos: gate contact position ("alternating", "top", "bottom").
        interdig: interdigitated layout toggle.
        patt: gate pattern option.
        deepnwell: deep N-well toggle.
        pcmpgr: P-comp guard-ring toggle.
        label: add text labels.
        sd_label: per-terminal source/drain label strings.
        g_label: gate label strings.
        sub_label: substrate label string.
        patt_label: enable pattern labels.
        dss: drain-side symmetric spacing.
        asym: asymmetric layout.
    """
    c = gf.Component()
    rules = dict(_RULES)
    rules["volt"] = volt

    if volt in ("5.0V", "6.0V", "10.0V"):
        rules["diff_poly_space"] = 0.30
        rules["diff_gate_space"] = 0.30
        rules["diff_spacing"] = 0.36
        rules["sub_surround"] = 0.16

    port_data = _mos_draw(
        c, w_gate, l_gate, nf, rules, is_nfet=False, guard=grw > 0, dss=dss, asym=asym
    )
    _add_mos_ports(c, port_data)
    return c


@gf.cell(tags=["fet"])
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
    """Return Native NFET 6V transistor matching Magic VLSI geometry.

    Args:
        l_gate: gate length in microns.
        w_gate: gate width in microns.
        sd_con_col: number of source/drain contact columns.
        inter_sd_l: inter source/drain length.
        nf: number of gate fingers.
        grw: guard-ring width; set to 0 to disable the guard ring.
        bulk: bulk connection option.
        con_bet_fin: contacts between fingers.
        gate_con_pos: gate contact position ("alternating", "top", "bottom").
        interdig: interdigitated layout toggle.
        patt: gate pattern option.
        label: add text labels.
        sd_label: per-terminal source/drain label strings.
        g_label: gate label strings.
        sub_label: substrate label string.
        patt_label: enable pattern labels.
    """
    c = gf.Component()
    rules = dict(_RULES)
    rules["volt"] = "nvt"
    rules["gate_extension"] = 0.35
    rules["sub_surround"] = 0.16

    port_data = _mos_draw(c, w_gate, l_gate, nf, rules, is_nfet=True, guard=grw > 0)
    _add_mos_ports(c, port_data)
    return c
