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
import subprocess
import sys
import time
from pathlib import Path


_DATE_RE = re.compile(r"[_-]\d{4}-\d{2}-\d{2}(?:[_-].*)?$")


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


def volume_exists(volume: str) -> bool:
    r = subprocess.run(
        ["docker", "volume", "inspect", volume],
        capture_output=True,
    )
    return r.returncode == 0


def curses_pick(
    items: list[tuple[Path, str, int]],
) -> list[tuple[Path, str, int]] | None:
    """Multi-select picker over (file, volume, size_bytes) triples."""
    selected = [True] * len(items)

    def run(stdscr) -> list[tuple[Path, str, int]] | None:
        curses.curs_set(0)
        stdscr.keypad(True)
        cursor = 0
        top = 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            list_h = max(1, h - 5)
            header1 = f"docker_volume_restore.py - select backups to restore ({len(items)} matched)"
            header2 = "  UP/DOWN move   SPACE toggle   a all   n none   ENTER confirm   q quit"
            stdscr.addnstr(0, 0, header1, w - 1)
            stdscr.addnstr(1, 0, header2, w - 1)
            if cursor < top:
                top = cursor
            elif cursor >= top + list_h:
                top = cursor - list_h + 1
            for row in range(list_h):
                idx = top + row
                if idx >= len(items):
                    break
                mark = "x" if selected[idx] else " "
                arrow = ">" if idx == cursor else " "
                fp, vol, size = items[idx]
                line = f"{arrow} [{mark}] {fp.name}  ({fmt_bytes(size)})  ->  {vol}"
                attr = curses.A_REVERSE if idx == cursor else curses.A_NORMAL
                stdscr.addnstr(3 + row, 0, line, w - 1, attr)
            sel_count = sum(selected)
            sel_bytes = sum(s for sel, (_, _, s) in zip(selected, items) if sel)
            footer = f"  {sel_count}/{len(items)} selected ({fmt_bytes(sel_bytes)})"
            stdscr.addnstr(h - 1, 0, footer, w - 1)
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


def confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def _tar_extract_flag(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "xzf"
    if name.endswith(".tar"):
        return "xf"
    return "xzf"


def restore_one(
    file_path: Path, volume: str, *, show_progress: bool, idx: int, total: int
) -> None:
    """Wipe the destination volume, then extract the backup. Aborts on failure.

    With progress on: splits into two docker runs - a short wipe, then a
    streamed extract via stdin so we can poll exact bytes-sent vs file size.

    With --no-progress: a single combined run reads the tar directly from the
    bind-mounted backup dir (no Python in the data path).
    """
    cname = f"restore_{volume}_{int(time.time())}_{os.getpid()}_{idx}"
    prefix = f"[{idx}/{total}] {file_path.name} -> {volume}"

    start = time.monotonic()
    sys.stdout.write(f"{prefix} ...\n")
    sys.stdout.flush()

    if show_progress:
        wipe_cname = f"{cname}_wipe"
        wipe = subprocess.run(
            ["docker", "run", "--rm", "--name", wipe_cname,
             "-v", f"{volume}:/data", "alpine",
             "sh", "-c", "cd /data && rm -rf ./* .??* 2>/dev/null || true"],
            capture_output=True,
        )
        if wipe.returncode != 0:
            subprocess.run(["docker", "rm", "-f", wipe_cname],
                           check=False, capture_output=True)
            print(f"ERROR: wipe failed for volume {volume}", file=sys.stderr)
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
                        pct = min(99, int(bytes_sent * 100 / max(1, total_bytes)))
                        msg = (f"{prefix}   {fmt_bytes(bytes_sent)} / "
                               f"{fmt_bytes(total_bytes)} ({pct}%)")
                        sys.stdout.write("\r\x1b[2K" + msg)
                        sys.stdout.flush()
                        last_update = now
            proc.stdin.close()
        except BrokenPipeError:
            pass
        rc = proc.wait()
        sys.stdout.write("\r\x1b[2K")
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
        rc = subprocess.run(cmd).returncode

    if rc != 0:
        subprocess.run(["docker", "rm", "-f", cname],
                       check=False, capture_output=True)
        print(f"ERROR: restore failed for {file_path.name} -> {volume}",
              file=sys.stderr)
        sys.exit(1)

    elapsed = time.monotonic() - start
    print(f"{prefix}   done in {elapsed:.1f}s")


def resolve_items(files: list[str]) -> list[tuple[Path, str, int]]:
    """Validate each input path, infer volume name, check the volume exists.
    Print one warning per skipped file. Returns the list of (path, vol, size).
    """
    items: list[tuple[Path, str, int]] = []
    for f in files:
        p = Path(f)
        if not p.is_file():
            print(f"SKIP: file not found: {f}", file=sys.stderr)
            continue
        vol = extract_volume_name(p)
        if not vol:
            print(f"SKIP: could not infer volume name from {f}", file=sys.stderr)
            continue
        if not volume_exists(vol):
            print(f"SKIP: docker volume does not exist: {vol}  (from {p.name})",
                  file=sys.stderr)
            continue
        items.append((p, vol, p.stat().st_size))
    return items


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docker_volume_restore.py",
        description=(
            "Restore docker volumes from tar.gz backups. "
            "WIPES the destination volume before extracting."
        ),
    )
    p.add_argument("files", nargs="+", metavar="backup-file",
                   help="backup file(s): .tar.gz / .tgz / .tar")
    p.add_argument("-y", "--yes", action="store_true",
                   help="skip picker and final confirm; restore everything")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="list file -> volume mapping and exit")
    p.add_argument("--no-progress", action="store_true",
                   help="suppress per-file live progress (faster, single docker run)")
    return p


def _print_manifest(items: list[tuple[Path, str, int]], title: str) -> None:
    total = sum(s for _, _, s in items)
    print(f"{title} ({len(items)} file(s), total {fmt_bytes(total)}):")
    name_w = max(len(p.name) for p, _, _ in items)
    size_w = max(len(fmt_bytes(s)) for _, _, s in items)
    for p, vol, s in items:
        print(f"  {p.name:<{name_w}}  {fmt_bytes(s):>{size_w}}  ->  {vol}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not shutil.which("docker"):
        print("ERROR: docker CLI not found in PATH", file=sys.stderr)
        return 2

    items = resolve_items(args.files)
    if not items:
        print("No restorable backup files.", file=sys.stderr)
        return 1

    _print_manifest(items, "Found restorable backup(s)")
    print()

    if args.dry_run:
        print("Dry run - nothing was restored.")
        return 0

    if args.yes:
        chosen = items
    else:
        if not sys.stdin.isatty():
            print("ERROR: not a TTY; pass -y to restore without confirmation.",
                  file=sys.stderr)
            return 2
        chosen = curses_pick(items)
        if chosen is None:
            print("Cancelled.")
            return 0
        if not chosen:
            print("Nothing selected.")
            return 0
        _print_manifest(chosen, "Selected backup(s)")
        print("WARNING: this WIPES the destination volume(s) before extracting.")
        if not confirm(f"Restore {len(chosen)} backup(s)?"):
            print("Cancelled.")
            return 0

    for i, (fp, vol, _) in enumerate(chosen, start=1):
        restore_one(fp, vol, show_progress=not args.no_progress,
                    idx=i, total=len(chosen))

    print()
    print(f"All done. {len(chosen)} backup(s) restored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
