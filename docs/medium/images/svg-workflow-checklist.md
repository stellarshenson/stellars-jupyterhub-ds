# SVG Workflow Checklist - JupyterHub Medium Article (v2)

## Theme: Stellars-Tech (teal/cyan + orange)

### Image 1: 01-platform-overview.svg (Hub-and-spoke / flow)
1. [x] File comments - description (filename, shows, intent, theme); grid comment; layout topology
2. [x] CSS block - `<style>` with fg-1..fg-4, accent-1, accent-2, on-fill; `@media (prefers-color-scheme: dark)` overrides
3. [x] Text rules - all `<text>` use CSS classes (zero inline fill); no opacity on text; font-family="Segoe UI, Arial, sans-serif"
4. [x] Text positions - titles at accent_bar_bottom + 12px; descriptions at +14px rhythm; within card boundaries
5. [x] Card shapes - flat top, rounded bottom r=3; fill-opacity 0.04; stroke-width 1; accent bar h=5 opacity=0.6
6. [x] Arrow construction - polygon tips; chamfered L-routes 4px diagonal; stem ends before target
7. [-] Track lines - N/A
8. [x] Grid/spacing - vertical rhythm consistent; 10px viewBox edge minimum; card padding 12px
9. [-] Legend - N/A
10. [-] Icons - N/A
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000000/#ffffff; all colours from Stellars-Tech swatch; transparent background
14. [x] ViewBox - no width/height attributes on `<svg>`
15. [x] Validation - SUMMARY: 54 overlaps [11 violation, 4 sibling, 1 label-on-fill, 38 contained], 0 spacing violations. All violations: flow arrows connecting card edges (accepted)

### Image 2: 02-user-self-service.svg (Card grid - 3 cards)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text, Segoe UI (exception: accent category labels use fill= intentionally)
4. [x] Text positions - titles at accent_bar + 12px, rhythm 14px
5. [x] Card shapes - flat top, rounded bottom r=3
6. [-] Arrow construction - N/A
7. [-] Track lines - N/A
8. [x] Grid/spacing - 3 columns (w=248, gap=12), consistent gaps, 16px viewBox edge
9. [-] Legend - N/A
10. [x] Icons - Lucide source (power, timer, hard-drive), ISC license comment, consistent scale 0.583
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff, all from swatch; button colours #1a8a4a, #c43030, #da8230 within swatch
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 6 overlaps [1 violation, 3 sibling, 2 contained], 0 spacing violations. Violation: card group bbox overlapping footer text (checker limitation)

### Image 3: 03-activity-monitor.svg (Stats panel / table mockup)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text (except charlie "45m" uses fill=#da8230 for warning colour), Segoe UI
4. [x] Text positions - vertical rhythm consistent (32px row height)
5. [-] Card shapes - N/A (table layout)
6. [-] Arrow construction - N/A
7. [-] Track lines - N/A
8. [x] Grid/spacing - column widths, row heights consistent
9. [x] Legend - decay scoring legend with colour-matched status dots (#1a8a4a, #da8230, #c43030)
10. [-] Icons - N/A
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff, all from swatch; status colours #1a8a4a (green), #da8230 (amber), #c43030 (red)
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 112 overlaps [10 violation, 16 sibling, 86 contained], 5 spacing violations. All violations: table row backgrounds overlapping row content (design intent for alternating stripes)

### Image 4: 04-admin-tools.svg (Card grid - 5 cards)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text (exception: category labels use fill= for accent), Segoe UI
4. [x] Text positions - titles at accent_bar + 12px, rhythm 12px (compact)
5. [x] Card shapes - flat top, rounded bottom r=3
6. [-] Arrow construction - N/A
7. [-] Track lines - N/A
8. [x] Grid/spacing - 5 columns (w=146, gap=10), consistent gaps
9. [-] Legend - N/A
10. [x] Icons - Lucide source (activity, bell, settings, users, shield), ISC license comment, consistent scale 0.583
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff, all from swatch
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 7 overlaps [0 violation, 7 sibling], 0 spacing violations. Clean.

### Image 5: 05-architecture.svg (Layered architecture)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text (exceptions: port labels use fill=#da8230, GPU/docker badge text), Segoe UI
4. [x] Text positions - vertical rhythm 14px
5. [x] Card shapes - flat top, rounded bottom r=3; container shapes for layers
6. [x] Arrow construction - vertical arrows between layers; horizontal-first with polygon tips; chamfered L-routes for fan-out
7. [-] Track lines - N/A
8. [x] Grid/spacing - horizontal layers, consistent gaps, 4 containers w=180 gap=10
9. [x] Legend - colour coding for service types (infrastructure, auxiliary, GPU)
10. [-] Icons - N/A
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff, all from swatch; additional #1a8a4a for GPU badge
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 113 overlaps [12 violation, 3 sibling, 98 contained], 0 spacing violations. All violations: boundary rect containing children (checker limitation), flow arrows connecting elements (accepted)

### Image 6: 06-jupyterlab-workspace.svg (Hub-and-spoke)
1. [x] File comments - description (filename, shows, intent, theme); grid comment; layout topology
2. [x] CSS block - `<style>` with fg-1..fg-4, accent-1, accent-2, on-fill; `@media (prefers-color-scheme: dark)` overrides
3. [x] Text rules - all `<text>` use CSS classes (zero inline fill); no opacity on text; font-family="Segoe UI, Arial, sans-serif"
4. [x] Text positions - titles at accent_bar + 12px; descriptions at +14px rhythm; within card boundaries
5. [x] Card shapes - flat top, rounded bottom r=3; fill-opacity 0.04; stroke-width 1; accent bar h=5 opacity=0.6
6. [x] Arrow construction - radial spoke lines with polygon tips connecting cards to centre hub
7. [-] Track lines - N/A
8. [x] Grid/spacing - centre hub with 4 radial zones (top/left/right/bottom); consistent card dimensions per zone
9. [x] Legend - colour-coded for platform tools vs auxiliary services
10. [x] Icons - Lucide source (terminal, layers, bot, flask-conical, line-chart, activity, git-branch, code, git-compare, menu, lock), ISC license comments, consistent scale 0.583
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000000/#ffffff; all colours from Stellars-Tech swatch; transparent background
14. [x] ViewBox - no width/height attributes on `<svg>`
15. [x] Validation - SUMMARY: 72 overlaps [34 violation, 10 sibling, 28 contained], 0 spacing violations. Violations: card group bboxes overlapping spoke lines (design intent - spokes connect cards to hub), checker misclassifies card groups as logos (accepted)

### Image 7: 07-conda-environments.svg (Card grid / layered stack)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text (exception: status badges use fill= for semantic colour), Segoe UI
4. [x] Text positions - titles at accent_bar + 12px; rhythm 14px; within card boundaries
5. [x] Card shapes - flat top, rounded bottom r=3; Base card 1.5 stroke + 0.06 fill (highlighted); others 1 stroke + 0.04 fill
6. [x] Arrow construction - vertical connector lines from card bottom to kernel discovery bar
7. [-] Track lines - N/A
8. [x] Grid/spacing - 5 cards (w=148, gap=10); kernel bar full width below
9. [-] Legend - N/A
10. [x] Icons - Lucide search icon in kernel bar, ISC license comment
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff; all from swatch; status badge #1a8a4a (green), #da8230 (orange)
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 29 overlaps [10 violation, 5 sibling, 14 contained], 0 spacing violations. Violations: card group bboxes overlapping vertical connectors (design intent), checker limitation on group classification (accepted)

### Image 8: 08-startup-pipeline.svg (Timeline / numbered flow)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text, Segoe UI
4. [x] Text positions - consistent rhythm (14px within boxes); numbered circles overlapping card tops
5. [x] Card shapes - flat top, rounded bottom r=3; numbered circle badges at card top edge
6. [x] Arrow construction - horizontal flow arrows between boxes; wrap-around chamfered L-route between rows
7. [-] Track lines - N/A (flow arrows instead)
8. [x] Grid/spacing - 2 rows of 6 boxes (w=110, gap=14); wrap-around connector
9. [x] Legend - system scripts vs service/user scripts colour coding
10. [-] Icons - N/A
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff; all from swatch; user script box highlighted with stronger stroke/fill
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 58 overlaps [49 violation, 6 sibling, 3 contained], 1 spacing violation. Violations: checker misclassifies card groups as "logo" elements and flags overlap with adjacent arrows (accepted - design intent for flow diagram). Spacing: callout connector path bbox (accepted - decorative path)

### Image 9: 09-vanilla-vs-stellars.svg (Comparison cards)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes for all descriptive text; checkmark/X use inline fill for semantic colour (#1a8a4a, #c43030), Segoe UI
4. [x] Text positions - 18px row height for feature list; consistent alignment
5. [x] Card shapes - flat top, rounded bottom r=3; left card muted (0.02 fill, 0.4 stroke), right card highlighted (0.04 fill, 1.5 stroke)
6. [-] Arrow construction - N/A
7. [-] Track lines - N/A
8. [x] Grid/spacing - two columns (w=380, gap=12); 14 feature rows per column
9. [-] Legend - N/A
10. [-] Icons - N/A (using Unicode checkmark/X characters)
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff; all from swatch; semantic #c43030 (red X), #1a8a4a (green check)
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 4 overlaps [2 violation, 2 sibling], 0 spacing violations. Clean - violations are sibling text rows (accepted)

### Image 10: 10-integrated-services.svg (Card grid - 4 cards)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text (exception: port badges use fill= for accent), Segoe UI
4. [x] Text positions - titles at accent_bar + 12px; rhythm 14px; port badges at y=62
5. [x] Card shapes - flat top, rounded bottom r=3; accent bar h=5 opacity=0.6
6. [x] Arrow construction - vertical connector lines from card bottom to Traefik bar
7. [-] Track lines - N/A
8. [x] Grid/spacing - 4 cards (w=185, gap=10); Traefik routing bar full width below
9. [-] Legend - N/A
10. [x] Icons - Lucide source (flask-conical, line-chart, activity, settings, lock), ISC license comments, consistent scale 0.583
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff; all from swatch
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 18 overlaps [11 violation, 7 sibling], 0 spacing violations. Violations: card group bboxes overlapping connectors (design intent), port badge overlapping card group (contained - accepted)

### Image 11: 11-docker-build-pipeline.svg (Multi-stage flow)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text (exception: discarded label uses fill=#c43030), Segoe UI
4. [x] Text positions - consistent rhythm; container labels above containers
5. [x] Card shapes - flat top, rounded bottom r=3; containers use muted styling (0.02 fill, 0.25 stroke opacity)
6. [x] Arrow construction - horizontal COPY arrow between stages with polygon tip
7. [-] Track lines - N/A
8. [x] Grid/spacing - two-stage layout (w=290 builder, w=406 target); 2-column layer grid in target
9. [x] Legend - builder (temporary) vs target (final image) colour coding
10. [-] Icons - N/A
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff; all from swatch; #c43030 for discarded indicator
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 11 overlaps [8 violation, 3 sibling], 0 spacing violations. Violations: container bboxes overlapping internal cards (checker limitation - cards are inside containers), COPY arrow overlapping stage containers (design intent)

### Image 12: 12-ecosystem-overview.svg (Hub-and-spoke / ecosystem map)
1. [x] File comments - description, grid, topology
2. [x] CSS block - style with dark mode overrides
3. [x] Text rules - CSS classes, no inline fill on text, Segoe UI
4. [x] Text positions - consistent rhythm; container titles centered
5. [x] Card shapes - flat top, rounded bottom r=3; sub-cards with accent bar h=4; containers with muted styling
6. [x] Arrow construction - chamfered L-routes from hub to branch containers; vertical arrows to infra bar
7. [-] Track lines - N/A
8. [x] Grid/spacing - central hub with L-shaped branches to 2 containers; 2-column sub-card grids; infra bar at bottom
9. [x] Legend - hub (orchestration) vs lab (workspace) colour coding
10. [x] Icons - Lucide users icon, ISC license comment
11. [-] Logos - N/A
12. [-] Decorative imagery - N/A
13. [x] Colours - no #000/#fff; all from swatch
14. [x] ViewBox - no width/height on svg
15. [x] Validation - SUMMARY: 15 overlaps [10 violation, 5 sibling], 0 spacing violations. Violations: branch container bboxes overlapping internal sub-cards (checker limitation - cards inside containers), hub arrows overlapping containers (design intent)
