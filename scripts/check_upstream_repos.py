#!/usr/bin/env python3
"""
check_upstream_repos.py — Automated Upstream Repository Watcher & Change Detector

Pings tracked upstream hardware/AI repositories (e.g. DingoOz/TraceMaker, KiCad MCPs),
detects new commits, releases, and architectural changes, and generates a structured
digest for AI agent review and integration.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional

# Tracked upstream repositories
DEFAULT_WATCHLIST = [
    {
        "name": "TraceMaker",
        "repo": "DingoOz/TraceMaker",
        "branch": "main",
        "description": "C++20/CUDA native KiCad placement and autorouting engine"
    },
    {
        "name": "KiCad-MCP-Server",
        "repo": "mixelpixx/KiCAD-MCP-Server",
        "branch": "main",
        "description": "KiCad MCP server with JLCPCB SQLite catalog search"
    },
    {
        "name": "kicad-happy",
        "repo": "aklofas/kicad-happy",
        "branch": "master",
        "description": "KiCad schematic power-tree analysis and EMC pre-compliance rules"
    },
    {
        "name": "kicad-mcp",
        "repo": "lamaalrajih/kicad-mcp",
        "branch": "main",
        "description": "Cross-platform Model Context Protocol server for KiCad"
    }
]

STATE_FILE = Path(__file__).resolve().parent.parent / ".upstream_state.json"


def load_state() -> Dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: Dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save upstream state: {e}", file=sys.stderr)


def fetch_github_commits(repo: str, branch: str = "main", per_page: int = 5) -> List[Dict]:
    """Fetches recent commits from GitHub public API without requiring an auth token."""
    url = f"https://api.github.com/repos/{repo}/commits?sha={branch}&per_page={per_page}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KiCad-Skills-Upstream-Watcher/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                commits = []
                for item in data:
                    commits.append({
                        "sha": item.get("sha", "")[:8],
                        "full_sha": item.get("sha", ""),
                        "message": item.get("commit", {}).get("message", "").split("\n")[0],
                        "author": item.get("commit", {}).get("author", {}).get("name", ""),
                        "date": item.get("commit", {}).get("author", {}).get("date", ""),
                        "url": item.get("html_url", "")
                    })
                return commits
    except urllib.error.HTTPError as e:
        # Fallback for rate limits or non-existent branches
        return [{"error": f"HTTP {e.code}: {e.reason}"}]
    except Exception as e:
        return [{"error": str(e)}]
    return []


def check_updates(update_state: bool = True) -> Dict:
    state = load_state()
    report = {
        "timestamp": "",
        "has_new_updates": False,
        "repositories": {}
    }

    for item in DEFAULT_WATCHLIST:
        repo = item["repo"]
        name = item["name"]
        branch = item.get("branch", "main")
        last_known_sha = state.get(repo, {}).get("last_sha")

        commits = fetch_github_commits(repo, branch=branch)
        if not commits or "error" in commits[0]:
            # Retry with master branch if main failed with 404
            if "error" in commits[0] and "404" in commits[0]["error"] and branch == "main":
                commits = fetch_github_commits(repo, branch="master")
                branch = "master"

        if commits and "error" not in commits[0]:
            latest_sha = commits[0]["full_sha"]
            is_new = (last_known_sha is not None) and (latest_sha != last_known_sha)
            is_initial = (last_known_sha is None)

            new_commits = []
            if is_new:
                report["has_new_updates"] = True
                for c in commits:
                    if c["full_sha"] == last_known_sha:
                        break
                    new_commits.append(c)

            report["repositories"][name] = {
                "repo": repo,
                "branch": branch,
                "latest_sha": commits[0]["sha"],
                "latest_date": commits[0]["date"],
                "latest_message": commits[0]["message"],
                "new_commits_count": len(new_commits) if is_new else (0 if not is_initial else 1),
                "new_commits": new_commits if is_new else [commits[0]],
                "is_new": is_new,
                "is_initial": is_initial
            }

            if update_state:
                state[repo] = {
                    "last_sha": latest_sha,
                    "last_date": commits[0]["date"],
                    "last_message": commits[0]["message"]
                }
        else:
            report["repositories"][name] = {
                "repo": repo,
                "error": commits[0].get("error") if commits else "Unknown fetch error"
            }

    if update_state:
        save_state(state)

    return report


def main():
    parser = argparse.ArgumentParser(description="Check for updates in upstream hardware/AI repositories")
    parser.add_argument("--no-update-state", action="store_true", help="Do not persist latest SHA to state file")
    parser.add_argument("--json", action="store_true", help="Print JSON report")

    args = parser.parse_args()
    report = check_updates(update_state=not args.no_update_state)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n" + "=" * 65)
        print("  Upstream Repository Watcher Report")
        print("=" * 65)
        for name, data in report["repositories"].items():
            if "error" in data:
                print(f"  [-] {name} ({data['repo']}): {data['error']}")
            else:
                status = "[NEW COMMITS]" if data.get("is_new") else ("[INITIAL SYNC]" if data.get("is_initial") else "[UP TO DATE]")
                print(f"  {status} {name} ({data['repo']} @ {data['branch']})")
                print(f"      Latest: {data['latest_sha']} - {data['latest_message']} ({data['latest_date'][:10]})")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
