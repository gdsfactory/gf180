"""GF180MCU resistor pcells matching Magic VLSI geometry exactly.

All layouts are centered at the origin with length (l) along Y and width (w) along X,
matching Magic's coordinate convention.
"""

from __future__ import annotations

from math import floor

import gdsfactory as gf
from gdsfactory.add_pins import add_electrical_pins
from gdsfactory.typings import LayerSpec

from gf180mcu.layers import layer

# ---------------------------------------------------------------------------
# Magic technology constants (from gf180mcu_generators.tcl ruleset)
# ---------------------------------------------------------------------------

_CONTACT_SIZE = 0.23  # internal contact box size
_CONTACT_GDS = 0.22  # contact size in GDS (shrunk 0.005 each side by CIF)
_POLY_SURROUND = 0.065  # poly surrounds contact
_DIFF_SURROUND = 0.065  # diffusion surrounds contact
_METAL_SURROUND = 0.055  # metal1 overlaps contact
_SUB_SURROUND = 0.12  # sub/well overlap of diffusion
_METAL_SPACING = 0.23  # metal1 spacing
_CONTACT_PITCH = 0.47  # contact center-to-center spacing (size + min space)

# Derived constants
_DIFFT = _CONTACT_SIZE + 2 * _DIFF_SURROUND  # 0.36, guard ring bar width
_HX = _CONTACT_SIZE / 2  # 0.115


# ---------------------------------------------------------------------------
# Contact array helper
# ---------------------------------------------------------------------------


def _contact_array_centers(fill_size: float) -> list[float]:
    """Return list of 1D contact center offsets for a fill region.

    Contacts of internal size _CONTACT_SIZE are tiled at _CONTACT_PITCH
    within a fill region of the given size, centered.
    """
    if fill_size < _CONTACT_SIZE:
        fill_size = _CONTACT_SIZE
    n = floor((fill_size - _CONTACT_SIZE) / _CONTACT_PITCH) + 1
    n = max(n, 1)
    span = (n - 1) * _CONTACT_PITCH
    start = -span / 2
    return [start + i * _CONTACT_PITCH for i in range(n)]


def _draw_contacts_2d(
    c: gf.Component,
    cx: float,
    cy: float,
    fill_w: float,
    fill_h: float,
) -> None:
    """Draw a 2D array of contacts centered at (cx, cy)."""
    xs = _contact_array_centers(fill_w)
    ys = _contact_array_centers(fill_h)
    hs = _CONTACT_GDS / 2
    for dx in xs:
        for dy in ys:
            c.add_polygon(
                [
                    (cx + dx - hs, cy + dy - hs),
                    (cx + dx + hs, cy + dy - hs),
                    (cx + dx + hs, cy + dy + hs),
                    (cx + dx - hs, cy + dy + hs),
                ],
                layer=layer["contact"],
            )


# ---------------------------------------------------------------------------
# Guard ring (matching Magic gf180mcu::guard_ring)
# ---------------------------------------------------------------------------

# Implant bloat rules (from Magic CIF extraction for GF180MCU):
# nsd -> comp + nplus with nplus_bloat = 0.16
# psd -> comp + pplus with pplus_bloat complicated (varies by context)
# We precompute the shapes from reference analysis.

_NSD_IMPLANT_OUTER_BLOAT = 0.16  # nplus extends outside comp by this amount
_NSD_IMPLANT_INNER_BLOAT = (
    0.11  # nplus extends inside comp (toward center) by this amount
)
# psd bloat is more complex - approximately 0.02-0.03 with corner patches


def _guard_ring(
    c: gf.Component,
    gw: float,
    gh: float,
    plus_diff_layer: LayerSpec,
    plus_contact_layer: LayerSpec,
    sub_type_layer: LayerSpec,
    implant_layer: LayerSpec,
    implant_bloat: float,
    is_psd: bool = False,
    draw_well: bool = True,
    well_ext_extra: float = 0.0,
) -> None:
    """Draw a guard ring centered at origin.

    Args:
        c: component to draw into
        gw: guard ring width (measured center-to-center of contacts)
        gh: guard ring height
        plus_diff_layer: comp layer (always comp for GF180MCU)
        plus_contact_layer: contact layer
        sub_type_layer: well layer (nwell or lvpwell)
        implant_layer: implant layer (nplus or pplus) for the guard ring diffusion
        implant_bloat: how much implant extends beyond comp
        is_psd: True if guard ring uses psd type (pplus, more complex bloat)
        draw_well: if False, skip drawing the sub_type_layer rectangle
        well_ext_extra: additional extension for the sub_type_layer beyond standard well_ext
    """
    hw = gw / 2
    hh = gh / 2
    hdifft = _DIFFT / 2  # 0.18

    # 1. Draw 4 comp bars forming a ring
    # Top bar
    c.add_polygon(
        [
            (-(hw + hdifft), hh - hdifft),
            (hw + hdifft, hh - hdifft),
            (hw + hdifft, hh + hdifft),
            (-(hw + hdifft), hh + hdifft),
        ],
        layer=layer["comp"],
    )
    # Bottom bar
    c.add_polygon(
        [
            (-(hw + hdifft), -(hh + hdifft)),
            (hw + hdifft, -(hh + hdifft)),
            (hw + hdifft, -(hh - hdifft)),
            (-(hw + hdifft), -(hh - hdifft)),
        ],
        layer=layer["comp"],
    )
    # Left bar
    c.add_polygon(
        [
            (-(hw + hdifft), -(hh + hdifft)),
            (-(hw - hdifft), -(hh + hdifft)),
            (-(hw - hdifft), hh + hdifft),
            (-(hw + hdifft), hh + hdifft),
        ],
        layer=layer["comp"],
    )
    # Right bar
    c.add_polygon(
        [
            (hw - hdifft, -(hh + hdifft)),
            (hw + hdifft, -(hh + hdifft)),
            (hw + hdifft, hh + hdifft),
            (hw - hdifft, hh + hdifft),
        ],
        layer=layer["comp"],
    )

    # 2. Draw implant layer around guard ring comp
    _draw_guard_ring_implant(c, gw, gh, implant_layer, implant_bloat, is_psd)

    # 3. Draw metal ring (full metal ring as seen in references)
    _draw_guard_ring_metal(c, gw, gh)

    # 4. Draw contacts on left and right sides
    ch = gh - _CONTACT_SIZE - 2 * (_METAL_SURROUND + _METAL_SPACING)
    if ch < _CONTACT_SIZE:
        ch = _CONTACT_SIZE

    # Left contacts
    _draw_contacts_2d(c, -hw, 0, 0, ch)
    # Right contacts
    _draw_contacts_2d(c, hw, 0, 0, ch)

    # 5. Draw sub_type (well) covering entire guard ring + surround
    if draw_well:
        well_ext = _HX + _DIFF_SURROUND + _SUB_SURROUND + well_ext_extra
        c.add_polygon(
            [
                (-(hw + well_ext), -(hh + well_ext)),
                (hw + well_ext, -(hh + well_ext)),
                (hw + well_ext, hh + well_ext),
                (-(hw + well_ext), hh + well_ext),
            ],
            layer=sub_type_layer,
        )


def _draw_guard_ring_metal(c: gf.Component, gw: float, gh: float) -> None:
    """Draw the 4 metal bars forming a guard ring metal ring."""
    hw = gw / 2
    hh = gh / 2
    hcs = _CONTACT_SIZE / 2  # 0.115

    # Left bar: contact_size wide, extends full height minus contact_size/2 at ends
    c.add_polygon(
        [
            (-(hw + hcs), -(hh - hcs)),
            (-(hw - hcs), -(hh - hcs)),
            (-(hw - hcs), hh - hcs),
            (-(hw + hcs), hh - hcs),
        ],
        layer=layer["metal1"],
    )
    # Right bar
    c.add_polygon(
        [
            (hw - hcs, -(hh - hcs)),
            (hw + hcs, -(hh - hcs)),
            (hw + hcs, hh - hcs),
            (hw - hcs, hh - hcs),
        ],
        layer=layer["metal1"],
    )
    # Top bar
    c.add_polygon(
        [
            (-(hw + hcs), hh - hcs),
            (hw + hcs, hh - hcs),
            (hw + hcs, hh + hcs),
            (-(hw + hcs), hh + hcs),
        ],
        layer=layer["metal1"],
    )
    # Bottom bar
    c.add_polygon(
        [
            (-(hw + hcs), -(hh + hcs)),
            (hw + hcs, -(hh + hcs)),
            (hw + hcs, -(hh - hcs)),
            (-(hw + hcs), -(hh - hcs)),
        ],
        layer=layer["metal1"],
    )


def _draw_guard_ring_implant(
    c: gf.Component,
    gw: float,
    gh: float,
    implant_layer: LayerSpec,
    bloat: float,
    is_psd: bool,
) -> None:
    """Draw the implant layer around guard ring comp bars.

    For nsd-type (nplus + comp), the implant is a simple rectangular ring
    with uniform bloat beyond comp.

    For psd-type (pplus + comp), the implant has a more complex shape
    matching Magic's CIF extraction rules.
    """
    hw = gw / 2
    hh = gh / 2
    hdifft = _DIFFT / 2

    if not is_psd:
        # nsd type: rectangular ring with asymmetric bloat
        # nplus extends _NSD_IMPLANT_OUTER_BLOAT beyond comp outer edges
        # and _NSD_IMPLANT_INNER_BLOAT beyond comp inner edges (toward center)
        outer_x = hw + hdifft + _NSD_IMPLANT_OUTER_BLOAT
        outer_y = hh + hdifft + _NSD_IMPLANT_OUTER_BLOAT
        inner_x = hw - hdifft - _NSD_IMPLANT_INNER_BLOAT
        inner_y = hh - hdifft - _NSD_IMPLANT_INNER_BLOAT

        # Top bar
        c.add_polygon(
            [
                (-outer_x, inner_y),
                (outer_x, inner_y),
                (outer_x, outer_y),
                (-outer_x, outer_y),
            ],
            layer=implant_layer,
        )
        # Bottom bar
        c.add_polygon(
            [
                (-outer_x, -outer_y),
                (outer_x, -outer_y),
                (outer_x, -inner_y),
                (-outer_x, -inner_y),
            ],
            layer=implant_layer,
        )
        # Left bar
        c.add_polygon(
            [
                (-outer_x, -inner_y),
                (-inner_x, -inner_y),
                (-inner_x, inner_y),
                (-outer_x, inner_y),
            ],
            layer=implant_layer,
        )
        # Right bar
        c.add_polygon(
            [
                (inner_x, -inner_y),
                (outer_x, -inner_y),
                (outer_x, inner_y),
                (inner_x, inner_y),
            ],
            layer=implant_layer,
        )
    else:
        # psd type: more complex shape from Magic CIF extraction
        # The pplus has different bloat amounts and corner patches
        # From reference analysis across multiple param sets:
        # - Top/bottom bars: extend 0.02 beyond comp outer, start 0.02 below comp inner
        # - Side bars: extend 0.03 beyond comp outer and inner
        #   but truncated in Y leaving room for corner patches
        # - Corner patches bridge the gap

        co_x = hw + hdifft  # comp outer X
        co_y = hh + hdifft  # comp outer Y
        ci_x = hw - hdifft  # comp inner X
        ci_y = hh - hdifft  # comp inner Y

        # psd bloat values (from reference analysis, consistent across sizes)
        b_out = 0.02  # bloat on comp outer edge for top/bottom bars
        b_side = 0.03  # bloat on comp inner/outer edge for side bars
        side_y_gap = 0.125  # how far below ci_y the side bars end
        corner_h = 0.105  # corner patch height = side_y_gap - b_out

        # Inner X edge of side bars / corner patches
        side_inner_x = ci_x - b_side

        # Top bar: full width, from (ci_y - b_out) to (co_y + b_out)
        c.add_polygon(
            [
                (-(co_x + b_out), ci_y - b_out),
                (co_x + b_out, ci_y - b_out),
                (co_x + b_out, co_y + b_out),
                (-(co_x + b_out), co_y + b_out),
            ],
            layer=implant_layer,
        )
        # Bottom bar
        c.add_polygon(
            [
                (-(co_x + b_out), -(co_y + b_out)),
                (co_x + b_out, -(co_y + b_out)),
                (co_x + b_out, -(ci_y - b_out)),
                (-(co_x + b_out), -(ci_y - b_out)),
            ],
            layer=implant_layer,
        )
        # Left side bar (from -(ci_y - side_y_gap) to +(ci_y - side_y_gap))
        c.add_polygon(
            [
                (-(co_x + b_side), -(ci_y - side_y_gap)),
                (-side_inner_x, -(ci_y - side_y_gap)),
                (-side_inner_x, ci_y - side_y_gap),
                (-(co_x + b_side), ci_y - side_y_gap),
            ],
            layer=implant_layer,
        )
        # Right side bar
        c.add_polygon(
            [
                (side_inner_x, -(ci_y - side_y_gap)),
                (co_x + b_side, -(ci_y - side_y_gap)),
                (co_x + b_side, ci_y - side_y_gap),
                (side_inner_x, ci_y - side_y_gap),
            ],
            layer=implant_layer,
        )
        # Corner patches (4 corners)
        # Top-left
        c.add_polygon(
            [
                (-(co_x + b_out), ci_y - side_y_gap),
                (-side_inner_x, ci_y - side_y_gap),
                (-side_inner_x, ci_y - b_out),
                (-(co_x + b_out), ci_y - b_out),
            ],
            layer=implant_layer,
        )
        # Top-right
        c.add_polygon(
            [
                (side_inner_x, ci_y - side_y_gap),
                (co_x + b_out, ci_y - side_y_gap),
                (co_x + b_out, ci_y - b_out),
                (side_inner_x, ci_y - b_out),
            ],
            layer=implant_layer,
        )
        # Bottom-left
        c.add_polygon(
            [
                (-(co_x + b_out), -(ci_y - b_out)),
                (-side_inner_x, -(ci_y - b_out)),
                (-side_inner_x, -(ci_y - side_y_gap)),
                (-(co_x + b_out), -(ci_y - side_y_gap)),
            ],
            layer=implant_layer,
        )
        # Bottom-right
        c.add_polygon(
            [
                (side_inner_x, -(ci_y - b_out)),
                (co_x + b_out, -(ci_y - b_out)),
                (co_x + b_out, -(ci_y - side_y_gap)),
                (side_inner_x, -(ci_y - side_y_gap)),
            ],
            layer=implant_layer,
        )


# ---------------------------------------------------------------------------
# End contact helper (matching Magic draw_contact for resistor end caps)
# ---------------------------------------------------------------------------


def _draw_end_contact(
    c: gf.Component,
    cx: float,
    cy: float,
    fill_w: float,
    end_layer: LayerSpec,
    orient: str = "horz",
) -> None:
    """Draw an end contact with metal and base layer at (cx, cy).

    Args:
        c: component
        cx: contact center x position in um
        cy: contact center y position in um
        fill_w: contact fill width (cpl)
        end_layer: base layer (poly2 or comp)
        orient: "horz" or "vert" for metal growth direction
    """
    w = max(fill_w, _CONTACT_SIZE)
    h = _CONTACT_SIZE  # h=0 input -> clipped to contact_size

    hw = w / 2
    hh = h / 2

    # Draw contacts
    _draw_contacts_2d(c, cx, cy, w, h)

    # Draw end_type (poly/comp) surrounding contacts
    es = _DIFF_SURROUND if end_layer == layer["comp"] else _POLY_SURROUND
    c.add_polygon(
        [
            (cx - hw - es, cy - hh - es),
            (cx + hw + es, cy - hh - es),
            (cx + hw + es, cy + hh + es),
            (cx - hw - es, cy + hh + es),
        ],
        layer=end_layer,
    )

    # Draw metal
    ms = _METAL_SURROUND
    if orient == "horz":
        c.add_polygon(
            [
                (cx - hw - ms, cy - hh),
                (cx + hw + ms, cy - hh),
                (cx + hw + ms, cy + hh),
                (cx - hw - ms, cy + hh),
            ],
            layer=layer["metal1"],
        )
    else:
        c.add_polygon(
            [
                (cx - hw, cy - hh - ms),
                (cx + hw, cy - hh - ms),
                (cx + hw, cy + hh + ms),
                (cx - hw, cy + hh + ms),
            ],
            layer=layer["metal1"],
        )


# ---------------------------------------------------------------------------
# Metal resistor (rm1, rm2, rm3)
# ---------------------------------------------------------------------------


def _metal_res(
    w: float,
    l: float,
    m_layer: LayerSpec,
    res_layer: LayerSpec,
) -> gf.Component:
    """Draw a metal resistor centered at origin (l along Y, w along X).

    From Magic: guard=0, no contacts, just res_type mark + end_type metal.
    Metal extends res_to_endcont + contact_size/2 + end_surround beyond res_mk.
    For metal resistors: end_surround=0.0, res_to_endcont=0.2.
    Extension = 0.2 + 0.115 + 0.0 = 0.315.
    """
    c = gf.Component()

    hw = w / 2
    hl = l / 2
    ext = 0.315  # verified across all rm1/rm2/rm3 test cases

    # Res mark (centered, w x l)
    c.add_polygon(
        [(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)],
        layer=res_layer,
    )

    # Metal (centered, w x (l + 2*ext))
    c.add_polygon(
        [(-hw, -(hl + ext)), (hw, -(hl + ext)), (hw, hl + ext), (-hw, hl + ext)],
        layer=m_layer,
    )

    return c


# ---------------------------------------------------------------------------
# Poly resistor (ppolyf_u, npolyf_u, ppolyf_s, npolyf_s)
# ---------------------------------------------------------------------------


def _poly_res(
    w: float,
    l: float,
    res_type: str,
) -> gf.Component:
    """Draw a poly resistor with guard ring, centered at origin."""
    c = gf.Component()

    hw = w / 2
    hl = l / 2

    # Device parameters per type
    if res_type in ("ppolyf_u", "npolyf_u"):
        # Unsilicided poly
        res_to_endcont = 0.33  # sblk_to_cont
        end_surround = _POLY_SURROUND  # 0.065
        end_spacing = 0.60
        res_diff_spacing = 0.60
        mask_clearance = 0.52
        sab_ext_x = 0.28  # sab extends beyond res_mk in X direction
        has_sab = True
    else:
        # Silicided poly
        res_to_endcont = _POLY_SURROUND + _CONTACT_SIZE / 2  # 0.065 + 0.115 = 0.18
        end_surround = _POLY_SURROUND
        end_spacing = 0.28 if res_type == "npolyf_s" else 0.28
        res_diff_spacing = 0.28 if res_type == "npolyf_s" else 0.41
        has_sab = False

    # Implant and well types (from Tcl *_draw procedures)
    # ppolyf_u: body=pplus(rpp), guard=nsd, well=nwell
    # ppolyf_s: body=pplus(rpps), guard=nsd, well=nwell
    # npolyf_u: body=nplus(rnp), guard=psd, well=pwell
    # npolyf_s: body=nplus(rnps), guard=nsd, well=nwell
    if res_type == "ppolyf_u":
        body_impl_layer = layer["pplus"]
        gr_impl_layer = layer["nplus"]
        well_layer = layer["nwell"]
        is_psd_gr = False
    elif res_type == "ppolyf_s":
        body_impl_layer = layer["pplus"]
        gr_impl_layer = layer["nplus"]
        well_layer = layer["nwell"]
        is_psd_gr = False
    elif res_type == "npolyf_u":
        body_impl_layer = layer["nplus"]
        gr_impl_layer = layer["pplus"]
        well_layer = layer["lvpwell"]
        is_psd_gr = True
    elif res_type == "npolyf_s":
        body_impl_layer = layer["nplus"]
        gr_impl_layer = layer["nplus"]
        well_layer = layer["nwell"]
        is_psd_gr = False

    # --- Compute geometry ---

    hesz = _CONTACT_SIZE / 2 + end_surround  # 0.18 for poly
    # epl: end contact width (reduced by end_surround on each side)
    epl = w - 2 * end_surround
    # cpl: contact fill width
    cpl = epl

    # Poly extent: from body center, extends to end contact center + hesz
    poly_ext_y = hl + res_to_endcont + hesz  # poly half-height

    # --- Draw layers ---

    # 1. Res mark (110,5): w x l centered
    c.add_polygon(
        [(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)],
        layer=layer["res_mk"],
    )

    # 2. Poly2 (30,0): w x 2*poly_ext_y centered
    c.add_polygon(
        [(-hw, -poly_ext_y), (hw, -poly_ext_y), (hw, poly_ext_y), (-hw, poly_ext_y)],
        layer=layer["poly2"],
    )

    # 3. SAB (49,0): for unsilicided types, extends sab_ext_x beyond res_mk in X
    if has_sab:
        sab_hw = hw + sab_ext_x
        c.add_polygon(
            [(-sab_hw, -hl), (sab_hw, -hl), (sab_hw, hl), (-sab_hw, hl)],
            layer=layer["sab"],
        )

    # 4. Body implant (pplus or nplus): extends 0.30 beyond poly2 in both directions
    impl_ext = 0.30
    if res_type in ("ppolyf_s", "npolyf_s"):
        # For silicided: implant extends 0.18 beyond poly in all directions
        impl_ext_x = end_surround + _CONTACT_SIZE / 2  # 0.18
        impl_ext_y = end_surround + _CONTACT_SIZE / 2  # 0.18
        c.add_polygon(
            [
                (-(hw + impl_ext_x), -(poly_ext_y + impl_ext_y)),
                (hw + impl_ext_x, -(poly_ext_y + impl_ext_y)),
                (hw + impl_ext_x, poly_ext_y + impl_ext_y),
                (-(hw + impl_ext_x), poly_ext_y + impl_ext_y),
            ],
            layer=body_impl_layer,
        )
    else:
        # For unsilicided: implant extends 0.30 beyond poly in all directions
        c.add_polygon(
            [
                (-(hw + impl_ext), -(poly_ext_y + impl_ext)),
                (hw + impl_ext, -(poly_ext_y + impl_ext)),
                (hw + impl_ext, poly_ext_y + impl_ext),
                (-(hw + impl_ext), poly_ext_y + impl_ext),
            ],
            layer=body_impl_layer,
        )

    # 5. End contacts (top and bottom of poly body)
    end_cy = hl + res_to_endcont  # contact center Y
    _draw_end_contact(c, 0, end_cy, cpl, layer["poly2"], orient="horz")
    _draw_end_contact(c, 0, -end_cy, cpl, layer["poly2"], orient="horz")

    # 6. Guard ring
    # Device footprint height (fh) = 2 * poly_ext_y
    fh = 2 * poly_ext_y
    fw = w  # device footprint width = w

    # Guard ring dimensions (measured to contact centers)
    gx = fw + 2 * (res_diff_spacing + _DIFF_SURROUND) + _CONTACT_SIZE
    gy = fh + 2 * (end_spacing + _DIFF_SURROUND) + _CONTACT_SIZE

    _guard_ring(
        c,
        gx,
        gy,
        plus_diff_layer=layer["comp"],
        plus_contact_layer=layer["contact"],
        sub_type_layer=well_layer,
        implant_layer=gr_impl_layer,
        implant_bloat=_NSD_IMPLANT_OUTER_BLOAT,
        is_psd=is_psd_gr,
    )

    return c


# ---------------------------------------------------------------------------
# Diffusion resistor (nplus_u, pplus_u)
# ---------------------------------------------------------------------------


def _diff_res(
    w: float,
    l: float,
    res_type: str,
) -> gf.Component:
    """Draw a diffusion resistor with guard ring, centered at origin."""
    c = gf.Component()

    hw = w / 2
    hl = l / 2

    # Parameters from Tcl
    res_to_endcont = 0.45
    end_surround = _DIFF_SURROUND  # 0.065
    end_spacing = 0.45
    res_diff_spacing = 0.45
    mask_clearance = 0.22
    sab_ext_x = 0.22  # sab extends beyond res_mk in X

    hesz = _CONTACT_SIZE / 2 + end_surround  # 0.18
    epl = w - 2 * end_surround  # end contact width
    cpl = epl

    # Comp body extends from body center to end contact + hesz
    comp_ext_y = hl + res_to_endcont + hesz  # comp half-height

    if res_type == "nplus_u":
        body_impl_layer = layer["nplus"]
        gr_impl_layer = layer["pplus"]
        well_layer = layer["lvpwell"]
        is_psd_gr = True
    else:
        body_impl_layer = layer["pplus"]
        gr_impl_layer = layer["nplus"]
        well_layer = layer["nwell"]
        is_psd_gr = False

    # --- Draw layers ---

    # 1. Res mark (110,5): w x l centered
    c.add_polygon(
        [(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)],
        layer=layer["res_mk"],
    )

    # 2. SAB (49,0): extends sab_ext_x beyond res_mk in X, same Y as res_mk
    sab_hw = hw + sab_ext_x
    c.add_polygon(
        [(-sab_hw, -hl), (sab_hw, -hl), (sab_hw, hl), (-sab_hw, hl)],
        layer=layer["sab"],
    )

    # 3. Comp body (22,0): w x 2*comp_ext_y centered
    c.add_polygon(
        [(-hw, -comp_ext_y), (hw, -comp_ext_y), (hw, comp_ext_y), (-hw, comp_ext_y)],
        layer=layer["comp"],
    )

    # 4. Body implant: two overlapping rectangles matching Magic's CIF extraction
    # nplus/pplus for the body has two rectangles:
    # One with 0.18 bloat (nplus_bloat = diff_surround + contact_size/2)
    # One with 0.16 bloat
    bloat_outer = end_surround + _CONTACT_SIZE / 2  # 0.18
    bloat_inner = _NSD_IMPLANT_OUTER_BLOAT  # 0.16
    c.add_polygon(
        [
            (-(hw + bloat_outer), -(comp_ext_y + bloat_outer)),
            (hw + bloat_outer, -(comp_ext_y + bloat_outer)),
            (hw + bloat_outer, comp_ext_y + bloat_outer),
            (-(hw + bloat_outer), comp_ext_y + bloat_outer),
        ],
        layer=body_impl_layer,
    )
    c.add_polygon(
        [
            (-(hw + bloat_inner), -(comp_ext_y + bloat_inner)),
            (hw + bloat_inner, -(comp_ext_y + bloat_inner)),
            (hw + bloat_inner, comp_ext_y + bloat_inner),
            (-(hw + bloat_inner), comp_ext_y + bloat_inner),
        ],
        layer=body_impl_layer,
    )

    # 5. End contacts (top and bottom)
    end_cy = hl + res_to_endcont
    _draw_end_contact(c, 0, end_cy, cpl, layer["comp"], orient="horz")
    _draw_end_contact(c, 0, -end_cy, cpl, layer["comp"], orient="horz")

    # 6. Guard ring
    fh = 2 * comp_ext_y
    fw = w
    gx = fw + 2 * (res_diff_spacing + _DIFF_SURROUND) + _CONTACT_SIZE
    gy = fh + 2 * (end_spacing + _DIFF_SURROUND) + _CONTACT_SIZE

    _guard_ring(
        c,
        gx,
        gy,
        plus_diff_layer=layer["comp"],
        plus_contact_layer=layer["contact"],
        sub_type_layer=well_layer,
        implant_layer=gr_impl_layer,
        implant_bloat=_NSD_IMPLANT_OUTER_BLOAT,
        is_psd=is_psd_gr,
    )

    return c


# ---------------------------------------------------------------------------
# Well resistor (nwell)
# ---------------------------------------------------------------------------


def _well_res(
    w: float,
    l: float,
) -> gf.Component:
    """Draw an nwell resistor with guard ring, centered at origin."""
    c = gf.Component()

    hw = w / 2
    hl = l / 2

    # Parameters from Tcl nwell_draw
    res_to_endcont = 0.38
    end_surround = _DIFF_SURROUND  # 0.065
    end_spacing = 1.4
    res_diff_spacing = 0.28
    well_res_overlap = 0.24

    hesz = _CONTACT_SIZE / 2 + end_surround  # 0.18

    # nwell body: extends hl + well_res_overlap + end cap
    # The nwell body = w (in X) x l + 2*well_res_overlap (extra) + end contacts
    # From reference: nwell = w x (l + 2*0.8) approximately
    # Let me compute from reference: nwell w=2, l=10 -> nwell (-1, -5.8)-(1, 5.8)
    # nwell half_x = 1.0 = w/2 = 1.0 ✓
    # nwell half_y = 5.8 = l/2 + 0.8
    # 0.8 = well_res_overlap + contact_size/2 + end_surround + res_to_endcont
    # = 0.24 + 0.115 + 0.065 + 0.38 = 0.80 ✓
    well_ext_y = res_to_endcont + hesz + well_res_overlap  # 0.38 + 0.18 + 0.24 = 0.80
    nwell_hy = hl + well_ext_y

    # Draw nwell
    c.add_polygon(
        [(-hw, -nwell_hy), (hw, -nwell_hy), (hw, nwell_hy), (-hw, nwell_hy)],
        layer=layer["nwell"],
    )

    # End contacts: nsd type (comp + nplus)
    # Contact center at hl + res_to_endcont (well_res_overlap shifts nwell body, not contacts)
    # From reference: nplus at (−0.92,5.04)-(0.92,5.72) for l=10, w=2
    # nplus center_y = 5.38 = hl + res_to_endcont = 5 + 0.38

    # epl for well resistor: w - 2*end_surround - 2*well_res_overlap
    epl = w - 2 * end_surround - 2 * well_res_overlap
    cpl = epl

    end_cy = hl + res_to_endcont  # contact center at hl + res_to_endcont

    # End comp (nsd): comp + nplus at top and bottom
    # comp extends: epl + 2*end_surround in X, contact_size + 2*end_surround in Y
    comp_hw = (epl + 2 * end_surround) / 2  # = (w - 2*well_res_overlap) / 2
    comp_hh = hesz  # contact_size/2 + end_surround

    # Top end comp
    c.add_polygon(
        [
            (-comp_hw, end_cy - comp_hh),
            (comp_hw, end_cy - comp_hh),
            (comp_hw, end_cy + comp_hh),
            (-comp_hw, end_cy + comp_hh),
        ],
        layer=layer["comp"],
    )
    # Bottom end comp
    c.add_polygon(
        [
            (-comp_hw, -(end_cy + comp_hh)),
            (comp_hw, -(end_cy + comp_hh)),
            (comp_hw, -(end_cy - comp_hh)),
            (-comp_hw, -(end_cy - comp_hh)),
        ],
        layer=layer["comp"],
    )

    # nplus for end contacts
    nplus_hw = comp_hw + _NSD_IMPLANT_OUTER_BLOAT
    nplus_hh = comp_hh + _NSD_IMPLANT_OUTER_BLOAT
    c.add_polygon(
        [
            (-nplus_hw, end_cy - nplus_hh),
            (nplus_hw, end_cy - nplus_hh),
            (nplus_hw, end_cy + nplus_hh),
            (-nplus_hw, end_cy + nplus_hh),
        ],
        layer=layer["nplus"],
    )
    c.add_polygon(
        [
            (-nplus_hw, -(end_cy + nplus_hh)),
            (nplus_hw, -(end_cy + nplus_hh)),
            (nplus_hw, -(end_cy - nplus_hh)),
            (-nplus_hw, -(end_cy - nplus_hh)),
        ],
        layer=layer["nplus"],
    )

    # End contacts
    _draw_contacts_2d(c, 0, end_cy, cpl, _CONTACT_SIZE)
    _draw_contacts_2d(c, 0, -end_cy, cpl, _CONTACT_SIZE)

    # End contact metal (horz orientation)
    m_hw = max(cpl, _CONTACT_SIZE) / 2 + _METAL_SURROUND
    m_hh = _CONTACT_SIZE / 2
    c.add_polygon(
        [
            (-m_hw, end_cy - m_hh),
            (m_hw, end_cy - m_hh),
            (m_hw, end_cy + m_hh),
            (-m_hw, end_cy + m_hh),
        ],
        layer=layer["metal1"],
    )
    c.add_polygon(
        [
            (-m_hw, -(end_cy + m_hh)),
            (m_hw, -(end_cy + m_hh)),
            (m_hw, -(end_cy - m_hh)),
            (-m_hw, -(end_cy - m_hh)),
        ],
        layer=layer["metal1"],
    )

    # Guard ring
    # Device footprint: nwell body extent determines the guard ring height
    # fh is based on nwell_hy (which includes well_res_overlap), not just end contact position
    fh = 2 * nwell_hy
    fw = w

    gx = fw + 2 * (res_diff_spacing + _DIFF_SURROUND) + _CONTACT_SIZE
    gy = fh + 2 * (end_spacing + _DIFF_SURROUND) + _CONTACT_SIZE

    # lvpwell guard ring (psd guard ring for nwell resistor)
    # Draw lvpwell as a ring (4 bars) around the nwell body, not as a solid rectangle.
    # The inner boundary of the lvpwell ring = nwell body edge (hw, nwell_hy).
    # The outer boundary = guard ring outer extent.
    well_ext = _HX + _DIFF_SURROUND + _SUB_SURROUND
    lvpwell_ox = gx / 2 + well_ext  # outer X
    lvpwell_oy = gy / 2 + well_ext  # outer Y
    lvpwell_ix = hw  # inner X = nwell body edge
    lvpwell_iy = nwell_hy  # inner Y = nwell body edge

    # Top bar
    c.add_polygon(
        [
            (-lvpwell_ox, lvpwell_iy),
            (lvpwell_ox, lvpwell_iy),
            (lvpwell_ox, lvpwell_oy),
            (-lvpwell_ox, lvpwell_oy),
        ],
        layer=layer["lvpwell"],
    )
    # Bottom bar
    c.add_polygon(
        [
            (-lvpwell_ox, -lvpwell_oy),
            (lvpwell_ox, -lvpwell_oy),
            (lvpwell_ox, -lvpwell_iy),
            (-lvpwell_ox, -lvpwell_iy),
        ],
        layer=layer["lvpwell"],
    )
    # Left bar
    c.add_polygon(
        [
            (-lvpwell_ox, -lvpwell_iy),
            (-lvpwell_ix, -lvpwell_iy),
            (-lvpwell_ix, lvpwell_iy),
            (-lvpwell_ox, lvpwell_iy),
        ],
        layer=layer["lvpwell"],
    )
    # Right bar
    c.add_polygon(
        [
            (lvpwell_ix, -lvpwell_iy),
            (lvpwell_ox, -lvpwell_iy),
            (lvpwell_ox, lvpwell_iy),
            (lvpwell_ix, lvpwell_iy),
        ],
        layer=layer["lvpwell"],
    )

    _guard_ring(
        c,
        gx,
        gy,
        plus_diff_layer=layer["comp"],
        plus_contact_layer=layer["contact"],
        sub_type_layer=layer["lvpwell"],
        implant_layer=layer["pplus"],
        implant_bloat=0.02,
        is_psd=True,
        draw_well=False,  # lvpwell ring drawn manually above
    )

    # Add pplus shoulder strips for the nwell resistor guard ring.
    # The psd _guard_ring_implant draws a uniform-width side bar, but the nwell
    # resistor requires a wider inner strip in the shoulder region adjacent to
    # the nwell end-contact area.  These 4 thin rectangles fill the gap between
    # the central bar inner edge (ci_x - 0.03) and the shoulder inner edge
    # (ci_x - 0.16), where ci_x = gx/2 - _DIFFT/2.
    #
    # Boundaries derived from reference GDS analysis:
    #   shoulder_inner_x = ci_x - _NSD_IMPLANT_OUTER_BLOAT (0.16)
    #   side_inner_x     = ci_x - 0.03  (psd b_side in _guard_ring_implant)
    #   shoulder_bottom  = nwell_hy - end_spacing + 0.01  (10 nm grid snap)
    #   shoulder_height  = 1.98 um  (constant across l and w)
    _ci_x = gx / 2 - _DIFFT / 2
    _shoulder_inner_x = _ci_x - _NSD_IMPLANT_OUTER_BLOAT
    _side_inner_x = _ci_x - 0.03
    _shoulder_bottom = nwell_hy - end_spacing + 0.01
    _shoulder_top = _shoulder_bottom + 1.98

    # Top-left shoulder strip
    c.add_polygon(
        [
            (-_side_inner_x, _shoulder_bottom),
            (-_shoulder_inner_x, _shoulder_bottom),
            (-_shoulder_inner_x, _shoulder_top),
            (-_side_inner_x, _shoulder_top),
        ],
        layer=layer["pplus"],
    )
    # Top-right shoulder strip
    c.add_polygon(
        [
            (_shoulder_inner_x, _shoulder_bottom),
            (_side_inner_x, _shoulder_bottom),
            (_side_inner_x, _shoulder_top),
            (_shoulder_inner_x, _shoulder_top),
        ],
        layer=layer["pplus"],
    )
    # Bottom-left shoulder strip
    c.add_polygon(
        [
            (-_side_inner_x, -_shoulder_top),
            (-_shoulder_inner_x, -_shoulder_top),
            (-_shoulder_inner_x, -_shoulder_bottom),
            (-_side_inner_x, -_shoulder_bottom),
        ],
        layer=layer["pplus"],
    )
    # Bottom-right shoulder strip
    c.add_polygon(
        [
            (_shoulder_inner_x, -_shoulder_top),
            (_side_inner_x, -_shoulder_top),
            (_side_inner_x, -_shoulder_bottom),
            (_shoulder_inner_x, -_shoulder_bottom),
        ],
        layer=layer["pplus"],
    )

    return c


# ---------------------------------------------------------------------------
# High-R poly resistor (ppolyf_u_1k, ppolyf_u_1k_6p0)
# ---------------------------------------------------------------------------


def _highR_poly_res(
    w: float,
    l: float,
    is_6p0: bool = False,
) -> gf.Component:
    """Draw a high-R poly resistor with guard ring."""
    c = gf.Component()

    hw = w / 2
    hl = l / 2

    # Parameters from Tcl ppolyf_u_1k_draw
    res_to_endcont = 0.43
    end_surround = _POLY_SURROUND  # 0.065
    end_spacing = 0.7
    res_diff_spacing = 0.7
    mask_clearance = 0.22

    hesz = _CONTACT_SIZE / 2 + end_surround  # 0.18
    epl = w - 2 * end_surround
    cpl = epl

    poly_ext_y = hl + res_to_endcont + hesz  # poly half-height

    # From reference: poly2 w=1.0, l=1.0 -> (-0.5, -1.11)-(0.5, 1.11)
    # poly_ext_y = 0.5 + 0.43 + 0.18 = 1.11 ✓

    # Guard ring uses psd type
    gr_impl_layer = layer["pplus"]
    well_layer = layer["lvpwell"]

    # --- Draw layers ---

    # 1. Inner res_mk: w x l centered
    c.add_polygon(
        [(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)],
        layer=layer["res_mk"],
    )

    # 2. Outer res_mk (fhres mark): extends sab_ext beyond inner in X, same Y
    # From reference: res_mk has TWO shapes:
    # (-0.78, -0.5)-(0.78, 0.5) and (-0.5, -0.5)-(0.5, 0.5)
    # The outer one has sab_ext = 0.28 in X
    sab_ext_x = 0.28
    c.add_polygon(
        [
            (-(hw + sab_ext_x), -hl),
            (hw + sab_ext_x, -hl),
            (hw + sab_ext_x, hl),
            (-(hw + sab_ext_x), hl),
        ],
        layer=layer["res_mk"],
    )

    # 3. SAB: two shapes
    # Inner sab: same as outer res_mk
    c.add_polygon(
        [
            (-(hw + sab_ext_x), -hl),
            (hw + sab_ext_x, -hl),
            (hw + sab_ext_x, hl),
            (-(hw + sab_ext_x), hl),
        ],
        layer=layer["sab"],
    )
    # Outer sab: extends 0.10 more in Y
    sab_ext_y = 0.10
    c.add_polygon(
        [
            (-(hw + sab_ext_x), -(hl + sab_ext_y)),
            (hw + sab_ext_x, -(hl + sab_ext_y)),
            (hw + sab_ext_x, hl + sab_ext_y),
            (-(hw + sab_ext_x), hl + sab_ext_y),
        ],
        layer=layer["sab"],
    )

    # 4. Resistor mark (62,0): large box around the device
    # From reference: resistor = (-0.9, -1.51)-(0.9, 1.51) for w=1,l=1
    # That's (hw+0.4, poly_ext_y+0.4) approximately
    # Actually: 0.9 = 0.5 + 0.4, 1.51 = 1.11 + 0.4
    res_mark_ext_x = 0.40
    res_mark_ext_y = 0.40
    c.add_polygon(
        [
            (-(hw + res_mark_ext_x), -(poly_ext_y + res_mark_ext_y)),
            (hw + res_mark_ext_x, -(poly_ext_y + res_mark_ext_y)),
            (hw + res_mark_ext_x, poly_ext_y + res_mark_ext_y),
            (-(hw + res_mark_ext_x), poly_ext_y + res_mark_ext_y),
        ],
        layer=layer["resistor"],
    )

    # 5. Poly2
    c.add_polygon(
        [(-hw, -poly_ext_y), (hw, -poly_ext_y), (hw, poly_ext_y), (-hw, poly_ext_y)],
        layer=layer["poly2"],
    )

    # 6. End contacts
    end_cy = hl + res_to_endcont
    _draw_end_contact(c, 0, end_cy, cpl, layer["poly2"], orient="horz")
    _draw_end_contact(c, 0, -end_cy, cpl, layer["poly2"], orient="horz")

    # 6b. Body end-contact pplus patches
    # pplus covers the poly end contact regions: from hl to poly_ext_y + 0.20 in Y,
    # and extends 0.20 beyond poly2 in X.
    # From reference analysis: pplus hw = w/2 + 0.20, y spans [hl, poly_ext_y + 0.20]
    body_pplus_impl_ext = 0.20
    body_pplus_hw = hw + body_pplus_impl_ext
    body_pplus_top = poly_ext_y + body_pplus_impl_ext
    # Top pplus patch
    c.add_polygon(
        [
            (-body_pplus_hw, hl),
            (body_pplus_hw, hl),
            (body_pplus_hw, body_pplus_top),
            (-body_pplus_hw, body_pplus_top),
        ],
        layer=layer["pplus"],
    )
    # Bottom pplus patch
    c.add_polygon(
        [
            (-body_pplus_hw, -body_pplus_top),
            (body_pplus_hw, -body_pplus_top),
            (body_pplus_hw, -hl),
            (-body_pplus_hw, -hl),
        ],
        layer=layer["pplus"],
    )

    # 7. Guard ring
    fh = 2 * poly_ext_y
    fw = w
    gx = fw + 2 * (res_diff_spacing + _DIFF_SURROUND) + _CONTACT_SIZE
    gy = fh + 2 * (end_spacing + _DIFF_SURROUND) + _CONTACT_SIZE

    # For the 6p0 variant, the lvpwell extends 0.04 beyond the standard well_ext
    well_ext_extra_6p0 = 0.04 if is_6p0 else 0.0

    _guard_ring(
        c,
        gx,
        gy,
        plus_diff_layer=layer["comp"],
        plus_contact_layer=layer["contact"],
        sub_type_layer=well_layer,
        implant_layer=gr_impl_layer,
        implant_bloat=0.02,
        is_psd=True,
        well_ext_extra=well_ext_extra_6p0,
    )

    # 8. Dualgate for 6p0 variant
    if is_6p0:
        # From reference: dualgate = (-1.8, -2.41)-(1.8, 2.41) for w=1, l=1
        # dualgate extends 0.12 beyond standard lvpwell (without 6p0 extension)
        well_ext = _HX + _DIFF_SURROUND + _SUB_SURROUND
        gx_half = gx / 2
        gy_half = gy / 2
        dg_ext = 0.12  # dualgate extends beyond well
        well_x = gx_half + well_ext
        well_y = gy_half + well_ext
        c.add_polygon(
            [
                (-(well_x + dg_ext), -(well_y + dg_ext)),
                (well_x + dg_ext, -(well_y + dg_ext)),
                (well_x + dg_ext, well_y + dg_ext),
                (-(well_x + dg_ext), well_y + dg_ext),
            ],
            layer=layer["dualgate"],
        )

    return c


# ---------------------------------------------------------------------------
# Main entry point: res()
# ---------------------------------------------------------------------------


@gf.cell(tags=["res"])
def res(
    l_res: float = 0.1,
    w_res: float = 0.1,
    res_type: str = "rm1",
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
) -> gf.Component:
    """Returns a resistor component matching Magic VLSI geometry.

    All layouts are centered at the origin with length along Y and width along X.

    Args:
        l_res: resistor length.
        w_res: resistor width.
        res_type: resistor variant.
        label: whether to generate labels.
        r0_label: label for terminal 0.
        r1_label: label for terminal 1.
    """
    # --- Metal resistors ---
    if res_type == "rm1":
        c = _metal_res(w_res, l_res, layer["metal1"], layer["metal1_res"])
    elif res_type == "rm2":
        c = _metal_res(w_res, l_res, layer["metal2"], layer["metal2_res"])
    elif res_type == "rm3":
        c = _metal_res(w_res, l_res, layer["metal3"], layer["metal3_res"])

    # --- Poly resistors ---
    elif res_type in ("ppolyf_u", "npolyf_u", "ppolyf_s", "npolyf_s"):
        c = _poly_res(w_res, l_res, res_type)

    # --- Diffusion resistors ---
    elif res_type in ("nplus_u", "pplus_u"):
        c = _diff_res(w_res, l_res, res_type)

    # --- Well resistor ---
    elif res_type == "nwell":
        c = _well_res(w_res, l_res)

    # --- High-R poly ---
    elif res_type == "ppolyf_u_1k":
        c = _highR_poly_res(w_res, l_res, is_6p0=False)
    elif res_type == "ppolyf_u_1k_6p0":
        c = _highR_poly_res(w_res, l_res, is_6p0=True)

    else:
        raise ValueError(f"Unknown res_type: {res_type}")

    # Copy to output component with ports
    out = gf.Component("res_dev")
    ref = out.add_ref(c)

    # Add electrical ports
    hw = w_res / 2
    hl = l_res / 2

    if res_type in ("rm1", "rm2", "rm3"):
        ext = 0.315
        m_layer = {
            "rm1": layer["metal1"],
            "rm2": layer["metal2"],
            "rm3": layer["metal3"],
        }[res_type]
        out.add_port(
            name="r0",
            center=(0, hl + ext),
            width=w_res,
            orientation=90,
            layer=m_layer,
            port_type="electrical",
        )
        out.add_port(
            name="r1",
            center=(0, -(hl + ext)),
            width=w_res,
            orientation=270,
            layer=m_layer,
            port_type="electrical",
        )
    else:
        out.add_port(
            name="r0",
            center=(0, hl),
            width=w_res,
            orientation=90,
            layer=layer["metal1"],
            port_type="electrical",
        )
        out.add_port(
            name="r1",
            center=(0, -hl),
            width=w_res,
            orientation=270,
            layer=layer["metal1"],
            port_type="electrical",
        )

    # VLSIR Simulation Metadata

    add_electrical_pins(out, port_pin_mapping={"r0": ["r0"], "r1": ["r1"]})
    return out
