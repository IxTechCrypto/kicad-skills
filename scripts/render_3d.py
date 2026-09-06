#!/usr/bin/env python3
"""
render_3d.py — Automated 3D Board Raytracer for KiCad 10

Generates high-resolution orthographic top, bottom, and perspective isometric
3D renders of any KiCad PCB layout.
"""

import argparse
import os
import shutil
import subprocess
import sys


def find_kicad_cli():
    """Locate kicad-cli executable across operating systems."""
    # Check PATH first
    cli = shutil.which("kicad-cli")
    if cli:
        return cli

    # Standard platform locations
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


def render_board(pcb_path, output_dir, width=2048, height=1536, quality="high"):
    cli = find_kicad_cli()
    if not cli:
        print("[ERROR] kicad-cli not found. Please install KiCad or add kicad-cli to PATH.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(pcb_path):
        print(f"[ERROR] PCB file not found: {pcb_path}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    board_name = os.path.splitext(os.path.basename(pcb_path))[0]

    renders = [
        {
            "name": f"{board_name}_top.png",
            "args": ["--side", "top", "--quality", quality, "--width", str(width), "--height", str(height)]
        },
        {
            "name": f"{board_name}_bottom.png",
            "args": ["--side", "bottom", "--quality", quality, "--width", str(width), "--height", str(height)]
        },
        {
            "name": f"{board_name}_iso.png",
            "args": ["--perspective", "--rotate", "-45,0,45", "--quality", quality, "--floor", "--width", str(width), "--height", str(height)]
        }
    ]

    print(f"[*] Rendering 3D views for: {pcb_path}")
    print(f"[*] Output directory: {output_dir}")

    for r in renders:
        out_path = os.path.join(output_dir, r["name"])
        cmd = [cli, "pcb", "render"] + r["args"] + ["-o", out_path, pcb_path]
        print(f"    -> Rendering {r['name']}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[WARN] Render failed for {r['name']}: {result.stderr.strip()}")
        else:
            size_kb = os.path.getsize(out_path) / 1024.0
            print(f"       [SUCCESS] Saved: {out_path} ({size_kb:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Automated 3D Board Raytracer for KiCad 10")
    parser.add_argument("pcb", help="Path to .kicad_pcb file")
    parser.add_argument("-o", "--output-dir", default="./renders", help="Directory to save render PNGs (default: ./renders)")
    parser.add_argument("--width", type=int, default=2048, help="Image width in pixels (default: 2048)")
    parser.add_argument("--height", type=int, default=1536, help="Image height in pixels (default: 1536)")
    parser.add_argument("--quality", choices=["low", "medium", "high"], default="high", help="Raytracing quality preset (default: high)")

    args = parser.parse_args()
    render_board(args.pcb, args.output_dir, args.width, args.height, args.quality)


if __name__ == "__main__":
    main()
