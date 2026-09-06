"""Parametrized XOR regression tests driven by scripts/magic/sweep_params.json.

Uses kdb.Region merge+XOR for polygon-exact comparison — no hidden tolerances.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import pathlib
import tempfile

import pytest

import klayout.db as kdb

# ---------------------------------------------------------------------------
# Skip layers: label layers and boundary markers
# ---------------------------------------------------------------------------

SKIP_LAYERS = {
    (0, 0),  # empty/context
    (235, 4),  # prBoundary
}

SKIP_DATATYPES = {2, 5, 10}  # pin, block


def xor_gds_files(
    ref_path: pathlib.Path, run_path: pathlib.Path
) -> dict[tuple[int, int], str]:
    """Layer-by-layer kdb.Region XOR. Returns dict of failing layers."""
    layout_ref = kdb.Layout()
    layout_ref.read(str(ref_path))
    layout_new = kdb.Layout()
    layout_new.read(str(run_path))

    dbu = layout_ref.dbu
    cell_ref = layout_ref.top_cell()
    cell_new = layout_new.top_cell()

    layers_ref = {}
    for li in layout_ref.layer_indices():
        info = layout_ref.get_info(li)
        key = (info.layer, info.datatype)
        r = kdb.Region(cell_ref.begin_shapes_rec(li))
        if not r.is_empty():
            layers_ref[key] = r

    layers_new = {}
    for li in layout_new.layer_indices():
        info = layout_new.get_info(li)
        key = (info.layer, info.datatype)
        r = kdb.Region(cell_new.begin_shapes_rec(li))
        if not r.is_empty():
            layers_new[key] = r

    all_layers = sorted(set(layers_ref) | set(layers_new))
    failures = {}

    for key in all_layers:
        if key in SKIP_LAYERS or key[1] in SKIP_DATATYPES:
            continue
        in_ref = key in layers_ref
        in_new = key in layers_new
        if in_ref and not in_new:
            failures[key] = "ONLY IN REF"
            continue
        if in_new and not in_ref:
            failures[key] = "ONLY IN NEW"
            continue

        r_ref = layers_ref[key].merged()
        r_new = layers_new[key].merged()
        xor_area = (r_ref ^ r_new).area() * dbu * dbu
        if xor_area > 1e-6:
            failures[key] = (
                f"XOR={xor_area:.6f} um^2 "
                f"(ref={r_ref.area() * dbu * dbu:.4f}, "
                f"new={r_new.area() * dbu * dbu:.4f})"
            )
    return failures


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SWEEP_JSON = _REPO_ROOT / "scripts" / "magic" / "sweep_params.json"
_REF_GDS_DIR = pathlib.Path(__file__).resolve().parent / "ref_gds"


def _param_hash(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]


def _human_id(device_name: str, params: dict) -> str:
    param_str = ",".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{device_name}[{param_str}]"


def _load_sweep_cases() -> list[tuple[str, dict, str]]:
    if not _SWEEP_JSON.exists():
        return []
    data = json.loads(_SWEEP_JSON.read_text())
    cases = []
    for device_name, device_cfg in data.get("devices", {}).items():
        cell_module = device_cfg.get("cell_module", "")
        for params in device_cfg.get("sweep", []):
            cases.append((device_name, params, cell_module))
    return cases


_sweep_cases = _load_sweep_cases()
_ids = [_human_id(dev, params) for dev, params, _ in _sweep_cases]


@pytest.mark.parametrize("device_name,params,cell_module", _sweep_cases, ids=_ids)
def test_xor(device_name: str, params: dict, cell_module: str) -> None:
    """XOR-compare generated layout against Magic reference."""

    # Resolve cell function — support cell_fn override and extra_params
    data = json.loads(_SWEEP_JSON.read_text())
    device_cfg = data["devices"].get(device_name, {})
    cell_fn_name = device_cfg.get("cell_fn", device_name)
    extra_params = device_cfg.get("extra_params", {})

    cell_fn = None
    try:
        mod = importlib.import_module(cell_module)
        fn = getattr(mod, cell_fn_name, None)
        if callable(fn):
            cell_fn = fn
    except (ModuleNotFoundError, ImportError):
        pass

    if cell_fn is None:
        try:
            import gf180mcu

            fn = gf180mcu._cells.get(cell_fn_name)
            if fn and callable(fn):
                cell_fn = fn
        except Exception:
            pass

    if cell_fn is None:
        pytest.skip(f"Cell {cell_fn_name} not yet implemented")

    # Merge sweep params with extra_params, filter to accepted
    all_params = {**params, **extra_params}
    try:
        sig = inspect.signature(cell_fn)
        accepted = {
            k
            for k, p in sig.parameters.items()
            if p.kind
            not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        }
    except (ValueError, TypeError):
        accepted = set(all_params.keys())
    filtered_params = {k: v for k, v in all_params.items() if k in accepted}

    # Check reference
    param_hash = _param_hash(params)
    ref_gds = _REF_GDS_DIR / device_name / f"{param_hash}.gds"
    if not ref_gds.exists():
        pytest.skip(f"Reference GDS not found: {ref_gds}")

    # Generate and compare
    component = cell_fn(**filtered_params)
    with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as tmp:
        run_gds = pathlib.Path(tmp.name)
    component.write_gds(str(run_gds))

    try:
        failures = xor_gds_files(ref_gds, run_gds)
        if failures:
            lines = [f"  ({l},{d}): {msg}" for (l, d), msg in sorted(failures.items())]
            raise AssertionError(
                f"XOR differences for {device_name} with {params}:\n" + "\n".join(lines)
            )
    finally:
        run_gds.unlink(missing_ok=True)
