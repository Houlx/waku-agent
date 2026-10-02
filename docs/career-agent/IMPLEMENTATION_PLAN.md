# Career Agent Web MVP — Approved Final Implementation Plan

The user approved this plan before Day 1 implementation. [PRODUCT_SPEC.md](PRODUCT_SPEC.md)
holds the authoritative requirements. [HANDOFF.md](HANDOFF.md) records actual code
and the next stage's authorization.

## Final clarifications

The user approved these clarifications after approving the plan:

- Day 3 resume language defaults to the detected primary language of the JD,
  replacing the earlier English default below. The user can explicitly select
  Chinese, English, or Japanese. This adds no Day 1 scope.
- Career evidence stays reasonably coarse-grained. Each work experience,
  project, education entry, research experience, or other coherent career record
  receives an evidence ID. Skills, responsibilities, achievements, and metrics
  live inside that record. The implementation does not atomize individual facts.

The following sections preserve the approved final plan. The clarifications above
supersede conflicting defaults.

## A. Architecture Mapping

| Area | Existing Waku component reused | Addition and purpose |
|---|---|---|
| Database | `waku/db.py`: SQLite connection, additive initialization, FTS5 pattern | Six Career tables and one evidence index in the existing `state.db`. |
| Runtime | `waku/loop/agent.py`: `run_loop`; `waku/app.py`: assembly pattern | `waku/runtime/career.py` coordinates fixed product stages around the existing loop. It does not create another agent engine. |
| Prompts | Existing `system` argument to `run_loop` | Stage-specific prompts in `waku/runtime/career.py`; no changes to `DEFAULT_SOUL` or ordinary session prompts. |
| Tools | `waku/tools/registry.py`: `Tool`, `ToolRegistry`, safe execution | Career factories in `waku/tools/career.py`; register only in stage-local registries. |
| Models | `waku/loop/models.py`: configured client and Anthropic-compatible interface | Reuse the configured dashboard client and model. No new SDK or direct provider integration. |
| Tracing | `waku/ops/tracing.py`: `Tracer`, observer composition, usage ledger | Career stage and artifact IDs in events; a concise activity display without reasoning transcripts. |
| Backend | `waku/ops/dashboard.py`: HTTP handlers and serialized agent execution | Thin Career API handlers calling the coordinator. |
| Frontend | Existing static dashboard, `VIEWS`, classic scripts, UI primitives | `waku/ops/static/js/career.js`, Career navigation, and token-based styles. Preserve drafts during polling. |
| Evaluation | `evals/helpers.py`: scripted clients; `evals/deterministic/` | Career behavioral tests and four small representative JD fixtures. |

Career runs bypass `Waku.respond()` because it assembles conversational memory,
ordinary tools, chat persistence, and consolidation. They reuse its underlying
loop, client, connection, and tracing components directly.

## B. Final Minimal Database Schema

Use the existing SQLite database. Initialize Career tables additively and
idempotently; do not clear runtime data.

| Table | Purpose and important columns | Relationships |
|---|---|---|
| `career_profile` | Singleton current profile: `id`, `raw_input_json`, `user_edits_json`, `normalized_json`, `confirmed`, timestamps | Owns Career evidence. Original onboarding input remains separate from normalization and explicit edits. |
| `career_evidence` | Current factual records: integer primary key, stable `evidence_id`, `profile_id`, `source_type`, `source_id`, `raw_text`, `normalized_json`, `search_text`, `active` | Sources reference onboarding records or explicit user edits. |
| `jobs` | Pasted JD and current analysis: `id`, `raw_jd`, `title`, `summary`, `responsibilities_json`, `status`, `outdated`, `coverage`, `report_json`, `activity_json`, timestamps | Owns requirements and current resume. Report JSON contains strengths, gaps, and recommended focus. |
| `job_requirements` | Atomic requirements: `id`, `job_id`, `text`, `category`, `importance`, `keywords_json`, `source_excerpt` | Each requirement belongs to one job. |
| `job_matches` | Current assessment: `requirement_id`, `status`, `evidence_ids_json`, `reason` | One match per requirement; cited evidence IDs are validated in application code. |
| `resumes` | One current draft per job: `id`, unique `job_id`, `language`, `content_json`, `activity_json`, timestamps | Structured claims contain evidence IDs. Markdown and HTML derive from this content. |

Additional rules:

- Application code assigns source and evidence IDs; the LLM references them
  rather than inventing them.
- Evidence IDs survive edits to the same record and are never reassigned to
  unrelated facts. Removed evidence becomes inactive.
- `career_evidence_fts` indexes `search_text`, which combines normalized
  descriptions, skills, tags, and raw text. Use external-content FTS5 and
  insert/update/delete triggers following Waku's existing pattern.
- Search and validation accept only active evidence from the confirmed profile.
- Rerunning a job replaces its requirements and matches in a normal transaction.
  No artifact history, revision tables, or dependency graph is introduced.
- Saving a factual profile change clears confirmation and marks existing analyses
  outdated. Existing reports and resumes remain viewable with an outdated notice;
  generation requires reanalysis.

## C. Career Agent Runtime

The coordinator executes a fixed sequence:

1. Normalize the profile.
2. Extract JD requirements.
3. Retrieve evidence and assess matches.
4. Calculate coverage in Python.
5. Generate a resume only after a separate user action.

Each LLM stage invokes the unchanged `run_loop` with fresh messages, a dedicated
system prompt, and a restricted registry.

| Stage | Tools exposed |
|---|---|
| Profile normalization | `submit_stage_result`, configured for a normalized profile |
| JD extraction | `submit_stage_result`, configured for job requirements |
| Evidence matching | `search_career_evidence`, `get_evidence`, and match-result submission |
| Resume generation | `get_evidence` and resume-result submission |

`submit_stage_result` validates and captures a structured proposal. The coordinator
persists it after the stage completes successfully. It does not let the model
choose arbitrary tables or action types.

Use the existing configured iteration limit, capped at ten per stage. Bound
retrieval results and permit a batch of queries in one search call. The agent can
formulate synonyms and perform additional searches; application code does not
prescribe one query per requirement.

If the loop reaches its limit, returns invalid output, or fails without a valid
submission, show an actionable error and retain saved inputs. Do not publish a
completed report from partial results.

Career runs receive no general chat history, retrieval gate, consolidation, MCP
tools, or ordinary Waku tools. Profile and JD text enter as explicitly delimited
data, never as system instructions.

## D. Tool and Capability Design

| Capability | Type | Input → output | Responsibility |
|---|---|---|---|
| `normalize_profile` | LLM stage | Raw records and explicit edits → structured profile and evidence proposals | Organize facts, wording, skills, and tags without adding qualifications. |
| `analyze_job` | LLM stage | Pasted JD → job summary and atomic required/preferred requirements | Extract requirements and retain supporting JD excerpts. |
| `search_career_evidence` | Deterministic tool | Agent-authored query list → ranked IDs and summaries | Safely tokenize queries, execute bounded FTS5 searches, deduplicate results, and return factual records. |
| `get_evidence` | Deterministic tool | Evidence ID → full raw and normalized record | Reject unknown or inactive IDs; expose provenance. |
| `evaluate_match` | LLM stage | Requirements and retrieved evidence → MATCH/PARTIAL/GAP assessments | Explain semantic coverage and cite evidence. |
| `calculate_match_score` | Deterministic function | Requirements and validated assessments → coverage or insufficient information | Calculate the final score independently of LLM output. |
| `generate_resume` | LLM stage | Confirmed profile, current report, relevant evidence, language → structured cited resume | Prioritize and rewrite supported experience for the job. |
| `submit_stage_result` | Deterministic tool | Stage-specific structured proposal → validation result | Enforce shape, enums, source references, complete requirement coverage, and evidence references. |

The stage capabilities are coordinator methods, not additional model-facing tools.
No tool is created solely to increase tool count.

## E. Frontend Flow

Use existing hash navigation under `#career`, with named substates managed by
`career.js`.

1. **First visit:** No normalized profile opens onboarding. Saved incomplete input
   resumes onboarding; an unconfirmed normalized profile opens review.
2. **Onboarding:** Collect optional contact information, repeatable
   education/work/project entries, and lightweight skills, languages,
   certifications, research/publications, awards, and other information. Do not
   add a preference subsystem.
3. **Normalization/review:** Show progress, then editable organized records
   alongside access to original input. **Confirm & Continue** confirms the whole
   profile.
4. **Dashboard:** Show profile summary, **View / Edit Profile**, and a JD text area
   with **Analyze Job**.
5. **Job analysis:** Display high-level stages and disable repeated submission
   while the request runs.
6. **Match report:** Show title, coverage, required/preferred breakdown,
   MATCH/PARTIAL/GAP, explanations, strengths, gaps, and recommended resume focus.
7. **Evidence inspection:** Use an expandable section showing evidence ID,
   original record, normalized facts, and the associated requirement.
8. **Resume generation:** Offer English, Chinese, or Japanese; default to English.
   The user explicitly clicks **Generate Tailored Resume**. The final language
   clarification above supersedes this original default.
9. **Resume review:** Render the resume with expandable evidence references,
   Markdown download, and browser printing. Hide citations and dashboard chrome
   in print output.

Backend interfaces:

- `GET /api/career`: current profile and saved job artifacts.
- `POST /api/career`: named actions for onboarding save, normalization, profile
  edits, confirmation, analysis, and resume generation.
- Return validation/provider errors using existing dashboard conventions.
- Reuse the execution lock and show a stage-labelled loading state. Fetch
  completed activity with the resulting artifact; a new streaming protocol is
  unnecessary.

The existing provider setup gate remains authoritative. Career drafts must
survive the dashboard's five-second polling and ordinary navigation.

## F. Grounding and Provenance

Maintain this chain:

**Raw source record → normalized record → stable evidence ID → requirement match
→ resume claim**

- Preserve original onboarding records with stable source IDs.
- Store explicit normalized-profile edits separately as user-authored factual
  input. Relevant evidence identifies whether its source is onboarding or an edit.
- Keep record-level raw text and normalized content available through the
  evidence viewer. Do not implement offsets or token spans.
- Require valid evidence IDs for MATCH and PARTIAL. GAP may have no evidence.
- Require citations for substantive resume statements, including summaries and
  bullets. Contact details come directly from profile fields.
- Render employers, job titles, dates, and supplied metrics from factual records
  wherever possible. Reject unknown citations and unsupported additions to
  protected factual fields before saving.
- Treat missing evidence as absence of support in the profile, not proof that
  the person lacks the skill.

Citation validation establishes traceability; it cannot prove that every
paraphrase is semantically faithful. Prompts, user profile confirmation, resume
review, and groundedness evals address that remaining risk.

## G. Deterministic Scoring

Python uses:

- Required = **2**; preferred = **1**
- MATCH = **1**; PARTIAL = **0.5**; GAP = **0**

`coverage = 100 × Σ(weight × value) / Σ(weight)`

Round to one decimal. Validate exactly one assessment per extracted requirement
before calculation. An empty requirement set displays **Insufficient information**
and blocks resume generation until usable analysis exists.

Label the result **JD Requirement Coverage** and explain:

> This score shows how much of the extracted job requirements your confirmed
> Career Profile supports. It is not a hiring or interview probability.

Display requirement weights and statuses so users can understand the calculation.

## H. Daily Delivery and Review Gates

| Day | Files/modules and deliverables | Acceptance and stopping point |
|---|---|---|
| **1** | `waku/db.py`, Career coordinator/tools, dashboard API, Career frontend shell; onboarding, raw persistence, normalization, editing, confirmation | Complete onboarding and reload successfully; verify raw input survives and Career facts never enter conversational memory. **Stop for review.** |
| **2** | Extend Career runtime/tools and frontend; JD extraction, agent-authored FTS queries, evidence lookup, matching, scoring, report/viewer | A previously unseen JD produces a complete explainable report; unsupported requirements remain GAP; evidence is inspectable. **Stop for review.** |
| **3** | Resume stage, language selection, provenance validation, preview, Markdown, print CSS, activity panel | Analysis generates no automatic resume; explicit action produces a cited tailored draft; outdated analysis blocks generation. **Stop for review.** |
| **4, optional** | Career eval fixtures, tracing verification, UI fixes, README and indexed usage/demo documentation | Run essential checks and demonstrate the complete acceptance scenario. Add no major architecture or feature. |

Behavioral tests accompany Days 1–3 rather than waiting until Day 4.

Use four JD fixtures: AI Engineer, Frontend Engineer, Full Stack Engineer, and
Technical Support Engineer. Offline scripted tests cover persistence, tool
execution, multiple synonym searches, evidence validation, GAP honesty, score
literals, outdated analysis, explicit generation gates, and resume citations.

Scripted tests verify application behavior; a separately invoked live
smoke/evaluation checks real-model extraction, relevance, and factual
paraphrasing. Record results honestly.

Run deterministic evals and lint. Verify both themes, draft preservation, reload
persistence, safe pasted-text rendering, multilingual printing, and browser
console errors. Add route pins and hosted policy entries as each endpoint lands.

## I. Risks, Conflicts, and Defaults

- **Normalization example:** The specification's React example adds TypeScript
  without mentioning it in raw input. Follow the no-invention rule and omit
  TypeScript unless the user supplies it.
- **“No RAG” wording:** Implement only the explicitly requested FTS5 lookup and
  evidence-grounded generation. Add no separate retrieval framework or vector
  pipeline.
- **Grounding:** Valid IDs alone do not guarantee factual wording. Preserve
  protected fields, require review, and include adversarial groundedness cases.
- **Multilingual output:** Translate prose, preserve canonical factual
  names/titles/dates, and use suitable system-font fallbacks for Chinese/Japanese
  printing.
- **Time budget:** Keep one resume template, one profile-level confirmation,
  synchronous bounded stages, and basic errors. Defer custom layouts and granular
  editing systems.
- **Repository process:** Keep tools scoped and avoid changes to core interfaces
  or every prompt. Do not create a new top-level package. Explicit plan approval
  authorizes implementation; daily review stops remain mandatory.
- **Hosted policy:** Block Career endpoints for this local MVP. Policy additions
  retain hosted's Elastic License 2.0; Career code retains Waku's MIT code license.
  No code moves across that boundary.

No further product decisions are required before implementation.

## J. Explicit Deferred Features

Do not implement embeddings, vector databases, GraphRAG, knowledge graphs,
another agent framework, multi-agent execution, scraping, browser automation,
job recommendations, autonomous applications, ATS/application tracking, salary
or career planning, authentication, multi-user hosting, payments, cloud
deployment, training, document upload, DOCX, custom PDF generation, resume
designers, granular evidence confirmation, revision graphs, or generalized
recovery infrastructure.

Stop when the specified vertical journey works reliably. Implementation begins
only after explicit approval.
