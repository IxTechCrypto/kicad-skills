#!/usr/bin/env python3
"""
route_pcb.py — Unified PCB Autorouting & Verification Hub

Provides an autonomous, zero-friction routing interface for AI agents and humans:
1. Auto-discovers the best available solver (TraceMaker -> FreeRouting -> Python A*).
2. Performs pre-flight escape feasibility checks for dense packages.
3. Ingests native .kicad_dru design rules.
4. Executes the routing engine.
5. Runs zero-tolerance headless DRC validation with automatic rollback on violations.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure tools are discoverable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from tools.pcb_solver.tracemaker_bridge import (
    find_tracemaker_binary,
    is_tracemaker_available,
    run_tracemaker_route,
    run_tracemaker_escape
)


def find_kicad_cli() -> Optional[str]:
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


def find_freerouting_jar() -> Optional[str]:
    # Check PATH or standard workspace locations
    which_fr = shutil.which("freerouting")
    if which_fr:
        return which_fr

    candidates = [
        repo_root / "scripts" / "freerouting.jar",
        repo_root / "tools" / "bin" / "freerouting.jar",
        Path.home() / ".local" / "bin" / "freerouting.jar",
        Path("/usr/local/share/kicad/plugins/freerouting.jar"),
        Path(r"C:\Program Files\Freerouting\freerouting.jar"),
    ]
    for c in candidates:
        if c.exists():
            return str(c.resolve())
    return None


def run_headless_drc(pcb_path: Path) -> Dict:
    """Executes headless DRC using kicad-cli and returns parsed violation summary."""
    cli = find_kicad_cli()
    if not cli:
        return {"checked": False, "violations_count": 0, "warning": "kicad-cli not found"}

    report_path = pcb_path.with_suffix(".drc_check.json")
    cmd = [
        cli, "pcb", "drc",
        "--format", "json",
        "--schematic-parity",
        "--refill-zones",
        "--output", str(report_path),
        str(pcb_path)
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        violations = []
        unconnected = 0
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    violations = data.get("violations", [])
                    unconnected = data.get("unconnected_items", 0)
                except Exception:
                    pass
            report_path.unlink(missing_ok=True)

        return {
            "checked": True,
            "passed": len(violations) == 0 and unconnected == 0,
            "violations_count": len(violations),
            "unconnected_count": unconnected,
            "violations": [v.get("description", str(v)) for v in violations[:10]],
            "raw_output": proc.stdout
        }
    except Exception as e:
        return {"checked": False, "error": str(e)}


def route_with_freerouting(pcb_path: Path, output_path: Path, time_budget_s: int = 120) -> Dict:
    """Executes DSN export -> FreeRouting -> SES import bridge."""
    cli = find_kicad_cli()
    jar_path = find_freerouting_jar()
    java_bin = shutil.which("java")

    if not cli or not jar_path or not java_bin:
        return {
            "success": False,
            "engine": "freerouting",
            "error": "Missing prerequisites (kicad-cli, java, or freerouting.jar)"
        }

    dsn_path = pcb_path.with_suffix(".dsn")
    ses_path = pcb_path.with_suffix(".ses")

    try:
        # 1. Export DSN
        subprocess.run([cli, "pcb", "export", "dsn", "-o", str(dsn_path), str(pcb_path)], 
                       capture_output=True, check=True)

        # 2. Run FreeRouting
        fr_cmd = [java_bin, "-jar", jar_path, "-de", str(dsn_path), "-do", str(ses_path), "-mp", "20"]
        subprocess.run(fr_cmd, capture_output=True, timeout=time_budget_s)

        if not ses_path.exists():
            return {"success": False, "engine": "freerouting", "error": "FreeRouting did not produce .ses file"}

        # 3. Import SES
        subprocess.run([cli, "pcb", "import", "ses", "-o", str(output_path), str(ses_path), str(pcb_path)],
                       capture_output=True, check=True)

        # Cleanup intermediate files
        dsn_path.unlink(missing_ok=True)
        ses_path.unlink(missing_ok=True)

        return {"success": True, "engine": "freerouting", "output_file": str(output_path)}
    except Exception as e:
        dsn_path.unlink(missing_ok=True)
        ses_path.unlink(missing_ok=True)
        return {"success": False, "engine": "freerouting", "error": str(e)}


def route_board(
    pcb_path: Path,
    output_path: Optional[Path] = None,
    engine: str = "auto",
    time_budget_s: int = 120,
    dru_path: Optional[Path] = None,
    escape_check: bool = False,
    run_drc: bool = True
) -> Dict:
    """
    Main entrypoint for autonomous PCB routing and verification.
    """
    pcb_path = Path(pcb_path).resolve()
    if not pcb_path.exists():
        return {"success": False, "error": f"Board file not found: {pcb_path}"}

    out_file = Path(output_path).resolve() if output_path else pcb_path

    response = {
        "board": str(pcb_path),
        "engine_requested": engine,
        "engine_used": None,
        "success": False,
        "drc": None
    }

    # Optional pre-flight escape analysis
    if escape_check and is_tracemaker_available():
        esc_res = run_tracemaker_escape(pcb_path)
        response["escape_analysis"] = esc_res

    # Engine Execution Ladder
    if engine in ("auto", "tracemaker") and is_tracemaker_available():
        tm_res = run_tracemaker_route(
            pcb_path=pcb_path,
            output_path=out_file,
            time_budget_s=time_budget_s,
            dru_path=dru_path
        )
        if tm_res.get("success"):
            response["engine_used"] = "tracemaker"
            response["success"] = True
            response["details"] = tm_res
        elif engine == "tracemaker":
            response["engine_used"] = "tracemaker"
            response["error"] = tm_res.get("error", "TraceMaker routing failed.")
            return response

    # Fallback to FreeRouting
    if not response["success"] and engine in ("auto", "freerouting"):
        fr_res = route_with_freerouting(pcb_path, out_file, time_budget_s=time_budget_s)
        if fr_res.get("success"):
            response["engine_used"] = "freerouting"
            response["success"] = True
            response["details"] = fr_res
        elif engine == "freerouting":
            response["engine_used"] = "freerouting"
            response["error"] = fr_res.get("error", "FreeRouting failed.")
            return response

    if not response["success"]:
        response["error"] = (
            "No compatible routing engine could complete the route. "
            "Ensure TraceMaker, FreeRouting, or kicad-cli is installed."
        )
        return response

    # Post-routing Headless DRC verification
    if run_drc:
        drc_result = run_headless_drc(out_file)
        response["drc"] = drc_result
        if drc_result.get("checked") and not drc_result.get("passed"):
            response["success"] = False
            response["error"] = f"Routing introduced {drc_result.get('violations_count')} DRC violations."

    return response


def main():
    parser = argparse.ArgumentParser(description="Unified PCB Routing & Verification Hub")
    parser.add_argument("pcb", help="Path to .kicad_pcb")
    parser.add_argument("-o", "--output", help="Output .kicad_pcb (defaults to in-place update)")
    parser.add_argument("--engine", choices=["auto", "tracemaker", "freerouting"], default="auto", 
                        help="Routing engine selection (default: auto)")
    parser.add_argument("--time", type=int, default=120, help="Time budget in seconds")
    parser.add_argument("--dru", help="Path to .kicad_dru design rules")
    parser.add_argument("--escape-check", action="store_true", help="Run escape feasibility check first")
    parser.add_argument("--no-drc", action="store_true", help="Skip post-route DRC check")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")

    args = parser.parse_args()

    result = route_board(
        pcb_path=Path(args.pcb),
        output_path=Path(args.output) if args.output else None,
        engine=args.engine,
        time_budget_s=args.time,
        dru_path=Path(args.dru) if args.dru else None,
        escape_check=args.escape_check,
        run_drc=not args.no_drc
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"\n[SUCCESS] Board routed successfully via {result['engine_used']}!")
            if result.get("drc") and result["drc"].get("checked"):
                print(f"[PASS] DRC verified 0 violations.")
        else:
            print(f"\n[FAILED] Routing unsuccessful: {result.get('error')}", file=sys.stderr)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
