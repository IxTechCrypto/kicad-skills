# Changelog — Agentic KiCad Skills

All notable changes to the `kicad-skills` repository are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-09-19

### 🚀 Major Architectural Restructure & Domain Packs

This release restructures `kicad-skills` from a single monolithic routing guideline into a high-performance **modular domain architecture** grounded in empirical research (*PCBWorld-Bench, arXiv:2607.05915, 2026*).

#### Added
- **`skills/kicad-core` (Universal Hub)**:
  - Introduced the mandatory **Step 0: Board Regime Classifier** that categorizes designs into High-Current, High-Speed Digital, RF Wireless/Low-Power, or Custom Silicon before layout begins.
  - Standardized regime-driven stackup selection: FR-4 Standard (JLC04161H-7628) vs Heavy Copper 2oz (JLC04161H-3313).
  - Universal baseline DFM rules: $0.127\,\text{mm}$ (5 mil) min trace/space, $0.3\,\text{mm}$ drill / $0.6\,\text{mm}$ annular ring, $45^\circ$ routing only.
  - Multi-tier Routing Decision Ladder: Manual/Interactive Native $\to$ External Freerouting (via `.dsn`/`.ses`) $\to$ Native `pcbnew` Python Scripting $\to$ Experimental Algorithmic Solvers.

- **`skills/kicad-highcurrent` (Power Electronics & ASIC Miners)**:
  - Multi-stage chained DC-DC power domains with $<15\,\text{mV}$ maximum allowable IR drop.
  - IPC-2152 2oz, 3oz, and 4oz copper trace width tables for continuous currents up to $30\,\text{A}$.
  - High-density thermal via matrices ($1.5\text{--}2.0\,\text{A}$ per $0.3\,\text{mm}$ drill via) directly under exposed thermal pads.
  - Mechanical power input: XT60PW-M right-angle connector outward edge placement.
  - Power protection architecture: SMCJ15A/SMDJ15A TVS diode clamping, and TI TPS25982 electronic circuit breaker (eFuse).
  - Explicit ban on PPTC resettable fuses on rails exceeding $5\,\text{A}$.

- **`skills/kicad-highspeed` (High-Speed Digital & SI)**:
  - Differential impedance geometry for USB 2.0 ($90\,\Omega \pm 10\%$) and Ethernet RMII/RGMII ($100\,\Omega \pm 10\%$).
  - 50 MHz RMII reference clock series termination ($22\text{--}33\,\Omega$) located within $5\,\text{mm}$ of the PHY/MAC pin.
  - Unbroken ground plane return path physics and $3H$ dielectric height crosstalk rule.
  - Via antipad clearance voids: enforces $\ge 3H$ keepout around ground cutouts to prevent return current pinching.
  - Ethernet magnetics isolation: strict separation of signal ground from RJ45 chassis ground with 2 kV isolation barrier.

- **`skills/kicad-rf-lowpower` (Wireless & Ultra-Low-Power IoT)**:
  - 4-layer sacred RF antenna keepouts: complete copper voids on all layers under PCB trace antennas (ESP32 / CC1352P / nRF52840).
  - $50\,\Omega$ Coplanar Waveguide with Ground (CPWG) with ground stitching fence vias spaced $\le \lambda / 10$ ($\approx 1.2\,\text{mm}$).
  - Solar MPPT battery charging circuit layout (TI BQ25798 / Analog Devices LTC4015).
  - Ultra-low deep sleep leakage budgeting ($<20\,\mu\text{A}$ total standby current).
  - Conformal coating and environmental DFM for outdoor mining / sensor deployments.

- **`skills/kicad-newpart` (Datasheet-to-Footprint Pipeline)**:
  - Systematic 4-tier part sourcing protocol: KiCad Official $\to$ JLCPCB/EasyEDA $\to$ Ultralibrarian/SnapEDA $\to$ Parametric Synthesis.
  - Automated IPC-7351B calculation formulas for toe, heel, and side solder fillets.
  - Mandatory thermal pad solder paste gridding ($2\times 2$ or $3\times 3$ matrix with $50\%\text{--}65\%$ total paste coverage) to eliminate solder bridging and IC tombstoning/floating.
  - Pinout parity cross-verification protocol between schematic symbols and footprint pads.

- **`tools/pcb_solver/route_and_verify.py`**:
  - Closed-loop incremental 45° track router.
  - Routes individual nets, executes headless DRC (`kicad-cli pcb drc`) after every modification, and automatically rolls back if violations are introduced.

- **`evals/` (PCBWorld-Bench Evaluation Harness)**:
  - `evals/run_pcbworld.py`: Benchmarking tool supporting D3-A (1–10 nets), D3-B (11–30 nets), and D3-C (>30 nets) complexity tiers.
  - Measures Clean Pass (CP) rate, unconnected nets, trace length, via count, and categorizes DRC violations.
  - `evals/README.md`: Explains benchmark theory, LLM routing scaling laws, and evaluation commands.

#### Changed
- **`skills/pcb-routing-best-practices`**:
  - Maintained as an overarching, backward-compatible index and master reference.
  - Reconciled $3H$ return path physics, high-Z analog traces, and right-angle connector orientations.
- **`skills/kicad-10-workflow`**:
  - Updated with navigation headers directing agents to the new modular domain packs.
  - Preserved all KiCad 10 S-expression headers, BoardRepo reference retrieval, and 3-Stage Multi-Persona Review protocols.
- **`skills/grill-me`**:
  - Consolidated duplicate grilling skills (`grilling` and `grill-with-docs`) into a single unified skill with Standard and With-Docs modes.
- **`tools/pcb_solver/astar_router.py`**:
  - Added advisory header clarifying it is an experimental standalone prototype operating on an unpopulated grid, directing production routing to Freerouting, native `pcbnew`, or `route_and_verify.py`.
- **`install.py`**:
  - Dynamically discovers all available skills in `skills/` and installs them seamlessly across Claude Code, Google Antigravity, and custom workspace directories.

#### Removed
- Deleted redundant duplicate directories `skills/grilling` and `skills/grill-with-docs` (subsumed by `skills/grill-me`).

---

## [1.0.0] — 2026-09-05
- Initial public release of Agentic KiCad Skills.
- Included `kicad-10-workflow`, `pcb-routing-best-practices`, `tools/pcb_solver`, and automated verification scripts.
