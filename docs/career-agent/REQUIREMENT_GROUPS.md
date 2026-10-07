# Canonical requirement groups

Career reuses one validated scoring structure for an exact JD and extraction-policy
version. The `groups-v1` policy stabilizes scoring opportunities and eligibility;
it leaves MATCH/PARTIAL/GAP definitions, evidence delivery and score weights unchanged.

## Schema and grouping

`career_requirements.py` owns the extraction schema, structural validation, identity,
eligibility guards and cache. The extraction result retains title, summary,
responsibilities and a `requirements` list. Each list entry represents one independent
scoring opportunity, including entries excluded from Coverage.

| Field | Meaning |
|---|---|
| `text` | The canonical qualification text preserves the JD's material constraints. |
| `source_excerpt` | A verbatim JD excerpt supplies group provenance. |
| `category` | A closed category identifies education, experience, skill, certification, language, demonstrated_capability, logistics, personal_trait or other. |
| `importance` | Explicit required/preferred wording controls importance; unspecified importance defaults to required. |
| `eligibility` | SCORED, NEEDS_CONFIRMATION or NON_SCORABLE determines membership before matching. |
| `eligibility_reason` | A visible explanation describes the disposition. |
| `constraints` | An ALL/ANY operator combines 1–20 material constraints. Each constraint contains a closed kind, literal source subject, faithful text and minimal verbatim excerpt. |
| `alternative_route` | An optional education route contains a verbatim condition, source excerpt and its own shallow ALL/ANY constraints. |
| `source_spans` | Python derives start-inclusive/end-exclusive character offsets for every occurrence of the constraint and route excerpts. |
| `semantic_id` | Python hashes exact JD content, policy version and normalized material subjects. Storage UUIDs remain separate. |
| `keywords` | Optional extraction keywords retain the existing search compatibility. |

Education has one group. Its normal route can require degree AND major; its conditional
bachelor's route remains inside the same group. The exception does not earn independent
preferred credit. An education alternative requires a degree constraint and a condition
copied from the route's source wording. LabVIEW OR C++ requires one ANY group rather
than two skill groups. A skill group can also contain an experience constraint, such
as a years threshold. The schema contains no recursive expression language.

The validator rejects invalid enums, missing eligibility, empty/invalid operators,
invented excerpts/subjects, independent exceptions, separate education groups,
recognized technology alternatives outside one ANY group, duplicate normalized
subjects and overlapping material provenance across groups. Case normalization,
a small reviewed alias map and modifier removal detect paraphrases around the same
qualification, such as Python proficiency versus Python programming experience.
Recognizable education, technology-alternative, trait and logistics qualification clauses
must retain group provenance. Excerpts with more than 100 occurrences must be narrowed.

### Qualification coverage invariant

Python requires group provenance for every recognized sensitive occurrence inside a
qualification clause, including repeated genuine qualifications. A responsibility or
company-description mention creates no qualification obligation. A technology repeated
in duties and qualifications needs the qualification occurrence only; extraction must
not create another scoring opportunity for the duty. Material constraints cannot use
exclusively responsibility or descriptive provenance.

The bounded lexical parser recognizes English and Chinese qualification, responsibility
and company/benefits section headings. Qualification sections retain all clauses;
responsibility and descriptive sections retain none. Without a recognized heading,
clauses remain candidates unless an explicit duty or description prefix identifies them.
English clauses such as “We require” remain qualifications. Python derives these ranges
from the original string without changing whitespace, spelling or the exact-JD key.
Technology-alternative checks also use qualification occurrences rather than the first
mention anywhere in the JD. Unrecognized headings and unusual mixed prose still need
semantic evaluation; these guards do not recognize every natural-language qualification.

### Source containment and repair

Every primary constraint excerpt lies inside its group excerpt. An education alternative's
excerpt lies inside the enclosing education excerpt, and contains every alternative
constraint excerpt and its verbatim condition. Inherited major wording requires textual
support and route provenance that includes that wording. A sentence naming only a
bachelor's degree cannot supply major provenance from a different sentence.

The prompt and schema explain degree AND major, one ANY technology group, and a primary
route versus a conditional fallback. A list of acceptable majors remains one major
constraint with the alternatives retained in its text. Python rejects recognized
alternative majors expressed as jointly required ALL constraints, and primary/fallback
degrees incorrectly combined as ALL. These checks enforce the existing route semantics.

The existing `text` field supplies canonical wording; no `canonical_text` field exists.
For original `1abview`, canonical text may say LabVIEW while the literal subject retains
`1abview` and the excerpt preserves original spacing and punctuation. Python never
repairs source wording before validation. Bare writing remains NON_SCORABLE even when
a broad excerpt also contains observable coordination wording.

Extraction errors identify a field and provide concise repair guidance. Stable identifiers
include `ALT_ROUTE_OUTSIDE_SOURCE`, `GROUP_PROVENANCE_CONTAINMENT`,
`NON_VERBATIM_EXCERPT`, `LITERAL_SUBJECT_MISMATCH`, `INVALID_ELIGIBILITY`,
`OVERLAPPING_SCORING_GROUP`, `INVALID_ALTERNATIVE_ROUTE` and `MISSING_QUALIFICATION`.
The existing tool registry returns these errors to the next extraction attempt.
Python still owns offsets, identities, policy validation and accepted-set persistence.
The iteration cap, groups-v1 cache identity and HTTP business-error behavior stay unchanged.

These guards are conservative structural checks, not a universal natural-language
paraphrase recognizer. Different subjects with unknown synonyms can still escape
semantic equivalence detection. Broad excerpts can cause rejection until the model
narrows them. The first extraction still needs semantic quality evaluation against
reviewed gold cases; reuse does not prove that every extracted qualification is correct.

## Eligibility and scoring

SCORED covers objective qualifications and capabilities with observable source criteria.
Coordination tasks and technical writing outputs can qualify. A bare writing-ability
label or generic teamwork spirit supplies no observable criterion and remains excluded.
Behavioral initiative can qualify when the JD supplies an observable task; undefined
initiative remains a trait. The guards inspect original source wording rather than
Career Profile achievements.

NEEDS_CONFIRMATION covers travel, relocation, shifts, availability and driver's-license
declarations. This stage displays those clauses without adding a confirmation editor
or inferring a declaration from Career Evidence. It conservatively leaves license
requirements in this disposition until a future explicit confirmation policy exists.

NON_SCORABLE covers health, vague diligence/dedication, moral character, responsibility,
undefined personality claims and unsupported other qualifications. Career never infers
health or moral character from successful work. A group cannot mix scored, confirmation
and excluded material constraints; extraction must separate their dispositions.
An education route's conditional wording remains visible inside its parent group and
does not independently change denominator membership.

Only SCORED groups reach matching or the score's assessment set. The matching schema
cannot change eligibility. Python rejects assessments for excluded groups. Required
weight remains 2, preferred weight remains 1; MATCH/PARTIAL/GAP values remain 1/0.5/0.
Python rounds `100 × sum(weight × value) / sum(weight)` once to one decimal. Zero
SCORED groups yield null Coverage and block resume generation. Excluded groups retain
null status and empty citations rather than fabricated GAP assessments.

## Persistence and reuse

`career_requirement_sets` is an additive table with `jd_key`, exact `raw_jd`,
`policy_version` and validated `extraction_json`. The key hashes exact JD content
and policy version. A cache lookup also checks exact JD equality and policy version.
Whitespace or wording changes create a different JD version.

The first validated extraction wins an atomic insert. A concurrent candidate cannot
overwrite that set. The coordinator saves extraction before matching, so matching
failure still leaves a reusable canonical set. Unchanged reanalysis, a separately
saved job with identical JD, profile edits and provider/model changes reuse the set.
A reopened process reads the same cache. Profile changes still require rematching.

This stage exposes no re-extraction action or requirement-history UI. A new JD or
policy version needs a new extraction. Existing reports remain inspectable during
failed updates. Old-policy reports are visibly outdated and block new resume generation
until reanalysis. Their historical Coverage is preserved rather than recomputed
against a different denominator.

The existing `job_requirements` columns remain compatible. `report_json` stores full
canonical group metadata, policy version and JD key; only scored groups have rows
in `job_matches`. Saved-job reads use a LEFT JOIN so excluded clauses stay visible.
Deleting a job prunes extraction sets only when no remaining raw JD or saved report
refers to them, including cached prior JD versions. The deletion transaction retains
shared sets and rolls back cache deletion with the job's other artifacts on failure.

## Evaluation

`career_requirement_groups.json` contains reviewed synthetic education, alternatives,
traits, collaboration, writing, logistics and importance cases. It uses invented
Northstar Instruments and Cedar Labs identities. `career_requirement_stability.json`
preserves the diagnosed Chinese JD's qualification structure without private profile
facts. The deterministic tests inject proposals through the actual coordinator,
validation, SQLite cache, evidence-delivery boundary and scorer.

`evals.career_extraction.extraction_stability` measures group counts, semantic identity
agreement, source-span coverage, changed-identity merge/split rate, normalized-subject
duplicate rate, importance/category/eligibility agreement and weighted denominators.
A reviewed canonical reference supplies gold source coverage; without that reference,
the function compares against the first accepted set. The merge/split rate measures
changed group identities and does not independently infer linguistic merge operations.

Six analyses of the diagnosed equivalent reuse seven groups, four SCORED groups,
three NON_SCORABLE groups and denominator 7. The degree/major and fallback clauses
remain one education group; health/diligence/dedication never reaches matching or
Coverage. Six analyses of the broader gold JD reuse ten groups, six SCORED groups,
one NEEDS_CONFIRMATION group, three NON_SCORABLE groups and denominator 10.
All identity, source coverage and policy-field agreements are 100%; changed-identity
and duplicate rates are zero. These results measure deterministic accepted-set reuse,
not independent live-extraction accuracy or semantic matching stability.

The subsequent [matching rubric](MATCHING_RUBRIC.md) adds explicit constraint support,
route validation and reviewed semantic rules. Semantic interpretation can still produce
different MATCH/PARTIAL/GAP judgments. This stage guarantees stable scoring questions and denominator membership
for a reused set, rather than promising identical Coverage after every matching call.

### Independent fresh extraction

`career_extraction_executability.json` retains synthetic degree/major, conditional
bachelor's relaxation, typo-preserving technology alternatives, mixed nearby capabilities,
excluded traits and preferred experience. Its compressed numbered JD repeats technologies
in responsibilities. The failure regressions cover acceptance, structural repair, omitted
qualifications, strict semantic guards and exhaustion without cache publication.

Run extraction without matching in a new temporary database for every trial:

```bash
python -m evals.career_extraction --live --trials 5 --output /tmp/career-fresh-extraction-results.json
```

The runner refuses to reuse a trial directory and never clears an existing cache. It records
success, submissions, iterations, group counts, canonical identity/eligibility agreement,
changed identities, duplicate rates and denominator agreement against the synthetic reference.
Source qualification coverage and source eligibility agreement compare reference material
spans with group provenance, ignoring only boundary punctuation and whitespace for these
metrics. This comparison changes no stored excerpt, offset or JD hash. Exact source-span
and semantic-ID agreement remain separate metrics; neither proves semantic equivalence.

Five configured GLM/glm-5.2 trials validated extraction with 1, 4, 1, 1 and 2 submissions.
Each began with zero cached sets and ended with one. All retained four SCORED groups,
denominator 7, 100% reference material-source coverage and source eligibility agreement,
and zero normalized-subject duplicates. Total groups varied between six and seven.
Exact identity agreement against the reference ranged from 16.7% to 18.2%; changed-identity
rates ranged from 81.8% to 83.3%. Literal-subject choices and excluded-clause grouping still
vary. These five trials establish executability on this case, not general extraction accuracy.

### Extraction submission reliability

Fresh extraction requests named `submit_stage_result` on OpenAI-compatible and native
Anthropic clients until validation succeeds. Explicit unsupported tool-choice rejections
disable forcing for that stage; injected clients keep their existing call signature.
The coordinator permits one corrective no-submit request within the existing iteration
cap. Recovery drops only the unsubmitted assistant completion and retains stable JD
inputs and prior validator feedback. Partial prose never reaches canonical validation
or cache publication. Repeated missing submissions return an explicit structured-submission
error; a truncation during either attempt returns a distinct output-truncation error.
Unknown provider termination reasons fail explicitly. Failed extraction preserves previous
reports, requirement rows, Coverage and resumes. Semantic validation, groups-v1, exact-JD
identity and deletion/cache-pruning behavior retain their existing contracts.
