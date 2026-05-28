#!/usr/bin/env python3
"""Back up matching docker volumes to dated tar.gz files.

Stdlib only - no pip installs. Confirmation by default (curses multi-select);
-y bypasses; --dry-run lists and exits.
"""

from __future__ import annotations

import argparse
import curses
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path


def list_docker_volumes() -> list[str]:
    out = subprocess.run(
        ["docker", "volume", "ls", "--format", "{{.Name}}"],
        check=True, capture_output=True, text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def match_patterns(volumes: list[str], patterns: list[str]) -> list[str]:
    """Union of matches across patterns. Warn on patterns matching nothing."""
    compiled = [(p, re.compile(p)) for p in patterns]
    seen: set[str] = set()
    matched: list[str] = []
    for v in volumes:
        if any(rx.search(v) for _, rx in compiled):
            if v not in seen:
                seen.add(v)
                matched.append(v)
    for p, rx in compiled:
        if not any(rx.search(v) for v in volumes):
            print(f"WARNING: pattern matched nothing: {p}", file=sys.stderr)
    return matched


def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def estimate_volume_bytes(volume: str) -> int | None:
    """One-shot `du -sb` inside an alpine container. None on failure."""
    try:
        r = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{volume}:/data:ro",
             "alpine", "du", "-sb", "/data"],
            check=True, capture_output=True, text=True, timeout=60,
        )
        return int(r.stdout.split()[0])
    except Exception:
        return None


def curses_pick(
    volumes: list[str], dest: Path, *, preselected: bool = True
) -> list[str] | None:
    """Interactive multi-select. Returns chosen list or None on quit."""
    selected = [preselected] * len(volumes)

    def run(stdscr) -> list[str] | None:
        curses.curs_set(0)
        stdscr.keypad(True)
        cursor = 0
        top = 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            list_h = max(1, h - 5)
            header1 = f"docker_volume_backupper.py - select volumes to back up ({len(volumes)} matched)"
            header2 = "  UP/DOWN move   SPACE toggle   a all   n none   ENTER confirm   q quit"
            stdscr.addnstr(0, 0, header1, w - 1)
            stdscr.addnstr(1, 0, header2, w - 1)
            if cursor < top:
                top = cursor
            elif cursor >= top + list_h:
                top = cursor - list_h + 1
            for row in range(list_h):
                idx = top + row
                if idx >= len(volumes):
                    break
                mark = "x" if selected[idx] else " "
                arrow = ">" if idx == cursor else " "
                line = f"{arrow} [{mark}] {volumes[idx]}"
                attr = curses.A_REVERSE if idx == cursor else curses.A_NORMAL
                stdscr.addnstr(3 + row, 0, line, w - 1, attr)
            footer = f"  {sum(selected)}/{len(volumes)} selected   dest: {dest}"
            stdscr.addnstr(h - 1, 0, footer, w - 1)
            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (curses.KEY_UP, ord("k")):
                cursor = max(0, cursor - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                cursor = min(len(volumes) - 1, cursor + 1)
            elif ch == curses.KEY_PPAGE:
                cursor = max(0, cursor - list_h)
            elif ch == curses.KEY_NPAGE:
                cursor = min(len(volumes) - 1, cursor + list_h)
            elif ch == curses.KEY_HOME:
                cursor = 0
            elif ch == curses.KEY_END:
                cursor = len(volumes) - 1
            elif ch == ord(" "):
                selected[cursor] = not selected[cursor]
            elif ch == ord("a"):
                for i in range(len(selected)):
                    selected[i] = True
            elif ch == ord("n"):
                for i in range(len(selected)):
                    selected[i] = False
            elif ch in (curses.KEY_ENTER, 10, 13):
                return [v for v, s in zip(volumes, selected) if s]
            elif ch in (ord("q"), 27):
                return None

    try:
        return curses.wrapper(run)
    except KeyboardInterrupt:
        return None


def confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def backup_one(
    volume: str, backup_dir: Path, *, show_progress: bool, idx: int, total: int
) -> None:
    """Run one docker tar backup. Aborts the program on failure."""
    today = date.today().isoformat()
    out_name = f"{volume}_{today}.tar.gz"
    out_path = backup_dir / out_name
    cname = f"backup_{int(time.time())}_{os.getpid()}_{idx}"
    prefix = f"[{idx}/{total}] {volume}"

    estimated = estimate_volume_bytes(volume) if show_progress else None

    cmd = [
        "docker", "run", "--rm", "--name", cname,
        "-u", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{volume}:/data:ro",
        "-v", f"{backup_dir}:/backup",
        "alpine", "sh", "-c", f"tar czf /backup/{out_name} -C /data .",
    ]

    start = time.monotonic()
    stop_flag = threading.Event()

    def poll():
        while not stop_flag.is_set():
            try:
                size = out_path.stat().st_size
            except FileNotFoundError:
                size = 0
            if estimated and estimated > 0:
                pct = min(99, int(size * 100 / estimated))
                msg = f"{prefix}   {fmt_bytes(size)} / ~{fmt_bytes(estimated)} ({pct}%)"
            else:
                msg = f"{prefix}   {fmt_bytes(size)} written..."
            sys.stdout.write("\r\x1b[2K" + msg)
            sys.stdout.flush()
            stop_flag.wait(0.25)

    if show_progress:
        sys.stdout.write(f"{prefix} ...\n")
        sys.stdout.flush()
        t = threading.Thread(target=poll, daemon=True)
        t.start()
    else:
        sys.stdout.write(f"{prefix} ...\n")
        sys.stdout.flush()

    try:
        proc = subprocess.run(cmd, check=False)
    finally:
        stop_flag.set()
        if show_progress:
            sys.stdout.write("\r\x1b[2K")
            sys.stdout.flush()

    if proc.returncode != 0:
        subprocess.run(["docker", "rm", "-f", cname],
                       check=False, capture_output=True)
        print(f"ERROR: backup failed for volume: {volume}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.monotonic() - start
    try:
        final_size = out_path.stat().st_size
        size_str = f" ({fmt_bytes(final_size)} compressed)"
    except FileNotFoundError:
        size_str = ""
    print(f"{prefix}   done in {elapsed:.1f}s -> {out_path}{size_str}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docker_volume_backupper.py",
        description="Back up matching docker volumes to dated tar.gz files.",
    )
    p.add_argument("patterns", nargs="*", metavar="pattern",
                   help="regex(es) to match volume names (union); "
                        "if omitted, picker opens with ALL volumes, none preselected")
    p.add_argument("-d", "--dir", default="./volumes",
                   help="backup directory (default: ./volumes)")
    p.add_argument("-y", "--yes", action="store_true",
                   help="skip picker and final confirm; back up all matches")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="list matches and exit (no docker run, no prompt)")
    p.add_argument("--no-progress", action="store_true",
                   help="suppress per-volume live progress")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not shutil.which("docker"):
        print("ERROR: docker CLI not found in PATH", file=sys.stderr)
        return 2

    try:
        all_volumes = list_docker_volumes()
    except subprocess.CalledProcessError as e:
        print(f"ERROR: `docker volume ls` failed: {e}", file=sys.stderr)
        return 2

    no_patterns = not args.patterns
    if no_patterns:
        matched = all_volumes
    else:
        matched = match_patterns(all_volumes, args.patterns)
    if not matched:
        msg = "No docker volumes found." if no_patterns else "No volumes matched any pattern."
        print(msg, file=sys.stderr)
        return 1

    backup_dir = Path(args.dir).expanduser().resolve()

    label = "All volumes" if no_patterns else "Matched"
    print(f"{label} ({len(matched)}):")
    for v in matched:
        print(f"  {v}")
    print(f"Destination: {backup_dir}")
    print()

    if args.dry_run:
        print("Dry run - nothing was backed up.")
        return 0

    if args.yes:
        chosen = matched
    else:
        if not sys.stdin.isatty():
            print("ERROR: not a TTY; pass -y to back up without confirmation.",
                  file=sys.stderr)
            return 2
        chosen = curses_pick(matched, backup_dir, preselected=not no_patterns)
        if chosen is None:
            print("Cancelled.")
            return 0
        if not chosen:
            print("Nothing selected.")
            return 0
        print(f"Selected {len(chosen)} volume(s):")
        for v in chosen:
            print(f"  {v}")
        if not confirm(f"Back up {len(chosen)} volume(s) to {backup_dir}?"):
            print("Cancelled.")
            return 0

    backup_dir.mkdir(parents=True, exist_ok=True)

    show_progress = not args.no_progress
    for i, v in enumerate(chosen, start=1):
        backup_one(v, backup_dir, show_progress=show_progress,
                   idx=i, total=len(chosen))

    print()
    print(f"All done. {len(chosen)} volume(s) backed up to {backup_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
