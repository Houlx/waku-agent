# Source-addressed extraction compiler

Fresh production extraction now submits Semantic IR to the pure compiler. Python
constructs groups-v1 and runs the existing final canonical validator before publication.
The compiler-core checkpoint remains recorded in the handoff; this integration preserves
its design and the Phase A submission recovery protocol.

## Source catalog

`waku/runtime/career_extraction_compiler.py` retains the exact raw JD in a frozen
`SourceCatalog`. Frozen `SourceItem` entries hold submission-local `t0`, `t1`, …
references, exact text, occurrence offsets and recognized section context. English
words and individual punctuation or Chinese characters form addressable tokens.
Whitespace stays in the raw string and survives every resolved range. Duplicate
wording has distinct token references. Unknown heading-like lines reset catalog
context; the catalog never filters source text.

A range contains `first` and `last` token references. Python slices from the first
token's start through the last token's end. The model receives the exact raw string once, [ID, text] token pairs and section
transitions beginning at named IDs, including null context for unknown headings.
This compact representation preserves every textual occurrence. The model receives token IDs;
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
provenance envelope or group text. The approved contract deliberately omits free-form fact
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
or proficiency wording require semantic review; the compiler rejects their collapse.
Inherited major constraints require explicit same-major wording in the fallback clause.
The compiler does not infer inheritance from nearby primary education wording.

The existing `validate_extraction` runs last. It supplies source spans, semantic IDs,
`groups-v1` policy metadata and the exact-JD key, while retaining its existing guards.
Storage UUIDs and matching-local constraint IDs remain downstream responsibilities.
The compiler cannot publish a rejected candidate. The coordinator retains
the existing atomic first-accepted publication and cache lookup behavior.

## Compatibility and limits

The compiler returns the current groups-v1 object. It introduces no schema migration,
policy version change, old-row backfill, provider default, UI change or dependency.
Existing caches retain groups-v1 and bypass Semantic IR extraction. Matching-v1, Coverage
and resume generation consume the same canonical objects and do not receive Semantic IR.

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

## Failure classes and repair

Fresh traces retain `career_extraction_outcome` and `career_extraction_submission` events.
Each rejected submission retains a failure class and code. Provider requests, raw and
normalized termination reasons, bounded recovery and usage remain observable.

| Class | Boundary |
|---|---|
| `submission_failure` | Missing submission, truncation or malformed tool arguments prevent usable IR delivery. |
| `ir_validation` | Closed shapes or source/fact/fallback/repetition/inheritance references are invalid. |
| `semantic_rejection` | Source support, unused facts, duplicate opportunities, relationships or recognized material qualification coverage fail. |
| `compiler_rejection` | Structurally valid IR reaches a retained final groups-v1 invariant that rejects the canonical candidate. |

Repair feedback names Semantic IR facts, ranges and relationships. Python never asks the
model to repair canonical category, eligibility, reasons, keywords, offsets, spelling,
provenance envelopes or semantic hashes. Final invariant failures retain their code and
request semantic review; faithful choices may still exceed compiler limits. Rejected
candidates never publish a cache row. Repeated invalid submissions retain rejection text
rather than returning the generic unfinished-result error. Known Phase A missing-submit
or truncation failures retain their more specific termination error.

## Integrated evaluation

`python -m evals.career_extraction_benchmark --output PATH` runs six scripted reliability
scenarios and 25 reviewed synthetic gold cases through the production fresh function.
Every trial creates a new isolated database with zero cached sets. The runner never
clears runtime data. The frozen Phase A artifact remains unchanged; its original
canonical client is not accepted by the current production path.

| Scripted reliability | Frozen Phase A | Integrated Phase B |
|---|---:|---:|
| Completed trials | 4/6 | 4/6 |
| Trials encountering normal missing submission | 2/6 | 2/6 |
| Trials encountering truncation | 2/6 | 2/6 |
| Canonical rejection | 1/6 | 0/6 |
| Malformed IR | Not applicable | 0/6 |
| Semantic IR rejection | Not applicable | 1/6 |
| Compiler/final rejection | Not separated | 0/6 |
| Submissions until acceptance | 1, 2, 1, 1 | 1, 2, 1, 1 |

The evaluator also reports malformed arguments, provider turns, attempts, recovery use,
raw/normalized reasons, latency and available input/output usage per trial. Scripted
usage is null. The six deliberately selected scenarios do not estimate provider failure
probabilities. The semantic-repair scenario moves rejection to the semantic boundary;
scripted completion establishes no semantic improvement by a model.

Gold cases cover education alternatives and fallback with/without explicit inheritance;
technology OR, duties, repetition and typo preservation; general and skill tenure;
ambiguous experience; logistics, license, health and traits; observable coordination,
writing outputs and bare ability; unknown headings, mixed clauses, repeated identical
occurrences, intervening text and ambiguous required/preferred scope.

`semantic_gold` compares reviewed literal normalized fact subjects, source containment,
primary opportunity sets, pairwise merge/split decisions, categories, eligibility,
ALL/ANY, fallback conditions/facts, inherited majors, duplicate scoring and weighted
denominators. It does not use semantic hash equality as a substitute for these checks.
All 25 scripted gold cases complete and agree with their reviewed semantics. Each has
100% source recall, opportunity, merge/split, category, eligibility, ALL/ANY, fallback,
inheritance and denominator agreement, with zero unsupported additions or duplicates.
These results calibrate construction and metric behavior rather than real-model quality.
Mutated outputs independently exercise missing facts, additions, split opportunities,
wrong categories/operators/dispositions, duplicate scoring and missing inheritance.

The evaluator reports quality across every fresh trial and among accepted outputs
separately. Failed trials earn zero completion-adjusted quality, and the all-trial view
always exposes non-completion. Addition/duplicate rates describe accepted outputs only,
because a failed trial has no canonical output to inspect. Literal gold comparison and
bounded source checks cannot prove semantic entailment.

For the Chinese executable fixture, raw JD text occupies 527 UTF-8 bytes. Serialized
catalog stage data occupies 3,429 bytes versus 8,916 bytes for the verbose catalog object.
The reviewed Semantic IR occupies 1,877 bytes versus 4,238 bytes for the canonical model
submission. Semantic instructions occupy 1,414 bytes versus 4,558; schemas occupy 2,434
versus 4,032 bytes. These JSON-byte measurements exclude provider framing and do not
predict tokenization or live output usage. Chinese token addressing still adds input
compared with sending only raw JD text.

The core retains conservative lexical support, uncertain unusual-heading scope,
contiguous canonical provenance envelopes and difficult multi-sentence fallback cases.
Lexical support does not prove entailment. The integration changes no provider/model
default, policy version, exact-JD identity, cache deletion, downstream semantic policy,
Coverage arithmetic, UI, database schema or resume contract.

## Live fresh benchmark

Two network-enabled trials used the configured OpenRouter model
`nvidia/nemotron-3-super-120b-a12b:free` and only the synthetic Cedar Instruments JD.
Both fresh databases started and ended with zero canonical rows. Both trials returned
`length` twice, normalized to `max_tokens`, and used the one bounded recovery without
submitting a tool result. Each trial consumed 5,995 input tokens and 16,384 output tokens
across two provider turns. Latencies were 137.6 and 152.5 seconds.

Live completion was 0/2. Both trials encountered truncation; neither delivered arguments,
so IR validation and compilation were not reached. The all-trial semantic view records
100% non-completion and zero completion-adjusted quality; accepted-output quality is
unavailable. These two observations establish neither provider failure probabilities nor
semantic improvement. The configured model still fails to submit under the retained
limits despite named tool choice and bounded recovery. The integration changes no model
default or token limit to hide that result. An earlier sandboxed connection attempt
received no model response and is excluded from these network-enabled trial measurements.
