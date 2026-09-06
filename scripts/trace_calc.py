#!/usr/bin/env python3
"""
trace_calc.py — IPC-2152 Trace Width & Microstrip Impedance Calculator

Calculates PCB trace width requirements based on current and thermal limits (IPC-2152),
and microstrip characteristic impedance (Z0) for standard PCB stackups.
"""

import argparse
import math
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def calc_ipc2152(current_a, temp_rise_c=10.0, copper_weight_oz=1.0, is_internal=False):
    """
    IPC-2152 / IPC-2221 trace width calculation.
    Area (mils^2) = (Current / (k * (DeltaT ^ b))) ^ (1 / c)
    For external: k = 0.048, b = 0.44, c = 0.725
    For internal: k = 0.024, b = 0.44, c = 0.725
    """
    k = 0.024 if is_internal else 0.048
    b = 0.44
    c = 0.725

    area_mils2 = (current_a / (k * (temp_rise_c ** b))) ** (1.0 / c)
    thickness_mils = copper_weight_oz * 1.378  # 1 oz ≈ 1.378 mils (35 µm)
    width_mils = area_mils2 / thickness_mils
    width_mm = width_mils * 0.0254

    return width_mm, width_mils, area_mils2


def calc_microstrip_z0(trace_width_mm, dielectric_height_mm, dielectric_er=4.3, copper_thickness_mm=0.035):
    """
    IPC-2141 microstrip characteristic impedance formula.
    Z0 = (87 / sqrt(er + 1.41)) * ln((5.98 * H) / (0.8 * W + T))
    """
    w = trace_width_mm
    h = dielectric_height_mm
    t = copper_thickness_mm
    er = dielectric_er

    if (0.8 * w + t) <= 0 or h <= 0:
        return 0.0

    z0 = (87.0 / math.sqrt(er + 1.41)) * math.log((5.98 * h) / (0.8 * w + t))
    return z0


def solve_microstrip_width(target_z0=50.0, dielectric_height_mm=0.20, dielectric_er=4.3, copper_thickness_mm=0.035):
    """Bisection search to find trace width for target Z0."""
    low = 0.01
    high = 10.0
    for _ in range(60):
        mid = (low + high) / 2.0
        z = calc_microstrip_z0(mid, dielectric_height_mm, dielectric_er, copper_thickness_mm)
        if z > target_z0:
            low = mid
        else:
            high = mid
    return mid


def main():
    parser = argparse.ArgumentParser(description="PCB Trace Width & Impedance Calculator (IPC-2152)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Current sizing parser
    p_current = subparsers.add_parser("current", help="Calculate trace width for continuous current (IPC-2152)")
    p_current.add_argument("amps", type=float, help="Continuous DC current in Amperes")
    p_current.add_argument("-t", "--temp-rise", type=float, default=10.0, help="Allowed temperature rise ΔT in °C (default: 10)")
    p_current.add_argument("-w", "--copper-oz", type=float, default=1.0, help="Copper weight in oz (default: 1.0 oz = 35 µm)")
    p_current.add_argument("--internal", action="store_true", help="Internal plane layer (doubles thermal insulation)")

    # Microstrip impedance parser
    p_z0 = subparsers.add_parser("impedance", help="Calculate single-ended microstrip characteristic impedance Z0")
    p_z0.add_argument("-z", "--target-z0", type=float, default=50.0, help="Target impedance in Ohms (default: 50.0)")
    p_z0.add_argument("-H", "--height", type=float, default=0.20, help="Dielectric height H to ground plane in mm (default: 0.20 mm for JLC04161H-7628)")
    p_z0.add_argument("-e", "--er", type=float, default=4.3, help="Dielectric constant εr (default: 4.3 for FR-4)")
    p_z0.add_argument("-c", "--copper-thickness", type=float, default=0.035, help="Copper thickness in mm (default: 0.035 mm = 1 oz)")

    args = parser.parse_args()

    if args.command == "current":
        w_mm, w_mils, area = calc_ipc2152(args.amps, args.temp_rise, args.copper_oz, args.internal)
        layer_type = "Internal Layer" if args.internal else "External Layer"
        print(f"\n[*] IPC-2152 Trace Width Sizing for {args.amps:.2f} A ({layer_type}):")
        print(f"    - Target Current:        {args.amps:.2f} A")
        print(f"    - Permissible Temp Rise: {args.temp_rise:.1f} °C")
        print(f"    - Copper Thickness:      {args.copper_oz:.1f} oz ({args.copper_oz * 35.0:.1f} µm)")
        print(f"    - Cross-Sectional Area:  {area:.1f} mils² ({area * 0.00064516:.3f} mm²)")
        print(f"    ------------------------------------------------")
        print(f"    -> MINIMUM TRACE WIDTH:  {w_mm:.3f} mm ({w_mils:.1f} mils)")
        print(f"    -> PRACTICAL RECOMMEND:  {math.ceil(w_mm * 10) / 10:.2f} mm\n")

    elif args.command == "impedance":
        w_req = solve_microstrip_width(args.target_z0, args.height, args.er, args.copper_thickness)
        z_actual = calc_microstrip_z0(w_req, args.height, args.er, args.copper_thickness)
        print(f"\n[*] Controlled Impedance Microstrip Calculation:")
        print(f"    - Target Impedance (Z0): {args.target_z0:.1f} Ω")
        print(f"    - Dielectric Height (H): {args.height:.3f} mm ({args.height / 0.0254:.1f} mils)")
        print(f"    - Dielectric Constant:   {args.er:.2f} (FR-4)")
        print(f"    - Copper Thickness (T):  {args.copper_thickness:.3f} mm ({args.copper_thickness / 0.0254:.1f} mils)")
        print(f"    ------------------------------------------------")
        print(f"    -> CALCULATED WIDTH (W): {w_req:.3f} mm ({w_req / 0.0254:.1f} mils)")
        print(f"    -> RESULTING Z0:         {z_actual:.2f} Ω\n")


if __name__ == "__main__":
    main()
