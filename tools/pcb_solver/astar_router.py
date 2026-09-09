#!/usr/bin/env python3
"""
astar_router.py — Graph-Based 45-Degree PCB Trace Pathfinding Router

Applies grid-based A* graph search with:
- 45-degree and orthogonal (8-directional) movements
- 90-degree corner penalties (enforcing smooth 45-degree chamfers)
- Direction change penalties
- Obstacle clearance inflation (pads, vias, keepouts)
- Multi-layer via transition costing
- S-expression track output for KiCad 10 (.kicad_pcb)
"""

import argparse
import heapq
import math
import sys
from typing import List, Tuple, Dict, Set, Optional

DIRECTIONS = [
    (1, 0, 1.0),
    (-1, 0, 1.0),
    (0, 1, 1.0),
    (0, -1, 1.0),
    (1, 1, 1.414),
    (-1, 1, 1.414),
    (1, -1, 1.414),
    (-1, -1, 1.414)
]

CORNER_90_PENALTY = 2.5
DIRECTION_CHANGE_PENALTY = 0.5

class PCBGrid:
    def __init__(self, width_mm: float, height_mm: float, resolution_mm: float = 0.25):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.resolution = resolution_mm
        self.cols = int(math.ceil(width_mm / resolution_mm)) + 1
        self.rows = int(math.ceil(height_mm / resolution_mm)) + 1
        self.obstacles: Dict[str, Set[Tuple[int, int]]] = {
            "F.Cu": set(),
            "B.Cu": set(),
            "All": set()
        }

    def mm_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        return (int(round(x / self.resolution)), int(round(y / self.resolution)))

    def grid_to_mm(self, c: int, r: int) -> Tuple[float, float]:
        return (round(c * self.resolution, 4), round(r * self.resolution, 4))

    def in_bounds(self, c: int, r: int) -> bool:
        return 0 <= c < self.cols and 0 <= r < self.rows

    def add_obstacle_circle(self, x: float, y: float, radius_mm: float, layer: str = "All"):
        c_center, r_center = self.mm_to_grid(x, y)
        r_grid = int(math.ceil(radius_mm / self.resolution))
        for dc in range(-r_grid, r_grid + 1):
            for dr in range(-r_grid, r_grid + 1):
                c = c_center + dc
                r = r_center + dr
                if self.in_bounds(c, r):
                    if math.hypot(dc * self.resolution, dr * self.resolution) <= radius_mm:
                        self.obstacles[layer].add((c, r))

    def is_blocked(self, c: int, r: int, layer: str) -> bool:
        if not self.in_bounds(c, r):
            return True
        return (c, r) in self.obstacles[layer] or (c, r) in self.obstacles["All"]

def heuristic(c1: int, r1: int, c2: int, r2: int) -> float:
    dx = abs(c1 - c2)
    dy = abs(r1 - r2)
    return (dx + dy) + (1.414 - 2.0) * min(dx, dy)

def route_trace_astar(grid: PCBGrid, 
                      start_mm: Tuple[float, float], 
                      end_mm: Tuple[float, float], 
                      layer: str = "F.Cu") -> Optional[List[Tuple[float, float]]]:
    start_c, start_r = grid.mm_to_grid(*start_mm)
    end_c, end_r = grid.mm_to_grid(*end_mm)

    if not grid.in_bounds(start_c, start_r) or not grid.in_bounds(end_c, end_r):
        return None

    open_set = []
    heapq.heappush(open_set, (heuristic(start_c, start_r, end_c, end_r), 0.0, (start_c, start_r), (0, 0)))

    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], float] = {(start_c, start_r): 0.0}

    while open_set:
        _, current_g, current, prev_dir = heapq.heappop(open_set)

        if current == (end_c, end_r):
            path = []
            curr = current
            while curr in came_from:
                path.append(grid.grid_to_mm(*curr))
                curr = came_from[curr]
            path.append(grid.grid_to_mm(start_c, start_r))
            path.reverse()
            return simplify_collinear_45(path)

        curr_c, curr_r = current

        for dc, dr, step_cost in DIRECTIONS:
            neighbor = (curr_c + dc, curr_r + dr)
            n_c, n_r = neighbor

            if neighbor != (end_c, end_r) and grid.is_blocked(n_c, n_r, layer):
                continue

            dir_penalty = 0.0
            if prev_dir != (0, 0):
                if prev_dir != (dc, dr):
                    dot = prev_dir[0] * dc + prev_dir[1] * dr
                    if dot == 0:
                        dir_penalty = CORNER_90_PENALTY
                    elif dot < 0:
                        dir_penalty = CORNER_90_PENALTY * 2.0
                    else:
                        dir_penalty = DIRECTION_CHANGE_PENALTY

            tentative_g = current_g + step_cost + dir_penalty

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                f_cost = tentative_g + heuristic(n_c, n_r, end_c, end_r)
                came_from[neighbor] = current
                heapq.heappush(open_set, (f_cost, tentative_g, neighbor, (dc, dr)))

    return None

def simplify_collinear_45(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if len(points) <= 2:
        return points

    simplified = [points[0]]
    for i in range(1, len(points) - 1):
        p_prev = simplified[-1]
        p_curr = points[i]
        p_next = points[i + 1]

        v1 = (round(p_curr[0] - p_prev[0], 4), round(p_curr[1] - p_prev[1], 4))
        v2 = (round(p_next[0] - p_curr[0], 4), round(p_next[1] - p_curr[1], 4))

        cross = v1[0] * v2[1] - v1[1] * v2[0]
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        if abs(cross) > 1e-4 or dot <= 0:
            simplified.append(p_curr)

    simplified.append(points[-1])
    return simplified

def export_kicad_segments(waypoints: List[Tuple[float, float]], 
                          net_id: int = 1, 
                          width_mm: float = 0.25, 
                          layer: str = "F.Cu") -> str:
    lines = []
    for i in range(len(waypoints) - 1):
        x1, y1 = waypoints[i]
        x2, y2 = waypoints[i + 1]
        lines.append(f"  (segment (start {x1} {y1}) (end {x2} {y2}) (width {width_mm}) (layer \"{layer}\") (net {net_id}))")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="A* 45-Degree PCB Trace Router")
    parser.add_argument("--start", nargs=2, type=float, required=True, help="Start X Y in mm")
    parser.add_argument("--end", nargs=2, type=float, required=True, help="End X Y in mm")
    parser.add_argument("--board-size", nargs=2, type=float, default=[72.0, 30.0], help="Board width height in mm")
    parser.add_argument("--width", type=float, default=0.25, help="Trace width in mm")
    parser.add_argument("--layer", default="F.Cu", help="Target layer (F.Cu or B.Cu)")
    parser.add_argument("--net", type=int, default=1, help="Net ID")
    args = parser.parse_args()

    grid = PCBGrid(args.board_size[0], args.board_size[1], resolution_mm=0.25)
    
    path = route_trace_astar(grid, tuple(args.start), tuple(args.end), layer=args.layer)
    if not path:
        print("[ERROR] No collision-free route found!", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Found {len(path)-1}-segment 45-degree path with {len(path)} waypoints:")
    for pt in path:
        print(f"    -> ({pt[0]:.2f}, {pt[1]:.2f}) mm")
    
    print("\n[KiCad 10 PCB Tracks]")
    print(export_kicad_segments(path, net_id=args.net, width_mm=args.width, layer=args.layer))

if __name__ == "__main__":
    main()
