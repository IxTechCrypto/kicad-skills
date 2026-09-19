---
name: kicad-core
description: Mandatory foundation and entrypoint for KiCad 10 design tasks. Classifies the board regime (High-Current, High-Speed, Low-Power RF), dictates layer stackup allocation, enforces the Routing Decision Ladder, and governs automated quality gates.
---

# KiCad Core: Regime Classifier, Stackups & Quality Gates

> **MANDATORY ENTRYPOINT:** Every agentic hardware design task in KiCad 10 MUST execute **Step 0: Board Regime Classification** before drawing footprints or routing tracks.

---

## 1. Step 0: The Board Regime Classifier

Never route or place components without explicitly identifying the dominant physical regime. Large Language Models excel at functional classification; make this classification explicit:

```
                                [Incoming Design Task]
                                          │
                                 ▼ (Step 0 Classifier)
         ┌────────────────────────────────┼────────────────────────────────┐
         │                                │                                │
         ▼                                ▼                                ▼
  [High-Current Regime]         [High-Speed Digital]              [Low-Power RF]
  • Dominant: IR drop, thermal  • Dominant: Return continuity,   • Dominant: Impedance,
    spreading, via arrays,        diff-pair skew, EMI,            antenna keepout, solar
    buck converter loops          stub lengths, crosstalk         MPPT, sleep leakage
         │                                │                                │
         ▼                                ▼                                ▼
  Load: kicad-highcurrent        Load: kicad-highspeed           Load: kicad-rf-lowpower
```

### Regime Evaluation Criteria:
1. **Regime A: High-Current (Load `kicad-highcurrent`)**
   * *Triggers:* DC current $> 3.0\,\text{A}$ on any rail, core ASIC supplies ($< 1.0\,\text{V}$ at high amps), switching converters $> 15\,\text{W}$, or server PSU inputs.
   * *Priorities:* Copper weight (2oz/3oz/4oz), polygon planes, thermal via matrices, TVS clamping, and eFuse protection.
2. **Regime B: High-Speed Digital (Load `kicad-highspeed`)**
   * *Triggers:* Clocks/signals $> 25\,\text{MHz}$, rise times $t_r < 2\,\text{ns}$, USB 2.0/3.0, Ethernet (RMII/RGMII), SPI $> 40\,\text{MHz}$, or HDMI/MIPI.
   * *Priorities:* Unbroken ground planes, matched diff-pair skew ($\le 5\,\text{mils}$), antipad void clearance, and magnetics/chassis ground splits.
3. **Regime C: Low-Power / RF (Load `kicad-rf-lowpower`)**
   * *Triggers:* Sub-GHz (LoRa, 433/868/915 MHz), 2.4 GHz (Wi-Fi, BLE), battery-powered nodes with solar/MPPT, sleep currents $< 50\,\mu\text{A}$.
   * *Priorities:* Antenna keepouts, 50Ω microstrip geometry, low-quiescent-current battery safety, and environmental DFM.
4. **Regime D: Mixed-Signal (Multi-Pack Loading)**
   * Most real-world production boards (e.g. Miner Display Bridge, Bitaxe) combine multiple domains. The agent must partition the board spatially and load the respective skill packs for each functional subsystem.

---

## 2. Regime-Driven Stackup Selection Matrix

Never use a single generic stackup for all boards. Dielectric thickness and copper weights must match the physical regime:

| Board Regime | Recommended Layers | Copper Weights (Outer / Inner) | Dielectric Allocation | Dominant Metric |
| :--- | :---: | :---: | :---: | :--- |
| **High-Current (Miner/PDN)** | 4 to 6 Layers | **2 oz / 1 oz** (or 3 oz / 2 oz) | Balanced thick core for vertical thermal conduction | IR drop ($< 15\,\text{mV}$), temperature rise $\Delta T < 10^\circ\text{C}$ |
| **High-Speed Digital** | 4 to 6 Layers | **1 oz / 0.5 oz** | Thin prepreg ($0.10\text{--}0.15\,\text{mm}$) over unbroken L2 ground | Controlled $50\,\Omega$ single / $90\text{--}100\,\Omega$ diff impedance |
| **Low-Power / RF** | 2 to 4 Layers | **1 oz / 0.5 oz** | Low-loss dielectric (e.g. Isola or verified JLC7628) | Minimal RF insertion loss ($S_{21}$), RF antenna ground clearance |

---

## 3. The Routing Decision Ladder

To avoid the collapse observed when LLMs attempt open-loop geometry generation, all routing follows this strict hierarchy:

```
Level 0: Placement & Floorplanning (Deterministic)
         ↳ Execute OR-Tools CP-SAT placement solver (`tools/pcb_solver/pcb_solver.py`)
         ↳ Enforce edge anchors, courtyard keepouts, and connector egress vectors.

Level 1: Power & Heavy Ground Highways (Semi-Automated)
         ↳ Scripted native `pcbnew` Python polygons with 45° chamfers & thermal via arrays.
         ↳ Directly connects heavy buck stages, inductors, and input protection.

Level 2: Dense Digital & Bus Routing (Automated Solver)
         ↳ Export Specctra DSN (`kicad-cli pcb export dsn`).
         ↳ Solve with Freerouting or native KiCad PNS push-and-shove router.
         ↳ Re-import SES session file (`kicad-cli pcb import ses`).

Level 3: Escape & Trivial Jumpers (Scripted A* or Native API)
         ↳ Use `tools/pcb_solver/route_and_verify.py` for incremental net routing with immediate DRC delta check.
```

---

## 4. Deterministic Quality Gates (Zero-Tolerance)

Every board modification must pass headless verification before proceeding to the next design phase:

```bash
# 1. Electrical Rules Check (Schematic)
kicad-cli sch erc --format json --output erc_report.json <schematic.kicad_sch>

# 2. Design Rules Check (PCB Layout + Schematic Parity + Zone Refill)
kicad-cli pcb drc --format json --schematic-parity --refill-zones --output drc_report.json <board.kicad_pcb>

# 3. Physical Layout & Multi-Layer Clash Audit
python tools/pcb_solver/verify_layout_physics.py <board.kicad_pcb>

# 4. Closed-Loop 3D Raytracing & Visual Inspection
python scripts/render_3d.py <board.kicad_pcb>
```
* **Gate Requirement:** 0 DRC violations, 0 ERC errors, 0 unrouted nets, 0 schematic parity discrepancies.
