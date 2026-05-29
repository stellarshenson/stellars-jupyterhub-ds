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
import signal
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path


# ── Colour / glyph helpers ──────────────────────────────────────────────────

def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    return os.environ.get("TERM", "") not in ("", "dumb")


class _Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.bold = "\x1b[1m" if enabled else ""
        self.dim = "\x1b[2m" if enabled else ""
        self.cyan = "\x1b[36m" if enabled else ""
        self.green = "\x1b[32m" if enabled else ""
        self.yellow = "\x1b[33m" if enabled else ""
        self.red = "\x1b[31m" if enabled else ""
        self.reset = "\x1b[0m" if enabled else ""


C = _Style(_supports_color())

GLYPH_ACTIVE = "▸"
GLYPH_DONE = "✓"
GLYPH_FAIL = "✗"


def fmt_bar(pct: int, width: int = 24) -> str:
    pct = max(0, min(100, pct))
    filled = int(pct * width / 100)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def hr() -> str:
    cols = shutil.get_terminal_size((80, 24)).columns
    return C.dim + "─" * min(cols, 80) + C.reset


def clear_screen() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.flush()


# ── Docker helpers ──────────────────────────────────────────────────────────

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
            print(f"{C.yellow}WARNING:{C.reset} pattern matched nothing: {p}",
                  file=sys.stderr)
    return matched


def fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def _try_remove_partial(path: Path, retries: int = 10, delay: float = 0.3) -> bool:
    """Best-effort unlink with retry. On Docker Desktop/WSL2 the daemon may
    re-create the file briefly after container teardown (deferred 9P writes);
    loop until removal actually sticks or we give up."""
    for _ in range(retries):
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        time.sleep(delay)
        if not path.exists():
            return True
    return not path.exists()


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


# ── Curses picker ───────────────────────────────────────────────────────────

def curses_pick(
    volumes: list[str], dest: Path, *, preselected: bool = True
) -> list[str] | None:
    """Interactive multi-select. Returns chosen list or None on quit."""
    selected = [preselected] * len(volumes)

    def run(stdscr) -> list[str] | None:
        curses.curs_set(0)
        stdscr.keypad(True)
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            color_title = curses.color_pair(1) | curses.A_BOLD
            color_help = curses.color_pair(3)
            color_check = curses.color_pair(2) | curses.A_BOLD
        except curses.error:
            color_title = curses.A_BOLD
            color_help = curses.A_DIM
            color_check = curses.A_BOLD

        cursor = 0
        top = 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            list_h = max(1, h - 5)
            title = f" docker_volume_backupper - select volumes ({len(volumes)} matched) "
            help1 = "  UP/DOWN move   SPACE toggle   a all   n none   ENTER confirm   q quit"
            stdscr.addnstr(0, 0, title, w - 1, color_title)
            stdscr.addnstr(1, 0, help1, w - 1, color_help)
            if cursor < top:
                top = cursor
            elif cursor >= top + list_h:
                top = cursor - list_h + 1
            for row in range(list_h):
                idx = top + row
                if idx >= len(volumes):
                    break
                checked = selected[idx]
                mark_glyph = GLYPH_DONE if checked else " "
                arrow = "▶" if idx == cursor else " "
                line = f" {arrow} [{mark_glyph}] {volumes[idx]}"
                attr = curses.A_NORMAL
                if idx == cursor:
                    attr = curses.A_REVERSE
                elif checked:
                    attr = color_check
                stdscr.addnstr(3 + row, 0, line, w - 1, attr)
            sel = sum(selected)
            footer = f"  {sel}/{len(volumes)} selected   dest: {dest}"
            stdscr.addnstr(h - 1, 0, footer, w - 1, color_help)
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


# ── Confirm + backup ────────────────────────────────────────────────────────

def confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} [Y/n]: ").strip().lower()
    except EOFError:
        return False
    return ans not in ("n", "no")


def backup_one(
    volume: str, backup_dir: Path, *, show_progress: bool, idx: int, total: int
) -> None:
    """Run one docker tar backup. On KeyboardInterrupt: remove container,
    delete partial tarball, re-raise. On non-interrupt failure: sys.exit(1)."""
    today = date.today().isoformat()
    out_name = f"{volume}_{today}.tar.gz"
    out_path = backup_dir / out_name
    cname = f"backup_{int(time.time())}_{os.getpid()}_{idx}"
    head = f"{C.bold}[{idx}/{total}]{C.reset}"
    prefix_active = f"{head} {C.cyan}{GLYPH_ACTIVE}{C.reset} {volume}"
    prefix_done = f"{head} {C.green}{GLYPH_DONE}{C.reset} {volume}"

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

    def _overall_line(current_frac: float) -> str:
        overall_frac = ((idx - 1) + min(1.0, max(0.0, current_frac))) / total
        opct = min(99, int(overall_frac * 100))
        return (f"{C.bold}{C.cyan}Overall{C.reset}  {C.cyan}{fmt_bar(opct)}{C.reset} "
                f"{C.bold}{opct:>3}%{C.reset}  "
                f"{C.green}{idx - 1}/{total}{C.reset} {C.dim}volumes done{C.reset}")

    sep = hr()  # dim horizontal rule above the Overall line

    def poll():
        while not stop_flag.is_set():
            try:
                size = out_path.stat().st_size
            except FileNotFoundError:
                size = 0
            if estimated and estimated > 0:
                pct = min(99, int(size * 100 / estimated))
                per_msg = (f"{prefix_active}  {fmt_bar(pct)} {pct:>3}%  "
                           f"{C.dim}{fmt_bytes(size)} / ~{fmt_bytes(estimated)}{C.reset}")
                overall_msg = _overall_line(size / estimated)
            else:
                per_msg = f"{prefix_active}  {C.dim}{fmt_bytes(size)} written...{C.reset}"
                overall_msg = _overall_line(0.0)
            # Three-line refresh: per-vol, hr, overall. Then up two lines.
            sys.stdout.write("\r\x1b[2K" + per_msg
                             + "\n\x1b[2K" + sep
                             + "\n\x1b[2K" + overall_msg
                             + "\x1b[2A\r")
            sys.stdout.flush()
            stop_flag.wait(0.25)

    if show_progress:
        # Reserve three lines (A: per-vol, B: hr, C: overall), park cursor at A.
        sys.stdout.write(f"{prefix_active} ...\n{sep}\n{_overall_line(0.0)}\x1b[2A\r")
        sys.stdout.flush()
        t = threading.Thread(target=poll, daemon=True)
        t.start()
    else:
        sys.stdout.write(f"{prefix_active} ...\n")
        sys.stdout.flush()

    # Popen + wait() rather than subprocess.run(): run()'s internal KI handler
    # does process.kill()+process.wait() and can block indefinitely while the
    # docker client tries to gracefully tear down the container, preventing our
    # cleanup from ever running.
    proc = subprocess.Popen(cmd)
    interrupted = False
    proc_rc = -1
    try:
        proc_rc = proc.wait()
    except KeyboardInterrupt:
        interrupted = True
    finally:
        stop_flag.set()
        if show_progress:
            # Clear all three lines (per-vol, hr, overall), return to line A.
            sys.stdout.write("\r\x1b[2K\n\x1b[2K\n\x1b[2K\x1b[2A\r")
            sys.stdout.flush()

    if interrupted:
        # The docker container is owned by dockerd, not by our killed client;
        # talk to the daemon directly to remove it.
        subprocess.run(["docker", "rm", "-f", cname],
                       check=False, capture_output=True, timeout=15)
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass
        # Small settle so the daemon flushes / releases its bind-mount handle
        # before we try to delete the partial tarball.
        removed = _try_remove_partial(out_path)
        file_msg = ", partial file deleted" if removed else f", partial file kept: {out_path}"
        print(f"{head} {C.yellow}{GLYPH_FAIL}{C.reset} {volume}  "
              f"{C.yellow}aborted (container removed{file_msg}){C.reset}",
              file=sys.stderr)
        raise KeyboardInterrupt

    if proc_rc != 0:
        subprocess.run(["docker", "rm", "-f", cname],
                       check=False, capture_output=True)
        print(f"{head} {C.red}{GLYPH_FAIL}{C.reset} {volume}  "
              f"{C.red}backup failed (rc={proc_rc}){C.reset}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.monotonic() - start
    try:
        size_str = f", {fmt_bytes(out_path.stat().st_size)} compressed"
    except FileNotFoundError:
        size_str = ""
    print(f"{prefix_done}  {C.dim}done in {elapsed:.1f}s{size_str}{C.reset}")


# ── Argparse / main ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docker_volume_backupper.py",
        description="Back up matching docker volumes to dated tar.gz files.",
    )
    p.add_argument("patterns", nargs="*", metavar="pattern",
                   help="one or more regex patterns matched against volume names "
                        "(a volume matches if ANY pattern matches); "
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


def _print_listing(title: str, volumes: list[str], dest: Path) -> None:
    print(f"{C.bold}{title} ({len(volumes)}){C.reset}")
    for v in volumes:
        print(f"  {C.dim}•{C.reset} {v}")
    print(f"{C.dim}Destination:{C.reset} {dest}")


def main(argv: list[str] | None = None) -> int:
    # If invoked as a background job, bash may set SIGINT to SIG_IGN;
    # Python inherits and won't override that, so Ctrl-C would be a no-op.
    # Re-arm explicitly so KeyboardInterrupt always fires.
    signal.signal(signal.SIGINT, signal.default_int_handler)

    args = build_parser().parse_args(argv)

    if not shutil.which("docker"):
        print(f"{C.red}ERROR:{C.reset} docker CLI not found in PATH",
              file=sys.stderr)
        return 2

    try:
        all_volumes = list_docker_volumes()
    except subprocess.CalledProcessError as e:
        print(f"{C.red}ERROR:{C.reset} `docker volume ls` failed: {e}",
              file=sys.stderr)
        return 2

    no_patterns = not args.patterns
    if no_patterns:
        matched = all_volumes
    else:
        matched = match_patterns(all_volumes, args.patterns)
    if not matched:
        msg = "No docker volumes found." if no_patterns else "No volumes matched any pattern."
        print(f"{C.yellow}{msg}{C.reset}", file=sys.stderr)
        return 1

    backup_dir = Path(args.dir).expanduser().resolve()
    label = "All volumes" if no_patterns else "Matched"
    _print_listing(label, matched, backup_dir)
    print()

    if args.dry_run:
        print(f"{C.dim}Dry run - nothing was backed up.{C.reset}")
        return 0

    if args.yes:
        chosen = matched
    else:
        if not sys.stdin.isatty():
            print(f"{C.red}ERROR:{C.reset} not a TTY; pass -y to back up "
                  "without confirmation.", file=sys.stderr)
            return 2
        try:
            chosen = curses_pick(matched, backup_dir, preselected=not no_patterns)
        except KeyboardInterrupt:
            chosen = None
        if chosen is None:
            print("Cancelled.")
            return 0
        if not chosen:
            print("Nothing selected.")
            return 0
        clear_screen()
        _print_listing("Selected", chosen, backup_dir)
        print()
        if not confirm(f"Back up {len(chosen)} volume(s)?"):
            print("Cancelled.")
            return 0

    backup_dir.mkdir(parents=True, exist_ok=True)

    clear_screen()
    print(f"{C.bold}Backing up {len(chosen)} volume(s) -> {backup_dir}{C.reset}")
    print(hr())

    show_progress = not args.no_progress
    try:
        for i, v in enumerate(chosen, start=1):
            backup_one(v, backup_dir, show_progress=show_progress,
                       idx=i, total=len(chosen))
    except KeyboardInterrupt:
        print(hr())
        print(f"{C.yellow}Aborted by user.{C.reset}", file=sys.stderr)
        return 130

    print(hr())
    print(f"{C.green}{GLYPH_DONE}{C.reset} {C.bold}All done.{C.reset} "
          f"{len(chosen)} volume(s) backed up to {backup_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
