# Dashboard frontend — the map

Career serves plain static files through `waku/ops/career_dashboard.py`, a stdlib
HTTP server. Career uses no build step, framework or bundler. Batch C2 removes
the old dashboard server. The following old assets await Batch D deletion; they
are outside the Career static allowlist.

- `index.html` — the shell (sidebar nav, `<main>`, chat dock) + the ordered
  `<script>` tags.
- `style.css` — one flat file of rules; every value comes from the tokens in
  `design/` (see "Design system" below).
- `design/`, `fonts/` — the Waku Memory design system and its three fonts.
- `js/` — the app, split by concern (below).

## The Career product

`waku` and `waku career` serve `career.html` through `career_dashboard.py`.
`make dashboard` starts Career. Batch A removes the old-shell Make shortcut.
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
MIT helper behavior is adapted with independent appearance. The old files
below remain for C2 asset retirement. C1 removes their general feature backends;
the old shell no longer supports chat, Memory, graph, voice or arenas. Verify Career with the checked-in
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

The old frontend table describes deferred files only. Its handlers, graph routes,
chat dock and polling no longer have a server or supported behavior contract.

## Design system

How the dashboard looks, the token rules and the `js/ui.js` primitives are in
[docs/context/design-system.md](../../../docs/context/design-system.md). Read it
before changing how anything looks.

## Verifying a Career change

Run the scripted Chromium journey described in [the Career guide](../../../docs/career.md).
For manual checks, run `make dashboard`, open `localhost:7777`, visit the Career
routes and Settings, and check the console for errors. Career assets and HTTP
contracts also have offline checks in `evals/deterministic/`.

A running server reads static Career files on each request. Restart the server
after editing `career_dashboard.py` or an imported Python module.
