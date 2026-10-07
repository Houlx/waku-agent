# Career frontend

Career serves plain static files through `waku/ops/career_dashboard.py`, a stdlib
HTTP server. It uses no build step, framework or bundler.

`career/` contains small classic scripts sharing the `CA` namespace:

| File | Responsibility |
|---|---|
| `ui.js` | Escaping, JSON requests, independent primitives and theme behavior |
| `i18n.js` | English/Simplified Chinese UI dictionaries, locale preference and number formatting |
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
separate owners. Drafts stay in memory for the tab; theme and UI locale preferences use browser storage.
Busy editors disable inputs while allowing navigation. Settings retains its own
form and failure state even after the user leaves it.

The shell loads only its eight scripts and one stylesheet. Career uses system
fonts, independent styles and no protected Waku assets. The server allows only
`career.html` and these nine assets; other static paths return JSON 404.

The desktop sidebar shows navigation and five recent jobs from the saved snapshot.
Below 900px it becomes an expandable navigation section. Job and Resume routes
select the same stable job-ID link. Full history and analysis remain at `#jobs`.
Job deletion uses the existing action API and a native localized confirmation dialog.
The delete action clears only that job's saved artifacts and remembered target/language.

Sticky bars keep primary profile, analysis, generation and export controls visible
within their own screen. Main content uses document scrolling. Print media hides
navigation, application controls and evidence disclosures while retaining the resume.

`career-locale` stores `en` or `zh-CN`. Saved preference wins; otherwise compatible
Simplified Chinese browser preferences select Chinese and other preferences select
English. Storage failures fall back to the tab's in-memory preference. Locale changes
render existing state without requests or AI calls. Stored field keys, generated prose,
resume language and diagnostic activity remain unchanged. Expected errors have translated
messages; unknown safe error details remain in their original language.

Job reports show scored groups separately from confirmation and non-scorable clauses.
Excluded clauses retain sources and reasons without match statuses. Coverage counts
only scored groups, and zero scored groups disable resume generation.

## Verification

Run the scripted [Chromium journey](../../../docs/career.md#run-the-browser-regression)
and Career asset/HTTP deterministic checks. For manual checks, launch `make dashboard`,
visit Career routes and Settings, and inspect the browser console.
Static files are read on each request; restart after Python backend changes.
