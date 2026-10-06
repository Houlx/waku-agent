# Dashboard frontend — the map

Plain static files served as-is by `waku/ops/dashboard.py` (a stdlib HTTP
server). **No build step, no framework, no bundler, no dependencies.** Edit these
files to change the UI; edit `dashboard.py` to change the server/API.

- `index.html` — the shell (sidebar nav, `<main>`, chat dock) + the ordered
  `<script>` tags.
- `style.css` — one flat file of rules; every value comes from the tokens in
  `design/` (see "Design system" below).
- `design/`, `fonts/` — the Waku Memory design system and its three fonts.
- `js/` — the app, split by concern (below).

## The Career product

`waku` and `waku career` serve `career.html` through `career_dashboard.py`.
`make dashboard` starts Career; `make legacy-dashboard` starts the old shell.
The dedicated server allows only `career.html` and its eight Career assets.

`career/` contains small classic scripts sharing the `CA` namespace:

| File | Responsibility |
|---|---|
| `ui.js` | Escaping, JSON requests, independent primitives and theme behavior |
| `state.js` | Saved snapshot, editor drafts, request progress and provider state |
| `router.js` | Hash parsing, stable job URLs, compatibility redirect and navigation |
| `actions.js` | Draft editing, explicit submissions, failure recovery and exports |
| `render.js` | Overview, grouped profile, jobs, reports, evidence and resumes |
| `settings.js` | Provider readiness, retained form inputs and explicit configuration |
| `bootstrap.js` | Initial reads and routing; no polling or AI actions |
| `style.css` | Independent Career visuals, responsive layout and resume print isolation |

Rendering starts no requests and creates no drafts. Navigation owns URL state;
a navigation counter prevents action completion from redirecting a user who moved
away. Saved artifacts, raw/profile/JD/language drafts and request errors have
separate owners. Drafts stay in memory for the tab; only the theme uses storage.
Busy editors disable inputs while allowing navigation. Settings retains its own
form and failure state even after the user leaves it.

The Career shell loads no old helper scripts, design files, fonts, mark or favicon.
MIT helper behavior is adapted with independent appearance. The rollback files
below remain unchanged for Phase 3. Verify Career with the checked-in
[browser regression](../../../docs/career.md#run-the-browser-regression) and
`test_career_assets.py`, which audits the actual loaded graph and its network/timer
boundary. Real-provider evaluation is separate.

## The files (`js/`), in load order

They are **classic scripts sharing one global scope** — a `function`/`let`/`const`
in one file is visible to all the others. Order matters only in that **`main.js`
runs the bootstrap and must load last**.

| file | what lives here |
|------|-----------------|
| `util.js`    | `esc`, markdown renderer, core globals (`D`, `editing`), `postJSON`, `reveal`, `stampSlots` |
| `theme.js`   | the system / light / dark toggle (`cycleTheme`), stored as `waku-theme` like the Memory console |
| `memory.js`  | inline Memory / SOUL / skill editing actions |
| `models.js`  | `applyModel` (the one `/api/settings` writer), model picker / catalog / pins |
| `render.js`  | formatters + chat card renderers (`stagesRow`/`teleFooter`) + chatlog + streaming + `sendChat` |
| `diagram.js` | `archSVG` (the architecture chart) **and** its live animation (`STAGE`/`hot`/`pollEvents`) |
| `graph.js`   | graph workflows: data-driven topology chart (`graphSVG` from `d.graph.workflows`), the Overview panel (`graphPanel`), and `animateGraphStage` for `graph_*`/`route` events |
| `views.js`   | subtab/db helpers, SQL console, Memory/Tools sub-views, the `VIEWS` router object |
| `compare.js` | the Model arena (`Arena` tab; internals keep the `compare` name) — race one message through several models at once |
| `dock.js`    | chat sessions/history (`loadThreadInto`), model chip, stats toggle |
| `career.js` | local Career onboarding, profile confirmation, job analysis, evidence reports, cited resume review, Markdown export and printing; preserves form drafts during polling |
| `main.js`    | `render`/`refresh` loop, resizers, voice, and the bootstrap (**loads last**) |

Data flows one way: `refresh()` (main.js) fetches `/api/data` into the global
`D`, then `render()` writes `VIEWS[hash](D)` into `#view`. Every mutation
(`applyModel`, `pinModel`, `saveFact`, …) calls `refresh()` when it's done.

## Rules that bite (read before editing)

- **Inline handlers need global names.** Buttons use `onclick="fn()"` in the
  HTML strings the JS generates. `fn` must stay a top-level name in some `js/`
  file. Rename/move a handler and forget its call sites → the button silently
  breaks. `test_static_assets.py` guards this.
- **`archSVG` is byte-frozen — do not rewrite the architecture chart.** It emits
  `data-node="…"`/`data-edge="…"` ids that the `STAGE` map (same file) drives the
  live animation from. If you ever change a node/edge id, change it in both
  places. (Both are in `diagram.js` precisely so they stay together.)
- **The graph chart is data-driven — never hand-edit a topology.** `graphSVG`
  renders `Graph.describe()` served in `/api/data`, so the picture is provably
  what the engine runs (`test_graph_topology_payload.py` pins it). To change the
  chart's shape, change the workflow in `waku/graph/workflows/`. Graph ids are
  namespaced `g-<node>` / `g-<src>-<dst>` so they can never collide with archSVG's.
- **No build step / no framework / no new dependencies.** If you reach for one,
  stop — the whole point is that this reads and runs with nothing installed.
- **No emojis in UI** (project rule). Known pre-existing exception: the `★`/`☆`
  pin stars in `models.js` (typographic dingbats, not colour emoji) — left as-is.

## Design system

How the dashboard looks, the token rules and the `js/ui.js` primitives are in
[docs/context/design-system.md](../../../docs/context/design-system.md). Read it
before changing how anything looks.

## Verifying a change (no JS test runner exists)

Frontend logic is not unit-tested; verify in the browser preview:
`make dashboard` (or the preview tool) → hard-reload `localhost:7777` → click the
sidebar tabs and the chat dock → check the console shows **zero errors**. The
Python side (`dashboard.py` endpoints, `_thread_history`, pins, session resume)
*is* covered by `evals/deterministic/`.

**A running server does not pick up Python changes.** Static files here (`.js`,
`.css`, `index.html`) are read from disk on every request, so a hard-reload shows
them. But `dashboard.py` and everything it imports are held in memory — after
pulling or editing backend code, **restart `make dashboard`**, or the page renders
new markup against stale data (e.g. a new Settings panel that shows nothing because
the old route isn't sending its fields).
