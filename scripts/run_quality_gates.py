#!/usr/bin/env python3
"""
run_quality_gates.py — Deterministic ERC & DRC Quality Gates for KiCad 10

Executes electrical rules check (ERC) and design rules check (DRC), parses the
JSON diagnostic outputs, and enforces zero-tolerance quality gates.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


def find_kicad_cli():
    """Locate kicad-cli executable across operating systems."""
    cli = shutil.which("kicad-cli")
    if cli:
        return cli

    candidates = [
        r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
        "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
        "/usr/bin/kicad-cli",
        "/usr/local/bin/kicad-cli",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def run_erc(cli, sch_path, report_path="erc_report.json"):
    print(f"[*] Running Electrical Rules Check (ERC) on: {sch_path}")
    cmd = [cli, "sch", "erc", "--format", "json", "--output", report_path, sch_path]
    subprocess.run(cmd, capture_output=True, text=True)

    if not os.path.exists(report_path):
        print(f"[ERROR] ERC report was not created at {report_path}", file=sys.stderr)
        return False, []

    with open(report_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to parse ERC JSON report: {e}", file=sys.stderr)
            return False, []

    violations = data.get("sheets", [{}])[0].get("violations", []) if "sheets" in data else data.get("violations", [])
    error_count = sum(1 for v in violations if v.get("severity") == "error")
    warn_count = sum(1 for v in violations if v.get("severity") == "warning")

    print(f"    -> ERC Result: {error_count} Errors, {warn_count} Warnings")
    for v in violations:
        sev = v.get("severity", "unknown").upper()
        desc = v.get("description", "No description")
        print(f"       [{sev}] {desc}")

    return (error_count == 0), violations


def run_drc(cli, pcb_path, report_path="drc_report.json"):
    print(f"[*] Running Design Rules Check (DRC) on: {pcb_path}")
    cmd = [
        cli, "pcb", "drc",
        "--format", "json",
        "--schematic-parity",
        "--refill-zones",
        "--output", report_path,
        pcb_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)

    if not os.path.exists(report_path):
        print(f"[ERROR] DRC report was not created at {report_path}", file=sys.stderr)
        return False, []

    with open(report_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to parse DRC JSON report: {e}", file=sys.stderr)
            return False, []

    violations = data.get("violations", [])
    unconnected = data.get("unconnected_items", [])
    parity_issues = data.get("schematic_parity_issues", [])

    print(f"    -> DRC Violations: {len(violations)}")
    print(f"    -> Unconnected Items: {len(unconnected)}")
    print(f"    -> Schematic Parity Discrepancies: {len(parity_issues)}")

    for v in violations:
        print(f"       [VIOLATION] {v.get('type')}: {v.get('description')}")
    for u in unconnected:
        print(f"       [UNCONNECTED] {u.get('description')}")
    for p in parity_issues:
        print(f"       [PARITY] {p.get('description')}")

    passed = (len(violations) == 0 and len(unconnected) == 0 and len(parity_issues) == 0)
    return passed, violations


def main():
    parser = argparse.ArgumentParser(description="KiCad 10 Quality Gates Runner")
    parser.add_argument("--sch", help="Path to .kicad_sch schematic file")
    parser.add_argument("--pcb", help="Path to .kicad_pcb board file")
    args = parser.parse_args()

    if not args.sch and not args.pcb:
        parser.error("Specify at least one of --sch or --pcb")

    cli = find_kicad_cli()
    if not cli:
        print("[ERROR] kicad-cli not found. Please install KiCad or configure PATH.", file=sys.stderr)
        sys.exit(1)

    all_passed = True

    if args.sch:
        erc_ok, _ = run_erc(cli, args.sch)
        if not erc_ok:
            all_passed = False

    if args.pcb:
        drc_ok, _ = run_drc(cli, args.pcb)
        if not drc_ok:
            all_passed = False

    if all_passed:
        print("\n==========================================")
        print("  ALL QUALITY GATES PASSED (0 VIOLATIONS)")
        print("==========================================")
        sys.exit(0)
    else:
        print("\n==========================================")
        print("  QUALITY GATES FAILED - REVIEW LOGS")
        print("==========================================")
        sys.exit(1)


if __name__ == "__main__":
    main()
