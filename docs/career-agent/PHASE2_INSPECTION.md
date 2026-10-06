# Phase 2 — Career Product Cutover inspection

> This historical document records an earlier project stage. [Current status](../status.md) and [the handoff](HANDOFF.md) describe the retained product.

Phase 2 will keep plain JavaScript, replace the transitional Career shell,
and separate routing, application state, draft state, request state and rendering.
The user approved this frontend recommendation after the inspection on 2026-10-06.
At inspection time, the user had not authorized Phase 2 implementation.
Separate approval subsequently authorized Phase 2 only; the current
[handoff](HANDOFF.md) records its implementation and verification.

V1 MVP and Phase 1 runtime separation are complete. Physical retirement of the
old Waku product remains Phase 3. Career should become the default product only
after the new UI passes acceptance.

## Starting context

Read [HANDOFF.md](HANDOFF.md) and
[CAREER_ONLY_REFACTOR_PLAN.md](CAREER_ONLY_REFACTOR_PLAN.md) before implementation.
Actual code governs current behavior. The refactor plan's earlier architecture
sections describe dependencies that Phase 1 has already removed.
[PRODUCT_SPEC.md](PRODUCT_SPEC.md) and
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) remain historical V1 references;
consult them only to resolve intended V1 behavior.

Phase 1 established `waku career`, the dedicated Career runtime, Career-only
database initialization, provider-only setup services and runtime/provider
serialization. Career startup does not require `app.Waku`, Memory, MCP, general
tools, graph or gateways. This inspection found no reason to redesign those
decisions. A concrete defect discovered during Phase 2 may justify a focused fix.

The inspection read the frontend, Career HTTP bootstrap, routing, provider setup,
static assets, styles and relevant regression contracts. It made no code changes
and ran no application, tests or provider calls. Historical verification in the
handoff is not fresh verification of this inspection.

## Current entry and HTTP bootstrap

`waku/__main__.py` dispatches `waku career` to
`waku/ops/career_dashboard.py`. `CareerServer` serves
`waku/ops/static/career.html` at `/` and owns its factory-created runtime.
The page already uses the title and heading "Career Agent". Its header contains
provider setup, a theme toggle and provider status; its main content uses `#view`.

The page loads these classic scripts in order:

1. `js/util.js` supplies shared helpers.
2. `js/ui.js` supplies HTML primitives and dialogs.
3. `js/theme.js` supplies theme behavior.
4. An inline script defines `VIEWS`.
5. `js/career.js` registers and renders the Career workspace.
6. `js/career_bootstrap.js` loads state and readiness and starts the page.

The bootstrap applies the stored theme, starts control-attribute stamping,
loads `/api/career` and reads `/api/provider-status`. It does not restore chat,
poll `/api/data`, poll `/api/events` or load the general dashboard bootstrap.

The Career handler already exposes a closed API surface:

| Method | Routes |
|---|---|
| GET | `/api/career`, `/api/provider-status`, `/api/models` |
| POST | `/api/career`, `/api/providers` |

The handler returns JSON 404 responses for unknown routes and checks static path
traversal. It serves any existing file beneath the shared static directory,
including `/static/index.html`; its static surface is not Career-only yet.
Loopback remains the default binding.

## Remaining Waku frontend dependencies

The Career page does not load `main.js`, `views.js`, `setup.js`, `models.js`,
the chat dock, diagrams, Memory, Graph or Arena scripts. The transitional launch
has already removed their visible navigation and background bootstrap.

| File | Current Career dependency |
|---|---|
| `js/util.js` | Career uses `esc`, `postJSON`, `stampSlots`, `watchSlots` and the `editing` global. |
| `js/ui.js` | Career uses cards, buttons, badges, notices and native dialogs. |
| `js/theme.js` | Career uses system/light/dark selection and persistence under `waku-theme`. |
| `style.css` | Career inherits global layout, typography, primitives, controls, forms, resume styles and print rules. |
| `design/fonts.css`, `tokens.css`, `type.css`, `controls.css` | Career inherits Waku's font loading, tokens, typography and control appearance. |
| `fonts/*.woff2` | The font-loading stylesheet references locally served fonts. |

`style.css` still defines the old rail, chat, diagram and arena styling. Its global
`body` rule uses a fixed-height flex layout; `main` scrolls independently. Those
rules originated in the rail/main/chat shell and still affect Career without
those elements. The stylesheet also retains a Waku mark mask reference, although
Career markup does not display the mark.

## Current state and rendering

At inspection time, `career.js` contained 249 lines and `career_bootstrap.js`
contained 55 lines. Both use shared global scope, template strings and inline
event handlers. Inline handlers require globally accessible function names.

`career.js` holds saved artifacts in `careerData`, a profile draft in
`careerDraft`, and the current screen in `careerMode`. Modes represent onboarding,
review, report, resume or the confirmed-profile dashboard. Other globals hold the
JD draft, selected job ID, one return mode, one language selection, one busy flag
and one error string.

`careerPaint()` replaces all of `#view.innerHTML`. Input handlers update draft
objects immediately, so subsequent renders can reconstruct their values.
Full replacement resets focus and native disclosure state. Report and resume
renderers embed evidence in native `details` elements.

`careerRun()` combines request submission, response handling, draft replacement
and screen transitions. Its busy flag prevents repeated Career submissions.
Normalization saves onboarding input first. Failed analysis preserves the JD
draft and refreshes jobs to recover the newly persisted failed job. Existing
renderers preserve confirmation, stale-analysis and explicit-generation gates.

The code is small enough to reuse, but route, editor and request transitions need
separate ownership. Profile records currently support work, education, project
and other types. Skills, languages, certifications and research appear within
record content or other records; Phase 2 does not require new schema entities.

## Navigation limitations

`career_bootstrap.js` forces every hash to `#career`. `careerPaint()` renders only
when the hash starts with `#career`. Screen changes alter globals rather than URLs.

- Profile, Jobs, Job Detail, Resume and Settings have no addressable routes.
- Browser back/forward cannot restore those screen transitions.
- Reload restores saved artifacts but loses screen selection and unsaved drafts.
- `careerReturnMode` remembers one mode rather than navigation history.
- Job-list handlers use array indices, although selected jobs use stable IDs.
- The UI has no deliberate unknown-job route state.
- Saved Jobs does not display coverage or MATCH/PARTIAL/GAP counts.
- Profile review follows record order rather than explicit grouped sections.

Draft preservation does not cover every transition. `careerStart()` reconstructs
the profile draft from saved data, so opening another editor can replace an
unsaved draft. Existing draft retention must become an explicit navigation
contract. Phase 2 must keep unsaved drafts in memory across navigation without
silently introducing persistence across reload.

## Provider setup

The Career provider form already uses provider-only services. It reads
`GET /api/provider-status`, submits `POST /api/providers`, and depends on
`openDialog`, `closeDialog`, `esc` and `postJSON`. Readiness reports configured
access without a background provider probe.

The form offers provider, free-text model, API key and base URL. It omits a blank
key from the payload to preserve saved credentials. Submission disables its save
button and displays configuration errors in the dialog. Changed keys or endpoints
may trigger explicit validation through the existing service.

`GET /api/models` exists, but the current Career form does not use it. Endpoint
suggestions populate when the provider changes rather than when the dialog first
opens. Settings may improve these controls using the existing narrow APIs.

Old `setup.js` and `models.js` depend on general dashboard state, refresh
functions, pins and small-model controls. Career does not need to load them.
Career Settings should expose the provider and main model needed for Career
stages, with actionable errors and preserved configuration rollback behavior.

## Reusable UI behavior and independent styling

Reuse MIT helper logic and product behavior where useful:

- Escape untrusted text, including quotes used in attributes.
- Preserve JSON request handling and semantic buttons, labels and fieldsets.
- Preserve cards, notices, status badges and native dialog behavior.
- Preserve native evidence disclosures and multiline source text.
- Preserve theme selection and theme application before first paint.
- Preserve resizable forms, resume language attributes and CJK font fallback.
- Preserve Markdown export and blob URL cleanup.
- Preserve resume-only printing, hidden debug/evidence content and pagination hints.

Career utilities do not need `D`, `editing`, chat Markdown rendering, session
helpers, reveal-file actions or shell-specific control selectors. Control stamping
currently supports Waku's `data-slot` styles; independent Career controls may use
their own explicit styling contract.

The Career rules at the end of `style.css` depend on Waku tokens. Preserve their
behavior while replacing their visual values. Print selectors currently assume
`main > #view > .career-resume`; layout changes must update print isolation too.

[LICENSE-BRAND](../../LICENSE-BRAND) separately protects the Waku design system,
mark and names. The user approved independent Career styling rather than
inheriting those protected assets. Do not edit copied files under `design/`.
Leave them available to the rollback dashboard until Phase 3.

The Career product must exclude the Waku mark/favicon, copied design styles,
Waku product promotion, the rail/chat identity, the four-pillar presentation,
the `waku-platform` logo and unrelated integration imagery. Third-party provider
logos are not required by the current text-based form. Font binaries have separate
OFL terms and may be retained with their notices; font licensing does not license
the Waku design system. Preserve upstream MIT attribution in About/README material.

## Frontend decision

Option A keeps plain JavaScript and replaces the Career shell. Option B would
introduce React and TypeScript for the frontend while preserving the backend.
The user approved Option A based on the inspected code.

| Criterion | Option A — plain JavaScript | Option B — React and TypeScript |
|---|---|---|
| Implementation effort | Extract existing code, introduce routes and state boundaries, and replace styles. | Perform the same product work plus convert renderers, handlers and forms and establish a build. |
| Regression risk | Reuse reduces initial conversion risk; navigation and drafts still require browser checks. | Conversion changes form ownership, disclosure behavior and print structure alongside navigation. |
| State and routing | An explicit store and small hash router fit the current screens. | Typed state and components help, but still require deliberate draft and asynchronous navigation rules. |
| Maintainability | Small modules suit this repository's readable static frontend. | Typed components help at larger scale but introduce a separate frontend toolchain. |
| Existing code reuse | Most form, action, report, evidence, resume and export logic can be adapted. | Contracts, field definitions and workflow rules survive; HTML-string renderers largely need conversion. |
| Build and tooling | Static files continue shipping with the Python package. | Dependency management, compilation, generated-asset packaging and build verification become necessary. |
| Screen suitability | The current request/response APIs support Profile, Jobs, Job Detail, Evidence, Resume and Settings. | These screens also fit React, but do not currently require it. |
| Portfolio value | Product architecture, provenance and reproducible acceptance provide substantial engineering evidence. | React/TypeScript skills add portfolio value when explicitly desired, but framework conversion adds work beyond V1 needs. |

The recommendation addresses global state, navigation and inherited styling.
It does not preserve the current global-mode architecture unchanged. React would
be more compelling if an approved later scope introduced substantially more
complex interacting editors, or explicitly required a React/TypeScript portfolio.
The inspected V1 does not establish that need.

## Phase 2 implementation boundaries

Separate five responsibilities without introducing a generic frontend framework:

| Responsibility | Required ownership |
|---|---|
| Routing | Parse and serialize Career URLs, resolve stable job IDs, handle compatibility and missing artifacts, and support history. |
| Application state | Hold saved profile, evidence, job and resume snapshots independently of the selected screen. |
| Draft state | Retain raw/profile/JD edits and pending language choices across navigation within the tab. |
| Request state | Track action, target, progress and error; prevent duplicate actions and avoid late responses overriding later navigation. |
| Rendering | Render the selected screen without starting AI work or recreating drafts as a side effect. |

Introduce addressable routes approximately matching:

| Route | User-facing purpose |
|---|---|
| `#overview` | Show profile readiness, recent analyses and the next useful action. |
| `#profile` | Support onboarding, grouped review, original evidence, editing and profile-level confirmation. |
| `#jobs` | List saved jobs, coverage, status counts and failed/outdated states. |
| `#jobs/<job-id>` | Show the JD, requirements, evidence, report, reanalysis and explicit generation. |
| `#jobs/<job-id>/resume` | Show the saved draft, language, evidence, stale notices, export and print. |
| `#settings` | Configure the Career provider, main model and credentials/endpoint. |

Preserve `#career` as a compatibility redirect. Unknown or unavailable job IDs
need a useful empty state. Direct links, refresh and browser history must restore
saved artifacts without running AI. Users must still explicitly generate or
regenerate resumes. Language selection must not regenerate a draft implicitly.

Keep Career coordinators, schema, IDs, storage paths, evidence snapshots,
invalidation and provider/runtime serialization unchanged. No schema migration or
new API is justified by these routes. The current snapshot supports client-side
job selection, coverage display and counts derived from saved matches.

## Browser acceptance and existing tests

The repository contains no checked-in automated Career browser journey or
frontend test runner at inspection time. HANDOFF records successful Chromium
journeys, but those historical runs are not a reproducible committed suite.

Committed protection includes Career profile/job/resume/acceptance evals,
runtime/provider separation tests and `test_career_http.py`. HTTP tests exercise
actual handlers, rejected general routes, traversal checks, CLI dispatch and
shutdown. Static asset, design-system and network/timer audits also protect shared
contracts. `test_browser_agent.py` tests the backend browser-agent service; it is
not a browser UI journey.

Existing static checks generally scan `index.html` and all JavaScript together.
They can miss a function absent from Career's actual loaded scripts. Design checks
primarily protect the old Waku shell. Preserve rollback contracts and add
Career-specific contracts rather than retaining unwanted assets to satisfy tests.

Add a reproducible committed browser regression using an isolated temporary home
and scripted model responses. It must cover:

- Provider setup, missing-provider errors and configuration failure recovery.
- Onboarding, record changes, normalization, grouped review and confirmation.
- Routes, direct links, reload, back/forward and unknown job IDs.
- Draft retention across navigation and delayed action responses.
- Duplicate submission prevention and failed-stage artifact retention.
- Analysis, all three match statuses, coverage and evidence disclosure.
- Explicit generation, language choices and stale-analysis/resume gates.
- Markdown download, both themes, print isolation and CJK heading behavior.
- Zero page errors and requests confined to Career/provider APIs.

The browser harness should document its setup and execution without adding a
default Python dependency or making real-provider evaluation implicit. Run focused
Career regressions and applicable static, timer, design, route and license checks
alongside browser acceptance. Offline success does not establish real-model
semantic grounding or translation quality.

## Default-product cutover and likely files

Implement and accept the new Career UI before changing default launch behavior.
The no-argument `waku` currently launches general terminal chat. `make run` follows
that dispatch, while `make dashboard` starts the old dashboard module directly.
Align the normal development entry, CLI help and startup URL with Career only
after acceptance passes. Keep the old dashboard available as an explicit rollback
entry during Phase 2.

Restrict the Career static surface to its own approved assets if the new product
must exclude access to old shell pages. Hash routes need no server history fallback
or new backend endpoints. The current handler already rejects general APIs.

Hosted policy and route tests describe `dashboard.py`, not the separate Career
handler. Reconcile them if shared routes or hosted consumers change. Career must
remain blocked in hosted access; Phase 2 does not authorize hosting changes or
movement of code across the MIT/Elastic License boundary.

| Treatment | Likely files |
|---|---|
| Replace the visible shell | `waku/ops/static/career.html` |
| Replace routing/bootstrap and extract Settings | `waku/ops/static/js/career_bootstrap.js` |
| Separate state, actions and screen rendering | `waku/ops/static/js/career.js` and new Career-scoped modules |
| Add independent visual styling and utilities | New Career-scoped files beneath `waku/ops/static/` |
| Change default dispatch and launch commands after acceptance | `waku/__main__.py`, `Makefile` |
| Adjust shell/static serving and startup URL | `waku/ops/career_dashboard.py` |
| Extend HTTP and launch contracts | `evals/deterministic/test_career_http.py` |
| Add reproducible browser and Career asset contracts | New regression files and any required test-only harness |
| Reconcile shared audits where applicable | `test_static_assets.py`, `test_design_system.py`, `test_dashboard_background_header.py` |
| Update current-product documentation | `docs/career.md`, `docs/career-agent/HANDOFF.md`, frontend README, root README and affected architecture/status docs |

Old `index.html`, shell scripts, `style.css`, copied design files and general
backend implementation remain available for rollback. Phase 3 owns verified
physical retirement, packaging cleanup and archival decisions. Preserve user
runtime data, legacy tables, configuration, traces and the usage ledger throughout.
