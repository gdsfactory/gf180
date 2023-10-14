import sys

from gdsfactory.get_factories import get_cells
from gdsfactory.pdk import Pdk

from gf180 import config, diode, fet, layers
from gf180.cap_mim import (
    cap_mim,
)
from gf180.cap_mos import (
    cap_mos,
    cap_mos_inst,
)
from gf180.config import PATH
from gf180.diode import (
    diode_dw2ps,
    diode_nd2ps,
    diode_nw2ps,
    diode_pd2nw,
    diode_pw2dw,
    sc_diode,
)
from gf180.fet import (
    add_gate_labels,
    add_inter_sd_labels,
    alter_interdig,
    bulk_gr_gen,
    get_patt_label,
    hv_gen,
    interdigit,
    labels_gen,
    nfet,
    nfet_06v0_nvt,
    nfet_deep_nwell,
    pfet,
    pfet_deep_nwell,
)
from gf180.guardring import (
    pcmpgr_gen,
)
from gf180.layers import LAYER, LAYER_VIEWS, LayerMap, layer
from gf180.res import (
    nplus_res,
    npolyf_res,
    plus_res_inst,
    polyf_res_inst,
    pplus_res,
    ppolyf_res,
    ppolyf_u_high_Rs_res,
    res,
    well_res,
)
from gf180.via_generator import (
    via_generator,
    via_stack,
)

__all__ = [
    "LAYER",
    "LayerMap",
    "PATH",
    "add_gate_labels",
    "add_inter_sd_labels",
    "alter_interdig",
    "bulk_gr_gen",
    "cap_mim",
    "cap_mos",
    "cap_mos_inst",
    "config",
    "diode",
    "diode_dw2ps",
    "diode_nd2ps",
    "diode_nw2ps",
    "diode_pd2nw",
    "diode_pw2dw",
    "cap_mos",
    "nplus_res",
    "npolyf_res",
    "pplus_res",
    "ppolyf_res",
    "ppolyf_u_high_Rs_res",
    "well_res",
    "fet",
    "get_patt_label",
    "hv_gen",
    "interdigit",
    "labels_gen",
    "layer",
    "layers",
    "nfet",
    "nfet_06v0_nvt",
    "nfet_deep_nwell",
    "pcmpgr_gen",
    "pfet",
    "pfet_deep_nwell",
    "plus_res_inst",
    "polyf_res_inst",
    "res",
    "sc_diode",
    "via_generator",
    "via_stack",
]
__version__ = "0.0.3"

cells = get_cells(sys.modules[__name__])
PDK = Pdk(
    name="gf180",
    cells=cells,
    layers=dict(LAYER),
    layer_views=LAYER_VIEWS,
    # layer_stack=LAYER_STACK,
)
PDK.activate()
