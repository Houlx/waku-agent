# Source-addressed extraction compiler

Phase B's first checkpoint adds a pure compiler and synthetic evals. Fresh production
extraction still uses the Phase A canonical submission contract. The next checkpoint
must connect the compiler to the coordinator and extend independent fresh evaluation.
The current checkpoint makes no before/after live reliability claim.

## Source catalog

`waku/runtime/career_extraction_compiler.py` retains the exact raw JD in a frozen
`SourceCatalog`. Frozen `SourceItem` entries hold submission-local `t0`, `t1`, …
references, exact text, occurrence offsets and recognized section context. English
words and individual punctuation or Chinese characters form addressable tokens.
Whitespace stays in the raw string and survives every resolved range. Duplicate
wording has distinct token references. Unknown heading-like lines reset catalog
context; the catalog never filters source text.

A range contains `first` and `last` token references. Python slices from the first
token's start through the last token's end. The model receives text and token IDs;
it does not author character offsets or copy literal excerpts. Leading and trailing
whitespace outside selected endpoints stays in the catalog, without entering the
selected excerpt. This convention leaves the exact-JD cache key unchanged.

## Semantic IR

`SEMANTIC_IR_SCHEMA` describes the internal contract. The compiler validates shapes,
bounds and references even when a provider ignores its tool schema.

| Field | Model responsibility |
|---|---|
| `title`, `summary` | The model supplies short descriptive metadata. |
| `responsibilities` | The model selects responsibility source ranges. |
| `facts` | Each fact supplies a local ID, semantic kind, supporting range and literal subject range. |
| `opportunities` | Each opportunity explicitly selects fact IDs and ALL or ANY. |
| `fallback` | An education fallback selects its facts, operator and condition range. |
| `inherit`, `inheritance_support` | The model names inherited primary majors and explicit source wording supporting inheritance. |
| `repeats` | The model links a repeated occurrence to its primary fact. |

The IR contains no canonical category, eligibility, reason, keywords, IDs, offsets,
provenance envelope or group text. This checkpoint deliberately omits free-form fact
criteria: canonical criteria retain source wording, with the reviewed `1abview` typo
correction. The model cannot introduce a new threshold through a canonical paraphrase.
Fallback nulls express an absent semantic relationship; they are not canonical defaults.

The model still decides qualification scope, source support, semantic kinds, grouping,
ALL/ANY, fallback conditions, inheritance and repeated-fact relationships. Python never
creates these relationships from adjacency.

## Compiler ownership

`compile_extraction(catalog, ir)` performs no I/O and does not mutate either input.
It resolves references, checks subject containment and qualification-clause support,
checks bounded kind cues, rejects unused facts and duplicate opportunities, and builds
shallow groups and education routes. Python derives category from kinds, applies the
existing `eligibility_for` and required/preferred scope policy, supplies reasons and
empty keywords, and constructs literal subjects and contiguous provenance envelopes.
Objective facts with trait or logistics wording require narrower support.

The compiler accepts explicit repetition links only for distinct occurrences with the
same source criterion after case and the reviewed typo correction. Different thresholds
or proficiency wording require semantic review; this checkpoint rejects their collapse.
Inherited major constraints require explicit same-major wording in the fallback clause.
The compiler does not infer inheritance from nearby primary education wording.

The existing `validate_extraction` runs last. It supplies source spans, semantic IDs,
`groups-v1` policy metadata and the exact-JD key, while retaining its existing guards.
Storage UUIDs and matching-local constraint IDs remain downstream responsibilities.
The compiler cannot publish a rejected candidate. Coordinator integration must retain
the existing atomic first-accepted publication and cache lookup behavior.

## Compatibility and limits

The compiler returns the current groups-v1 object. It introduces no schema migration,
policy version change, old-row backfill, provider default, UI change or dependency.
Existing caches and the Phase A coordinator continue using their current contracts.
Matching-v1, Coverage and resume generation do not call the new module yet.

Bounded lexical checks cannot prove arbitrary semantic entailment. Kind cues deliberately
reject some unusual but valid wording. Technology and other kinds still need reviewed
semantic accuracy checks. Multi-sentence fallback conditions and paraphrased repetitions
can require a future bounded contract refinement. Source token references can be verbose
for Chinese text; live trials must measure total input and output costs.

The retained groups-v1 validator derives spans for every matching literal excerpt and
uses contiguous group envelopes. The catalog distinguishes occurrences, but canonical
span semantics remain unchanged. Envelopes across unrelated material clauses can trigger
conservative overlap or eligibility rejection. The retained qualification parser can
also misclassify unusual headings following a recognized duties section. The compiler
retains those source tokens but does not override the final validator's scope policy.
These limits must remain explicit during integration and semantic evaluation.

## Baseline and next checkpoint

`evals/fixtures/career_phase_a_baseline.json` freezes six scripted synthetic trials
against `3d6d4fe`. `python -m evals.career_extraction_baseline --output PATH` replays
them in new temporary databases. No trial clears runtime data or reuses a canonical set.

Four of six trials complete. Two of six never submit, two encounter truncation, and
one encounters canonical rejection before acceptance. Accepted trials need 1, 2, 1
and 1 submission attempts. Token usage remains null because scripted usage is not a
provider measurement. These deliberately selected cases measure regression behavior;
their proportions do not estimate provider failure probabilities.

The next checkpoint must replace fresh model submissions with this IR, supply the source
catalog, and adapt scripted coordinator clients without accepting legacy canonical model
submissions. It must classify malformed IR, semantic rejection and compiler rejection
separately and retain Phase A recovery unchanged. Every evaluator trial must use a new
database and report completion separately from semantic quality across all trials and
accepted trials. Reviewed gold comparisons must cover source recall, unsupported additions,
opportunity agreement, merge/split behavior, category, eligibility, ALL/ANY, fallback,
inheritance, duplicate scoring and weighted denominator agreement.

No post-integration fresh benchmark or live provider call ran at this checkpoint.
Compiler tests establish deterministic construction and rejection, not model improvement.
