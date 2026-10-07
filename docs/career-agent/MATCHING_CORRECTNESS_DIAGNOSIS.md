# Job matching correctness diagnosis

Status, 2026-10-07: The approved [matching correctness fix](HANDOFF.md#matching-correctness-fix)
implements full evidence delivery, checked inventory fallback and server-owned GAP
coverage. The findings below preserve the pre-fix diagnosis as historical evidence.

The confirmed master's evidence reaches persistence and FTS correctly, but the
matching stage can classify a requirement as GAP without retrieving or inspecting
that evidence. Agent-authored literal queries gate the facts available to the
model, and submission validation does not enforce evidence coverage.

This investigation changes no production code, prompts, retrieval, or scoring.
The new fixture and deterministic evals preserve the failing boundary. The
investigation read the current runtime database through a read-only connection
and performed integrity checks and analyses on isolated copies. It made no live
provider calls and collected no hidden model reasoning.

## 1. Persistence contains both degrees

The inspected runtime home was `/home/houlx/.waku`. Its profile was confirmed.
The raw profile, normalized profile, and active evidence each contained eight
records. Every raw source had exactly one normalized record and one active
evidence row. The following suffixes identify the full `career-<source_id>` IDs.

| Source ID | Source type | Record | Active | Field checks |
|---|---|---|---|---|
| `917fbb561874475097971dc352581a3b` | education | Master's degree | 1 | Pass |
| `b54e4930977249a4ae0bedf6fcbdcdcf` | education | Bachelor's degree | 1 | Pass |
| `1e5cebd5bf764f38aaaf7dc957e66b6a` | work | Application Engineer | 1 | Pass |
| `135605663a8f4e4aa1d10aa35f61ee77` | project | SSR optimization | 1 | Pass |
| `6b40e017dc854b2f84a12423e16ee05e` | project | Review management and AI replies | 1 | Pass |
| `6c7dbe21ac444eae9404f52836ee46ec` | project | Onboarding RAG assistant | 1 | Pass |
| `c722c1c5677b4ad981cd78f379f1b40c` | project | AB Test framework | 1 | Pass |
| `ec6c3a0a71134232b0b2d7b8adda2ade` | project | React upgrade | 1 | Pass |

The field checks verified the stable ID formula, source type, active flag,
preservation of original source text, equality of persisted normalized JSON to
the confirmed record, and exact `search_text = raw_text + newline + normalized_json`.
The local audit artifact retains every complete row, including raw text and JSON.

`save_raw` deactivates existing evidence when onboarding changes.
`save_profile` validates a one-to-one source mapping, deactivates old evidence,
then upserts every current record and reactivates it in one transaction.
IDs remain stable while source IDs remain stable. Resubmitting onboarding without
source IDs generates new source IDs. Confirmation alone sets `confirmed=1`;
confirmation with a profile payload first saves that profile.

`analyze_job` checks confirmation and writes only jobs, requirements, matches,
and resume outdated flags. It does not delete, deactivate, overwrite, or rebuild
Career evidence, nor change the normalized profile. Initialization executes
idempotent table/trigger creation; it does not rebuild FTS. Six scripted analyses
on an in-memory copy of the actual profile produced alternating MATCH/GAP while
complete profile/evidence snapshots stayed identical. SQL tracing found no
profile/evidence mutation statements. Twelve minimal-fixture analyses also
preserved those tables byte for byte.

These checks prove current persistence and isolated analysis stability. Historical
traces do not contain full before/after profile snapshots, so they cannot prove
that no user edits occurred between every past analysis.

## 2. FTS is synchronized and deterministic on a fixed snapshot

`career_evidence_fts` uses external content from `career_evidence` and row IDs
from its integer primary key. INSERT, DELETE, and UPDATE triggers maintain the
index. The UPDATE trigger removes old terms and inserts new terms, including
when only the active flag changes. The index contains inactive rows by design;
the search JOIN filters `e.active=1` before ranking and limiting.

An FTS5 `integrity-check` with `rank=1` passed on a database copy. This checks
the real inverted index against external content. An `fts5vocab` instance table
also found all eight expected row IDs. A plain SELECT from an external-content
FTS table would not have established index completeness.

Thirteen queries repeated twenty times each returned identical IDs in identical
order on the current snapshot. Separate evals cover activation filtering,
term replacement, deletion, actual equal-rank ties, duplicate queries, query
order reversal, and Top-K behavior.

| Current-profile query | Result |
|---|---|
| `硕士` | Master's evidence |
| `名古屋大学` | Master's evidence |
| `信息系统学` | Master's evidence |
| `degree` | Both education records |
| `学历`, `教育`, `大学`, or `学位`, separately | Empty |
| `Master` or `master degree` | Empty |
| `硕士 学历 电气 自动化 机电一体化` | Empty |

The index preserves multilingual text, but its default tokenizer does not provide
Chinese word segmentation, substring matching, translation, or degree synonyms.
For example, `大学` does not match the full token `名古屋大学`. English JSON field
names such as `degree` can retrieve records whose substantive degree text is
Chinese. This behavior creates a recall problem without losing stored text.

The search function takes at most sixteen Unicode word groups per query and
joins them with literal AND. It runs each query separately with a limit, keeps
the best BM25 rank for each unique ID, then sorts the union by `(rank, evidence_id)`
and applies the limit again. The default limit is eight; the maximum is twenty.
Tie-breaking is deterministic. Duplicate queries do not create duplicate IDs.
Different query sets can change ranks and displace relevant candidates after
the union; the API offers no category completeness guarantee. BM25 ranks from
different expressions do not establish semantic relevance across categories.

Top-K did not explain the two reported failures: the profile had eight active
records, the relevant search calls used limits of ten or twenty, and the education
queries returned nothing before limiting.

## 3. Historical traces locate variability

The investigation parsed only tool arguments, tool outputs, stage markers, and
submitted results from existing local JSONL traces. It grouped repeated analyses
by extraction-stage boundaries because reanalysis reuses the job ID.

| Analysis start, Asia/Shanghai | Inspected education | Submitted education result |
|---|---|---|
| 2026-10-06 21:35:06 | None | GAP; reason claimed the profile had no education information |
| 2026-10-06 21:39:09 | Master's | PARTIAL; degree recognized, major compatibility questioned |
| 2026-10-06 21:48:47 | Both degrees | MATCH; master's degree recognized |
| 2026-10-06 22:33:03 | Bachelor's only | GAP; reason claimed the candidate held only a bachelor's degree |
| 2026-10-07 09:30:24 | None; only React inspected | GAP; reason treated the React project as the only resume record |
| 2026-10-07 09:32:23 | Bachelor's only | GAP; reason claimed the candidate had a bachelor's rather than master's degree |

The last two runs reproduce the user's specific examples. The first used
`硕士 电气 自动化 机电一体化` and later separate queries `学历`, `教育`, `大学`,
`学位`; those searches returned no education. The second used
`硕士 学历 电气 自动化 机电一体化`, `教育背景 学位 专业`, and
`学历 教育 大学 本科 硕士`; those searches also returned nothing. Later
`Rakuten`, `前端开发`, `frontend`, `JavaScript`, and `React` queries happened to
retrieve the bachelor's record, whose contents mention frontend work. Neither
run retrieved or inspected the master's record.

The master requirement's text, category, and importance agree across those two
runs. Their requirement IDs differ because the coordinator generates fresh UUIDs
on every extraction. Query formulation is the first relevant divergence for this
pair: B. Deterministic retrieval then exposes different subsets, inspection
follows those subsets, and judgment extrapolates them to the whole profile.

Across the larger history, extraction also varies: the education exception can
be merged or separated, seven versus eight requirements can be emitted, and
technical categories vary. Thus A is the earliest overall historical variability;
B explains the reported missing-degree boundary even with extraction fixed.
Major compatibility also shows semantic judgment variability after the degree
has been found. The actual JD combines degree and major conditions, so finding
the master's does not by itself establish MATCH for that entire compound clause.

Replaying all historical search arguments on the current snapshot reproduced
84 of 86 recorded combined ID lists exactly. All lists in the last two reported
runs reproduced exactly. Two older calls differed; historical traces lack
index/profile snapshots and code revision stamps, so their differences cannot
be attributed conclusively to historical data changes or older code. This audit
does not claim historical FTS consistency for those two calls. Current-snapshot
integrity and repeatability passed independently.

## 4. The model receives a retrieved subset

The matching stage starts a fresh message list. Its initial JSON contains only
`job` (the extraction output), `requirements` (with assigned IDs), and `job_id`.
It receives neither the complete Career Profile nor an inventory of active
evidence, basic profile fields, or the previous job's evidence context.

Search results supply ID, source type, title, normalized description, and skills.
They omit original raw text. `get_evidence` returns the selected active record's
ID, source ID, source type, raw text, and normalized JSON. The model can call it
directly if it knows an ID; retrieval is the practical discovery mechanism.

The loop appends assistant tool calls and every tool result to the message list.
Later calls preserve earlier results. The offline eval checks accumulated
messages at every matching turn. OpenAI adapter conversion also retains tool
outputs. The server-side `collected` dictionary adds inspected IDs; later
inspection does not clear other records. Persisted `report.evidence` contains
only cited records, so that saved subset is not a complete inspection audit.

No loop-side context truncation or compaction exists in this path. The coordinator
caps stages at ten iterations and sets an output-token limit of at least 4096.
It does not budget input against a model context window. A long profile/tool
history can exceed provider limits; output truncation or provider behavior can
also interrupt a run. This audit did not observe context loss as the cause of
the reported failures: the master record never entered their tool context.

## 5. Retrieval failure can become false GAP

`validate_match` requires at least one completed search for the entire report.
An empty successful result satisfies that check. It requires valid requirement
IDs, statuses, reasons, and active inspected IDs for citations. It requires
citations for MATCH/PARTIAL, but GAP may cite nothing. It does not associate
searches or inspected coverage with each requirement.

Consequently, an unrelated search followed by an empty-citation education GAP
passes validation. A bachelor-only GAP also passes while the master's evidence
remains active. Even a MATCH citing only an inspected React project passes the
structural validator; it does not validate education support semantically.

The prompt says that search results are candidates, but it also defines GAP in
terms of what the profile supports without ensuring that the model sees the
profile. The system currently allows “search returned nothing” to become
“the profile contains no supporting fact.” This is a demonstrated semantic
correctness risk, not merely a possible model-reasoning problem.

## 6. The minimal regression reproduces the boundary

`evals/fixtures/career_matching_diagnostic.json` contains bachelor's and master's
education records plus an unrelated React project. Its JD contains exactly
`Master's degree required`. The deterministic client scripts decisions and tool
choices while executing the real coordinator, loop, SQLite search, inspection,
validator, and persistence.

| Scripted query | Inspected IDs | Submitted citations | Accepted result |
|---|---|---|---|
| `React` | `career-react` | None | GAP |
| `Bachelor` | `career-bachelor` | `career-bachelor` | GAP |
| `Master's degree required` | None | None | GAP |
| `Master's degree` | `career-master` | `career-master` | MATCH |

The third query fails because the evidence does not contain the token `required`.
Each route runs three times against the same confirmed profile and same JD.
All twelve runs preserve every profile and evidence field. The eval captures the
requirement ID/text/category/importance, queries, per-query IDs, combined IDs in
tool outputs, inspected IDs, submitted citations, status, and reason in
`diagnostic.json` under pytest's temporary directory.

The strict expected-failure eval requires validation to reject an education GAP
with no education inspected. Running it with `--runxfail` fails because the
validator accepts that unsupported negative claim without raising an error.
This preserves an executable failing example before a fix. Scripted outcomes
prove that the current validator admits the failure; they do not prove that a
live model always follows that script or guarantee semantic judgment after a fix.
Historical traces independently establish that live runs took these failing paths.

## 7. Root cause

The failure occurs between query-based evidence discovery and submission.
Literal lexical recall determines the model's visible facts, but no stable
inventory or required coverage distinguishes missing retrieval from missing
profile evidence. The validator then accepts a profile-wide negative conclusion
from an incomplete subset. Persistence and current FTS synchronization are intact.

The system must separate evidence availability, evidence delivery, and semantic
support. Improving query wording alone would not establish completeness and
would leave this failure boundary open.

## 8. Architecture options and recommendation

| Option | Assessment |
|---|---|
| A: Deterministic category candidates | All active education records bypass lexical recall for degree requirements. Category labels are free-form model output, and source types are only work/project/education/other, so unknown and mixed categories need conservative fallbacks. Certifications currently have no dedicated source type. |
| B: Stable inventory | Every stage can see active IDs/types/summaries. This fixes discovery blind spots but does not force full inspection or prove a GAP. |
| C: Full evidence for small profiles | This is the simplest complete context for the current eight-record profile. The full audited row JSON is 17,143 characters including duplicated search text; a stage payload can omit database-only fields. A model-aware input budget must decide whether a profile fits. |
| D: Hybrid | A stable inventory plus deterministic category candidates can supply complete education context while FTS retrieves detail for broader requirements. This supports larger profiles but needs explicit coverage accounting. |

The recommended target is D, with C for profiles that fit a checked input budget.
Pure education requirements should always receive all active education records
in full. FTS should supplement those facts rather than determine their existence.
Unknown categories, mixed requirements, and records classified as other require
conservative coverage rather than an unrecognized-label shortcut. An inventory
alone does not enforce GAP correctness. This failure provides no evidence that
embeddings or a vector database are necessary.

## 9. GAP invariant and smallest safe scope

A requirement must not become GAP merely because retrieval missed its support.
For a pure education requirement, the minimum domain includes all active
education evidence from the confirmed snapshot. Mixed education/experience
clauses also require the applicable work/project evidence. Facts may exist in
other or misclassified records; uncertain routing should expand coverage, with
all active evidence as the conservative fallback.

The coordinator should compute the required evidence IDs independently of
model-authored queries. It should deliver complete records or track successful
inspection of every required candidate. Submission should reject GAP when
required IDs are absent from that server-owned delivered/inspected set. The
coordinator should bind coverage to the confirmed snapshot and invalidate it
after profile changes. A model-supplied assertion that it checked everything
would not establish coverage. Deterministic checks can prove delivery and
inspection, but cannot prove the model understood unstructured degree text.

The smallest safe first implementation can stay within Career matching context
construction and validation, using existing evidence rows and tools. It should
add deterministic full education delivery, server-owned coverage validation,
conservative category handling, and an education-citation guard that rejects a
project-only citation for a pure degree requirement. It should leave persistence,
FTS schema, scoring, dependencies, and the shared loop unchanged. A checked
all-evidence payload for small profiles can simplify coverage further. Oversized
profiles must use a complete candidate/inspection path or refuse an incomplete
GAP; silently truncating the payload would recreate the bug.

Any implementation that adds context to every matching prompt requires a short
design proposal and maintainer approval under conventions section 2. This
diagnosis proposes that work and does not implement it.

## 10. Verification and recurrence tests

The focused profile/job/diagnostic suite passed 55 tests and recorded one expected
failure. The explicit `--runxfail` invocation failed because validation did not
reject the uncovered GAP, which proves that the regression exercises the known
bug. Repository lint passed. The complete offline release gate passed 498 tests,
skipped 14, and recorded one expected failure. `make` was unavailable, so the
investigation used the Python commands from its targets. The initial sandboxed
gate blocked localhost sockets; the successful rerun allowed localhost HTTP evals
and directed gate reports to `/tmp/career-diagnosis-gate`.

The implementation needs deterministic tests that:

- Preserve both degrees, source IDs, raw text, normalized JSON, active flags, and
  search text across initial analysis, reanalysis, and failed analysis.
- Check external-content FTS integrity, multilingual exact-token behavior,
  inactive filtering, trigger updates/deletes, rank ties, union deduplication,
  query reordering, and per-query/global Top-K limits.
- Hold extraction fixed while empty, irrelevant, multilingual, and overly
  restrictive queries cannot hide education from matching context.
- Reject education GAP with incomplete candidate coverage, including a report
  that searched only for another requirement or inspected only the bachelor's.
- Permit GAP after complete applicable evidence coverage when support is absent;
  complete coverage must not force every requirement to MATCH.
- Reject project-only support for a pure degree requirement, and retain a
  positive master's MATCH fixture with grounded education citations.
- Retain every prior tool result across successive calls and provider adapters.
- Handle unknown/mixed categories, other records, large profiles, and context
  limits without silently accepting an incomplete GAP.
- Invalidate coverage after profile changes and retain previous saved reports
  if a reanalysis cannot complete.

The local artifacts are `/tmp/career-current-snapshot-diagnostic/audit.json`
(complete current evidence and six snapshot analyses),
`/tmp/career-historical-diagnostic.json` (historical tool queries, returned IDs,
inspections, and education submissions), and pytest's `diagnostic.json`
(twelve isolated minimal-fixture runs). These runtime-derived artifacts remain
outside the repository. The repository fixture contains synthetic data only.
