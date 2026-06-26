#!/usr/bin/env python3
"""Render a self-contained HTML sign-off report from the functional run.

Inputs (all produced by the harness):
  - the board TSV (label<TAB>result<TAB>tests<TAB>secs), one row per regime
  - per-regime JSON sidecars `reports/regime-<regime>.json` written by conftest
    (totals + acceptance-criteria coverage + per-test outcomes)

Output: one self-contained `reports/signoff.html` (no external assets) showing the
regime board, the aggregated acceptance-criteria coverage (MET / UNMET / NOT RUN),
and a collapsible per-regime test breakdown. Regenerated on EVERY run.sh invocation.
"""
import argparse
import glob
import html
import json
import os


def _esc(s):
    return html.escape(str(s), quote=True)


def load_board(path):
    rows = []
    if path and os.path.exists(path):
        with open(path) as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 4:
                    rows.append({"regime": parts[0], "result": parts[1], "tests": parts[2], "secs": parts[3]})
    return rows


def load_regimes(reports_dir):
    out = {}
    for p in sorted(glob.glob(os.path.join(reports_dir, "regime-*.json"))):
        try:
            with open(p) as f:
                d = json.load(f)
            out[d.get("regime", os.path.basename(p))] = d
        except Exception:
            continue
    return out


def aggregate_criteria(regimes):
    """Merge per-regime coverage: UNMET if unmet anywhere, else MET if met anywhere,
    else NOT RUN. Track the covering tests (union) and the regimes that exercised it."""
    agg = {}
    for regime, d in regimes.items():
        for c in d.get("criteria", []):
            ref = c["ref"]
            e = agg.setdefault(ref, {"status": "NOT RUN", "tests": set(), "regimes": set()})
            e["tests"].update(c.get("tests", []))
            e["regimes"].add(regime)
            st = c.get("status", "NOT RUN")
            if st == "UNMET":
                e["status"] = "UNMET"
            elif st == "MET" and e["status"] != "UNMET":
                e["status"] = "MET"
    return agg


CSS = """
:root{--ok:#1f9d57;--bad:#d4351c;--warn:#b8860b;--ink:#1a2329;--mut:#5a6b75;--line:#d4dde3;--bg:#f5f7fa}
*{box-sizing:border-box}body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg);margin:0;padding:32px}
.wrap{max-width:1100px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px;border-bottom:2px solid var(--line);padding-bottom:6px}
.meta{color:var(--mut);font-size:13px;margin-bottom:18px}
.verdict{display:inline-block;font-weight:700;padding:4px 14px;border-radius:999px;color:#fff;font-size:13px;letter-spacing:.04em}
.verdict.PASS{background:var(--ok)}.verdict.FAIL{background:var(--bad)}
table{border-collapse:collapse;width:100%;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line)}
th{background:#eef1f5;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:var(--mut)}
tr:last-child td{border-bottom:0}tr:nth-child(even) td{background:#fafbfc}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:1px 9px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}
.badge.PASS,.badge.MET,.badge.passed{background:var(--ok)}
.badge.FAIL,.badge.UNMET,.badge.failed,.badge.error{background:var(--bad)}
.badge.skipped,.badge.NOTRUN{background:var(--mut)}
.cards{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 2px}
.card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 18px;min-width:120px}
.card .n{font-size:24px;font-weight:700}.card .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.03em}
details{background:#fff;border:1px solid var(--line);border-radius:8px;margin:8px 0;padding:4px 12px}
summary{cursor:pointer;font-weight:600;padding:6px 0}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px}
.ref{font-family:ui-monospace,Menlo,monospace;font-size:12.5px}
.small{color:var(--mut);font-size:12px}
"""


def render(board, regimes, agg, image, timestamp):
    overall = "PASS"
    for r in board:
        if r["result"] != "PASS":
            overall = "FAIL"
    if not board and any(d.get("totals", {}).get("failed") for d in regimes.values()):
        overall = "FAIL"

    met = sum(1 for e in agg.values() if e["status"] == "MET")
    unmet = sum(1 for e in agg.values() if e["status"] == "UNMET")
    notrun = sum(1 for e in agg.values() if e["status"] == "NOT RUN")
    tot_tests = sum(int(r["tests"]) for r in board) if board else \
        sum(sum(d.get("totals", {}).get(k, 0) for k in ("passed", "failed", "error")) for d in regimes.values())

    p = []
    p.append(f"<!doctype html><html><head><meta charset='utf-8'>"
             f"<title>Duoptimum Hub - Functional Sign-off</title><style>{CSS}</style></head><body><div class='wrap'>")
    p.append("<h1>Duoptimum Hub &mdash; Functional Sign-off</h1>")
    p.append(f"<div class='meta'>{_esc(timestamp)} &middot; image <span class='mono'>{_esc(image)}</span> &middot; "
             f"{len(board) or len(regimes)} regime(s) &middot; {tot_tests} tests &middot; "
             f"<span class='verdict {overall}'>{overall}</span></div>")

    # summary cards
    p.append("<div class='cards'>")
    p.append(f"<div class='card'><div class='n'>{tot_tests}</div><div class='l'>Tests</div></div>")
    p.append(f"<div class='card'><div class='n' style='color:var(--ok)'>{met}</div><div class='l'>Criteria met</div></div>")
    p.append(f"<div class='card'><div class='n' style='color:{'var(--bad)' if unmet else 'var(--mut)'}'>{unmet}</div><div class='l'>Criteria unmet</div></div>")
    if notrun:
        p.append(f"<div class='card'><div class='n' style='color:var(--mut)'>{notrun}</div><div class='l'>Not run</div></div>")
    p.append("</div>")

    # board
    p.append("<h2>Regime board</h2><table><tr><th>Regime</th><th>Result</th><th>Tests</th><th>Duration</th></tr>")
    if board:
        for r in board:
            p.append(f"<tr><td>{_esc(r['regime'])}</td><td><span class='badge {_esc(r['result'])}'>{_esc(r['result'])}</span></td>"
                     f"<td class='num'>{_esc(r['tests'])}</td><td class='num'>{_esc(r['secs'])}s</td></tr>")
    else:
        for regime, d in regimes.items():
            t = d.get("totals", {})
            res = "FAIL" if t.get("failed") or t.get("error") else "PASS"
            n = t.get("passed", 0) + t.get("failed", 0) + t.get("error", 0)
            p.append(f"<tr><td>{_esc(regime)}</td><td><span class='badge {res}'>{res}</span></td><td class='num'>{n}</td><td class='num'>-</td></tr>")
    p.append("</table>")

    # acceptance criteria
    p.append("<h2>Acceptance criteria coverage</h2>")
    if agg:
        p.append("<table><tr><th>Criterion</th><th>Status</th><th>Covering tests</th></tr>")
        for ref in sorted(agg):
            e = agg[ref]
            cls = {"MET": "MET", "UNMET": "UNMET", "NOT RUN": "NOTRUN"}[e["status"]]
            tests = ", ".join(sorted(e["tests"])) or "-"
            p.append(f"<tr><td class='ref'>{_esc(ref)}</td><td><span class='badge {cls}'>{_esc(e['status'])}</span></td>"
                     f"<td class='small'>{_esc(tests)}</td></tr>")
        p.append("</table>")
    else:
        p.append("<p class='small'>No acceptance-criteria coverage recorded for this run.</p>")

    # per-regime test breakdown
    p.append("<h2>Test detail</h2>")
    for regime in sorted(regimes):
        d = regimes[regime]
        t = d.get("totals", {})
        tests = d.get("tests", [])
        head = (f"{regime} &mdash; "
                f"<span class='badge passed'>{t.get('passed',0)} passed</span> "
                + (f"<span class='badge failed'>{t.get('failed',0)} failed</span> " if t.get('failed') else "")
                + (f"<span class='badge error'>{t.get('error',0)} error</span> " if t.get('error') else "")
                + (f"<span class='badge skipped'>{t.get('skipped',0)} skipped</span>" if t.get('skipped') else ""))
        p.append(f"<details><summary>{head}</summary><table><tr><th>Test</th><th>Outcome</th></tr>")
        for tc in sorted(tests, key=lambda x: x.get("nodeid", "")):
            oc = tc.get("outcome", "?")
            p.append(f"<tr><td class='mono'>{_esc(tc.get('nodeid',''))}</td>"
                     f"<td><span class='badge {_esc(oc)}'>{_esc(oc)}</span></td></tr>")
        p.append("</table></details>")

    p.append("</div></body></html>")
    return "".join(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default="")
    ap.add_argument("--reports-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--image", default="unknown")
    ap.add_argument("--timestamp", default="")
    a = ap.parse_args()
    board = load_board(a.board)
    regimes = load_regimes(a.reports_dir)
    agg = aggregate_criteria(regimes)
    open(a.out, "w").write(render(board, regimes, agg, a.image, a.timestamp))


if __name__ == "__main__":
    main()
