---
name: grill-me
description: A relentless, round-based interview methodology to sharpen a plan, architecture, product direction, or design before implementation. Supports standard interview mode and with-docs mode (generating ADRs and glossary). Use when the user asks to be grilled or says /grill-me.
---

# Grill-Me: Relentless Design & Architecture Stress-Testing

Interview the user relentlessly until reaching an airtight shared understanding. Map this as a **design tree**: every decision branches into downstream decisions.

---

## 1. Operating Modes

* **Standard Mode (`/grill-me`):** Focuses purely on architectural stress-testing, eliminating hidden assumptions, and finding domain constraints.
* **With-Docs Mode (`/grill-me --docs`):** In addition to the interview rounds, automatically records settled decisions as Architectural Decision Records (ADRs) and extracts terms into a persistent domain glossary.

---

## 2. Interview Methodology

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```markdown
❓ **Q1** - **<question title>**: <question body, including options>

➡️ **Recommendation:** <your recommended answer with physical/technical rationale>

---

❓ **Q2** - **<question title>**: <question body, including options>

➡️ **Recommendation:** <your recommended answer with physical/technical rationale>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

---

## 3. Grounding Rules

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, datasheets), find it autonomously; don't ask the user for anything you could look up yourself. Don't block on it: an open exploration is an unsettled prerequisite, so only the questions downstream of it wait; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed.
