#!/usr/bin/env python3
"""
search_jlcpcb.py — Fast Local Search for JLCPCB / LCSC Turnkey Parts Database

Queries the local SQLite FTS5 database indexed from JLCPCB's component library.
"""

import argparse
import os
import sqlite3
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def find_db():
    """Locate jlcpcb_parts.db database file."""
    candidates = [
        os.path.expanduser("~/.kicad-mcp/data/jlcpcb_parts.db"),
        os.path.join(os.environ.get("USERPROFILE", ""), ".kicad-mcp", "data", "jlcpcb_parts.db"),
        "./jlcpcb_parts.db",
        "../data/jlcpcb_parts.db"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def search_parts(query, package=None, basic_only=False, min_stock=100, limit=20):
    db_path = find_db()
    if not db_path:
        print("[ERROR] JLCPCB parts database not found.", file=sys.stderr)
        print("Expected location: ~/.kicad-mcp/data/jlcpcb_parts.db", file=sys.stderr)
        print("Download and index with: python -m kicad_mcp.jlcpcb_db download", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    conditions = ["stock >= ?"]
    params = [min_stock]

    if basic_only:
        conditions.append("library_type = 'Basic'")

    if package:
        conditions.append("package LIKE ?")
        params.append(f"%{package}%")

    if query:
        conditions.append("(mfr_part LIKE ? OR description LIKE ? OR manufacturer LIKE ? OR category LIKE ?)")
        q_wildcard = f"%{query}%"
        params.extend([q_wildcard, q_wildcard, q_wildcard, q_wildcard])

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT lcsc, mfr_part, manufacturer, package, library_type, stock, description
        FROM components
        WHERE {where_clause}
        ORDER BY stock DESC
        LIMIT ?
    """
    params.append(limit)

    cur.execute(sql, params)
    rows = cur.fetchall()

    if not rows:
        print(f"[*] No components found matching: '{query}' (min_stock: {min_stock})")
        return

    print(f"\n[*] Found {len(rows)} parts in JLCPCB catalog:\n")
    header = f"{'LCSC #':<10} {'Part Number':<22} {'Manufacturer':<16} {'Package':<14} {'Type':<8} {'Stock':<10} {'Description'}"
    print(header)
    print("-" * len(header))

    for r in rows:
        lcsc, part_num, mfr, pkg, lib_type, stock, desc = r
        desc_short = (desc[:45] + '...') if desc and len(desc) > 48 else (desc or "")
        print(f"{lcsc:<10} {part_num[:20]:<22} {mfr[:14]:<16} {pkg[:12]:<14} {lib_type:<8} {stock:<10} {desc_short}")


def main():
    parser = argparse.ArgumentParser(description="Fast local JLCPCB / LCSC parts database search")
    parser.add_argument("query", nargs="?", default="", help="Search query (e.g. 'TVS 15V', 'XT60', 'buck 5V')")
    parser.add_argument("-p", "--package", help="Filter by footprint package (e.g. '0805', 'SMC', 'QFN')")
    parser.add_argument("-b", "--basic", action="store_true", help="Filter by Basic parts only (no reel fee)")
    parser.add_argument("-s", "--min-stock", type=int, default=10, help="Minimum in-stock quantity (default: 10)")
    parser.add_argument("-l", "--limit", type=int, default=25, help="Maximum results to return (default: 25)")

    args = parser.parse_args()
    search_parts(args.query, args.package, args.basic, args.min_stock, args.limit)


if __name__ == "__main__":
    main()
