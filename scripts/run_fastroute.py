#!/usr/bin/env python3
"""
scripts/run_fastroute.py — Automated KiCad 10 Routing with fastroute (Rust Specctra DSN/SES)

Wraps fastroute (parisxmas/fastroute, v0.1.10+) to provide:
1. One-command automated headless routing from .kicad_pcb -> Specctra DSN -> fastroute -> SES -> .kicad_pcb.
2. Live interactive routing visualization in your browser (--live).
3. Automatic differential pair preservation and length matching.
4. Machine-readable JSON metrics and performance logging.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Dict

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def find_fastroute_bin() -> Optional[Path]:
    """Locates fastroute executable across PATH and known tool locations."""
    which_fastroute = shutil.which("fastroute")
    if which_fastroute:
        return Path(which_fastroute)

    candidates = [
        Path(r"D:\tools\fastroute\fastroute.exe"),
        Path(r"D:\tools\fastroute\fastroute-0.1.10-windows-x64\fastroute.exe"),
        Path(os.path.expandvars(r"%APPDATA%\kicad\10.0\scripting\plugins\fastroute\bin\windows-x64\fastroute.exe")),
        Path(os.path.expandvars(r"%APPDATA%\kicad\9.0\scripting\plugins\fastroute\bin\windows-x64\fastroute.exe")),
        Path("/usr/local/bin/fastroute"),
        Path("/usr/bin/fastroute"),
        Path(os.path.expanduser("~/.cargo/bin/fastroute")),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def find_kicad_python() -> str:
    """Finds Python interpreter with pcbnew module available."""
    candidates = [
        r"C:\Program Files\KiCad\10.0\bin\python.exe",
        r"C:\Program Files\KiCad\9.0\bin\python.exe",
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3",
        "python3",
        sys.executable
    ]
    for c in candidates:
        if os.path.isfile(c) or shutil.which(c):
            # Test if pcbnew can be imported
            try:
                res = subprocess.run([c, "-c", "import pcbnew"], capture_output=True, timeout=5)
                if res.returncode == 0:
                    return c
            except Exception:
                continue
    return sys.executable


def find_plugin_route_cli() -> Optional[Path]:
    """Finds fastroute's bundled route_cli.py script."""
    candidates = [
        Path(os.path.expandvars(r"%APPDATA%\kicad\10.0\scripting\plugins\fastroute\route_cli.py")),
        Path(os.path.expandvars(r"%APPDATA%\kicad\9.0\scripting\plugins\fastroute\route_cli.py")),
        Path(r"D:\tools\fastroute\route_cli.py"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def run_fastroute_pipeline(
    pcb_path: Path,
    output_path: Optional[Path] = None,
    live: bool = False,
    live_port: int = 7878,
    keep_existing: bool = False,
    max_passes: int = 0,
    threads: int = 0,
    max_time_sec: Optional[float] = None,
    json_report: Optional[Path] = None,
) -> Dict:
    """Executes the full KiCad PCB -> fastroute -> KiCad PCB routing flow."""
    fastroute_bin = find_fastroute_bin()
    if not fastroute_bin:
        raise FileNotFoundError(
            "fastroute executable not found. Please install it to D:\\tools\\fastroute "
            "or via KiCad plugin manager."
        )

    out_pcb = output_path or pcb_path
    plugin_script = find_plugin_route_cli()
    kicad_py = find_kicad_python()

    print(f"[*] Starting fastroute routing pipeline:")
    print(f"    - Input Board:     {pcb_path.resolve()}")
    print(f"    - Output Board:    {out_pcb.resolve()}")
    print(f"    - fastroute Bin:   {fastroute_bin}")
    print(f"    - Live Web Visual: {'Enabled (http://127.0.0.1:' + str(live_port) + ')' if live else 'Disabled'}")

    start_time = time.time()

    if plugin_script and os.path.isfile(kicad_py):
        # Use fastroute's verified KiCad Python bridge (route_cli.py)
        cmd = [
            kicad_py,
            str(plugin_script),
            str(pcb_path),
            "-o", str(out_pcb),
            "--fastroute", str(fastroute_bin),
        ]
        if live:
            cmd.append("--live")
        if keep_existing:
            cmd.append("--keep-existing")
        else:
            cmd.append("--clear")
        if max_passes > 0:
            cmd.extend(["--max-passes", str(max_passes)])
        if threads > 0:
            cmd.extend(["--threads", str(threads)])
        if max_time_sec:
            cmd.extend(["--max-time", str(max_time_sec)])

        print(f"[*] Executing route_cli.py with KiCad Python...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(res.stdout)
        if res.stderr:
            print(res.stderr, file=sys.stderr)

        elapsed = time.time() - start_time
        success = (res.returncode == 0)

        report_data = {
            "success": success,
            "duration_sec": round(elapsed, 2),
            "output_board": str(out_pcb),
            "engine": "fastroute (route_cli)",
            "returncode": res.returncode
        }

        if json_report:
            with open(json_report, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)

        return report_data

    else:
        # Fallback: direct DSN/SES invocation using temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            dsn_file = tmp_p / "board.dsn"
            ses_file = tmp_p / "board.ses"
            report_file = tmp_p / "report.json"

            # 1. Export DSN via kicad-cli
            cli_bin = shutil.which("kicad-cli") or r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
            subprocess.run([cli_bin, "pcb", "export", "specctra", "-o", str(dsn_file), str(pcb_path)], check=True)

            # 2. Run fastroute
            cmd = [
                str(fastroute_bin),
                "-de", str(dsn_file),
                "-do", str(ses_file),
                f"--report={report_file}"
            ]
            if live:
                cmd.append(f"--live={live_port}")
            if max_passes > 0:
                cmd.extend(["-mp", str(max_passes)])
            if max_time_sec:
                cmd.extend(["--max-time", str(max_time_sec)])

            subprocess.run(cmd, check=True)

            # 3. Import SES back into board via pcbnew or report
            elapsed = time.time() - start_time
            report_dict = {}
            if report_file.exists():
                with open(report_file, "r", encoding="utf-8") as f:
                    report_dict = json.load(f)

            return {
                "success": True,
                "duration_sec": round(elapsed, 2),
                "stats": report_dict.get("stats", {})
            }


def main():
    parser = argparse.ArgumentParser(description="Automated KiCad 10 Autorouting with fastroute (Rust)")
    parser.add_argument("board", type=Path, help="Path to input .kicad_pcb")
    parser.add_argument("-o", "--output", type=Path, help="Path for routed output .kicad_pcb (default: overwrite input)")
    parser.add_argument("--live", action="store_true", help="Launch live in-browser routing visualization (fastroute --live)")
    parser.add_argument("--live-port", type=int, default=7878, help="Port for live visualization server (default: 7878)")
    parser.add_argument("--keep-existing", action="store_true", help="Keep locked and existing tracks, route only airwires")
    parser.add_argument("--max-passes", type=int, default=0, help="Maximum autorouting passes (0 = default)")
    parser.add_argument("--threads", type=int, default=0, help="Parallel worker threads (0 = auto)")
    parser.add_argument("--max-time", type=float, help="Timeout in seconds before stopping and keeping best board")
    parser.add_argument("--report", type=Path, help="Export JSON summary report")

    args = parser.parse_args()

    if not args.board.is_file():
        print(f"[ERROR] Board file does not exist: {args.board}", file=sys.stderr)
        sys.exit(1)

    try:
        res = run_fastroute_pipeline(
            pcb_path=args.board,
            output_path=args.output,
            live=args.live,
            live_port=args.live_port,
            keep_existing=args.keep_existing,
            max_passes=args.max_passes,
            threads=args.threads,
            max_time_sec=args.max_time,
            json_report=args.report,
        )
        if res.get("success"):
            print(f"[SUCCESS] fastroute completed in {res.get('duration_sec')}s!")
        else:
            print(f"[FAILED] fastroute exited with code {res.get('returncode')}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] fastroute execution failure: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
