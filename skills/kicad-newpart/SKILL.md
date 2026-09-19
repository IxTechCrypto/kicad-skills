---
name: kicad-newpart
description: Automated, hallucination-free generation and verification of new schematic symbols (.kicad_sym) and IPC-7351B PCB footprints (.kicad_mod) from manufacturer datasheets. Governs pinout cross-checking, QFN thermal pad paste gridding, and 3D model alignment.
---

# KiCad New Part: Datasheet to Verified Footprint & Symbol

> **CRITICAL RULE:** A hallucinated pin assignment or inverted package footprint permanently destroys a physical prototype run. Never emit a footprint or symbol without deterministic verification against the manufacturer datasheet.

---

## 1. Pinout Extraction & Verification Protocol

When creating a new part for which no standard KiCad library part exists:

```
[Manufacturer Datasheet] ──► [Pinout Table Extraction] ──► [Package Drawing Verification]
                                          │                                │
                                          ▼                                ▼
                             [Symbol: .kicad_sym]             [Footprint: .kicad_mod]
                                          │                                │
                                          └──────────────┬─────────────────┘
                                                         │
                                                         ▼
                                            [Automated Parity Audit]
                                          (0 Mismatches, 0 Missing Pins)
```

1. **Dual-Source Pin Verification:**
   * Extract pin numbers, pin names, and electrical types (Power Input, Output, Bidirectional, Passive) directly from the datasheet pin table.
   * Cross-reference against the mechanical top-view / bottom-view pin assignment drawing.
   * Pay extreme attention to QFN/BGA numbering conventions: QFNs number counter-clockwise from Pin 1 (top-left index dot); BGAs use alphanumeric grids (omitting letters I, O, Q, S, X, Z).
2. **Exposed Thermal Pad (Pad 0 / Pad EP):**
   * Confirm whether the exposed thermal pad must be tied to `GND`, a negative rail (e.g. $-V_{\text{IN}}$ on some OpAmps), or left floating.

---

## 2. Parametric IPC-7351B Footprint Generation

Use the integrated parametric generator script:
```bash
python tools/pcb_solver/generate_footprint.py --type qfn --pins 32 --pitch 0.5 --body 5.0 5.0 --ep 3.5 3.5 -o MyLib.pretty
```

### Mandatory DFM Rules for Custom Footprints:
1. **IPC-7351 Fillet Calculations:**
   * Toe fillet: $\ge 0.35\,\text{mm}$ (front solder joint inspection).
   * Heel fillet: $\ge 0.35\,\text{mm}$ (mechanical retention).
   * Side fillet: $\ge 0.05\,\text{mm}$.
2. **Thermal Pad Solder Paste Gridding (50%–65% Rule):**
   * Never lay down a solid $100\%$ solder paste mask over a large exposed thermal pad.
   * Trapped flux outgassing creates massive solder voids, lifts the component off perimeter signal pads, and causes solder ball bridging.
   * Divide the paste stencil layer (`F.Paste`) into a $2\times 2$, $3\times 3$, or $4\times 4$ windowpane array with $50\%\text{--}65\%$ total paste area coverage.
3. **Thermal Via Array:**
   * Embed an array of $0.30\,\text{mm}$ drill / $0.60\,\text{mm}$ pad thermal vias inside the ground slug on a $1.0\text{--}1.2\,\text{mm}$ grid.
4. **Silkscreen & Courtyard Geometry:**
   * Pin 1 marker must be clearly visible outside the package body after component assembly.
   * Courtyard boundary (`F.CrtYd`) must provide at least $0.25\,\text{mm}$ clearance beyond maximum package lead extent.

---

## 3. Pre-Flight Quality Gate Checklist

Before adding a new component to any project schematic:
- [ ] **Pin Count Equality:** Symbol pin count matches footprint pad count exactly (including thermal pad EP).
- [ ] **Pin Number Matching:** Pin `1` in symbol corresponds to physical Pin `1` pad in footprint.
- [ ] **Thermal Pad Paste Array:** Exposed pad contains segmented windowpane paste apertures.
- [ ] **Solder Mask Dam:** Minimum $0.10\,\text{mm}$ solder mask bridge between adjacent SMD pads.
- [ ] **3D Step Model Alignment:** STEP 3D model aligned with zero pin offset.
