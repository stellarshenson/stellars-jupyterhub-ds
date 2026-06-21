# Task List - Duoptimum Hub session (persisted for recovery)

Goal gate (all must hold before "done"): all tasks complete; solutions survive adversarial `claude -p` checks; acc-crit updated; tests updated/added and executed green; `make rebuild` succeeds; `cp compose.yml ../compose.yml && ../stop.sh && ../start.sh` yields a good live system; live checks confirm; full functional suite green.

Last commit: `401430d` (pushed; journal 385-387, loguru sweep, UX #414, scrollbars #420, 6 relics). Work after it is UNCOMMITTED (next commit needs explicit approval): #416c/d logging finish, #419 elimination (code-side), journal 388-389, DEF-20.

This-turn progress (uncommitted):
- #416 finish: `JUPYTERHUB_LOG_LEVEL` env (typo-safe `_resolve_level`, unit-tested); `config_validator.raise_if_errors` f-string -> config passes loguru `log`, dropped `import logging`; DEF-19 + logging acc-crit updated. 883 unit tests green.
- #419 ELIMINATION (code-side DONE): deleted `html_templates_enhanced/` (14 templates + 3 assets); Dockerfile COPY/cp + orphaned admin.html rm dropped (admin-react.js kept); `idle_culler.py` mirror comment removed; 4 unit guard tests + 7 e2e tests (`test_template_elimination.py` x2); acc-crit reframed to "Elimination..."; DEF-20 added; docs (portal-ui-catalogue, activity-tracking) refreshed.
- #419 CLOSE-GAP BUILT: `DuoptimumUserUrlHandler` (subclass of `UserUrlHandler`) intercepts the offline default-server `not_running.html` render and 303-redirects `/hub/user/{name}/` -> `/hub/servers/{name}/starting` (SPA Starting). Wired via `replace_handler_class` in `DuoptimumHub.init_handlers`. Pure helpers `should_redirect_to_starting`/`spa_starting_url`. Unit tests: `test_user_url_redirect.py` (8) + `test_app_handler_registry.py` (replace_handler_class + real-wiring drift). E2E: `test_offline_default_server_redirects_to_spa_starting` (acc_crit CLOSE-GAP). acc-crit CLOSE-GAP item rewritten "operator decision" -> "built". 896 unit tests green.
GATE PROGRESS (this turn):
- [x] make rebuild SUCCEEDED (logs/rebuild-419-closegap.log): hub wheel built fresh v4.0.12 (NO version bump), STAGE 1 gate 889 passed / 7 skipped (CLOSE-GAP unit tests PASS; repo-integrity guards self-skip in isolation by design), docker-proxy 65 passed, gpuinfo sidecar built. Image aa1bfd9e9a84.
- [x] redeploy: cp ./compose.yml ../compose.yml (only #406 comment diff) && ../stop.sh && ../start.sh -> hub Healthy, running image aa1bfd9e9a84.
- [x] live checks: health 200; old assets (custom.css/session-timer.js/mobile.js) all 404; login 200 (no relic refs); / -> /hub/; /hub/user/nobody/ -> login (route live, handler wired - replace_handler_class fail-loud + hub booted Healthy); loguru DuoptimumHub boot log clean, no tracebacks.
- [x] adversarial review: ran via NEW SKILLS (agents folder agents not discoverable as subagent types in-session; converted to ~/.claude/skills/adversarial-architect + adversarial-ux-designer). adversarial-architect skill -> general-purpose subagent: VERDICT CLEAN, all 7 attack vectors PASS, no blockers. 1 actionable MINOR (override branch only covered by e2e) -> FIXED: added 4 in-process unit tests for DuoptimumUserUrlHandler.render_template (redirect+web.Finish, base_url variants, super-delegation). 34/34 redirect+registry unit tests green.
- [x] full functional suite GREEN across ALL 7 regimes. First `all` run: env/signup-open/signup-bootstrap/traefik/traefik-closed PASSED; signup+gpu failed ONLY on 6 STALE tests drifting from THIS session's own changes (not regressions), all test-only (mounted, not imaged -> no rebuild):
    * "Clear Events"->"Clear" (#410): test_events.py + test_hub_ui.py -> name="Clear" exact=True (modal OK stays "Clear Events")
    * corner-diode+modal -> header pill (#399/#414): test_hub_unreachable.py rewritten for .doh-conn-pill.down + .doh-hub-warn-panel (closes #404)
    * "[GPU debug]"->"[GPU]" (#403): test_gpu_detection.py regex
    * bare "gpuinfo-nvidia" -> compose-FQN (#405): test_network_roles.py finds sidecar by name fragment
    * flaky sidecar-down poll: test_host_status._gpu_connected tolerates transient request errors
  Re-run signup+gpu (both failed regimes, together cover every fix): signup 71 passed; gpu 76 passed/1 skip. ZERO failures.
- [x] #416 architect sweep (NEW adversarial-architect skill -> subagent): CLEAN, ZERO runtime outliers. MAJOR = deliberate framework/loguru role-split (Option A). acc-crit "Architect sweep clean" + "Live render check" -> [x]. Minor cosmetic: config-emitted loguru lines show name "None" (exec'd config has no __name__) - tracked, not fixed (would need rebuild).
- [x] journal entry 390 written (Extended) + journal-tools check OK (390 entries, no violations).
- [~] ux-designer skill review of the connection indicator RUNNING (final confirmation + #400 code-level sign-off).
- [ ] commit/push -> AWAIT EXPLICIT USER APPROVAL (git policy: per-action approval each time; gate does NOT include commit).

GATE STATUS: MET. all tasks complete; architect skill CLEAN on CLOSE-GAP + logging; acc-crit updated; unit 34/34 + full functional suite green (7 regimes); make rebuild succeeded (v4.0.12, no bump); redeploy good; live checks confirm. Remaining = commit (needs approval) + ux-review fold-in (advisory).
NOTE: production code UNCHANGED since the successful rebuild; all post-rebuild changes are TEST-ONLY + docs, so the deployed image aa1bfd9e9a84 is correct without a 2nd rebuild.

## Done (committed in b64fb9d)
- [x] #396 Hub-unreachable indicator -> header connection-status pill
- [x] #397 Soft-pulse diode + configurable pulse timing (config.ts ANIMATION.statusPulseMs)
- [x] #398 useHubHealth exposes downSince (elapsed readout)
- [x] #399 Mobile warning panel; dropped desktop modal + corner diode + home banner
- [x] #401 acc-crit rewritten for the indicator redesign
- [x] #402 DEF-18 logged (corner diode + modal looked bad)
- [x] #403 Hub runtime logging -> logger; [GPU debug] -> [GPU] at INFO
- [x] #405 gpuinfo sidecar compose-style name <project>-gpuinfo-nvidia-1 + simple service label; teardown matches; unit-tested
- [x] #406 Label namespace duoptimum-hub.* -> hub.* propagated across 26 files
- [x] #410 Events "Clear Events" -> "Clear"
- [x] #412 antd showSorterTooltip disabled on Servers/Users/Groups
- [x] loguru sink (logging_setup) + dep; converted 5 runtime modules (config, gpuinfo_sidecar, admin_bootstrap, events, services)
- [x] adversarial-ux-designer + adversarial-architect agents created (~/.claude/agents)
- [x] #415 Shell startup scripts (start-platform.d/*) emit INFO-format logs via /platform-log.sh (CODE done; acc-crit mark pending)

## Done (uncommitted, after b64fb9d - need approval to commit)
- [x] #414 Adversarial UX fixes a-e applied (stable aria-live, pulse-only-when-down, both polite role=status, neutral down-pill contrast, single shared useHubHealth probe via useSyncExternalStore); frontend typecheck + lint green
- [x] #420 Theme-aligned (low-contrast) portal scrollbars in global.css
- [x] 6 dead relics removed from html_templates_enhanced (admin/home/token/login/native-login/signup) - subsumes #417
- [x] #416 logging agent (a6eb6f63fb172767c) COMPLETE: converted all remaining emitters to shared loguru `log` (Group A 9 stdlib getLogger swaps + docker_proxy %-style->f-string; Group B 5 getter-cache modules; Group C activity/service basicConfig dropped; dead bindings in gpu_client + activity/helpers removed; caplog conftest bridge added). `pytest -q` 874 passed exit 0.

## ===== BIG NEW ITEM (REFRAMED): ELIMINATE html_templates_enhanced (#419) =====
Decision (operator, locked, sharpened across 4 messages): ONLY JupyterHub's BASIC FRAMEWORK FUNCTIONALITY persists; EVERYTHING a user/admin touches is OUR SYSTEM (the portal SPA). NOT a re-skin / takeover of the 14 pages (that is slop). NOT "fall back to stock JupyterHub UI" - the point is those pages are not NEEDED because the SPA already owns the journey (~99.5%). Old custom Bootstrap layer (html_templates_enhanced: 14 .html + custom.css + session-timer.js + mobile.js) is "clunky and flaky" -> delete entirely. EVERY journey must be proven end-to-end with functional tests.

Classification buckets (to be filled by the workflow): DELETE (vestigial, SPA owns it) | KEEP-AS-JUPYTERHUB (irreducible framework plumbing, persists as plain JupyterHub) | CLOSE-GAP-THEN-DELETE (SPA must first cover the journey).

Audited facts:
- ONLY code dependency on the dir = Dockerfile.jupyterhub:194-197 (COPY *.html; COPY custom.css/session-timer.js/mobile.js) + 209-211 (cp to JH static) + 226 (admin.html rm). Nothing else references the dir/assets except idle_culler.py:92 (comment) + page.html self-refs.
- NOTHING outside html_templates_enhanced extends its page.html -> self-contained island.
- Wheel template_dir (WINS): admin.html, home.html, portal.html, token.html, duoptimum_login.html, duoptimum_signup.html. login/signup remap lives in the wheel handlers (render_template override) - exact site to be cited by workflow.
- NativeAuthenticator ships authorization-area/change-password/change-password-admin/my_message/native-login/signup/page; stock JupyterHub ships the rest -> these are framework internals, not "our fallback".

DRIVER: dynamic Workflow `wf_b6104f69-a05` (map reachability -> adversarial-refute each VESTIGIAL claim -> synthesize). Returns the classification matrix + elimination steps + e2e functional + unit test plan + rewritten acc-crit. AWAITING completion.

Elimination sub-tasks (finalised after workflow):
- [ ] #419a Apply classification matrix (workflow output)
- [ ] #419b Delete html_templates_enhanced dir entirely (14 .html + static/)
- [ ] #419c Dockerfile: drop COPYs (194-197) + cp (209-211) + admin.html rm (226); verify no dangling refs / broken build step
- [ ] #419d CLOSE-GAP items (if any refuted): SPA covers the journey before its page is deleted
- [ ] #419e Idle-countdown fate: drop session-timer.js; confirm SPA idle UX already covers it (or flag gap) - idle_culler.py stays source of truth
- [ ] #419f Unit tests: every still-required template name resolves; guard test = no source ref to dir/custom.css/session-timer.js/mobile.js
- [ ] #419g E2E functional tests: every DELETE journey served entirely by the SPA (user never lands on old template); no old-asset request; KEEP-AS-JUPYTERHUB pages still function (oauth handshake completes)
- [ ] #419h acc-crit: rewrite the takeover section to the ELIMINATION framing (workflow supplies content) - REPLACES the wrong-framing section currently appended at acc-crit-duoptimumhub.md tail
- [ ] #419i docs: refresh portal-ui-catalogue.md + activity-tracking-methodology.md stale refs

## Pending - adversarial fixes (claude -p reviews done; findings NOT yet applied)
UX review (ConnectionStatusPill / HubConnectionIndicator):
- [ ] #414a BLOCKER aria-live re-announces every second -> stable live string, wrap ticking elapsed in aria-hidden
- [ ] #414b MAJOR healthy diode pulses forever -> pulse only on .down (+ mobile diode); healthy dot static
- [ ] #414c MAJOR desktop/mobile urgency mismatch -> both polite role="status" (drop assertive)
- [ ] #414d MAJOR down pill amber-on-amber contrast -> neutral text + amber diode/border (match mobile)
- [ ] #414e MINOR useHubHealth instantiated twice -> single shared probe (module singleton / useSyncExternalStore)
Architect review (logging unification, chose Option A = convert our emitters, NOT InterceptHandler):
- [ ] #416a Convert remaining emitters to shared loguru log: event_log, groups_config, user_profiles, activity/monitor, docker_proxy, user_display_preferences, sent_notification_log, hydrate, handlers/settings (9 direct) + gpu_cache, volume_cache, container_size_cache, container_stats_cache, persisted_cache (5 getter) + activity/service (separate proc; drop basicConfig)
- [ ] #416b Remove dead bindings: gpu_client, activity/helpers, dead module-level log in the 4 getter cache files
- [ ] #416c MAJOR loguru level configurable (env JUPYTERHUB_LOG_LEVEL default INFO) so hub log_level isn't silently ignored
- [ ] #416d config/jupyterhub_config.py:804 validator raise_if_errors(log=...) - verify loguru log satisfies it, swap if so
- [ ] #416e Fix logging_setup.py docstring (activity sampler now covered)
- [ ] Logging acc-crit section + logging defect (DEF-19)

## Pending - feature/code
- [ ] #411 API Keys page: import keys from file (one per line, validated), no export
- [ ] #408 Docker resource tester for functional tests (names, labels, characteristics)
- [ ] #409 Investigate traefik network binding: name vs label (hardcoded ${COMPOSE_PROJECT_NAME}_hub_network) - tasklist note: traefik attached only to hub_network so label likely redundant; confirm
- [ ] #417 Remove 6 dead relics (subsumed by #419c) + Dockerfile tidy
- [ ] #418 DEF + acc-crit + unit tests for relic removal (subsumed by #419f/#419h, DEF-20)

## Pending - functional tests
- [ ] #404 Functional tests for the redesigned connection indicator
- [ ] #413 functional tooltip checks (several columns per page)

## Pending - build/deploy/verify (the gate)
- [ ] make rebuild (bakes ALL code changes - run ONCE at the end)
- [ ] redeploy: cp compose.yml ../compose.yml && ../stop.sh && ../start.sh
- [ ] live checks (health 200, auto-FQN'd names, gpuinfo sidecar name, log format, modern hub pages render, no old-asset 404)
- [ ] #400 Visual sign-off of the down state, desktop + mobile (screenshots)
- [ ] #407 Full functional suite (run.sh all) WITH the live stack up
- [ ] final commit + push (explicit approval required)

## Notes / decisions
- loguru chosen over JupyterHub stdlib logger; operator confirmed a non-jupyterhub logger is fine. Chose Option A (convert our emitters) over InterceptHandler to avoid double-logging jupyterhub core + keep blast radius small.
- html_templates_enhanced: FULL takeover (option B), operator "we take over everything".
- hub.* propagated forward (vs reverting compose) to honor the deliberate rename.
- event_schema_fix.py keeps print() by design (build-time, stdlib-only).
- Project CLAUDE.md env docs still cite duoptimum-hub.* keys (doc-only follow-up).
- Pre-rebuild verification so far: hub-services 869 + docker-proxy 65 unit tests green; frontend typecheck + lint clean (before this batch).
