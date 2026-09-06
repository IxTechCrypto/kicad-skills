# Acknowledgments & Source Attribution 📚🤝

This project stands on the shoulders of brilliant engineers, researchers, and open-source contributors across the hardware design and AI agent communities. We gratefully acknowledge and credit the following primary sources, tools, and inspirations:

---

### 1. PCB Routing Best Practices & Design Rules
* **Source:** [PCB Runner — A Complete Guide to PCB Routing Design Rules and Best Practices for Success](https://www.pcbrunner.com/a-complete-guide-to-pcb-routing-design-rules-and-best-practices-for-success/#Ground_and_Power_Planes)
* **Contributions:** The foundational engineering principles codified in `skills/pcb-routing-best-practices/SKILL.md` — specifically return path loop inductance, unbroken ground reference planes, strict 45° chamfering to eliminate acid traps, the 3W crosstalk rule, via placement solder wicking avoidance, and thermal relief spoke geometry — are adapted from PCB Runner's industry guide.

---

### 2. KiCad Model Context Protocol (MCP) Ecosystem
Our tooling and workflows are deeply inspired by the pioneering MCP implementations connecting Large Language Models to KiCad:

* **[mixelpixx/KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server)**:
  * Pioneered LLM-to-KiCad direct interaction via MCP.
  * Inspired the local SQLite FTS5 database architecture for offline querying of 630,000+ JLCPCB components used in `scripts/search_jlcpcb.py`.
* **[lamaalrajih/kicad-mcp](https://github.com/lamaalrajih/kicad-mcp)**:
  * Outstanding cross-platform Model Context Protocol server for KiCad across macOS, Windows, and Linux.
* **[Seeed-Studio/kicad-mcp-server](https://github.com/Seeed-Studio/kicad-mcp-server)**:
  * Robust MCP server for schematic & PCB netlist analysis, pin-level connection tracing, and automated design editing.

---

### 3. KiCad Circuit Analysis Suite (`kicad-happy`)
* **Author:** Andrew Klofas ([@aklofas](https://github.com/aklofas))
* **Repository:** [aklofas/kicad-happy](https://github.com/aklofas/kicad-happy)
* **Contributions:** The automated diagnostic philosophy in `skills/kicad-10-workflow/SKILL.md` and our quality gate pipelines build upon Andrew's excellent Python scripts for schematic power-tree analysis, thermal pad inspection, and 44 radiated/conducted EMC pre-compliance rules.

---

### 4. KiStack & The Visual Feedback Principle
* **Inspiration:** The core tenet that AI coding agents must never "place or route blind".
* **Contributions:** Inspired our closed-loop visual feedback workflow (`scripts/render_3d.py` and layer SVG exports), requiring agents to render and inspect high-resolution raytraced 3D images to verify spatial clearances and component alignment.

---

### 5. Standards & Manufacturing Organizations
* **IPC (Association Connecting Electronics Industries):**
  * **IPC-2152**: Standard for Determining Current-Carrying Capacity in Printed Board Design (basis for `scripts/trace_calc.py`).
  * **IPC-2221**: Generic Standard on Printed Board Design.
  * **IPC-2141**: Controlled Impedance Circuit Boards and High-Speed Properties.
* **KiCad EDA:** The incredible open-source development team and contributors at [kicad.org](https://kicad.org) who make open hardware engineering accessible worldwide.
* **JLCPCB / LCSC:** For open DFM capabilities, manufacturing constraints, standard 4-layer/6-layer stackup parameters (e.g. `JLC04161H-7628`), and open component catalog indexing.

---

### 6. Community Inspiration
* Thanks to the active electronics design and AI engineering community on **X (Twitter)** whose experiments and prompts on autonomous KiCad project generation sparked the creation and open-sourcing of this repository.
