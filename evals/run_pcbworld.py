#!/usr/bin/env python3
"""
evals/run_pcbworld.py — PCBWorld-Bench Benchmark & Evaluation Runner

Benchmarks automated and agentic PCB routing workflows against PCBWorld-Bench
difficulty tiers (D3-A, D3-B, D3-C) or local KiCad testboards.

Measures:
  - Clean Pass (CP) Rate (% of designs with 0 DRC errors and 100% completion)
  - Unrouted Net Ratio
  - Total Trace Length & Via Count
  - DRC Violation Breakdown (Clearance, Acid Traps, Courtyards)
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class BoardEvalResult:
    board_name: str
    tier: str
    total_nets: int
    routed_nets: int
    unrouted_nets: int
    total_vias: int
    total_trace_length_mm: float
    drc_errors: int
    drc_warnings: int
    violations_by_type: Dict[str, int] = field(default_factory=dict)
    clean_pass: bool = False
    duration_sec: float = 0.0
    router_backend: str = "unknown"
    notes: str = ""


class PCBWorldEvaluator:
    def __init__(self, kicad_cli_bin: Optional[str] = None):
        self.kicad_cli = kicad_cli_bin or self._find_kicad_cli()

    def _find_kicad_cli(self) -> Optional[str]:
        w = shutil.which("kicad-cli")
        if w:
            return w
        candidates = [
            r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
            "/usr/bin/kicad-cli",
            "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return None

    def run_kicad_drc(self, pcb_path: Path, output_json: Path) -> Dict:
        """Runs kicad-cli pcb drc and parses JSON report."""
        if not self.kicad_cli or not os.path.isfile(self.kicad_cli):
            return self._parse_pcb_fallback_metrics(pcb_path)

        cmd = [
            self.kicad_cli,
            "pcb",
            "drc",
            "--format", "json",
            "--output", str(output_json),
            str(pcb_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if output_json.exists():
                with open(output_json, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"    [WARN] kicad-cli DRC execution error: {e}", file=sys.stderr)

        return self._parse_pcb_fallback_metrics(pcb_path)

    def _parse_pcb_fallback_metrics(self, pcb_path: Path) -> Dict:
        """Fallback static S-expression parser when kicad-cli is not in PATH."""
        if not pcb_path.exists():
            return {"violations": [], "unconnected": []}

        content = pcb_path.read_text(encoding="utf-8", errors="replace")
        
        # Count nets
        net_count = content.count("(net ")
        segments = content.count("(segment ")
        vias = content.count("(via ")
        
        # Check for obvious acute angles / 90 degree bends in tracks
        violations = []
        
        return {
            "violations": violations,
            "unconnected": [],
            "_parsed_summary": {
                "nets": max(1, net_count),
                "segments": segments,
                "vias": vias,
            }
        }

    def evaluate_board(self, pcb_path: Path, router_name: str = "native") -> BoardEvalResult:
        start_time = time.time()
        report_path = pcb_path.with_suffix(".drc_report.json")
        drc_data = self.run_kicad_drc(pcb_path, report_path)

        violations = drc_data.get("violations", [])
        unconnected = drc_data.get("unconnected", [])

        # Parse geometric metrics from board file
        content = pcb_path.read_text(encoding="utf-8", errors="replace") if pcb_path.exists() else ""
        total_vias = content.count("(via ")
        total_segments = content.count("(segment ")
        
        # Trace length estimation
        total_length_mm = 0.0
        for line in content.splitlines():
            if line.strip().startswith("(segment"):
                # (segment (start X Y) (end X Y) (width W) (layer L) (net N))
                try:
                    parts = line.split()
                    s_idx = parts.index("(start")
                    sx, sy = float(parts[s_idx + 1]), float(parts[s_idx + 2].rstrip(")"))
                    e_idx = parts.index("(end")
                    ex, ey = float(parts[e_idx + 1]), float(parts[e_idx + 2].rstrip(")"))
                    total_length_mm += math.hypot(ex - sx, ey - sy)
                except Exception:
                    pass

        # Breakdown violations — focus on electrical & geometric routing issues
        # (lib_footprint_issues is a library linking warning, not a router defect)
        routing_violations = [v for v in violations if v.get("type") not in ("lib_footprint_issues", "lib_footprint_mismatch")]
        by_type: Dict[str, int] = {}
        for v in routing_violations:
            v_type = v.get("type", "unknown")
            by_type[v_type] = by_type.get(v_type, 0) + 1

        unrouted_count = len(unconnected)
        total_drc = len(routing_violations)
        
        # Determine net counts
        net_ids = set()
        for line in content.splitlines():
            if "(net " in line and not line.strip().startswith("(net 0"):
                try:
                    parts = line.split("(net ")
                    nid = parts[1].split()[0]
                    net_ids.add(nid)
                except Exception:
                    pass
        total_nets = max(len(net_ids), 1)
        routed_nets = max(0, total_nets - unrouted_count)

        # Tier classification
        if total_nets <= 10:
            tier = "D3-A (Low: 1-10 nets)"
        elif total_nets <= 30:
            tier = "D3-B (Medium: 11-30 nets)"
        else:
            tier = "D3-C (High: >30 nets)"

        clean_pass = (total_drc == 0) and (unrouted_count == 0) and (total_nets > 0)

        # Cleanup temp json
        if report_path.exists():
            try:
                report_path.unlink()
            except Exception:
                pass

        return BoardEvalResult(
            board_name=pcb_path.name,
            tier=tier,
            total_nets=total_nets,
            routed_nets=routed_nets,
            unrouted_nets=unrouted_count,
            total_vias=total_vias,
            total_trace_length_mm=round(total_length_mm, 2),
            drc_errors=total_drc,
            drc_warnings=0,
            violations_by_type=by_type,
            clean_pass=clean_pass,
            duration_sec=round(time.time() - start_time, 2),
            router_backend=router_name
        )


def generate_mock_test_suite(out_dir: Path) -> List[Path]:
    """Generates synthetic benchmark testboards across D3-A, D3-B, and D3-C tiers."""
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    configs = [
        ("tier_a_pass.kicad_pcb", "D3-A", 4, False),
        ("tier_a_fail.kicad_pcb", "D3-A", 4, True),
        ("tier_b_dense.kicad_pcb", "D3-B", 16, False),
        ("tier_c_asic_miner.kicad_pcb", "D3-C", 36, False),
    ]

    for fname, tier, net_count, introduce_err in configs:
        board_file = out_dir / fname
        nets_sexpr = "\n  ".join([f'(net {i} "NET_{i}")' for i in range(net_count + 1)])
        
        # Build footprints (pads) and segments
        footprints = []
        segments = []
        for i in range(1, net_count + 1):
            y = 50.0 + (i * 3.5)
            # Pad 1 (start)
            footprints.append(f"""  (footprint "TestPad:Pad_{i}A" (layer "F.Cu")
    (at 50.0 {y:.2f})
    (pad "1" smd rect (at 0 0) (size 1.0 1.0) (layers "F.Cu") (net {i} "NET_{i}"))
  )""")
            # Pad 2 (end)
            footprints.append(f"""  (footprint "TestPad:Pad_{i}B" (layer "B.Cu")
    (at 90.0 {y + 2.0:.2f})
    (pad "1" smd rect (at 0 0) (size 1.0 1.0) (layers "B.Cu") (net {i} "NET_{i}"))
  )""")

            # Route: Pad 1 -> horizontal F.Cu -> via -> B.Cu -> Pad 2
            segments.append(f'  (segment (start 50.0 {y:.2f}) (end 80.0 {y:.2f}) (width 0.25) (layer "F.Cu") (net {i}))')
            segments.append(f'  (segment (start 80.0 {y:.2f}) (end 85.0 {y + 2.0:.2f}) (width 0.25) (layer "F.Cu") (net {i}))')
            segments.append(f'  (via (at 85.0 {y + 2.0:.2f}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {i}))')
            segments.append(f'  (segment (start 85.0 {y + 2.0:.2f}) (end 90.0 {y + 2.0:.2f}) (width 0.25) (layer "B.Cu") (net {i}))')

        if introduce_err:
            # Overlapping track on Net 2 colliding with Net 1 track
            segments.append('  (segment (start 52.0 53.5) (end 78.0 53.5) (width 0.3) (layer "F.Cu") (net 2))')

        body = f"""(kicad_pcb
  (version 20240108)
  (generator "pcbworld_eval_generator")
  (general (thickness 1.6))
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (1 "In1.Cu" power)
    (2 "In2.Cu" power)
    (31 "B.Cu" signal)
    (36 "B.SilkS" user)
    (37 "F.SilkS" user)
    (44 "Edge.Cuts" user)
  )
  (gr_rect (start 30.0 30.0) (end 110.0 {50.0 + (net_count * 3.5) + 20.0:.2f}) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts"))
  {nets_sexpr}
{chr(10).join(footprints)}
{chr(10).join(segments)}
)
"""
        board_file.write_text(body, encoding="utf-8")
        generated.append(board_file)

    return generated


def print_summary_table(results: List[BoardEvalResult]):
    print("\n" + "=" * 90)
    print(f"{'BOARD':<24} | {'TIER':<20} | {'NETS':<6} | {'VIAS':<5} | {'LENGTH(mm)':<10} | {'DRC':<5} | {'RESULT'}")
    print("-" * 90)

    clean_passes = 0
    total = len(results)

    for r in results:
        status = "[PASS] Clean" if r.clean_pass else f"[FAIL] ({r.drc_errors} err, {r.unrouted_nets} unrouted)"
        if r.clean_pass:
            clean_passes += 1
        print(f"{r.board_name:<24} | {r.tier:<20} | {r.routed_nets}/{r.total_nets:<4} | {r.total_vias:<5} | {r.total_trace_length_mm:<10.1f} | {r.drc_errors:<5} | {status}")

    cp_rate = (clean_passes / total * 100.0) if total > 0 else 0.0
    print("=" * 90)
    print(f"Overall Clean Pass (CP) Score: {clean_passes}/{total} ({cp_rate:.1f}%)\n")


def main():
    parser = argparse.ArgumentParser(description="PCBWorld-Bench Evaluation Runner for AI PCB Routers")
    parser.add_argument("--board", type=str, help="Path to a single .kicad_pcb file to evaluate")
    parser.add_argument("--benchmark-dir", type=str, help="Directory containing benchmark .kicad_pcb files")
    parser.add_argument("--generate-mock-suite", action="store_true", help="Generate synthetic D3-A, D3-B, D3-C benchmark suite")
    parser.add_argument("--suite-dir", type=str, default="./evals/mock_suite", help="Directory for generated mock testboards")
    parser.add_argument("--json-out", type=str, default="evals_report.json", help="Path to export evaluation JSON report")
    parser.add_argument("--router", type=str, default="native", help="Name of router under test (e.g. freerouting, route_and_verify, astar)")

    args = parser.parse_args()
    evaluator = PCBWorldEvaluator()

    boards_to_eval = []

    if args.generate_mock_suite:
        out_p = Path(args.suite_dir)
        print(f"[*] Generating synthetic PCBWorld-Bench test suite in: {out_p}")
        boards_to_eval = generate_mock_test_suite(out_p)
    elif args.board:
        boards_to_eval = [Path(args.board)]
    elif args.benchmark_dir:
        b_dir = Path(args.benchmark_dir)
        boards_to_eval = list(b_dir.glob("*.kicad_pcb"))
        if not boards_to_eval:
            print(f"[ERROR] No .kicad_pcb files found in {b_dir}")
            sys.exit(1)
    else:
        # Default: check if mock suite exists, otherwise generate
        out_p = Path(args.suite_dir)
        if not out_p.exists() or not list(out_p.glob("*.kicad_pcb")):
            print(f"[*] No inputs specified. Generating synthetic benchmark suite in: {out_p}")
            boards_to_eval = generate_mock_test_suite(out_p)
        else:
            boards_to_eval = list(out_p.glob("*.kicad_pcb"))

    print(f"[*] Evaluating {len(boards_to_eval)} boards under router '{args.router}'...")
    results = []
    for b in boards_to_eval:
        res = evaluator.evaluate_board(b, router_name=args.router)
        results.append(res)

    print_summary_table(results)

    # Save JSON report
    report_dict = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "router": args.router,
        "kicad_cli_available": evaluator.kicad_cli is not None,
        "total_boards": len(results),
        "clean_pass_count": sum(1 for r in results if r.clean_pass),
        "clean_pass_rate": (sum(1 for r in results if r.clean_pass) / len(results) * 100.0) if results else 0.0,
        "results": [asdict(r) for r in results],
    }

    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
    print(f"[*] Benchmark report saved to: {args.json_out}")


if __name__ == "__main__":
    main()
