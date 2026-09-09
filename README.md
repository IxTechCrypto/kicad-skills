# Agentic KiCad Skills ⚡🛠️

> **Production-grade AI agent skills, automation scripts, and DFM design rules for modern KiCad 10 electronics engineering.**

[![KiCad 10](https://img.shields.io/badge/KiCad-10.0%2B-blue.svg)](https://kicad.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#system-requirements)
[![JLCPCB DFM](https://img.shields.io/badge/DFM-JLCPCB%20Turnkey-brightgreen.svg)](https://jlcpcb.com/)

---

## 🎯 Overview

Designing printed circuit boards with AI coding agents (Claude Code, Google Antigravity, Cursor, Codex) often suffers from coordinate hallucination, blind trace routing, acid traps, and violated return paths.

This repository provides **agentic skills** and **deterministic verification scripts** that transform LLMs into rigorous hardware engineering partners. It bridges the gap between natural language prompts and machine-verified `.kicad_sch` and `.kicad_pcb` files.

---

## 📦 What's Included

### 1. Agent Skills (`skills/`)

| Skill | Description | Key Focus Areas |
| :--- | :--- | :--- |
| [`kicad-10-workflow`](skills/kicad-10-workflow/SKILL.md) | Standardizes KiCad 10 automation, synthesis, BoardRepo reference retrieval, and 3-stage independent reviews. | S-expression headers, visual feedback loop (3D rendering), deterministic ERC/DRC quality gates, 3-Stage Multi-Persona Review Protocol (Master EE + PCB/DFM Expert + Ultra-Aggressive Usability Reviewer), BoardRepo MCP open-source reference retrieval, and 3-Tier Custom Footprint Pipeline. |
| [`pcb-routing-best-practices`](skills/pcb-routing-best-practices/SKILL.md) | Core electrical, signal integrity, RF mixed-signal, algorithmic routing, and physical ergonomics rules. | Phil's Lab STRF 4-layer RF stackup, $50\Omega$ coplanar waveguides, via stitching fences, domain isolation, return path physics, IPC-2152 trace sizing, thermal vias, JLCPCB DFM rules, Routing Decision Ladder ($A^*$ Graph vs. Topological), connector outward orientation & simultaneous cable overmold envelopes. |
| [`grill-me`](skills/grill-me/SKILL.md) | Relentless, round-based design tree interview. | Stress-test plans, architecture, and hardware assumptions before implementation. Frontier-based rounds, fact-finding separation, and confirmation gates. |
| [`grilling`](skills/grilling/SKILL.md) | Core design tree and frontier questioning engine. | Primitive for round-based technical interviews and architectural exploration. |
| [`grill-with-docs`](skills/grill-with-docs/SKILL.md) | Codebase-aligned stateful grilling. | Synchronizes interview outcomes with `CONTEXT.md` and Architecture Decision Records (ADRs). |

### 2. Constraint Placement Solver & Tooling (`tools/` & `scripts/`)

* **`tools/pcb_solver/verify_layout_physics.py`**: Automated multi-layer 3D collision and ergonomics pre-flight gate. Detects cross-layer THT pin penetrations into opposite SMT pads ($\ge 1.5\,\text{mm}$ rule), RF 4-layer void breaches, M3/M2.5 standoff keepout intrusions, inward-facing connectors, and button mechanical strain stacks.
* **`tools/pcb_solver/astar_router.py`**: Graph-based 8-directional $A^*$ PCB trace router with 90° corner penalties, collinear segment simplification, and automated KiCad 10 `(segment ...)` S-expression generation.
* **`tools/pcb_solver/generate_footprint.py`**: Parametric IPC-7351B footprint generator for custom SMD IC packages (QFN, DFN, SOIC, TSSOP, SOT) with automatic **thermal pad solder paste gridding** ($2\times 2$ / $3\times 3$ apertures, 60% coverage) to prevent IC floating and solder bridging.
* **`tools/pcb_solver/pcb_solver.py`**: Discrete PCB constraint optimizer powered by Google OR-Tools CP-SAT and KiCad 10 Python IPC bridge. Enforces `NoOverlap2D` bounding boxes, sacred mechanical keepouts ($\ge 6.0\,\text{mm}$ for M3 screws), perimeter edge anchors, and top/bottom layer segregation.
* **`scripts/render_3d.py`**: Automated high-resolution orthographic top, bottom, and perspective isometric 3D board raytracer.
* **`scripts/run_quality_gates.py`**: Zero-tolerance ERC and DRC runner that refills copper zones, checks schematic-to-layout parity, and parses JSON reports.
* **`scripts/search_jlcpcb.py`**: Fast local CLI search engine for querying 630,000+ components in the JLCPCB/LCSC catalog (filters by package, in-stock quantity, and "Basic" parts).
* **`scripts/trace_calc.py`**: Terminal calculator for IPC-2152 trace current capacity and microstrip controlled impedance ($Z_0 = 50\,\Omega$).

---

## 🚀 Quick Start & Installation

Install into your preferred AI agent environment using the universal installer:

```bash
# Clone the repository
git clone https://github.com/IxTechCrypto/kicad-skills.git
cd kicad-skills

# Install to BOTH Claude Code and Google Antigravity (Default)
python install.py

# Or install to Claude Code only
python install.py --claude

# Or install to Google Antigravity only
python install.py --antigravity

# Or install to a specific project workspace
python install.py --dest ./my-hardware-project/.agents/skills
```

### Manual Installation

* **Claude Code:** Copy or symlink `skills/*` into `~/.claude/skills/`
* **Google Antigravity:** Copy or symlink `skills/*` into `~/.gemini/config/skills/`
* **Cursor / Windsurf:** Add the contents of `skills/pcb-routing-best-practices/SKILL.md` to your `.cursorrules` or `.windsurfrules`.

---

## 💡 Example Agent Prompts

Once installed, your AI agent can leverage these skills autonomously:

### 1. High-Current Power Stage Design
> *"Design a 4-layer synchronous buck converter in KiCad 10 stepping down 12V to 0.8V at 25A continuous. Size power traces per IPC-2152, keep the high-frequency switching loop minimal, and verify zero DRC violations."*

### 2. DFM & Signal Integrity Layout Review
> *"Audit this `.kicad_pcb` using your PCB routing best practices skill. Check for acid traps, return path splits on In1.Cu, unmasked vias on SMT pads, and ensure all differential pairs adhere to the 3W spacing rule."*

### 3. JLCPCB Sourcing & Turnkey BOM
> *"Find in-stock JLCPCB parts for a 15V unidirectional TVS diode and a right-angle XT60 connector. Return LCSC numbers, packages, and current inventory."*

### 4. Automated Verification & 3D Render
> *"Run automated quality gates on my schematic and board. If all checks pass with 0 errors, generate 3D raytraced renders of the top, bottom, and isometric views."*

---

## 🛠️ System Requirements

* **KiCad EDA**: Version 10.0+ recommended (also compatible with KiCad 9.0 and 8.0).
* **Python**: 3.9+ (utilizes standard library `argparse`, `json`, `sqlite3`, `subprocess`).

---

## 🌟 Acknowledgments & Prior Art

This repository builds upon and credits the foundational work of several outstanding open-source projects and industry guides. See [**ATTRIBUTION.md**](ATTRIBUTION.md) for full citations.

* **[PCB Runner](https://www.pcbrunner.com/a-complete-guide-to-pcb-routing-design-rules-and-best-practices-for-success/#Ground_and_Power_Planes):** Formed the foundational signal integrity and PCB routing engineering rules codified in `pcb-routing-best-practices`.
* **[Altium Academy / Phil Salmony (Phil's Lab)](https://youtu.be/D0X76Kbf8fQ):** Inspired the reconciled $3H$ dielectric height crosstalk rule, via antipad clearance void keepouts, high-Z analog line sizing, and low-inductance decoupling geometry.
* **[mixelpixx/KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server):** Pioneer in LLM-to-KiCad MCP interaction and creator of the local SQLite FTS5 JLCPCB database indexing architecture.
* **[lamaalrajih/kicad-mcp](https://github.com/lamaalrajih/kicad-mcp)** & **[Seeed-Studio/kicad-mcp-server](https://github.com/Seeed-Studio/kicad-mcp-server):** Pioneering Model Context Protocol servers for KiCad EDA automation.
* **[BoardRepo](https://boardrepo.com/):** Web-based hardware repository and MCP platform for open-source reference design retrieval.
* **[tscircuit/footprinter](https://github.com/tscircuit/footprinter):** Micro-builder DSL inspiring our parametric IPC-7351 footprint generation pipeline.
* **[KiCad EDA](https://kicad.org/):** The world-class open-source EDA suite.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

Developed with ⚡ by **Ix Tech** ([support@ixtech.xyz](mailto:support@ixtech.xyz)).

