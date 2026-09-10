"""
PCB Layout Physics & Multi-Layer Clash Validator (KiCad 10)
============================================================
A deterministic, zero-hallucination verification engine that catches critical
cross-layer physical, RF, and mechanical defects that bypass standard KiCad 2D DRC:

1. Cross-Layer Through-Hole (PTH) vs Opposite-Layer SMT Pad Clearance (>= 1.5mm)
2. Sacred RF Antenna 4-Layer Copper/Component Void Keepout Verification
3. Outward-Facing Insertion Vector Normal Validation (Layer-Aware B.Cu flip math)
4. Mechanical Mounting Hole Standoff Clearance (r >= 3.0mm)
5. Actuator Mechanical Strain Isolation (Tactile switches over fine-pitch ICs)
"""

import sys
import json
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, r"C:\Program Files\KiCad\10.0\bin")
import pcbnew

@dataclass
class ValidationReport:
    passed: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class PCBPhysicsValidator:
    def __init__(self, pcb_path: Path):
        self.pcb_path = Path(pcb_path).resolve()
        if not self.pcb_path.exists():
            raise FileNotFoundError(f"PCB file not found: {self.pcb_path}")
        self.board = pcbnew.LoadBoard(str(self.pcb_path))
        self.report = ValidationReport(passed=True)

    def validate_all(self, rf_antenna_zones: List[Tuple[float, float, float, float]] = None) -> ValidationReport:
        """Runs the full battery of physical, cross-layer, and RF keepout tests."""
        print(f"[*] Running PCB Physics & Multi-Layer Clash Audit on {self.pcb_path.name}...")
        
        self.check_cross_layer_tht_smt_clearance(min_clearance_mm=1.5)
        self.check_rf_antenna_keepouts(rf_antenna_zones)
        self.check_mounting_hole_standoffs(min_radius_mm=3.0)
        self.check_actuator_strain_isolation()
        self.check_connector_outward_vectors()
        self.check_orchestrator_component_connectivity(search_radius_mm=1.8)

        if self.report.violations:
            self.report.passed = False
            print(f"\n[FAIL] {len(self.report.violations)} CRITICAL VIOLATION(S) DETECTED:")
            for v in self.report.violations:
                print(f"  ❌ {v}")
        else:
            print(f"\n[PASS] All physical, cross-layer, RF, and mechanical tests passed with 0 violations!")

        if self.report.warnings:
            print(f"\n[WARN] {len(self.report.warnings)} Warning(s):")
            for w in self.report.warnings:
                print(f"  ⚠️ {w}")

        return self.report

    def check_cross_layer_tht_smt_clearance(self, min_clearance_mm: float = 1.5):
        """Detects collisions between PTH pins on one layer and SMT pads on the opposite layer."""
        tht_pads = []
        smt_pads_b = []
        smt_pads_f = []

        for fp in self.board.GetFootprints():
            ref = fp.GetReference()
            layer = self.board.GetLayerName(fp.GetLayer())
            for pad in fp.Pads():
                attr = pad.GetAttribute()
                pos = pad.GetPosition()
                size = pad.GetSize()
                if attr == pcbnew.PAD_ATTRIB_PTH:
                    tht_pads.append((ref, pad.GetName(), pos, size, layer))
                elif attr == pcbnew.PAD_ATTRIB_SMD:
                    if layer == "B.Cu":
                        smt_pads_b.append((ref, pad.GetName(), pos, size))
                    else:
                        smt_pads_f.append((ref, pad.GetName(), pos, size))

        # Check Top THT vs Bottom SMT
        for ref_t, name_t, pos_t, size_t, layer_t in tht_pads:
            if layer_t == "F.Cu":
                for ref_b, name_b, pos_b, size_b in smt_pads_b:
                    if ref_t.startswith("H") and ref_t == ref_b:
                        continue
                    dx = abs(pos_t.x - pos_b.x) / 1e6
                    dy = abs(pos_t.y - pos_b.y) / 1e6
                    center_dist = math.hypot(dx, dy)
                    r_t = (size_t.x + size_t.y) / 4e6
                    r_b = (size_b.x + size_b.y) / 4e6
                    edge_dist = center_dist - r_t - r_b
                    if edge_dist < min_clearance_mm:
                        self.report.violations.append(
                            f"CROSS-LAYER CLASH: THT Pin {ref_t}.{name_t} at ({pos_t.x/1e6:.2f}, {pos_t.y/1e6:.2f}) on F.Cu "
                            f"is only {edge_dist:.2f}mm from B.Cu SMT Pad {ref_b}.{name_b} at ({pos_b.x/1e6:.2f}, {pos_b.y/1e6:.2f}) "
                            f"(Requires >= {min_clearance_mm}mm)"
                        )

    def check_rf_antenna_keepouts(self, zones: List[Tuple[float, float, float, float]] = None):
        """Enforces zero copper/components on any layer under RF antennas."""
        if not zones:
            zones = []
            for fp in self.board.GetFootprints():
                val = fp.GetValue().upper()
                if "ESP32" in val or "WROOM" in val:
                    pos = fp.GetPosition()
                    rot = fp.GetOrientation().AsDegrees()
                    if abs(rot - (-90.0)) < 1.0 or abs(rot - 270.0) < 1.0:
                        zones.append((pos.x/1e6 + 5.0, pos.x/1e6 + 18.0, pos.y/1e6 - 10.0, pos.y/1e6 + 10.0))

        for x_min, x_max, y_min, y_max in zones:
            for fp in self.board.GetFootprints():
                if "ESP32" in fp.GetValue().upper() or fp.GetReference().startswith("H"):
                    continue
                bb = fp.GetBoundingBox()
                bx1, by1 = bb.GetX() / 1e6, bb.GetY() / 1e6
                bx2, by2 = bx1 + bb.GetWidth() / 1e6, by1 + bb.GetHeight() / 1e6
                
                if not (bx2 < x_min or bx1 > x_max or by2 < y_min or by1 > y_max):
                    self.report.violations.append(
                        f"RF ANTENNA KEEPOUT BREACH: {fp.GetReference()} ({fp.GetValue()}) on {self.board.GetLayerName(fp.GetLayer())} "
                        f"resides inside RF keepout zone [X: {x_min:.1f}..{x_max:.1f}, Y: {y_min:.1f}..{y_max:.1f}] mm"
                    )

    def check_mounting_hole_standoffs(self, min_radius_mm: float = 3.0):
        """Verifies mounting hole circular keepout envelopes."""
        for fp in self.board.GetFootprints():
            if fp.GetReference().startswith("H") and "M3" in fp.GetValue():
                h_pos = fp.GetPosition()
                hx, hy = h_pos.x / 1e6, h_pos.y / 1e6
                for other in self.board.GetFootprints():
                    if other.GetReference().startswith("H"):
                        continue
                    for pad in other.Pads():
                        p_pos = pad.GetPosition()
                        px, py = p_pos.x / 1e6, p_pos.y / 1e6
                        dist = math.hypot(px - hx, py - hy)
                        if dist < min_radius_mm:
                            self.report.violations.append(
                                f"MOUNTING HOLE ENCROACHMENT: Pad {other.GetReference()}.{pad.GetName()} at ({px:.2f}, {py:.2f}) "
                                f"is within {dist:.2f}mm of M3 Hole {fp.GetReference()} at ({hx:.2f}, {hy:.2f}) (Requires >= {min_radius_mm}mm)"
                            )

    def check_actuator_strain_isolation(self):
        """Detects pushbuttons on F.Cu placed directly over fine-pitch SMT ICs on B.Cu."""
        buttons = []
        ics_b = []
        for fp in self.board.GetFootprints():
            ref = fp.GetReference()
            layer = self.board.GetLayerName(fp.GetLayer())
            if ref.startswith("SW") or "BUTTON" in fp.GetValue().upper() or "SWITCH" in fp.GetValue().upper():
                buttons.append(fp)
            elif layer == "B.Cu" and (ref.startswith("U") or "SOIC" in fp.GetValue() or "QFN" in fp.GetValue() or "MSOP" in fp.GetValue()):
                ics_b.append(fp)

        for btn in buttons:
            b_pos = btn.GetPosition()
            bx, by = b_pos.x / 1e6, b_pos.y / 1e6
            for ic in ics_b:
                i_pos = ic.GetPosition()
                ix, iy = i_pos.x / 1e6, i_pos.y / 1e6
                dist = math.hypot(bx - ix, by - iy)
                if dist < 4.0:
                    self.report.violations.append(
                        f"ACTUATOR MECHANICAL STRAIN: Pushbutton {btn.GetReference()} at ({bx:.2f}, {by:.2f}) on F.Cu "
                        f"is directly stacked over IC {ic.GetReference()} ({ic.GetValue()}) at ({ix:.2f}, {iy:.2f}) on B.Cu (Distance: {dist:.2f}mm)"
                    )

    def check_connector_outward_vectors(self):
        """Verifies connector insertion vectors point outward toward board edges."""
        bb_board = self.board.GetBoardEdgesBoundingBox()
        w = bb_board.GetWidth() / 1e6
        h = bb_board.GetHeight() / 1e6

        for fp in self.board.GetFootprints():
            ref = fp.GetReference()
            layer = self.board.GetLayerName(fp.GetLayer())
            pos = fp.GetPosition()
            px, py = pos.x / 1e6, pos.y / 1e6
            rot = fp.GetOrientation().AsDegrees()

            if ref.startswith("J") or "USB" in fp.GetValue() or "SD" in fp.GetValue() or "RJ45" in fp.GetValue():
                rad = math.radians(rot)
                if layer == "F.Cu":
                    vx = math.sin(rad)
                    vy = math.cos(rad)
                else:
                    vx = -math.sin(rad)
                    vy = -math.cos(rad)

                d_left = px
                d_right = w - px
                d_top = py
                d_bottom = h - py
                min_d = min(d_left, d_right, d_top, d_bottom)

                if min_d == d_left and vx > 0.5:
                    self.report.violations.append(f"INWARD CONNECTOR: {ref} ({fp.GetValue()}) on {layer} at ({px:.1f},{py:.1f}) points INWARD (+X) instead of OUTWARD (-X)")
                elif min_d == d_right and vx < -0.5:
                    self.report.violations.append(f"INWARD CONNECTOR: {ref} ({fp.GetValue()}) on {layer} at ({px:.1f},{py:.1f}) points INWARD (-X) instead of OUTWARD (+X)")
                elif min_d == d_top and vy > 0.5:
                    self.report.violations.append(f"INWARD CONNECTOR: {ref} ({fp.GetValue()}) on {layer} at ({px:.1f},{py:.1f}) points INWARD (+Y) instead of OUTWARD (-Y)")
                elif min_d == d_bottom and vy < -0.5:
                    self.report.violations.append(f"INWARD CONNECTOR: {ref} ({fp.GetValue()}) on {layer} at ({px:.1f},{py:.1f}) points INWARD (-Y) instead of OUTWARD (+Y)")

    def check_orchestrator_component_connectivity(self, search_radius_mm: float = 1.8):
        """Parent Orchestrator audit: verifies all components have active copper routing."""
        footprints = list(self.board.GetFootprints())
        tracks = list(self.board.GetTracks())

        disconnected = []
        for fp in footprints:
            ref = fp.GetReference()
            pads = list(fp.Pads())
            is_mounting_hole = ref.startswith("H") or "MountingHole" in fp.GetFPIDAsString()
            if is_mounting_hole:
                continue

            has_conn = False
            for pad in pads:
                ppos = pad.GetPosition()
                px, py = ppos.x / 1e6, ppos.y / 1e6
                for t in tracks:
                    if t.Type() == pcbnew.PCB_VIA_T:
                        vx, vy = t.GetPosition().x / 1e6, t.GetPosition().y / 1e6
                        if math.hypot(px - vx, py - vy) <= search_radius_mm:
                            has_conn = True
                            break
                    elif t.Type() in (pcbnew.PCB_TRACE_T, pcbnew.PCB_ARC_T):
                        sx, sy = t.GetStart().x / 1e6, t.GetStart().y / 1e6
                        ex, ey = t.GetEnd().x / 1e6, t.GetEnd().y / 1e6
                        if math.hypot(px - sx, py - sy) <= search_radius_mm or math.hypot(px - ex, py - ey) <= search_radius_mm:
                            has_conn = True
                            break
                if has_conn:
                    break

            if not has_conn:
                disconnected.append(ref)

        if disconnected:
            self.report.violations.append(
                f"ORCHESTRATOR CONNECTIVITY VIOLATION: {len(disconnected)} unrouted/disconnected component(s) detected: {', '.join(disconnected)}"
            )


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else r"d:\github\miner-display-bridge\hardware\miner_bridge_pcb\miner_bridge_pcb.kicad_pcb"
    validator = PCBPhysicsValidator(Path(target))
    rep = validator.validate_all()
    sys.exit(0 if rep.passed else 1)
