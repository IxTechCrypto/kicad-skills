#!/usr/bin/env python3
"""
tracemaker_bridge.py — High-Performance Python Bridge for TraceMaker Router

Wraps DingoOz/TraceMaker (C++20/CUDA native KiCad placement & routing engine)
with automatic binary discovery, Docker fallback, and standardized JSON output.
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


def find_tracemaker_binary(custom_path: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Locates the TraceMaker executable across standard system and workspace paths.
    Returns (binary_path_or_command, execution_mode: 'native' | 'docker' | 'none').
    """
    if custom_path and os.path.exists(custom_path):
        return str(Path(custom_path).resolve()), "native"

    env_path = os.environ.get("TRACEMAKER_PATH")
    if env_path and os.path.exists(env_path):
        return str(Path(env_path).resolve()), "native"

    # Check system PATH
    which_bin = shutil.which("tracemaker") or shutil.which("tracemaker.exe")
    if which_bin:
        return which_bin, "native"

    # Standard candidate locations on macOS, Linux, and Windows
    repo_root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        # Local workspace build artifacts
        repo_root / "build" / "release" / "src" / "app" / "tracemaker",
        repo_root / "build" / "release" / "src" / "app" / "tracemaker.exe",
        repo_root / "tools" / "bin" / "tracemaker",
        repo_root / "tools" / "bin" / "tracemaker.exe",
        # macOS / Linux paths
        Path("/opt/homebrew/bin/tracemaker"),
        Path("/usr/local/bin/tracemaker"),
        Path("/usr/bin/tracemaker"),
        Path.home() / ".local" / "bin" / "tracemaker",
        # Windows standard paths
        Path(r"C:\Program Files\TraceMaker\bin\tracemaker.exe"),
        Path(r"C:\TraceMaker\tracemaker.exe"),
    ]

    for c in candidates:
        if c.exists() and os.access(c, os.X_OK if os.name != "nt" else os.R_OK):
            return str(c.resolve()), "native"

    # Check for Docker availability
    docker_cli = shutil.which("docker")
    if docker_cli:
        try:
            res = subprocess.run([docker_cli, "image", "inspect", "ghcr.io/dingooz/tracemaker:latest"], 
                                 capture_output=True, text=True)
            if res.returncode == 0:
                return "ghcr.io/dingooz/tracemaker:latest", "docker"
        except Exception:
            pass

    return None, "none"


def is_tracemaker_available(custom_path: Optional[str] = None) -> bool:
    """Returns True if TraceMaker is ready to execute."""
    bin_path, mode = find_tracemaker_binary(custom_path)
    return mode in ("native", "docker")


def run_tracemaker_route(
    pcb_path: Path,
    output_path: Optional[Path] = None,
    time_budget_s: Optional[int] = 120,
    work_budget: Optional[int] = None,
    dru_path: Optional[Path] = None,
    reroute: bool = False,
    component_rules: bool = True,
    live_view: bool = False,
    custom_bin: Optional[str] = None,
) -> Dict:
    """
    Executes TraceMaker route on a .kicad_pcb board.
    """
    pcb_path = Path(pcb_path).resolve()
    if not pcb_path.exists():
        return {"success": False, "error": f"Board file not found: {pcb_path}"}

    out_file = Path(output_path).resolve() if output_path else pcb_path
    bin_path, mode = find_tracemaker_binary(custom_bin)

    if mode == "none":
        return {
            "success": False,
            "engine": "tracemaker",
            "available": False,
            "error": "TraceMaker executable not found on system."
        }

    cmd = []
    if mode == "native":
        cmd = [bin_path, "route", str(pcb_path), "-o", str(out_file)]
        if time_budget_s:
            cmd.extend(["--time", str(time_budget_s)])
        elif work_budget:
            cmd.extend(["--work", str(work_budget)])
        if dru_path and Path(dru_path).exists():
            cmd.extend(["--dru", str(Path(dru_path).resolve())])
        if reroute:
            cmd.append("--reroute")
        if component_rules:
            cmd.extend(["--component-rules", "on"])
        if live_view:
            cmd.append("--view")
    else:
        # Docker mode
        host_dir = pcb_path.parent
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{host_dir}:/work",
            "-w", "/work",
            bin_path, "route", pcb_path.name, "-o", out_file.name
        ]
        if time_budget_s:
            cmd.extend(["--time", str(time_budget_s)])
        elif work_budget:
            cmd.extend(["--work", str(work_budget)])
        if reroute:
            cmd.append("--reroute")

    start_time = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=(time_budget_s or 300) + 30)
        elapsed = time.time() - start_time
        success = (proc.returncode == 0) and out_file.exists()
        
        return {
            "success": success,
            "engine": "tracemaker",
            "mode": mode,
            "time_elapsed_s": round(elapsed, 2),
            "output_file": str(out_file),
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "engine": "tracemaker",
            "error": f"TraceMaker routing timed out after {time_budget_s}s",
            "time_elapsed_s": round(time.time() - start_time, 2)
        }
    except Exception as e:
        return {
            "success": False,
            "engine": "tracemaker",
            "error": f"Failed to execute TraceMaker: {str(e)}"
        }


def run_tracemaker_escape(pcb_path: Path, custom_bin: Optional[str] = None) -> Dict:
    """
    Runs escape feasibility analysis for dense ICs and BGAs.
    """
    pcb_path = Path(pcb_path).resolve()
    if not pcb_path.exists():
        return {"success": False, "error": f"Board file not found: {pcb_path}"}

    bin_path, mode = find_tracemaker_binary(custom_bin)
    if mode == "none":
        return {
            "success": False,
            "engine": "tracemaker",
            "available": False,
            "error": "TraceMaker executable not found for escape analysis."
        }

    cmd = [bin_path, "escape", str(pcb_path)] if mode == "native" else [
        "docker", "run", "--rm", "-v", f"{pcb_path.parent}:/work", "-w", "/work",
        bin_path, "escape", pcb_path.name
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {
            "success": proc.returncode == 0,
            "engine": "tracemaker",
            "mode": mode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode
        }
    except Exception as e:
        return {"success": False, "engine": "tracemaker", "error": str(e)}


def run_tracemaker_inspect(pcb_path: Path, custom_bin: Optional[str] = None) -> Dict:
    """
    Runs board inspection and summary diagnostic via TraceMaker.
    """
    pcb_path = Path(pcb_path).resolve()
    if not pcb_path.exists():
        return {"success": False, "error": f"Board file not found: {pcb_path}"}

    bin_path, mode = find_tracemaker_binary(custom_bin)
    if mode == "none":
        return {
            "success": False,
            "engine": "tracemaker",
            "available": False,
            "error": "TraceMaker executable not found for inspect."
        }

    cmd = [bin_path, "inspect", str(pcb_path)] if mode == "native" else [
        "docker", "run", "--rm", "-v", f"{pcb_path.parent}:/work", "-w", "/work",
        bin_path, "inspect", pcb_path.name
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {
            "success": proc.returncode == 0,
            "engine": "tracemaker",
            "mode": mode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode
        }
    except Exception as e:
        return {"success": False, "engine": "tracemaker", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="TraceMaker Bridge CLI")
    parser.add_argument("pcb", help="Path to .kicad_pcb")
    parser.add_argument("-o", "--output", help="Output .kicad_pcb path")
    parser.add_argument("--mode", choices=["route", "escape", "inspect", "check"], default="route", help="Operation mode")
    parser.add_argument("--time", type=int, default=120, help="Routing time budget in seconds")
    parser.add_argument("--dru", help="Path to .kicad_dru custom rules")
    parser.add_argument("--reroute", action="store_true", help="Clear existing tracks and route cleanly from scratch")
    parser.add_argument("--bin", help="Custom path to tracemaker executable")

    args = parser.parse_args()

    if args.mode == "check":
        bin_path, mode = find_tracemaker_binary(args.bin)
        status = {
            "available": mode != "none",
            "mode": mode,
            "binary_path": bin_path
        }
        print(json.dumps(status, indent=2))
        return

    if args.mode == "escape":
        res = run_tracemaker_escape(Path(args.pcb), custom_bin=args.bin)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("success") else 1)

    if args.mode == "inspect":
        res = run_tracemaker_inspect(Path(args.pcb), custom_bin=args.bin)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("success") else 1)

    if args.mode == "route":
        res = run_tracemaker_route(
            Path(args.pcb),
            output_path=Path(args.output) if args.output else None,
            time_budget_s=args.time,
            dru_path=Path(args.dru) if args.dru else None,
            reroute=args.reroute,
            custom_bin=args.bin
        )
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("success") else 1)


if __name__ == "__main__":
    main()
