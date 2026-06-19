# Defects - Duoptimum Hub

Defect registry for the Duoptimum Hub portal and platform - one section per defect, same checklist model as the acceptance criteria ([acc-crit-duoptimumhub.md](acc-crit-duoptimumhub.md)). One document, not many.

Checkbox state: `[ ]` = open / unresolved, `[x]` = fixed and verified; in-progress stays `[ ]` and is marked in the latest `log:` line. Each defect carries severity, status, symptom, then repro / root cause / fix / verification as checklist items with a dated `log:` trail. Severity: BLOCKER (platform unusable) > HIGH (core flow broken) > MED (degraded) > LOW (cosmetic).

## Contents

- [DEF-1: Start-server page falls through to the stock JupyterHub spawn screen, no logs](#def-1-start-server-page-falls-through-to-the-stock-jupyterhub-spawn-screen-no-logs)

---

## DEF-1: Start-server page falls through to the stock JupyterHub spawn screen, no logs

- **Severity**: HIGH - the dedicated Start-server experience (progress bar + live log tail) is bypassed
- **Status**: fix applied (code); runtime verify pending operator rebuild (2026-06-19)
- **Surface**: `src/pages/Starting.tsx` (route `servers/:name/starting`), `hooks/useSpawnProgress.ts`, `hooks/useContainerLogTail.ts`
- **Origin**: NOT the `/dashboard` -> `/home` rename (that only coincided); introduced by the React-portal rewrite (`3dd620b`), which replaced the readiness-probing `home.html` start flow with a page that trusts the hub `ready` flag

Clicking Start on your own server opens the dedicated Starting page; the progress bar jumps quickly to 100%, then the browser switches to the stock JupyterHub spawn-pending screen and no container logs are ever shown. Worked before the portal rewrite.

Root cause: the SSE-drop fallback poll in `useSpawnProgress.ts` treated `'spawning'` as "running" and flipped the bar to `percent:100, phase:'ready'` on the first poll (~1.5s after Start, when the spawner is merely present). That premature `ready` (a) hard-navigated to `/user/{name}/` before the lab served HTTP, so the hub rendered its stock `spawn_pending.html`, and (b) ended the `'spawning'` phase before the 1.5s log-tail poll ran, so the panel stayed empty. A residual ~1s false-positive also exists on the genuine path: the hub `ready` flag flips before the lab actually answers. The purpose-built `LabReadyHandler` (`/api/users/{name}/lab-ready`, always-200 `{ready}`) that the old flow used was never wired into the React page.

- [x] **Repro** - Start your own stopped server; progress shoots to 100% (~1.5s) then the stock hub spawn page replaces the dedicated page; the log-tail panel stays empty
  - log: 2026-06-19 reported by operator; mechanism confirmed by code trace
- [x] **Root cause identified** - SSE-drop fallback accepts `'spawning'` as ready (`useSpawnProgress.ts`) plus an unguarded hub-`ready` false-positive on the redirect (`Starting.tsx`)
  - log: 2026-06-19 confirmed
- [x] **Fix** - fallback now requires `active`/`idle` (not `spawning`); the own-server redirect probes `/lab-ready` and enters only once the lab truly answers (60s deadline last-resort)
  - log: 2026-06-19 `useSpawnProgress.ts` fallback condition tightened + dead `isRunning` removed; `Starting.tsx` redirect gated on `hubGet('/users/{name}/lab-ready')`; tsc + eslint clean
- [x] **No premature 100%** - the bar stays `spawning` through the real spawn; reaches `ready` only on active/idle (fallback) or the hub `ready` SSE frame
  - log: 2026-06-19 code
- [x] **Logs shown** - phase stays `'spawning'` for the spawn duration, so `useContainerLogTail` keeps polling and renders lines while the container boots
  - log: 2026-06-19 code
- [ ] **Verified** - confirmed on the live stack after the operator rebuilds the image
  - log: 2026-06-19 pending rebuild
- [ ] **Edge: log endpoint reachability** - confirm `GET /api/users/{name}/server/logs` returns 200 during a spawn; a 500 would mean the hub can't reach the docker socket (a separate cause of empty logs the silent catch hides)
  - log: 2026-06-19 runtime check to rule out a second cause

### Cross-references

- acc-crit: [dedicated Start-server page with live container-log feed](acc-crit-duoptimumhub.md#dedicated-start-server-page-with-live-container-log-feed)
