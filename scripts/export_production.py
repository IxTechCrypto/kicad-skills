#!/usr/bin/env python3
"""
export_production.py — Automated KiCad 10 Fabrication & Release Generator
Inspired by KiBot & InteractiveHtmlBom (from kitspace/awesome-electronics)

Generates:
1. Production Gerbers (with zone refilling & JLCPCB/PCBWay compatibility)
2. Excellon Drill files (PTH & NPTH)
3. Pick & Place component centroid files (POS CSV)
4. Interactive HTML BOM (iBOM) for bench assembly & debugging
5. Schematic PDF (if .kicad_sch is found)
6. Zipped manufacturing package (<BoardName>_gerbers.zip)
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def find_kicad_cli():
    # 1. System PATH
    cli = shutil.which("kicad-cli")
    if cli:
        return cli

    # 2. Standard KiCad 10 Windows paths
    candidates = [
        r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\bin\kicad-cli.exe",
        r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def find_kicad_python():
    candidates = [
        r"C:\Program Files\KiCad\10.0\bin\python.exe",
        r"C:\Program Files\KiCad\bin\python.exe",
        r"C:\Program Files\KiCad\9.0\bin\python.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return sys.executable


def find_ibom_script():
    appdata = os.environ.get("APPDATA", "")
    candidates = [
        os.path.join(appdata, r"kicad\10.0\scripting\plugins\InteractiveHtmlBom\InteractiveHtmlBom\generate_interactive_bom.py"),
        os.path.join(appdata, r"kicad\scripting\plugins\InteractiveHtmlBom\InteractiveHtmlBom\generate_interactive_bom.py"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def run_cmd(cmd, desc):
    print(f"[*] {desc}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] Error during {desc}:")
        if res.stdout:
            print(res.stdout)
        if res.stderr:
            print(res.stderr)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="KiCad 10 Automated Fabrication Package Generator")
    parser.add_argument("board_file", type=str, help="Path to .kicad_pcb file")
    parser.add_argument("-o", "--output-dir", type=str, default="production", help="Output directory name (default: 'production')")
    parser.add_argument("--skip-ibom", action="store_true", help="Skip Interactive HTML BOM generation")
    parser.add_argument("--skip-sch", action="store_true", help="Skip Schematic PDF export")
    parser.add_argument("--layers", type=str, default="F.Cu,B.Cu,In1.Cu,In2.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
                        help="Comma-separated layers for Gerber plot")

    args = parser.parse_args()

    pcb_path = Path(args.board_file).resolve()
    if not pcb_path.exists():
        print(f"[-] Error: PCB file not found at {pcb_path}")
        sys.exit(1)

    project_dir = pcb_path.parent
    board_name = pcb_path.stem
    out_dir = project_dir / args.output_dir
    gerber_dir = out_dir / "gerbers"
    pos_dir = out_dir / "assembly"
    bom_dir = out_dir / "bom"
    doc_dir = out_dir / "documentation"

    for d in [gerber_dir, pos_dir, bom_dir, doc_dir]:
        d.mkdir(parents=True, exist_ok=True)

    kicad_cli = find_kicad_cli()
    if not kicad_cli:
        print("[-] Error: kicad-cli.exe could not be found.")
        sys.exit(1)

    print(f"\n============================================================")
    print(f"  KiCad 10 Automated Production Export: {board_name}")
    print(f"  Target Directory: {out_dir}")
    print(f"============================================================\n")

    # 1. Export Gerbers
    gerber_cmd = [
        kicad_cli, "pcb", "export", "gerbers",
        "--output", str(gerber_dir),
        "--layers", args.layers,
        "--check-zones",
        "--subtract-soldermask",
        "--no-x2",
        str(pcb_path)
    ]
    run_cmd(gerber_cmd, "Exporting Gerbers (Zone refill, Protel, JLCPCB standard)")

    # 2. Export Drill Files (Excellon)
    drill_cmd = [
        kicad_cli, "pcb", "export", "drill",
        "--output", str(gerber_dir) + os.sep,
        "--format", "excellon",
        "--excellon-separate-th",
        "--excellon-units", "mm",
        "--generate-map",
        "--map-format", "pdf",
        str(pcb_path)
    ]
    run_cmd(drill_cmd, "Exporting Excellon drill files (PTH + NPTH)")

    # 3. Export Pick & Place (POS CSV)
    pos_cmd = [
        kicad_cli, "pcb", "export", "pos",
        "--output", str(pos_dir / f"{board_name}-pos.csv"),
        "--format", "csv",
        "--units", "mm",
        "--side", "both",
        str(pcb_path)
    ]
    run_cmd(pos_cmd, "Exporting Centroid / Pick-and-Place (POS CSV)")

    # 4. Generate InteractiveHtmlBom
    if not args.skip_ibom:
        ibom_script = find_ibom_script()
        kicad_py = find_kicad_python()
        if ibom_script and kicad_py:
            ibom_cmd = [
                kicad_py,
                ibom_script,
                str(pcb_path),
                "--no-browser",
                "--dest-dir", str(bom_dir),
                "--name-format", f"{board_name}-ibom"
            ]
            run_cmd(ibom_cmd, "Generating Interactive HTML BOM (iBOM)")
        else:
            print("[!] InteractiveHtmlBom script not found. Skipping iBOM.")

    # 5. Export Schematic PDF (if .kicad_sch exists)
    if not args.skip_sch:
        sch_path = project_dir / f"{board_name}.kicad_sch"
        if sch_path.exists():
            sch_cmd = [
                kicad_cli, "sch", "export", "pdf",
                "--output", str(doc_dir / f"{board_name}-schematic.pdf"),
                str(sch_path)
            ]
            run_cmd(sch_cmd, "Exporting Schematic PDF")

    # 6. Create Zipped Gerber Package
    zip_filename = out_dir / f"{board_name}_gerbers.zip"
    print(f"[*] Packaging manufacturing archive -> {zip_filename.name}...")
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in gerber_dir.iterdir():
            if file.is_file():
                zf.write(file, arcname=file.name)

    print(f"\n[+] SUCCESS! Production package built:")
    print(f"    - Gerbers Zip:        {zip_filename}")
    print(f"    - Pick & Place (POS): {pos_dir / f'{board_name}-pos.csv'}")
    print(f"    - Interactive BOM:    {bom_dir / f'{board_name}-ibom.html'}")
    if (doc_dir / f"{board_name}-schematic.pdf").exists():
        print(f"    - Schematic PDF:      {doc_dir / f'{board_name}-schematic.pdf'}")
    print()


if __name__ == "__main__":
    main()
