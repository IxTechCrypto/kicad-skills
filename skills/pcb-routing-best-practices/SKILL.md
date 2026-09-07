---
name: pcb-routing-best-practices
description: Comprehensive PCB routing, component placement, spatial floorplanning, and DFM rules based on Phil's Lab, Altium Academy, and production ASIC/embedded hardware (Bitaxe, NerdAxe, Raspberry Pi).
---

# PCB Component Placement & Routing Best Practices

This skill standardizes spatial floorplanning, component placement, high-speed routing, return path physics, and mechanical DFM constraints for professional hardware design in KiCad 10.

---

## 1. Component Placement & Floorplanning Principles

### A. Spatial Zonation & Manhattan Alignment
- **Subsystem Clustering:** Group components by functional domain (Power/Buck, RF/MCU, PHY/Ethernet, User UI/Display).
- **Manhattan Alignment:** All ICs, connectors, and passives must adhere to strict $0^\circ$ or $90^\circ$ orthogonal orientations.
- **Symmetric Passive Banks:**
  - Pullup/series resistors must be arranged in orderly linear arrays or $2	imes N$ grids (e.g. Bitaxe Turbo Touch resistor arrays).
  - Bulk and decoupling capacitors must be placed in parallel columns directly adjacent to the power pins or inductor terminals for minimal ESR and loop area (e.g. NerdAxe buck output cap banks).

### B. Sacred Mechanical Keepouts
- **Mounting Holes (M3 / M2.5):**
  - All M3 mounting holes require a strict $\ge 6.0\,	ext{mm}$ diameter ($r \ge 3.0\,	ext{mm}$) annular keepout zone centered on the hole.
  - **ZERO SMD pads, ZERO components, and ZERO copper traces** are permitted inside this radius to prevent screw head or standoff crushing.
- **RF Antenna Keepouts:**
  - PCB trace antennas (ESP32-WROOM/ESP32-S3) must overhang the board perimeter with **all 4 copper layers voided** underneath and $\ge 5.0\,	ext{mm}$ clearance from mounting hardware.
- **Connector Through-Hole Keepouts:**
  - Top-layer SMD components must NEVER be placed beneath through-hole connector housings (e.g. RJ45 Magjack body, barrel jack metal shield).

### C. Multi-Layer Functional Partitioning
- **Asymmetric Layer Allocation (The Naja Duo / LilyGO T-ETH Pattern):**
  - **Top Layer (`F.Cu`):** Dedicated to heavy mechanical interfaces (RJ45, FPC display connector, user buttons, RF module).
  - **Bottom Layer (`B.Cu`):** Houses switching power regulators (buck converters, power inductors), USB-UART bridges, and MicroSD sockets.
  - **Internal Layers:** Solid unbroken Ground Plane (`In1.Cu`) acts as an electrostatic shield between switching power loops on `B.Cu` and sensitive RF/PHY lines on `F.Cu`.

### D. Customer Usability & Physical Ergonomics Constraints
- **Connector Outward Orientation (Non-Negotiable):**
  - All user-facing ports (USB-C, RJ45, MicroSD slots, Barrel Jacks, FPC ribbon latches) MUST face outward towards the board perimeter with their insertion opening pointing off-board.
  - Never rotate a user connector $180^\circ$ into the board interior.
- **FPC / Ribbon Actuator Throat Orientation & Servicing Keepout:**
  - Verify that the FPC flip latch / insertion opening faces the outer PCB edge, allowing flat flex ribbons to insert straight from off-board without $180^\circ$ hairpin loops.
  - Maintain $\ge 3.0\,\text{mm}$ clear perimeter around FPC latches to allow finger and tweezer clearance during actuator opening/closing.
- **Cross-Layer Through-Hole Clash Avoidance:**
  - Through-hole connector pins (e.g. RJ45 Magjack pins) protruding through to `B.Cu` create sharp mechanical obstacles.
  - Opposite-layer SMD sockets (e.g. MicroSD push-pull slot) must be located in clear zones (e.g. underneath SMD modules like ESP32) where no through-hole pins can block card insertion or finger grip.
- **Tactile Button & Switch Ergonomic Envelope:**
  - Pushbuttons (`RESET`, `BOOT`, user switches) require a minimum **$6.0\,\text{mm} \times 6.0\,\text{mm}$ clear finger envelope** centered on the switch actuator.
  - Never place switches in narrow crevices between tall RF shield cans and connector bodies.
- **Mating Cable Envelopes:**
  - Maintain $\ge 12\,\text{mm}$ clear envelope in front of USB-C and RJ45 ports and $\ge 3.0\,\text{mm}$ lateral clearance between adjacent connectors.

---


## 2. Power Supply & High-Current Routing

### A. Critical $di/dt$ Switching Loops
1. **Input Capacitor Placement:** Place high-frequency ceramic bypass capacitors ($100\,	ext{nF}$ and $10	ext{--}22\,\mu	ext{F}$) directly against the buck IC `VIN` and `GND` pins before the inductor.
2. **Switching Node ($LX / SW$):** Keep the copper polygon connecting the buck IC switch pin to the inductor short and wide to minimize radiated EMI.
3. **Output Capacitor Bank:** Align output capacitors in parallel immediately following the inductor, returning directly to the IC power ground.

---

## 3. High-Speed & Differential Routing

### A. RMII / SPI / USB Differential Routing
- **USB 2.0 D+/D-:** Route as a $90\,\Omega$ differential pair with length matching $\Delta L \le 1.25\,	ext{mm}$ (50 mils) and continuous ground reference underneath.
- **RMII 50MHz Clock & Data:** Route as $50\,\Omega$ controlled impedance microstrip lines with short, direct runs between PHY (LAN8720A) and ESP32.
- **3W Spacing Rule:** Maintain separation $S \ge 2W$ (and $S \ge 3H$) between high-speed signal traces and adjacent nets to eliminate crosstalk.

---

## 4. DFM & Fabrication Quality Gates

| Parameter | Standard Capability (JLCPCB 4-Layer) | Advanced / High-Density |
| :--- | :--- | :--- |
| **Minimum Trace Width** | $0.127\,	ext{mm}$ (5.0 mil) | $0.090\,	ext{mm}$ (3.5 mil) |
| **Minimum Clearance** | $0.127\,	ext{mm}$ (5.0 mil) | $0.090\,	ext{mm}$ (3.5 mil) |
| **Via Drill / Diameter** | $0.30\,	ext{mm} / 0.60\,	ext{mm}$ | $0.20\,	ext{mm} / 0.45\,	ext{mm}$ |
| **Silkscreen Min Height / Width** | $1.0\,	ext{mm} / 0.15\,	ext{mm}$ | $0.8\,	ext{mm} / 0.12\,	ext{mm}$ |
| **Silkscreen to Pad Clearance** | $\ge 0.15\,	ext{mm}$ | $\ge 0.10\,	ext{mm}$ |
