# PCBWorld-Bench Evaluation Harness

Automated benchmarking suite for AI agentic PCB routing workflows and external routers, based on **PCBWorld / PCBWorld-Bench** (*LG AI Research & Seoul National University, arXiv:2607.05915, 2026*).

---

## 1. Why PCBWorld-Bench?

Recent empirical research establishes a critical scaling law for generative AI in electronics design:

> **Finding:** LLMs instructed to emit raw `.kicad_pcb` track coordinates directly into board files achieve a **0.00% Clean Pass (CP)** rate on complex multi-layer boards (>30 nets). LLMs lack continuous spatial perception and inevitably produce track collisions, acute-angle acid traps, and courtyard violations.

**The Solution:** Rather than using the LLM as an ungrounded geometry generator, production AI hardware engineering requires a **closed-loop rule system**:
1. High-level net planning & topological constraints set by LLM/agent.
2. Deterministic routing solvers (Freerouting, `pcbnew` Python scripting, or `route_and_verify.py`).
3. Continuous headless Design Rule Checking (`kicad-cli pcb drc`) with automated rollback.

This evaluation suite quantifies router reliability across standardized complexity tiers.

---

## 2. Complexity Tiers

Following the PCBWorld-Bench specification, benchmark boards are categorized by net density and layer count:

| Tier | Net Count | Target Board Type | Benchmark Expectation |
| :--- | :--- | :--- | :--- |
| **D3-A** | 1 – 10 nets | Simple breakout boards, sensor adapters | $\ge 95\%$ Clean Pass |
| **D3-B** | 11 – 30 nets | Microcontroller nodes, IoT peripherals | $\ge 80\%$ Clean Pass |
| **D3-C** | > 30 nets | High-density ASIC miners, FPGA boards, SOMs | High via efficiency, 0 DRC violations |

---

## 3. Metrics

- **Clean Pass (CP) Rate**: The percentage of testboards routed with **zero** DRC violations and **zero** unrouted nets:
  $$\text{CP} = \frac{N_{\text{clean}}}{N_{\text{total}}} \times 100\%$$
- **Unconnected Net Ratio**: Number of dangling airwires remaining after routing passes.
- **Total Trace Length (mm)**: Total routed copper length.
- **Via Count**: Number of layer transitions utilized (penalized for unnecessary vias).
- **Violation Breakdown**: Exact counts of:
  - `clearance`: Copper-to-copper spacing below netclass limits.
  - `acid_trap`: Acute track bend angles $< 90^\circ$.
  - `courtyard_overlap`: Component footprint boundary collisions.
  - `hole_clearance`: Annular ring and drill-to-copper violations.

---

## 4. Usage

### A. Run Evaluation on Synthetic Benchmark Suite
Generate and evaluate standard test cases across all three tiers:
```bash
python evals/run_pcbworld.py --generate-mock-suite --json-out evals/report.json
```

### B. Benchmark a Specific Directory of Boards
```bash
python evals/run_pcbworld.py --benchmark-dir ./path/to/boards/ --router freerouting
```

### C. Evaluate a Single Board
```bash
python evals/run_pcbworld.py --board ./hardware/board.kicad_pcb --router route_and_verify
```

---

## 5. Output Report

The runner generates a terminal table and exports an actionable JSON artifact (`evals_report.json`):

```json
{
  "timestamp": "2026-09-19T19:50:00Z",
  "router": "freerouting",
  "kicad_cli_available": true,
  "total_boards": 4,
  "clean_pass_count": 3,
  "clean_pass_rate": 75.0,
  "results": [
    {
      "board_name": "tier_a_pass.kicad_pcb",
      "tier": "D3-A (Low: 1-10 nets)",
      "total_nets": 6,
      "routed_nets": 6,
      "unrouted_nets": 0,
      "total_vias": 6,
      "total_trace_length_mm": 240.5,
      "drc_errors": 0,
      "clean_pass": true
    }
  ]
}
```
