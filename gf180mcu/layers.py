import gdsfactory as gf
from gdsfactory.technology import LayerLevel, LayerMap, LayerStack
from gdsfactory.typings import Layer

from gf180mcu.config import PATH


class LAYER(LayerMap):
    comp: Layer = (22, 0)
    dnwell: Layer = (12, 0)
    nwell: Layer = (21, 0)
    lvpwell: Layer = (204, 0)
    dualgate: Layer = (55, 0)
    poly2: Layer = (30, 0)
    nplus: Layer = (32, 0)
    pplus: Layer = (31, 0)
    sab: Layer = (49, 0)
    esd: Layer = (24, 0)
    contact: Layer = (33, 0)
    metal1: Layer = (34, 0)
    via1: Layer = (35, 0)
    metal2: Layer = (36, 0)
    via2: Layer = (38, 0)
    metal3: Layer = (42, 0)
    via3: Layer = (40, 0)
    metal4: Layer = (46, 0)
    via4: Layer = (41, 0)
    metal5: Layer = (81, 0)
    via5: Layer = (82, 0)
    metaltop: Layer = (53, 0)
    pad: Layer = (37, 0)
    resistor: Layer = (62, 0)
    fhres: Layer = (227, 0)
    fusetop: Layer = (75, 0)
    fusewindow_d: Layer = (96, 1)
    polyfuse: Layer = (220, 0)
    mvsd: Layer = (210, 0)
    mvpsd: Layer = (11, 39)
    nat: Layer = (5, 0)
    comp_dummy: Layer = (22, 4)
    poly2_dummy: Layer = (30, 4)
    metal1_dummy: Layer = (34, 4)
    metal2_dummy: Layer = (36, 4)
    metal3_dummy: Layer = (42, 4)
    metal4_dummy: Layer = (46, 4)
    metal5_dummy: Layer = (81, 4)
    metaltop_dummy: Layer = (53, 4)
    comp_label: Layer = (22, 10)
    poly2_label: Layer = (30, 10)
    metal1_label: Layer = (34, 10)
    metal2_label: Layer = (36, 10)
    metal3_label: Layer = (42, 10)
    metal4_label: Layer = (46, 10)
    metal5_label: Layer = (81, 10)
    metaltop_label: Layer = (53, 10)
    metal1_slot: Layer = (34, 3)
    metal2_slot: Layer = (36, 3)
    metal3_slot: Layer = (42, 3)
    metal4_slot: Layer = (46, 3)
    metal5_slot: Layer = (81, 3)
    metaltop_slot: Layer = (53, 3)
    metal1_pin: Layer = (34, 2)
    metal2_pin: Layer = (36, 2)
    metal3_pin: Layer = (42, 2)
    metal4_pin: Layer = (46, 2)
    metal5_pin: Layer = (81, 2)
    metaltop_pin: Layer = (53, 2)
    ubmpperi: Layer = (183, 0)
    ubmparray: Layer = (184, 0)
    ubmeplate: Layer = (185, 0)
    schottky_diode: Layer = (241, 0)
    zener: Layer = (178, 0)
    res_mk: Layer = (110, 5)
    opc_drc: Layer = (124, 5)
    ndmy: Layer = (111, 5)
    pmndmy: Layer = (152, 5)
    v5_xtor: Layer = (112, 1)
    cap_mk: Layer = (117, 5)
    mos_cap_mk: Layer = (166, 5)
    ind_mk: Layer = (151, 5)
    diode_mk: Layer = (115, 5)
    drc_bjt: Layer = (127, 5)
    lvs_bjt: Layer = (118, 5)
    mim_l_mk: Layer = (117, 10)
    latchup_mk: Layer = (137, 5)
    guard_ring_mk: Layer = (167, 5)
    otp_mk: Layer = (173, 5)
    mtpmark: Layer = (122, 5)
    neo_ee_mk: Layer = (88, 17)
    sramcore: Layer = (108, 5)
    lvs_rf: Layer = (100, 5)
    lvs_drain: Layer = (100, 7)
    ind_mk1: Layer = (151, 5)
    hvpolyrs: Layer = (123, 5)
    lvs_io: Layer = (119, 5)
    probe_mk: Layer = (13, 17)
    esd_mk: Layer = (24, 5)
    lvs_source: Layer = (100, 8)
    well_diode_mk: Layer = (153, 51)
    ldmos_xtor: Layer = (226, 0)
    plfuse: Layer = (125, 5)
    efuse_mk: Layer = (80, 5)
    mcell_feol_mk: Layer = (11, 17)
    ymtp_mk: Layer = (86, 17)
    dev_wf_mk: Layer = (128, 17)
    metal1_blk: Layer = (34, 5)
    metal2_blk: Layer = (36, 5)
    metal3_blk: Layer = (42, 5)
    metal4_blk: Layer = (46, 5)
    metal5_blk: Layer = (81, 5)
    metalt_blk: Layer = (53, 5)
    pr_bndry: Layer = (0, 0)
    mdiode: Layer = (116, 5)
    metal1_res: Layer = (110, 11)
    metal2_res: Layer = (110, 12)
    metal3_res: Layer = (110, 13)
    metal4_res: Layer = (110, 14)
    metal5_res: Layer = (110, 15)
    metal6_res: Layer = (110, 16)
    border: Layer = (63, 0)


layer = LAYER
LAYER_VIEWS = gf.technology.LayerViews(PATH.lyp_yaml)


# Define layer stack for GF180MCU 180nm process
# Based on typical 180nm CMOS process parameters
def get_layer_stack(
    thickness_substrate: float = 200.0,  # substrate thickness in um
    thickness_dnwell: float = 2.5,  # deep n-well thickness in um
    thickness_nwell: float = 1.8,  # n-well thickness in um
    thickness_comp: float = 0.18,  # active area thickness in um
    thickness_poly2: float = 0.18,  # poly2 thickness in um
    thickness_contact: float = 0.4,  # contact thickness in um
    thickness_metal1: float = 0.35,  # metal1 thickness in um
    thickness_via1: float = 0.4,  # via1 thickness in um
    thickness_metal2: float = 0.35,  # metal2 thickness in um
    thickness_via2: float = 0.4,  # via2 thickness in um
    thickness_metal3: float = 0.7,  # metal3 thickness in um
    thickness_via3: float = 0.4,  # via3 thickness in um
    thickness_metal4: float = 0.7,  # metal4 thickness in um
    thickness_via4: float = 0.4,  # via4 thickness in um
    thickness_metal5: float = 0.7,  # metal5 thickness in um
    thickness_via5: float = 0.4,  # via5 thickness in um
    thickness_metaltop: float = 2.0,  # top metal thickness in um
    thickness_pad: float = 10.0,  # pad thickness in um
) -> LayerStack:
    """Return GF180MCU LayerStack.

    Based on GlobalFoundries 180nm MCU process technology.
    Typical layer thicknesses for 180nm CMOS process.

    The LayerStack defines the physical properties of each layer including:
    - Layer thickness
    - Z-position in the stack
    - Material properties
    - Mesh order for simulations

    Usage:
        ```python
        import gf180mcu

        # Use default layer stack
        layer_stack = gf180mcu.LAYER_STACK

        # Create custom layer stack with different parameters
        custom_stack = gf180mcu.get_layer_stack(
            thickness_metal1=0.5,  # thicker metal1
            thickness_metaltop=3.0  # thicker top metal
        )

        # Use for 3D visualization
        import gdsfactory as gf
        c = gf.components.rectangle(layer=gf180mcu.LAYER.metal1)
        scene = c.to_3d(layer_stack=layer_stack)
        ```

    Args:
        thickness_substrate: substrate thickness
        thickness_dnwell: deep n-well thickness
        thickness_nwell: n-well thickness
        thickness_comp: active area thickness
        thickness_poly2: poly2 thickness
        thickness_contact: contact thickness
        thickness_metal1: metal1 thickness
        thickness_via1: via1 thickness
        thickness_metal2: metal2 thickness
        thickness_via2: via2 thickness
        thickness_metal3: metal3 thickness
        thickness_via3: via3 thickness
        thickness_metal4: metal4 thickness
        thickness_via4: via4 thickness
        thickness_metal5: metal5 thickness
        thickness_via5: via5 thickness
        thickness_metaltop: top metal thickness
        thickness_pad: pad thickness

    Returns:
        LayerStack: Complete layer stack for GF180MCU process
    """

    # Z-positions (cumulative heights)
    z_substrate = 0.0
    z_dnwell = z_substrate
    z_nwell = z_substrate
    z_comp = z_substrate
    # poly2 sits on top of the active area (gate oxide assumed negligible)
    z_poly2 = z_comp + thickness_comp
    # implants are embedded in the upper half of the comp (silicon) layer,
    # so they never render above comp/poly2
    thickness_implant = thickness_comp / 2
    z_implant = z_comp + thickness_comp / 2
    # contact starts at the top of comp/poly2 and reaches up to metal1
    z_contact = z_comp + thickness_comp
    z_metal1 = z_contact + thickness_contact
    z_via1 = z_metal1 + thickness_metal1
    z_metal2 = z_via1 + thickness_via1
    z_via2 = z_metal2 + thickness_metal2
    z_metal3 = z_via2 + thickness_via2
    z_via3 = z_metal3 + thickness_metal3
    z_metal4 = z_via3 + thickness_via3
    z_via4 = z_metal4 + thickness_metal4
    z_metal5 = z_via4 + thickness_via4
    z_via5 = z_metal5 + thickness_metal5
    z_metaltop = z_via5 + thickness_via5
    z_pad = z_metaltop

    layers = {
        # Substrate and wells
        "substrate": LayerLevel(
            layer=LAYER.pr_bndry,
            thickness=thickness_substrate,
            zmin=z_substrate - thickness_substrate,
            material="si",
            mesh_order=100,
        ),
        "dnwell": LayerLevel(
            layer=LAYER.dnwell,
            thickness=thickness_dnwell,
            zmin=z_dnwell,
            material="si",
            mesh_order=10,
        ),
        "lvpwell": LayerLevel(
            layer=LAYER.lvpwell,
            thickness=thickness_nwell,  # similar to nwell
            zmin=z_nwell,
            material="si",
            mesh_order=9,
        ),
        # Active areas and implants
        "comp": LayerLevel(
            layer=LAYER.comp,
            thickness=thickness_comp,
            zmin=z_comp,
            material="si",
            mesh_order=8,
        ),
        "nplus": LayerLevel(
            layer=LAYER.nplus,
            thickness=thickness_implant,
            zmin=z_implant,
            material="si",
            mesh_order=7,
        ),
        "pplus": LayerLevel(
            layer=LAYER.pplus,
            thickness=thickness_implant,
            zmin=z_implant,
            material="si",
            mesh_order=7,
        ),
        "nat": LayerLevel(
            layer=LAYER.nat,
            thickness=thickness_implant,
            zmin=z_implant,
            material="si",
            mesh_order=7,
        ),
        # Polysilicon
        "poly2": LayerLevel(
            layer=LAYER.poly2,
            thickness=thickness_poly2,
            zmin=z_poly2,
            material="poly",
            mesh_order=6,
        ),
        # Contacts and vias
        "contact": LayerLevel(
            layer=LAYER.contact,
            thickness=thickness_contact,
            zmin=z_contact,
            material="tungsten",
            mesh_order=5,
        ),
        "via1": LayerLevel(
            layer=LAYER.via1,
            thickness=thickness_via1,
            zmin=z_via1,
            material="tungsten",
            mesh_order=5,
        ),
        "via2": LayerLevel(
            layer=LAYER.via2,
            thickness=thickness_via2,
            zmin=z_via2,
            material="tungsten",
            mesh_order=5,
        ),
        "via3": LayerLevel(
            layer=LAYER.via3,
            thickness=thickness_via3,
            zmin=z_via3,
            material="tungsten",
            mesh_order=5,
        ),
        "via4": LayerLevel(
            layer=LAYER.via4,
            thickness=thickness_via4,
            zmin=z_via4,
            material="tungsten",
            mesh_order=5,
        ),
        "via5": LayerLevel(
            layer=LAYER.via5,
            thickness=thickness_via5,
            zmin=z_via5,
            material="tungsten",
            mesh_order=5,
        ),
        # Metal layers
        "metal1": LayerLevel(
            layer=LAYER.metal1,
            thickness=thickness_metal1,
            zmin=z_metal1,
            material="aluminum",
            mesh_order=4,
        ),
        "metal2": LayerLevel(
            layer=LAYER.metal2,
            thickness=thickness_metal2,
            zmin=z_metal2,
            material="aluminum",
            mesh_order=4,
        ),
        "metal3": LayerLevel(
            layer=LAYER.metal3,
            thickness=thickness_metal3,
            zmin=z_metal3,
            material="aluminum",
            mesh_order=4,
        ),
        "metal4": LayerLevel(
            layer=LAYER.metal4,
            thickness=thickness_metal4,
            zmin=z_metal4,
            material="aluminum",
            mesh_order=4,
        ),
        "metal5": LayerLevel(
            layer=LAYER.metal5,
            thickness=thickness_metal5,
            zmin=z_metal5,
            material="aluminum",
            mesh_order=4,
        ),
        "metaltop": LayerLevel(
            layer=LAYER.metaltop,
            thickness=thickness_metaltop,
            zmin=z_metaltop,
            material="aluminum",
            mesh_order=4,
        ),
        # Pads and special layers
        "pad": LayerLevel(
            layer=LAYER.pad,
            thickness=thickness_pad,
            zmin=z_pad,
            material="aluminum",
            mesh_order=3,
        ),
        # Resistors
        "resistor": LayerLevel(
            layer=LAYER.resistor,
            thickness=thickness_poly2,  # typically same as poly
            zmin=z_poly2,
            material="poly",
            mesh_order=6,
        ),
        "fhres": LayerLevel(
            layer=LAYER.fhres,
            thickness=thickness_poly2,
            zmin=z_poly2,
            material="poly",
            mesh_order=6,
        ),
        # Special device layers (markers, typically no physical thickness)
        "sab": LayerLevel(
            layer=LAYER.sab,
            thickness=0.001,  # minimal thickness for visualization
            zmin=z_comp,
            material="si",
            mesh_order=1,
        ),
        "esd": LayerLevel(
            layer=LAYER.esd,
            thickness=0.001,
            zmin=z_comp,
            material="si",
            mesh_order=1,
        ),
    }

    return LayerStack(layers=layers)


# Create default layer stack instance
LAYER_STACK = get_layer_stack()

if __name__ == "__main__":
    LAYER_VIEWS.to_lyp(PATH.lyp)

    # Demo: LayerStack usage
    print("GF180MCU LayerStack Demo")
    print("=" * 40)
    print(f"Number of layers: {len(LAYER_STACK.layers)}")
    print(
        f"Total stack height: {max(layer.zmin + layer.thickness for layer in LAYER_STACK.layers.values()):.2f} um"
    )
    print("\nMetal layers:")
    for name, layer in LAYER_STACK.layers.items():
        if "metal" in name:
            print(
                f"  {name}: {layer.thickness}um thick at z={layer.zmin:.2f}um ({layer.material})"
            )

    print("\nCustom layer stack example:")
    custom = get_layer_stack(thickness_metal1=0.5, thickness_metaltop=3.0)
    print(f"  Custom metal1: {custom.layers['metal1'].thickness}um")
    print(f"  Custom metaltop: {custom.layers['metaltop'].thickness}um")
