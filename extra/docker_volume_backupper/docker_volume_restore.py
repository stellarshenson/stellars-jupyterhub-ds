#!/usr/bin/env python3
"""Restore docker volumes from dated tar.gz backups produced by docker_volume_backupper.py.

Stdlib only. Confirmation by default (curses multi-select); -y bypasses;
--dry-run lists the file -> volume mapping and exits.

Restoration WIPES the destination volume's contents before extracting.
If the destination docker volume does not exist, the file is skipped (no
auto-create) - matches the original .sh behaviour.
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
import time
from pathlib import Path


_DATE_RE = re.compile(r"[_-]\d{4}-\d{2}-\d{2}(?:[_-].*)?$")


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


# ── Helpers ─────────────────────────────────────────────────────────────────

def extract_volume_name(path: Path) -> str:
    """Strip extension and trailing _YYYY-MM-DD[<suffix>] from a backup filename."""
    name = path.name
    for ext in (".tar.gz", ".tgz", ".tar"):
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
            break
    return _DATE_RE.sub("", name)


def fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def _force_remove_container(name: str) -> None:
    subprocess.run(["docker", "rm", "-f", name],
                   check=False, capture_output=True, timeout=15)


def volume_exists(volume: str) -> bool:
    r = subprocess.run(
        ["docker", "volume", "inspect", volume],
        capture_output=True,
    )
    return r.returncode == 0


def _tar_extract_flag(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "xzf"
    if name.endswith(".tar"):
        return "xf"
    return "xzf"


# ── Curses picker ───────────────────────────────────────────────────────────

def curses_pick(
    items: list[tuple[Path, str, int]],
) -> list[tuple[Path, str, int]] | None:
    """Multi-select picker over (file, volume, size_bytes) triples."""
    selected = [True] * len(items)

    def run(stdscr) -> list[tuple[Path, str, int]] | None:
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
            title = f" docker_volume_restore - select backups ({len(items)} matched) "
            help1 = "  UP/DOWN move   SPACE toggle   a all   n none   ENTER confirm   q quit"
            stdscr.addnstr(0, 0, title, w - 1, color_title)
            stdscr.addnstr(1, 0, help1, w - 1, color_help)
            if cursor < top:
                top = cursor
            elif cursor >= top + list_h:
                top = cursor - list_h + 1
            for row in range(list_h):
                idx = top + row
                if idx >= len(items):
                    break
                fp, vol, size = items[idx]
                checked = selected[idx]
                mark_glyph = GLYPH_DONE if checked else " "
                arrow = "▶" if idx == cursor else " "
                line = f" {arrow} [{mark_glyph}] {fp.name}  ({fmt_bytes(size)})  ->  {vol}"
                attr = curses.A_NORMAL
                if idx == cursor:
                    attr = curses.A_REVERSE
                elif checked:
                    attr = color_check
                stdscr.addnstr(3 + row, 0, line, w - 1, attr)
            sel_count = sum(selected)
            sel_bytes = sum(s for sel, (_, _, s) in zip(selected, items) if sel)
            footer = f"  {sel_count}/{len(items)} selected ({fmt_bytes(sel_bytes)})"
            stdscr.addnstr(h - 1, 0, footer, w - 1, color_help)
            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (curses.KEY_UP, ord("k")):
                cursor = max(0, cursor - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                cursor = min(len(items) - 1, cursor + 1)
            elif ch == curses.KEY_PPAGE:
                cursor = max(0, cursor - list_h)
            elif ch == curses.KEY_NPAGE:
                cursor = min(len(items) - 1, cursor + list_h)
            elif ch == curses.KEY_HOME:
                cursor = 0
            elif ch == curses.KEY_END:
                cursor = len(items) - 1
            elif ch == ord(" "):
                selected[cursor] = not selected[cursor]
            elif ch == ord("a"):
                for i in range(len(selected)):
                    selected[i] = True
            elif ch == ord("n"):
                for i in range(len(selected)):
                    selected[i] = False
            elif ch in (curses.KEY_ENTER, 10, 13):
                return [it for it, s in zip(items, selected) if s]
            elif ch in (ord("q"), 27):
                return None

    try:
        return curses.wrapper(run)
    except KeyboardInterrupt:
        return None


# ── Confirm + restore ───────────────────────────────────────────────────────

def confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} [Y/n]: ").strip().lower()
    except EOFError:
        return False
    return ans not in ("n", "no")


def restore_one(
    file_path: Path, volume: str, *, show_progress: bool, idx: int, total: int
) -> None:
    """Wipe + extract. On KeyboardInterrupt: kill containers, warn about
    partial state, re-raise. On non-interrupt failure: sys.exit(1)."""
    cname = f"restore_{volume}_{int(time.time())}_{os.getpid()}_{idx}"
    wipe_cname = f"{cname}_wipe"
    head = f"{C.bold}[{idx}/{total}]{C.reset}"
    prefix_active = f"{head} {C.cyan}{GLYPH_ACTIVE}{C.reset} {file_path.name} -> {volume}"
    prefix_done = f"{head} {C.green}{GLYPH_DONE}{C.reset} {file_path.name} -> {volume}"

    def _overall_line(current_frac: float) -> str:
        overall_frac = ((idx - 1) + min(1.0, max(0.0, current_frac))) / total
        opct = min(99, int(overall_frac * 100))
        return (f"{C.bold}{C.cyan}Overall{C.reset}  {C.cyan}{fmt_bar(opct)}{C.reset} "
                f"{C.bold}{opct:>3}%{C.reset}  "
                f"{C.green}{idx - 1}/{total}{C.reset} {C.dim}files done{C.reset}")

    sep = hr()  # dim horizontal rule above the Overall line

    if show_progress:
        # Reserve three lines (A: per-file, B: hr, C: overall), park cursor at A.
        sys.stdout.write(f"{prefix_active} ...\n{sep}\n{_overall_line(0.0)}\x1b[2A\r")
        sys.stdout.flush()
    else:
        sys.stdout.write(f"{prefix_active} ...\n")
        sys.stdout.flush()

    start = time.monotonic()
    interrupted = False
    rc = -1

    try:
        if show_progress:
            wipe = subprocess.run(
                ["docker", "run", "--rm", "--name", wipe_cname,
                 "-v", f"{volume}:/data", "alpine",
                 "sh", "-c", "cd /data && rm -rf ./* .??* 2>/dev/null || true"],
                capture_output=True,
            )
            if wipe.returncode != 0:
                subprocess.run(["docker", "rm", "-f", wipe_cname],
                               check=False, capture_output=True)
                print(f"{head} {C.red}{GLYPH_FAIL}{C.reset} {volume}  "
                      f"{C.red}wipe failed (rc={wipe.returncode}){C.reset}",
                      file=sys.stderr)
                sys.exit(1)

            flag = _tar_extract_flag(file_path)
            proc = subprocess.Popen(
                ["docker", "run", "--rm", "-i", "--name", cname,
                 "-v", f"{volume}:/data", "alpine",
                 "tar", flag, "-", "-C", "/data"],
                stdin=subprocess.PIPE,
            )
            assert proc.stdin is not None

            total_bytes = file_path.stat().st_size
            bytes_sent = 0
            last_update = 0.0
            try:
                with open(file_path, "rb") as fh:
                    while True:
                        chunk = fh.read(1024 * 1024)
                        if not chunk:
                            break
                        proc.stdin.write(chunk)
                        bytes_sent += len(chunk)
                        now = time.monotonic()
                        if now - last_update > 0.25:
                            pct = min(99, int(bytes_sent * 100 /
                                              max(1, total_bytes)))
                            per_msg = (f"{prefix_active}  {fmt_bar(pct)} "
                                       f"{pct:>3}%  {C.dim}{fmt_bytes(bytes_sent)} / "
                                       f"{fmt_bytes(total_bytes)}{C.reset}")
                            overall_msg = _overall_line(bytes_sent / max(1, total_bytes))
                            sys.stdout.write("\r\x1b[2K" + per_msg
                                             + "\n\x1b[2K" + sep
                                             + "\n\x1b[2K" + overall_msg
                                             + "\x1b[2A\r")
                            sys.stdout.flush()
                            last_update = now
                proc.stdin.close()
            except BrokenPipeError:
                pass
            rc = proc.wait()
            # Clear all three lines (per-file, hr, overall), return to line A.
            sys.stdout.write("\r\x1b[2K\n\x1b[2K\n\x1b[2K\x1b[2A\r")
            sys.stdout.flush()
        else:
            absdir = file_path.parent.resolve()
            flag = _tar_extract_flag(file_path)
            inner = (
                "set -e; cd /data; "
                "rm -rf ./* .??* 2>/dev/null || true; "
                f"tar {flag} \"/backup/{file_path.name}\" -C /data"
            )
            cmd = [
                "docker", "run", "--rm", "--name", cname,
                "-v", f"{volume}:/data",
                "-v", f"{absdir}:/backup",
                "alpine", "sh", "-c", inner,
            ]
            # Popen + wait() rather than subprocess.run(): run()'s internal KI
            # handler blocks indefinitely on the docker client's graceful
            # tear-down, preventing our cleanup branch from ever running.
            proc = subprocess.Popen(cmd)
            try:
                rc = proc.wait()
            except KeyboardInterrupt:
                interrupted = True
    except KeyboardInterrupt:
        interrupted = True

    if interrupted:
        for c in (wipe_cname, cname):
            _force_remove_container(c)
        try:
            if 'proc' in locals():
                proc.kill()
                proc.wait(timeout=5)
        except Exception:
            pass
        # Brief settle for the daemon to flush container teardown (esp.
        # Docker Desktop/WSL2 where bind-mount writes are 9P-deferred).
        time.sleep(0.5)
        print(f"{head} {C.yellow}{GLYPH_FAIL}{C.reset} {file_path.name}  "
              f"{C.yellow}aborted (containers removed; volume contents "
              f"PARTIAL - re-run restore to recover){C.reset}",
              file=sys.stderr)
        raise KeyboardInterrupt

    if rc != 0:
        subprocess.run(["docker", "rm", "-f", cname],
                       check=False, capture_output=True)
        print(f"{head} {C.red}{GLYPH_FAIL}{C.reset} {file_path.name}  "
              f"{C.red}restore failed (rc={rc}){C.reset}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.monotonic() - start
    print(f"{prefix_done}  {C.dim}done in {elapsed:.1f}s{C.reset}")


def resolve_items(files: list[str]) -> list[tuple[Path, str, int]]:
    """Validate each input path, infer volume name, check the volume exists.
    Print one warning per skipped file. Returns the list of (path, vol, size).
    """
    items: list[tuple[Path, str, int]] = []
    for f in files:
        p = Path(f)
        if not p.is_file():
            print(f"{C.yellow}SKIP:{C.reset} file not found: {f}",
                  file=sys.stderr)
            continue
        vol = extract_volume_name(p)
        if not vol:
            print(f"{C.yellow}SKIP:{C.reset} could not infer volume name from {f}",
                  file=sys.stderr)
            continue
        if not volume_exists(vol):
            print(f"{C.yellow}SKIP:{C.reset} docker volume does not exist: "
                  f"{vol}  (from {p.name})", file=sys.stderr)
            continue
        items.append((p, vol, p.stat().st_size))
    return items


# ── Argparse / main ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docker_volume_restore.py",
        description=(
            "Restore docker volumes from tar.gz backups. "
            "WIPES the destination volume before extracting."
        ),
    )
    p.add_argument("files", nargs="+", metavar="backup-file",
                   help="one or more backup files (.tar.gz / .tgz / .tar) - "
                        "each maps to its source volume by the filename")
    p.add_argument("-y", "--yes", action="store_true",
                   help="skip picker and final confirm; restore everything")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="list file -> volume mapping and exit")
    p.add_argument("--no-progress", action="store_true",
                   help="suppress per-file live progress (faster, single docker run)")
    return p


def _print_manifest(items: list[tuple[Path, str, int]], title: str) -> None:
    total = sum(s for _, _, s in items)
    print(f"{C.bold}{title} ({len(items)} file(s), total "
          f"{fmt_bytes(total)}){C.reset}")
    name_w = max(len(p.name) for p, _, _ in items)
    size_w = max(len(fmt_bytes(s)) for _, _, s in items)
    for p, vol, s in items:
        print(f"  {C.dim}•{C.reset} {p.name:<{name_w}}  "
              f"{fmt_bytes(s):>{size_w}}  -> {vol}")


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

    items = resolve_items(args.files)
    if not items:
        print(f"{C.yellow}No restorable backup files.{C.reset}", file=sys.stderr)
        return 1

    _print_manifest(items, "Found restorable backup(s)")
    print()

    if args.dry_run:
        print(f"{C.dim}Dry run - nothing was restored.{C.reset}")
        return 0

    if args.yes:
        chosen = items
    else:
        if not sys.stdin.isatty():
            print(f"{C.red}ERROR:{C.reset} not a TTY; pass -y to restore "
                  "without confirmation.", file=sys.stderr)
            return 2
        try:
            chosen = curses_pick(items)
        except KeyboardInterrupt:
            chosen = None
        if chosen is None:
            print("Cancelled.")
            return 0
        if not chosen:
            print("Nothing selected.")
            return 0
        clear_screen()
        _print_manifest(chosen, "Selected backup(s)")
        print(f"{C.yellow}WARNING:{C.reset} this WIPES the destination "
              "volume(s) before extracting.")
        if not confirm(f"Restore {len(chosen)} backup(s)?"):
            print("Cancelled.")
            return 0

    clear_screen()
    print(f"{C.bold}Restoring {len(chosen)} backup(s){C.reset}")
    print(hr())

    try:
        for i, (fp, vol, _) in enumerate(chosen, start=1):
            restore_one(fp, vol, show_progress=not args.no_progress,
                        idx=i, total=len(chosen))
    except KeyboardInterrupt:
        print(hr())
        print(f"{C.yellow}Aborted by user.{C.reset}", file=sys.stderr)
        return 130

    print(hr())
    print(f"{C.green}{GLYPH_DONE}{C.reset} {C.bold}All done.{C.reset} "
          f"{len(chosen)} backup(s) restored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
