#!/usr/bin/env python3
"""
install.py — Cross-Platform Installer for KiCad AI Agent Skills

Installs KiCad 10 hardware engineering skills into Claude Code, Google Antigravity,
or project-local workspace directories.
"""

import argparse
import os
import shutil
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def get_available_skills(base_dir):
    skills_dir = os.path.join(base_dir, "skills")
    if not os.path.exists(skills_dir):
        return []
    return [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d)) and not d.startswith(".")]


def link_or_copy(src, dst):
    """Safely create directory symlink/junction, or fallback to standalone copy."""
    # Attempt symlink/junction if supported
    linked = False
    try:
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(os.path.abspath(src), os.path.abspath(dst))
            linked = True
        else:
            os.symlink(os.path.abspath(src), os.path.abspath(dst), target_is_directory=True)
            linked = True
    except Exception:
        pass

    if linked:
        print(f"    [LINKED] {dst} -> {src}")
        return True

    # Robust fallback: standalone directory copy
    try:
        shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"    [COPIED] {dst} (standalone copy)")
        return True
    except Exception as e:
        print(f"    [ERROR] Failed to install to {dst}: {e}", file=sys.stderr)
        return False


def install_skills(targets):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = os.path.join(base_dir, "skills")
    skills = get_available_skills(base_dir)

    for target in targets:
        print(f"\n[*] Installing skills to: {target}")
        os.makedirs(target, exist_ok=True)
        for skill in skills:
            src = os.path.join(skills_dir, skill)
            dst = os.path.join(target, skill)
            if not os.path.exists(src):
                print(f"[WARN] Skill source directory not found: {src}")
                continue
            link_or_copy(src, dst)


def main():
    home = os.path.expanduser("~")
    claude_skills = os.path.join(home, ".claude", "skills")
    antigravity_skills = os.path.join(home, ".gemini", "config", "skills")

    parser = argparse.ArgumentParser(description="Install KiCad AI Agent Skills")
    parser.add_argument("--claude", action="store_true", help=f"Install to Claude Code ({claude_skills})")
    parser.add_argument("--antigravity", action="store_true", help=f"Install to Google Antigravity ({antigravity_skills})")
    parser.add_argument("--all", action="store_true", help="Install to both Claude Code and Antigravity")
    parser.add_argument("--dest", help="Custom destination directory (e.g. ./my-repo/.agents/skills)")

    args = parser.parse_args()

    targets = []
    if args.all or (not args.claude and not args.antigravity and not args.dest):
        targets.extend([claude_skills, antigravity_skills])
    else:
        if args.claude:
            targets.append(claude_skills)
        if args.antigravity:
            targets.append(antigravity_skills)
        if args.dest:
            targets.append(os.path.abspath(args.dest))

    install_skills(targets)
    print("\n[SUCCESS] KiCad skills installation complete!\n")


if __name__ == "__main__":
    main()
