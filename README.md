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
| [`kicad-10-workflow`](skills/kicad-10-workflow/SKILL.md) | Standardizes KiCad 10 automation and design workflows. | S-expression headers, visual feedback loop (3D rendering), deterministic ERC/DRC quality gates, power stage layout topology. |
| [`pcb-routing-best-practices`](skills/pcb-routing-best-practices/SKILL.md) | Core electrical and signal integrity routing rules. | Return path physics, strict 45° chamfers, 3W crosstalk suppression, IPC-2152 trace sizing, thermal vias, JLCPCB DFM rules. |

### 2. Automation Tooling (`scripts/`)

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

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

Developed with ⚡ by **Ix Tech** ([support@ixtech.xyz](mailto:support@ixtech.xyz)).
