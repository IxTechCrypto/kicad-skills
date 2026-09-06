---
name: kicad-10-workflow
description: Modern KiCad 10 hardware design, schematic engineering, PCB layout, visual validation, and automated ERC/DRC verification workflow. Use whenever designing schematics, modifying PCB layouts, checking design rules, plotting SVG/3D renders, or reviewing electronics in KiCad 10.
---

# KiCad 10 Hardware Engineering & Automation Workflow

This skill standardizes modern KiCad 10 electronic design automation (EDA) for AI coding agents and engineers, bridging deterministic CLI rule checks, Python `pcbnew` geometric operations, deep circuit analysis, and closed-loop visual validation.

---

## 1. System Toolchain & Binaries

KiCad 10 introduces enhanced CLI subcommands and a modernized Python API (`pcbnew` 10.0+). Standard default paths by operating system:

| Platform | `kicad-cli` Path | KiCad Python Path |
| :--- | :--- | :--- |
| **Windows** | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` | `C:\Program Files\KiCad\10.0\bin\python.exe` |
| **macOS** | `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` | `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3` |
| **Linux** | `/usr/bin/kicad-cli` | `/usr/bin/python3` (with `python3-kicad` installed) |

### CLI Invocation Examples
```bash
# General format
kicad-cli <command> <subcommand> [options] <input_file>

# Windows PowerShell example
& "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb drc board.kicad_pcb
```

---

## 2. KiCad 10 File Format Standards

When creating or modifying project files, ensure exact compatibility with KiCad 10 S-expression headers:

### Schematics (`.kicad_sch`)
```lisp
(kicad_sch
	(version 20260306)
	(generator "eeschema")
	(generator_version "10.0")
	(uuid "00000000-0000-4000-8000-000000000001")
	(paper "A4")
	(title_block ...)
    ...
)
```

#### Hierarchical Sub-Sheets
```lisp
(sheet
    (at 100.0 50.0)
    (size 30.0 25.0)
    (fields_autoplaced yes)
    (uuid "00000000-0000-4000-8000-000000000002")
    (property "Sheetname" "Power" (at 100.0 48.0 0) (effects (font (size 1.27 1.27))))
    (property "Sheetfile" "Power.kicad_sch" (at 100.0 76.5 0) (effects (font (size 1.27 1.27))))
    (pin "VIN" input (at 100.0 55.0 180) (uuid "00000000-0000-4000-8000-000000000003"))
    (pin "VOUT" output (at 130.0 55.0 0) (uuid "00000000-0000-4000-8000-000000000004"))
)
```

### Printed Circuit Boards (`.kicad_pcb`)
```lisp
(kicad_pcb
	(version 20260206)
	(generator "pcbnew")
	(generator_version "10.0")
	(general
		(thickness 1.6)
		(legacy_teardrops no)
	)
	(paper "A4")
    ...
)
```

### Project Configurations (`.kicad_pro`)
* Stored in JSON format.
* Key KiCad 10 settings: `"tuning_profiles"`, `"variants"`, `"page_layout_descr_file"`.

---

## 3. The Visual-Spatial Feedback Loop

**Never place or route blind.** Large Language Models cannot maintain complete internal spatial coordinate models across thousands of coordinates. Always render visual artifacts to inspect your work:

### A. High-Resolution 3D Board Renders
Render high-resolution PNGs to inspect component placement, footprint alignment, and physical clearances:
```bash
# Top orthographic render
kicad-cli pcb render --side top --quality high --width 2048 --height 1536 -o top.png board.kicad_pcb

# Bottom orthographic render
kicad-cli pcb render --side bottom --quality high --width 2048 --height 1536 -o bottom.png board.kicad_pcb

# Perspective isometric render
kicad-cli pcb render --perspective --rotate -45,0,45 --quality high --floor -o iso.png board.kicad_pcb
```

### B. Vector Layer Plots (Copper & Silkscreen)
Export exact vector layer plots to inspect trace routing, acid traps, and return path ground splits:
```bash
kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,Edge.Cuts --fit-page-to-board -o ./plots/ board.kicad_pcb
```

### C. Schematic Sheet Plots
Export all schematic pages to SVG for circuit auditing:
```bash
kicad-cli sch export svg -o ./sch_plots/ root.kicad_sch
```

---

## 4. Deterministic Quality Gates (Zero-Hallucination Checks)

Always validate design integrity using native KiCad 10 rule engines:

### Electrical Rules Check (ERC)
```bash
kicad-cli sch erc --format json --output erc_report.json <schematic.kicad_sch>
```
* Verify `erc_report.json` passes with:
  * `0` unconnected pins
  * `0` conflicting power outputs
  * `0` pin direction mismatches
  * Proper `PWR_FLAG` anchors on input power nets

### Design Rules Check (DRC)
```bash
kicad-cli pcb drc --format json --schematic-parity --refill-zones --output drc_report.json <board.kicad_pcb>
```
* Verify `drc_report.json` passes with:
  * `0` track clearance violations
  * `0` unrouted nets
  * `0` courtyard collisions
  * `0` drill-to-copper errors
  * `0` schematic parity discrepancies

---

## 5. Layout & Trace Routing Strategy

### The 3 Golden Rules of Agentic Routing
1. **Never guess long multi-segment trace coordinates manually in S-expressions.**
2. **For complex routing**, use:
   * **Specctra DSN / External Autorouter**: Export DSN netlist from KiCad -> run routing solver -> import SES session file.
   * **`pcbnew` Python API**: Script deterministic tracks using exact pad center vectors (`pad.GetPosition()`) and snap to 45° angles.
3. **Power Stage Topology (Buck Converters, Regulators, Power Distribution)**:
   * **Loop Area Minimization**: Keep the input capacitor ($C_{\text{IN}}$), high-side switch, low-side switch, and inductor loop as physically compact as possible.
   * **Thermal Vias**: Place a dense $3\times 3$ or $4\times 4$ thermal via grid under exposed power pads ($0.3\text{mm}$ drill, $0.6\text{mm}$ pad, tented/filled).
   * **Kelvin Connections**: Always route voltage feedback ($V_{\text{FB}}$) as a dedicated, shielded trace directly from the point-of-load bypass capacitor, isolated from the high $di/dt$ switching node ($SW$).
   * **Solid Ground Reference**: Ensure copper pours on adjacent inner layers remain unbroken directly underneath switching loops and differential pairs.
