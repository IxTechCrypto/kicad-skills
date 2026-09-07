---
name: pcb-routing-best-practices
description: Comprehensive PCB routing, component placement, spatial floorplanning, RF mixed-signal architecture, and DFM rules based on Phil's Lab (STRF), Altium Academy, and production ASIC/embedded hardware (Bitaxe, NerdAxe, Raspberry Pi).
---

# PCB Component Placement, RF Mixed-Signal & Routing Best Practices

This skill standardizes spatial floorplanning, component placement, RF mixed-signal architecture, high-speed routing, return path physics, and mechanical DFM constraints for professional hardware design in KiCad 10.

---

## 1. Component Placement & Floorplanning Principles

### A. Spatial Zonation & Manhattan Alignment
- **Subsystem Clustering:** Group components by functional domain (Power/Buck, RF/Transceiver, MCU/Digital, User UI/Display).
- **Domain Isolation (The Phil's Lab STRF Pattern):** Strictly isolate noisy digital switching microcontrollers (e.g. STM32, ESP32) from sensitive RF front-ends (e.g. nRF24, Sub-GHz transceivers). Power to analog/RF domains must pass through dedicated ferrite beads (`FB`) and multi-decade bypass arrays ($10\,\mu\text{F} \to 1\,\mu\text{F} \to 100\,\text{nF} \to 10\,\text{nF} \to 1\,\text{pF}$).
- **Manhattan Alignment:** All ICs, connectors, and passives must adhere to strict $0^\circ$ or $90^\circ$ orthogonal orientations.
- **Symmetric Passive Banks:**
  - Pullup/series resistors must be arranged in orderly linear arrays or $2 \times N$ grids.
  - Bulk and decoupling capacitors must be placed in parallel columns directly adjacent to the power pins or inductor terminals for minimal ESR and loop area.

### B. Sacred Mechanical Keepouts
- **Mounting Holes (M3 / M2.5):**
  - All M3 mounting holes require a strict $\ge 6.0\,\text{mm}$ diameter ($r \ge 3.0\,\text{mm}$) annular keepout zone centered on the hole. M2.5 requires $r \ge 2.75\,\text{mm}$.
  - **ZERO SMD pads, ZERO components, and ZERO copper traces** are permitted inside this radius to prevent screw head or standoff crushing.
- **RF Antenna Keepouts:**
  - PCB trace antennas (ESP32-WROOM/ESP32-S3) must overhang the board perimeter with **all 4 copper layers voided** underneath and $\ge 5.0\,\text{mm}$ clearance from mounting hardware.
- **Connector Through-Hole Keepouts:**
  - Top-layer SMD components must NEVER be placed beneath through-hole connector housings (e.g. RJ45 Magjack body, barrel jack metal shield).

### C. Multi-Layer Functional Partitioning & Stackup Standards
- **4-Layer Ground-Centric Stackup (Phil's Lab / JLC2313 / JLC7628):**
  - **Layer 1 (Top / `F.Cu`):** High-speed signals, RF coplanar waveguides, critical ICs, and discrete passives.
  - **Layer 2 (`In1.Cu`):** **Solid, Unbroken Ground Reference Plane.** Must sit directly below L1 with thin dielectric ($0.1\text{--}0.2\,\text{mm}$) to provide tight, uninterrupted return current loops and precise $50\,\Omega$ characteristic impedance.
  - **Layer 3 (`In2.Cu`):** Power distribution planes (+3.3V, +5V, core rails) and auxiliary ground pours.
  - **Layer 4 (Bottom / `B.Cu`):** Low-speed routing, debug SWD headers, secondary ground fill, and underside SMT components (e.g. MicroSD sockets).
- **Asymmetric Layer Allocation (The Naja Duo / Pi Zero Pattern):**
  - **Top Layer (`F.Cu`):** Heavy mechanical interfaces, FPC displays, user buttons, GPIO expansion headers, SoC.
  - **Bottom Layer (`B.Cu`):** Switching power regulators, USB-UART bridges, and push-pull MicroSD sockets.

### D. Ultra-Aggressive Customer Usability & Ergonomics Constraints
- **Connector Outward Orientation (Non-Negotiable):**
  - All user-facing ports (USB-C, RJ45, MicroSD slots, Barrel Jacks, FPC ribbon latches, HDMI) MUST face outward towards the board perimeter with their insertion opening pointing off-board.
  - **Bottom Layer (`B.Cu`) Coordinate Flip Guard:** On `B.Cu`, KiCad's `fp.Flip()` mirrors the footprint across the X-axis (inverting the local Y vector). A rotation that points right on `F.Cu` ($+90^\circ$) will point **left/inward** on `B.Cu`. To point outward to the right edge on `B.Cu`, rotation must be **$270^\circ$ ($-90^\circ$)**.
- **Simultaneous Cable Plug Overmolds:**
  - Never evaluate connectors with bare metal contacts in isolation. Apply standard molded cable boot dimensions:
    - **Mini / Full HDMI:** $18\,\text{mm} \times 9\,\text{mm}$
    - **Micro-USB:** $11\,\text{mm} \times 7\,\text{mm}$
    - **USB-C:** $13\,\text{mm} \times 7.5\,\text{mm}$
  - Verify side-by-side pitch: adjacent ports (e.g. dual USB ports) must have $\ge 12.5\,\text{mm}$ center pitch so two standard molded cables plug in simultaneously without colliding.
- **SD Card 3-Stage Mechanical Dynamics & Pinch Corridor:**
  - 1) **Locked state:** Card overhangs board edge by $\approx 1.5\text{--}2.0\,\text{mm}$.
  - 2) **Push-to-Eject stroke:** Card travels **inward an additional $1.5\text{--}2.0\,\text{mm}$** past the locked position before releasing. No internal components may obstruct this inward stroke.
  - 3) **Ejected protrusion:** Card extends $3.5\text{--}4.5\,\text{mm}$ past PCB edge.
  - Maintain an open **$\ge 12.0\,\text{mm}$ pinch corridor** for human fingernail leverage.
- **Expansion Header & HAT Strike-Zone:**
  - When $2 \times 20$ $2.54\,\text{mm}$ GPIO headers are placed on Top (`F.Cu`), the entire $5.08\,\text{mm}$ plastic shroud and daughterboard seating zone must be 100% clear of colliding SMT components (e.g., MicroSD sockets must be partitioned to `B.Cu`).
- **Tactile Button & Switch Ergonomic Envelope:**
  - Pushbuttons (`RESET`, `BOOT`) require a minimum **$6.0\,\text{mm} \times 6.0\,\text{mm}$ clear finger envelope** centered on the switch actuator.

---

## 2. RF & Mixed-Signal Layout Principles (Phil's Lab STRF Standard)

### A. $50\,\Omega$ Coplanar Waveguide & Transmission Line Rules
- **Controlled Impedance Trace Width:** Calculate trace width strictly against the L1--L2 dielectric thickness and copper weight (typically $0.26\text{--}0.30\,\text{mm}$ on 4-layer standard FR4).
- **Zero Vias on RF Path:** The primary RF transmission line between the matching network and antenna/SMA connector must have **zero layer transitions or vias**.
- **Ground Via Fencing:** Flank both sides of the RF microstrip with continuous ground stitching vias spaced $\le \lambda/10$ to suppress EMI radiation and lateral cross-talk.

### B. Discrete LC Balun & Matching Networks
- **Microscopic Loop Area:** Place inductors and capacitors for the matching network (e.g. $L_1\text{--}L_3, C_{15}\text{--}C_{18}$) immediately adjacent to transceiver IC pins.
- **Thermal Pad Grounding:** IC exposed ground pads (QFN EP) require a dense grid of ground vias directly into the internal ground plane for thermal dissipation and RF return grounding.

### C. ESD & Transient Entry Gate
- **Diode Array Placement:** Place TVS diode arrays (e.g. `USBLC6-2SC6`) and PTC reset fuses directly at the edge connector pins before traces enter the board body.

---

## 3. Power Supply & High-Current Routing

### A. Critical $di/dt$ Switching Loops
1. **Input Capacitor Placement:** Place high-frequency ceramic bypass capacitors ($100\,\text{nF}$ and $10\text{--}22\,\mu\text{F}$) directly against the buck IC `VIN` and `GND` pins before the inductor.
2. **Switching Node ($LX / SW$):** Keep the copper polygon connecting the buck IC switch pin to the inductor short and wide to minimize radiated EMI.
3. **Output Capacitor Bank:** Align output capacitors in parallel immediately following the inductor, returning directly to the IC power ground.

---

## 4. High-Speed & Differential Routing

### A. Differential Pair Guidelines
- **USB 2.0 D+/D-:** Route as a $90\,\Omega$ differential pair with length matching $\Delta L \le 1.25\,\text{mm}$ (50 mils) and continuous ground reference underneath.
- **HDMI TMDS Pairs:** Route as $100\,\Omega$ differential pairs with tight inter-pair length matching ($\Delta L \le 0.5\,\text{mm}$) and continuous ground shielding.
- **3W Spacing Rule:** Maintain separation $S \ge 2W$ (and $S \ge 3H$) between high-speed signal traces and adjacent nets to eliminate crosstalk.

---

## 5. DFM & Fabrication Quality Gates

| Parameter | Standard Capability (JLCPCB 4-Layer) | Advanced / High-Density |
| :--- | :--- | :--- |
| **Minimum Trace Width** | $0.127\,\text{mm}$ (5.0 mil) | $0.090\,\text{mm}$ (3.5 mil) |
| **Minimum Clearance** | $0.127\,\text{mm}$ (5.0 mil) | $0.090\,\text{mm}$ (3.5 mil) |
| **Via Drill / Diameter** | $0.30\,\text{mm} / 0.60\,\text{mm}$ | $0.20\,\text{mm} / 0.45\,\text{mm}$ |
| **RF Coplanar Ground Clearance** | $0.25\text{--}0.35\,\text{mm}$ | $0.20\,\text{mm}$ |
| **Cross-Layer THT-to-SMT Clearance** | $\ge 1.50\,\text{mm}$ | $\ge 1.00\,\text{mm}$ |
| **RF Antenna Keepout** | Strict 4-Layer Copper/Component Void | Strict 4-Layer Copper/Component Void |
| **M3 / M2.5 Standoff Radial Keepout** | $r \ge 3.0\,\text{mm} / 2.75\,\text{mm}$ | $r \ge 3.0\,\text{mm} / 2.75\,\text{mm}$ |
