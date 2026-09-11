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

def calc_via_properties(drill_mm=0.3, plating_um=25.0, temp_rise_c=10.0, board_thick_mm=1.6):
    """
    IPC-2152 / Saturn PCB Toolkit via current, resistance, and voltage drop calculations.
    Plated barrel area A = pi * (drill + plating) * plating
    """
    plating_mm = plating_um / 1000.0
    area_mm2 = math.pi * (drill_mm + plating_mm) * plating_mm
    area_mils2 = area_mm2 / (0.0254 ** 2)

    # IPC-2152 via current capacity
    k = 0.048
    b = 0.44
    c = 0.725
    current_cap_a = k * (temp_rise_c ** b) * (area_mils2 ** c)

    # Via DC Resistance: R = rho * (L / A)
    # Copper resistivity at 20°C ≈ 1.72e-5 ohm*mm
    rho_copper = 1.724e-5
    r_via_ohm = rho_copper * (board_thick_mm / area_mm2)
    r_via_mohm = r_via_ohm * 1000.0

    return {
        "drill_mm": drill_mm,
        "plating_um": plating_um,
        "area_mm2": area_mm2,
        "area_mils2": area_mils2,
        "current_cap_a": current_cap_a,
        "r_via_mohm": r_via_mohm,
        "board_thick_mm": board_thick_mm
    }


def calc_plane_capacitance(area_cm2, dielectric_height_mm=0.10, er=4.3):
    """
    Planar Power/Ground capacitance: C = (epsilon_0 * epsilon_r * Area) / d
    """
    eps_0 = 8.8541878128e-12  # F/m
    area_m2 = area_cm2 * 1e-4
    height_m = dielectric_height_mm * 1e-3
    c_farads = (eps_0 * er * area_m2) / height_m
    c_pf = c_farads * 1e12
    return c_pf


def main():
    parser = argparse.ArgumentParser(description="PCB Trace Width, Via & Impedance Calculator (IPC-2152 & Saturn PCB)")
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

    # Via calculation parser
    p_via = subparsers.add_parser("via", help="Calculate via current capacity, resistance & thermal stitching (IPC-2152)")
    p_via.add_argument("amps", type=float, help="Total continuous current passing through via array in Amperes")
    p_via.add_argument("-d", "--drill", type=float, default=0.30, help="Via drill hole diameter in mm (default: 0.30 mm)")
    p_via.add_argument("-p", "--plating", type=float, default=25.0, help="Barrel copper plating thickness in µm (default: 25.0 µm ≈ 1 mil)")
    p_via.add_argument("-t", "--temp-rise", type=float, default=10.0, help="Allowed temperature rise ΔT in °C (default: 10)")
    p_via.add_argument("-L", "--board-thick", type=float, default=1.6, help="PCB total thickness / barrel length in mm (default: 1.6 mm)")

    # Planar capacitance parser
    p_plane = subparsers.add_parser("plane", help="Calculate power/ground plane inter-layer capacitance")
    p_plane.add_argument("area_cm2", type=float, help="Overlapping copper area in cm²")
    p_plane.add_argument("-H", "--height", type=float, default=0.10, help="Dielectric distance between planes in mm (default: 0.10 mm)")
    p_plane.add_argument("-e", "--er", type=float, default=4.3, help="Dielectric constant εr (default: 4.3)")

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

    elif args.command == "via":
        props = calc_via_properties(args.drill, args.plating, args.temp_rise, args.board_thick)
        i_cap = props["current_cap_a"]
        r_single = props["r_via_mohm"]
        min_vias = max(1, math.ceil(args.amps / i_cap))
        rec_vias = max(min_vias, math.ceil(min_vias * 1.25))  # 25% safety margin for current sharing
        r_array = r_single / rec_vias
        v_drop_mv = args.amps * r_array
        p_diss_mw = (args.amps ** 2) * (r_array / 1000.0) * 1000.0

        print(f"\n[*] IPC-2152 / Saturn PCB Via Sizing for {args.amps:.2f} A:")
        print(f"    - Drill Hole Diameter:   {args.drill:.2f} mm ({args.drill / 0.0254:.1f} mils)")
        print(f"    - Barrel Plating:        {args.plating:.1f} µm")
        print(f"    - Single Via Rating:     {i_cap:.2f} A (at ΔT = {args.temp_rise:.1f} °C)")
        print(f"    - Single Via Resistance: {r_single:.2f} mΩ")
        print(f"    ------------------------------------------------")
        print(f"    -> MINIMUM VIAS:         {min_vias} vias")
        print(f"    -> RECOMMENDED ARRAY:    {rec_vias} vias (includes 25% current sharing margin)")
        print(f"    -> PARALLEL RESISTANCE:  {r_array:.3f} mΩ")
        print(f"    -> VOLTAGE DROP (IR):    {v_drop_mv:.2f} mV")
        print(f"    -> POWER LOSS (I²R):     {p_diss_mw:.1f} mW\n")

    elif args.command == "plane":
        c_pf = calc_plane_capacitance(args.area_cm2, args.height, args.er)
        print(f"\n[*] Inter-Plane Planar Decoupling Capacitance:")
        print(f"    - Overlap Area:          {args.area_cm2:.2f} cm²")
        print(f"    - Inter-Plane Spacing:   {args.height:.3f} mm ({args.height / 0.0254:.1f} mils)")
        print(f"    - Dielectric (FR-4):     εr = {args.er:.2f}")
        print(f"    ------------------------------------------------")
        print(f"    -> PLANAR CAPACITANCE:   {c_pf:.1f} pF ({c_pf / args.area_cm2:.2f} pF/cm²)")
        print(f"    -> NOTE: Provides zero-ESL high-frequency decoupling for GHz core transients.\n")


if __name__ == "__main__":
    main()

