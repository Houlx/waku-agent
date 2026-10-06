# Career frontend

Career serves plain static files through `waku/ops/career_dashboard.py`, a stdlib
HTTP server. It uses no build step, framework or bundler.

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

The shell loads only its seven scripts and one stylesheet. Career uses system
fonts, independent styles and no protected Waku assets. The server allows only
`career.html` and these eight assets; other static paths return JSON 404.

## Verification

Run the scripted [Chromium journey](../../../docs/career.md#run-the-browser-regression)
and Career asset/HTTP deterministic checks. For manual checks, launch `make dashboard`,
visit Career routes and Settings, and inspect the browser console.
Static files are read on each request; restart after Python backend changes.
