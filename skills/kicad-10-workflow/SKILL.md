---
name: kicad-10-workflow
description: Modern KiCad 10 hardware design, schematic engineering, PCB layout, visual validation, and automated ERC/DRC verification workflow. Use whenever designing schematics, modifying PCB layouts, checking design rules, plotting SVG/3D renders, or reviewing electronics in KiCad 10.
---

# KiCad 10 Hardware Engineering & Automation Workflow

This skill standardizes modern KiCad 10 electronic design automation (EDA) for AI coding agents and engineers, bridging deterministic CLI rule checks, Python `pcbnew` geometric operations, deep circuit analysis, and closed-loop visual validation.

> **Attribution Notice:** Circuit diagnostic methodology and EMC pre-compliance concepts adapted from Andrew Klofas's [kicad-happy](https://github.com/aklofas/kicad-happy). EDA engine powered by [KiCad EDA](https://kicad.org/). Full credits in [ATTRIBUTION.md](../../ATTRIBUTION.md).

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

---

## 6. Multi-Role Independent Engineering Review Protocol

Once the primary schematic and PCB layout are generated, the design MUST undergo a mandatory three-stage independent review before being marked as complete or released for fabrication:

### Stage 1: Independent Master Electrical Engineer Review
1. **Power Supply & Switching Converter Topology:**
   - Verify input capacitor ($C_{\text{IN}}$) and output capacitor ($C_{\text{OUT}}$) placement directly adjacent to switching IC.
   - Confirm switching loop area ($V_{\text{IN}} \rightarrow \text{SW} \rightarrow L \rightarrow C_{\text{OUT}} \rightarrow \text{GND}$) is strictly minimized.
   - Verify feedback divider ($V_{\text{FB}}$) takes a clean Kelvin connection from $C_{\text{OUT}}$, shielded from inductor $SW$ flux.
2. **Decoupling & Power Integrity:**
   - Confirm every IC power pin has a local $100\,\text{nF}$ bypass cap within $< 2.0\,\text{mm}$.
   - Check ferrite bead / LC filters for sensitive analog/RF/PHY rails ($V_{\text{DDA33}}$).
3. **High-Speed Signal & Clock Integrity:**
   - Verify 50MHz RMII clock, crystal oscillators, and SPI high-speed buses run over unbroken ground reference planes.
   - Verify termination resistors ($49.9\,\Omega \pm 1\%$ on Ethernet, series dampening on high-speed clocks).
4. **Protection & Safety:**
   - Confirm TVS diodes on exposed user connectors (USB VBUS/D+/D-, Ethernet pairs) and proper fuse/eFuse sizing.

### Stage 2: Independent PCB Layout, Mechanical & DFM Expert Review
1. **Mechanical Keepouts & Hardware Clearances (CRITICAL):**
   - **Mounting Holes:** Screw heads, washers, and standoffs require a strict circular keepout:
     - **M3 Holes:** $\ge 6.0\,\text{mm}$ diameter circular clearance centered on hole.
     - **M2.5 Holes:** $\ge 5.0\,\text{mm}$ diameter circular clearance.
     - **Zero Tolerance:** No SMD/THT components, copper tracks, or vias may enter the hardware keepout zone.
2. **Courtyard Collisions & Physical Clearances:**
   - 0 component body overlaps, 0 courtyard collisions in DRC.
   - Ensure tall components (RJ45, electrolytic caps, inductors) do not obstruct ribbon cables or daughterboards.
3. **Silkscreen Integrity & Collision Prevention:**
   - Silkscreen text, component outlines, and reference designators must **NEVER** overlap solder pads, test points, or mounting hole annular rings.
   - Minimum text height $\ge 0.80\,\text{mm}$, line thickness $\ge 0.15\,\text{mm}$.
   - All text oriented consistently (readable from bottom or right).
4. **Closed-Loop Visual Inspection Gate:**
   - Generate and visually inspect high-resolution 3D renders (`render_top.png`, `render_bottom.png`, `render_iso.png`).
   - Specifically zoom in and audit:
     - All 4 corners & mounting holes.
     - Board perimeter & connector overhangs.
     - High-density IC fanouts and passive clusters.
   - If any violation is observed in the 3D render, the design fails the review and must be adjusted before final sign-off.

### Stage 3: Independent Customer Usability & Physical Ergonomics Reviewer
1. **Connector Outward Orientation (CRITICAL):**
   - **Outward Facing Rule:** All user-mating interfaces (USB-C, RJ45, MicroSD slots, Barrel Jacks, Audio Jacks, FPC ribbon latches, Terminal Blocks) MUST face directly outward towards the PCB edge with the insertion axis pointing off-board.
   - **Zero Inward Receptacles:** A connector oriented $180^\circ$ inward into the board body is a critical usability defect and must be rejected immediately.
2. **FPC / ZIF Ribbon Connector Insertion & Actuator Flap:**
   - Verify the footprint orientation distinguishes between fixed solder pins and the hinged actuator flap. The **ribbon entry throat and flip latch MUST face the board edge** so flex cables insert straight off-board without $180^\circ$ hairpin loops.
   - Maintain $\ge 3.0\,\text{mm}$ clear perimeter around the FPC latch to allow finger or tweezer access to open and lock the actuator during assembly and servicing.
3. **Plug & Cable Insertion Keepout Envelope:**
   - Ensure a minimum $10\text{--}15\,\text{mm}$ clear 3D volume in front of every port opening for cable overmolds, mating plugs, and user fingers.
   - Adjacent connectors must have $\ge 3.0\,\text{mm}$ lateral clearance to prevent wide USB-C / Ethernet cable hoods from colliding when plugged in simultaneously.
4. **Cross-Layer Through-Hole Clash Prevention:**
   - Through-hole connector leads (e.g. RJ45 Magjack pins, PTH terminals) protruding through to the opposite copper layer (`B.Cu`) must **NEVER** block or obstruct the insertion path, socket mouth, or card body of opposite-side SMD sockets (e.g. MicroSD push-pull cards).
5. **Physical Controls Ergonomics & Finger Clearance:**
   - Tactile switches (`RESET`, `BOOT`), dip switches, and pushbuttons require a **minimum $6.0\,\text{mm} \times 6.0\,\text{mm}$ clear finger envelope** centered on the button cap.
   - Switches must **NEVER** be placed in narrow crevices directly abutting tall shielding cans (e.g. ESP32 metal can), massive connector housings, or underneath flex cables.
   - Operational status LEDs (Power, Wi-Fi, Ethernet Link) must remain visible during active operation and not be masked by plugged-in cables or large daughterboards.



