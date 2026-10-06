#!/usr/bin/env python3
"""
install.py — Cross-Platform Installer & Health Checker for KiCad AI Agent Skills

Installs KiCad 10 hardware engineering skills into Claude Code, Google Antigravity,
or project-local workspace directories, and performs automated toolchain audits.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check_environment():
    """Performs a comprehensive toolchain audit across macOS, Linux, and Windows."""
    print("=" * 60)
    print("  KiCad AI Skills Toolchain Health Check")
    print("=" * 60)

    # 1. Check kicad-cli
    kicad_cli = shutil.which("kicad-cli")
    if not kicad_cli:
        candidates = [
            "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
            r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
            "/usr/bin/kicad-cli",
        ]
        for c in candidates:
            if os.path.exists(c):
                kicad_cli = c
                break

    if kicad_cli:
        print(f"  [✓] KiCad CLI:     Found ({kicad_cli})")
    else:
        print("  [!] KiCad CLI:     Not found (Headless ERC/DRC gates will be limited)")

    # 2. Check Python pcbnew module
    try:
        import pcbnew
        print(f"  [✓] Python pcbnew: Available (KiCad {getattr(pcbnew, 'GetBuildVersion', lambda: 'Unknown')()})")
    except ImportError:
        print("  [!] Python pcbnew: Not found in current Python environment (CLI fallback active)")

    # 3. Check TraceMaker
    try:
        from tools.pcb_solver.tracemaker_bridge import find_tracemaker_binary
        tm_bin, tm_mode = find_tracemaker_binary()
        if tm_mode != "none":
            print(f"  [✓] TraceMaker:    Found ({tm_bin} - Mode: {tm_mode})")
        else:
            print("  [i] TraceMaker:    Not installed (Fallback to FreeRouting / Python A* active)")
    except Exception:
        print("  [i] TraceMaker:    Module check skipped")

    # 4. Check FreeRouting & Java
    java_bin = shutil.which("java")
    repo_root = Path(__file__).resolve().parent
    fr_candidates = [
        repo_root / "scripts" / "freerouting.jar",
        repo_root / "tools" / "bin" / "freerouting.jar",
        Path.home() / ".local" / "bin" / "freerouting.jar",
    ]
    fr_jar = next((str(c) for c in fr_candidates if c.exists()), None)

    if java_bin and fr_jar:
        print(f"  [✓] FreeRouting:   Found ({fr_jar})")
    elif java_bin:
        print("  [i] FreeRouting:   Java present, freerouting.jar not yet downloaded")
    else:
        print("  [i] FreeRouting:   Java runtime not detected")

    print("=" * 60)


def get_available_skills(base_dir):
    skills_dir = os.path.join(base_dir, "skills")
    if not os.path.exists(skills_dir):
        return []
    return [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d)) and not d.startswith(".")]


def link_or_copy(src, dst):
    """Safely create directory symlink/junction, or fallback to file-by-file update."""
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)

    # 1. If destination is already a symlink/junction
    if os.path.islink(dst):
        try:
            target = os.path.realpath(dst)
            if target == src:
                print(f"    [UP-TO-DATE LINK] {dst}")
                return True
        except Exception:
            pass

    # 2. Try creating directory symlink or Windows junction if dst doesn't exist
    if not os.path.exists(dst):
        linked = False
        try:
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(src, dst)
                linked = True
            else:
                os.symlink(src, dst, target_is_directory=True)
                linked = True
        except Exception:
            pass

        if linked:
            print(f"    [LINKED] {dst} -> {src}")
            return True

    # 3. Synchronize file by file to avoid whole-folder lock issues
    try:
        os.makedirs(dst, exist_ok=True)
        updated_count = 0
        for root, dirs, files in os.walk(src):
            rel_path = os.path.relpath(root, src)
            target_root = os.path.join(dst, rel_path) if rel_path != "." else dst
            os.makedirs(target_root, exist_ok=True)

            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_root, file)
                
                # Check if file needs update
                needs_copy = True
                if os.path.exists(dst_file):
                    try:
                        if os.path.getsize(src_file) == os.path.getsize(dst_file):
                            with open(src_file, "rb") as f1, open(dst_file, "rb") as f2:
                                if f1.read() == f2.read():
                                    needs_copy = False
                    except Exception:
                        needs_copy = True

                if needs_copy:
                    try:
                        shutil.copy2(src_file, dst_file)
                        updated_count += 1
                    except PermissionError:
                        pass # In use by active IDE session
        
        if updated_count > 0:
            print(f"    [UPDATED] {dst} ({updated_count} files changed)")
        else:
            print(f"    [UP-TO-DATE] {dst}")
        return True
    except Exception as e:
        print(f"    [ERROR] Failed to sync to {dst}: {e}", file=sys.stderr)
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
    parser.add_argument("--check-only", action="store_true", help="Run toolchain health check only")

    args = parser.parse_args()

    check_environment()

    if args.check_only:
        return

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
