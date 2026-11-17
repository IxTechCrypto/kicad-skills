#!/usr/bin/env python3
"""
check_upstream_repos.py — Automated Upstream Repository Watcher & Change Detector

Pings tracked upstream hardware/AI repositories and tools:
- aklofas/kicad-happy (schematic power-tree analysis, EMC rules)
- mixelpixx/KiCAD-MCP-Server (KiCad MCP server with JLCPCB SQLite catalog search)
- parisxmas/fastroute (Rust Specctra autorouter binary & releases)
- DingoOz/TraceMaker (C++20/CUDA KiCad autorouter)
- lamaalrajih/kicad-mcp (cross-platform KiCad MCP)

Detects new commits, releases, and architectural changes, compares against
local working repositories / installed binaries, and writes an audit log.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional

# Tracked upstream repositories and local paths
DEFAULT_WATCHLIST = [
    {
        "name": "kicad-happy",
        "repo": "aklofas/kicad-happy",
        "branch": "main",
        "local_path": r"D:\github\kicad-happy",
        "type": "git",
        "description": "KiCad schematic power-tree analysis and EMC pre-compliance rules"
    },
    {
        "name": "KiCad-MCP-Server",
        "repo": "mixelpixx/KiCAD-MCP-Server",
        "branch": "main",
        "local_path": r"D:\github\KiCAD-MCP-Server",
        "type": "git",
        "description": "KiCad MCP server with JLCPCB SQLite catalog search"
    },
    {
        "name": "fastroute",
        "repo": "parisxmas/fastroute",
        "branch": "master",
        "type": "release",
        "binary_name": "fastroute",
        "description": "High-performance Rust Specctra DSN/SES autorouter"
    },
    {
        "name": "TraceMaker",
        "repo": "DingoOz/TraceMaker",
        "branch": "main",
        "type": "git",
        "description": "C++20/CUDA native KiCad placement and autorouting engine"
    },
    {
        "name": "kicad-mcp",
        "repo": "lamaalrajih/kicad-mcp",
        "branch": "main",
        "type": "git",
        "description": "Cross-platform Model Context Protocol server for KiCad"
    }
]

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / ".upstream_state.json"
AUDIT_LOG_FILE = REPO_ROOT / "upstream_audit.log"


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


def get_installed_binary_version(bin_name: str) -> Optional[str]:
    """Retrieves installed binary version string via --version."""
    cmd = shutil.which(bin_name)
    if not cmd:
        # Check standard candidate paths
        candidates = [
            Path(r"D:\tools\fastroute\fastroute.exe"),
            Path(os.path.expanduser("~/.cargo/bin/fastroute.exe")),
            Path(os.path.expandvars(r"%APPDATA%\kicad\10.0\scripting\plugins\fastroute\bin\windows-x64\fastroute.exe"))
        ]
        for c in candidates:
            if c.exists():
                cmd = str(c)
                break
    if not cmd:
        return None

    try:
        res = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
        out = (res.stdout or res.stderr).strip()
        # e.g., "fastroute 0.1.14" -> "0.1.14"
        parts = out.split()
        if len(parts) >= 2:
            return parts[-1]
        return out
    except Exception:
        return None


def get_local_git_status(local_path: str) -> Optional[Dict]:
    """Checks git commit status of local repository clone."""
    p = Path(local_path)
    if not p.exists() or not (p / ".git").exists():
        return None

    try:
        # Get current branch
        res_br = subprocess.run(["git", "-C", str(p), "branch", "--show-current"], capture_output=True, text=True, timeout=5)
        branch = res_br.stdout.strip() or "HEAD"

        # Get current commit SHA
        res_sha = subprocess.run(["git", "-C", str(p), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5)
        current_sha = res_sha.stdout.strip()

        # Get latest commit date & subject
        res_log = subprocess.run(["git", "-C", str(p), "log", "-1", "--format=%cd|%s", "--date=short"], capture_output=True, text=True, timeout=5)
        log_parts = res_log.stdout.strip().split("|", 1)
        commit_date = log_parts[0] if len(log_parts) > 0 else ""
        commit_msg = log_parts[1] if len(log_parts) > 1 else ""

        return {
            "branch": branch,
            "sha": current_sha,
            "date": commit_date,
            "message": commit_msg
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_github_release(repo: str) -> Optional[Dict]:
    """Fetches latest release info from GitHub API."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
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
                tag = data.get("tag_name", "").lstrip("v")
                return {
                    "tag_name": data.get("tag_name", ""),
                    "version": tag,
                    "name": data.get("name", ""),
                    "published_at": data.get("published_at", "")[:10],
                    "html_url": data.get("html_url", ""),
                    "prerelease": data.get("prerelease", False)
                }
    except Exception:
        pass
    return None


def fetch_github_commits(repo: str, branch: str = "main", per_page: int = 5) -> List[Dict]:
    """Fetches recent commits from GitHub public API."""
    branches_to_try = [branch]
    if branch == "main":
        branches_to_try.append("master")
    elif branch == "master":
        branches_to_try.append("main")

    last_error = None
    for try_branch in branches_to_try:
        url = f"https://api.github.com/repos/{repo}/commits?sha={try_branch}&per_page={per_page}"
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
                            "branch": try_branch,
                            "message": item.get("commit", {}).get("message", "").split("\n")[0],
                            "author": item.get("commit", {}).get("author", {}).get("name", ""),
                            "date": item.get("commit", {}).get("author", {}).get("date", ""),
                            "url": item.get("html_url", "")
                        })
                    return commits
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            last_error = str(e)

    return [{"error": last_error or "Failed to fetch commits"}]


def check_updates(update_state: bool = True) -> Dict:
    state = load_state()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = {
        "timestamp": now_iso,
        "has_new_updates": False,
        "repositories": {}
    }

    for item in DEFAULT_WATCHLIST:
        repo = item["repo"]
        name = item["name"]
        preferred_branch = item.get("branch", "main")
        item_type = item.get("type", "git")
        local_path = item.get("local_path")
        last_known = state.get(repo, {})

        repo_report = {
            "name": name,
            "repo": repo,
            "type": item_type,
            "is_new": False,
            "is_up_to_date": True
        }

        # Check local repo status if present
        if local_path:
            local_stat = get_local_git_status(local_path)
            repo_report["local"] = local_stat

        # For release-type tools (e.g. fastroute), check release version
        if item_type == "release" or item.get("binary_name"):
            installed_ver = get_installed_binary_version(item.get("binary_name", name))
            repo_report["installed_version"] = installed_ver
            rel = fetch_github_release(repo)
            if rel:
                repo_report["latest_release"] = rel
                if installed_ver and rel["version"]:
                    is_newer_release = (rel["version"] != installed_ver)
                    repo_report["release_update_available"] = is_newer_release
                    if is_newer_release:
                        report["has_new_updates"] = True
                        repo_report["is_new"] = True
                        repo_report["is_up_to_date"] = False

        # Check git commits
        commits = fetch_github_commits(repo, branch=preferred_branch)
        if commits and "error" not in commits[0]:
            active_branch = commits[0].get("branch", preferred_branch)
            latest_sha = commits[0]["full_sha"]
            last_sha = last_known.get("last_sha")
            is_new = (last_sha is not None) and (latest_sha != last_sha)
            is_initial = (last_sha is None)

            new_commits = []
            if is_new:
                report["has_new_updates"] = True
                repo_report["is_new"] = True
                repo_report["is_up_to_date"] = False
                for c in commits:
                    if c["full_sha"] == last_sha:
                        break
                    new_commits.append(c)

            repo_report.update({
                "branch": active_branch,
                "latest_sha": commits[0]["sha"],
                "latest_date": commits[0]["date"][:10],
                "latest_message": commits[0]["message"],
                "new_commits_count": len(new_commits) if is_new else (0 if not is_initial else 1),
                "is_initial": is_initial
            })

            # Check local vs upstream drift
            if repo_report.get("local") and "sha" in repo_report["local"]:
                local_sha = repo_report["local"]["sha"]
                if not latest_sha.startswith(local_sha):
                    repo_report["local_drift"] = True
                    repo_report["is_up_to_date"] = False

            if update_state:
                state[repo] = {
                    "last_sha": latest_sha,
                    "last_date": commits[0]["date"],
                    "last_message": commits[0]["message"]
                }
                if repo_report.get("latest_release"):
                    state[repo]["latest_release"] = repo_report["latest_release"]["version"]
        else:
            repo_report["error"] = commits[0].get("error") if commits else "Unknown fetch error"

        report["repositories"][name] = repo_report

    if update_state:
        save_state(state)

    # Append to audit log
    append_to_audit_log(report)

    return report


def append_to_audit_log(report: Dict):
    """Appends audit summary to upstream_audit.log."""
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"--- Upstream Audit Run: {report['timestamp']} ---\n")
            for name, data in report["repositories"].items():
                if "error" in data:
                    f.write(f"  [-] {name}: ERROR ({data['error']})\n")
                else:
                    sha_str = data.get("latest_sha", "N/A")
                    date_str = data.get("latest_date", "N/A")
                    msg = data.get("latest_message", "")
                    ver = data.get("latest_release", {}).get("version", "")
                    inst_ver = data.get("installed_version", "")
                    status = "[UPDATE AVAILABLE]" if data.get("is_new") or data.get("local_drift") else "[UP TO DATE]"
                    
                    extra = []
                    if ver:
                        extra.append(f"upstream v{ver}")
                    if inst_ver:
                        extra.append(f"installed v{inst_ver}")
                    if data.get("local_drift"):
                        extra.append("local repo behind upstream")
                    extra_str = f" ({', '.join(extra)})" if extra else ""

                    f.write(f"  {status} {name}: {sha_str} {date_str} \"{msg}\"{extra_str}\n")
            f.write("\n")
    except Exception as e:
        print(f"[WARN] Failed to write audit log: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Check for updates in upstream hardware/AI repositories and tools")
    parser.add_argument("--no-update-state", action="store_true", help="Do not persist latest state to file")
    parser.add_argument("--json", action="store_true", help="Print raw JSON report")

    args = parser.parse_args()
    report = check_updates(update_state=not args.no_update_state)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n" + "=" * 70)
        print("  Upstream Hardware & AI Repository Watcher Report")
        print(f"  Timestamp: {report['timestamp']}")
        print("=" * 70)
        for name, data in report["repositories"].items():
            if "error" in data:
                print(f"  [-] {name} ({data['repo']}): {data['error']}")
            else:
                status = "[NEW COMMITS]" if data.get("is_new") else ("[UP TO DATE]" if data.get("is_up_to_date") else "[UPDATE AVAILABLE]")
                br = data.get("branch", "")
                sha = data.get("latest_sha", "")
                msg = data.get("latest_message", "")
                dt = data.get("latest_date", "")
                
                print(f"  {status} {name} ({data['repo']} @ {br})")
                print(f"      Upstream: {sha} - {msg} ({dt})")
                
                if data.get("installed_version") or data.get("latest_release"):
                    inst = data.get("installed_version", "None")
                    rel = data.get("latest_release", {}).get("version", "N/A")
                    print(f"      Release:  Installed: v{inst} | Upstream Latest: v{rel}")
                
                if data.get("local"):
                    loc = data["local"]
                    print(f"      Local:    {loc.get('sha', 'N/A')} ({loc.get('branch', '')}) - {loc.get('message', '')}")
                    if data.get("local_drift"):
                        print(f"      [!] Local copy in {DEFAULT_WATCHLIST[0].get('local_path', '')} has unpulled changes.")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
