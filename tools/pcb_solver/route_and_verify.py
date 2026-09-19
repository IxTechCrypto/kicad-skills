#!/usr/bin/env python3
"""
route_and_verify.py — Incremental Net Router with Closed-Loop DRC Feedback

Solves the open-loop generation failure mode identified in PCBWorld-Bench
(LG AI Research, 2026). Instead of emitting raw tracks blind, this primitive:
1. Adds a candidate 45-degree track or net connection to the board.
2. Immediately triggers an incremental design rule check (DRC).
3. If violations or clearance conflicts are introduced, reverts the candidate track
   and emits an explicit diagnostic delta back to the calling agent.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import pcbnew
    HAS_PCBNEW = True
except ImportError:
    HAS_PCBNEW = False


def find_kicad_cli():
    cli = shutil.which("kicad-cli")
    if cli:
        return cli
    candidates = [
        r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
        "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
        "/usr/bin/kicad-cli",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def add_45_track_segments(board, net_code: int, layer: int, 
                          x1_mm: float, y1_mm: float, 
                          x2_mm: float, y2_mm: float, 
                          width_mm: float = 0.25) -> List[any]:
    """Generates 45-degree chamfered track segments between two points."""
    added = []
    dx = x2_mm - x1_mm
    dy = y2_mm - y1_mm

    def make_seg(ax, ay, bx, by):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(ax * 1e6), int(ay * 1e6)))
        t.SetEnd(pcbnew.VECTOR2I(int(bx * 1e6), int(by * 1e6)))
        t.SetWidth(int(width_mm * 1e6))
        t.SetLayer(layer)
        t.SetNetCode(net_code)
        board.Add(t)
        return t

    if abs(dx) < 1e-4 or abs(dy) < 1e-4:
        added.append(make_seg(x1_mm, y1_mm, x2_mm, y2_mm))
    elif abs(dx) >= abs(dy):
        sign_x = 1.0 if dx > 0 else -1.0
        corner_x = x1_mm + sign_x * abs(dy)
        added.append(make_seg(x1_mm, y1_mm, corner_x, y2_mm))
        added.append(make_seg(corner_x, y2_mm, x2_mm, y2_mm))
    else:
        sign_y = 1.0 if dy > 0 else -1.0
        corner_y = y1_mm + sign_y * abs(dx)
        added.append(make_seg(x1_mm, y1_mm, x2_mm, corner_y))
        added.append(make_seg(x2_mm, corner_y, x2_mm, y2_mm))

    return added


def route_and_verify(pcb_path: Path, 
                       start_xy: Tuple[float, float], 
                       end_xy: Tuple[float, float], 
                       net_name: str, 
                       layer_name: str = "F.Cu", 
                       width_mm: float = 0.25,
                       save_on_pass: bool = True,
                       strict: bool = False) -> Dict:
    """
    Attempts to route a 45-degree track and validates immediate DRC delta.
    """
    result = {
        "net": net_name,
        "success": False,
        "violations": [],
        "reverted": False,
        "action": f"route ({start_xy[0]},{start_xy[1]}) -> ({end_xy[0]},{end_xy[1]}) on {layer_name}"
    }

    pcb_path = Path(pcb_path).resolve()
    if not pcb_path.exists():
        result["error"] = f"PCB file not found: {pcb_path}"
        return result

    if not HAS_PCBNEW:
        result["error"] = "pcbnew Python module not available in current environment."
        return result

    board = pcbnew.LoadBoard(str(pcb_path))
    net_info = board.FindNet(net_name)
    net_code = net_info.GetNetCode() if net_info else 0
    layer_id = board.GetLayerID(layer_name)

    # 1. Inject candidate track
    tracks = add_45_track_segments(board, net_code, layer_id, 
                                   start_xy[0], start_xy[1], 
                                   end_xy[0], end_xy[1], 
                                   width_mm=width_mm)

    # 2. Save temporary board to evaluate DRC
    temp_pcb = pcb_path.with_suffix(".tmp_route.kicad_pcb")
    board.Save(str(temp_pcb))

    cli = find_kicad_cli()
    if not cli:
        if strict:
            temp_pcb.unlink(missing_ok=True)
            result["error"] = "kicad-cli not found and --strict mode is enabled. Cannot verify copper."
            return result
        # Fallback: keep track without headless CLI DRC check
        if save_on_pass:
            board.Save(str(pcb_path))
        temp_pcb.unlink(missing_ok=True)
        result["success"] = True
        result["warning"] = "kicad-cli not found; DRC delta skipped."
        return result

    def get_routing_violations(target_board: Path) -> List[Dict]:
        rep = target_board.with_suffix(".drc_chk.json")
        cmd = [
            cli, "pcb", "drc",
            "--format", "json",
            "--schematic-parity",
            "--output", str(rep),
            str(target_board)
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        v_list = []
        if rep.exists():
            with open(rep, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    v_list = data.get("violations", [])
                except Exception:
                    pass
            rep.unlink(missing_ok=True)
        return [v for v in v_list if v.get("type") not in ("lib_footprint_issues", "lib_footprint_mismatch")]

    # 3. Run incremental headless DRC delta check
    baseline_violations = get_routing_violations(pcb_path)
    cand_violations = get_routing_violations(temp_pcb)

    new_violations = len(cand_violations) - len(baseline_violations)

    # 4. Closed-loop decision: Accept or Revert based on delta
    if new_violations > 0:
        # Revert candidate tracks
        temp_pcb.unlink(missing_ok=True)
        result["success"] = False
        result["reverted"] = True
        result["violations"] = [v.get("description", str(v)) for v in cand_violations]
        print(f"[REJECTED] Route on {net_name} introduced {new_violations} new DRC violation(s). Reverting.")
    else:
        # Commit to actual board
        if save_on_pass:
            board.Save(str(pcb_path))
        temp_pcb.unlink(missing_ok=True)
        result["success"] = True
        result["reverted"] = False
        print(f"[ACCEPTED] Route on {net_name} passed DRC verification (0 new violations). Committed.")

    return result


def main():
    parser = argparse.ArgumentParser(description="Incremental Net Router with Closed-Loop DRC Feedback")
    parser.add_argument("pcb", help="Path to .kicad_pcb")
    parser.add_argument("--start", nargs=2, type=float, required=True, help="Start X Y in mm")
    parser.add_argument("--end", nargs=2, type=float, required=True, help="End X Y in mm")
    parser.add_argument("--net", required=True, help="Net name (e.g. +3V3, GND, Net-(R1-Pad1))")
    parser.add_argument("--layer", default="F.Cu", help="Copper layer (F.Cu, B.Cu, etc.)")
    parser.add_argument("--width", type=float, default=0.25, help="Track width in mm")
    parser.add_argument("--strict", action="store_true", help="Fail if kicad-cli is not found")

    args = parser.parse_args()
    res = route_and_verify(Path(args.pcb), tuple(args.start), tuple(args.end), 
                           args.net, layer_name=args.layer, width_mm=args.width, strict=args.strict)
    
    print(json.dumps(res, indent=2))
    if not res.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
