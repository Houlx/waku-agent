# JD Requirement Coverage stability diagnosis

Implementation status, 2026-10-07: The approved first stabilization stage implements
[canonical requirement groups and score eligibility](REQUIREMENT_GROUPS.md), immutable
JD/policy extraction reuse and visible excluded clauses. The matching rubric and
Coverage weights/arithmetic remain unchanged. The diagnosis below remains historical.

Semantic status changes explain most of the reported 46.2%–64.3% spread;
extraction changes explain the remainder. The same eight evidence records reached
all four recent matching runs. The low and high runs differ in three score inputs:
a separately scored education exception, initiative/teamwork PARTIAL versus MATCH,
and health/diligence/dedication GAP versus PARTIAL. The current arithmetic reproduces
every saved score exactly.

This diagnosis changes no production code, prompts, schema, eligibility, weights,
or arithmetic. The proposed contracts below require approval before implementation.

## Evidence and scope

The investigation inspected current `career_jobs.py`, `career_matching.py`, the
Career evidence tool contracts, the [handoff](HANDOFF.md#matching-correctness-fix),
and the [previous diagnosis](MATCHING_CORRECTNESS_DIAGNOSIS.md). The current checkout
was `2f8dc15`. The investigation read the user's SQLite database through a read-only
connection and examined only Career stage markers, coverage metadata, submitted
requirements, and submitted assessments in the October 6–7 traces. It did not
inspect retired product behavior or hidden model reasoning.

Five saved jobs contain byte-identical raw JDs for the Chinese 测试/软件工程师 role.
The JD asks for a master's degree and a related major, with a conditional bachelor's
exception; proficiency in either LabVIEW or C++; coordination; writing; health,
diligence, dedication, initiative and teamwork; and preferred engine-test-platform
experience. The JD spells LabVIEW as `1abview`. Extracted text sometimes corrects
that spelling, while source excerpts preserve the original.

The four new jobs at 12:19–12:24 on October 7 reproduce the user's reported range.
Eight completed post-fix analyses at 10:33–12:24 share the full snapshot digest
`d84e2fecdad147b9ac0e60d0ba27d2349f3616a1d6f59fcd860c4712ae34a2c8`.
Each matching trace reports full delivery of eight active records. The current
confirmed snapshot has the same digest. These facts establish unchanged confirmed
profile/evidence inputs for this cohort, rather than merely assuming them.

The 10:29 run has a different snapshot digest and is excluded from controlled
comparisons. Pre-fix traces establish additional extraction examples but cannot
isolate semantic variability from the old delivery bug. Historical traces do not
stamp the exact source revision or prove the exact initial JD for every overwritten
reanalysis. The four separately saved recent jobs establish exact JD equality;
earlier same-job runs establish equivalent clauses through their extraction artifacts.
All times below use Asia/Shanghai on 2026-10-07 unless another date appears.

Private profile records and complete trace-derived artifacts remain outside the
repository under `/tmp/career-coverage-diagnosis/`. The report uses anonymous evidence
aliases: E1 is master's education, E2 is bachelor's education, W is work, P1 is SSR,
P2 is review-management, P3 is RAG, P4 is AB testing and P5 is React upgrade.
The local `runs.json` retains actual evidence IDs and observable reasons.

## Current architecture and unchecked choices

`analyze_job` runs extraction, assigns fresh requirement UUIDs, runs matching against
a checked evidence snapshot, validates assessments, then calls `calculate_match_score`.
It replaces saved requirements and assessments only after successful completion.
Reanalysis does not reuse a canonical requirement set.

| Stage | Current contract | Remaining freedom |
|---|---|---|
| Extraction | The prompt requests “atomic requirements,” required/preferred importance and a verbatim source excerpt. | The prompt gives no splitting, AND/OR, exception, relevance or eligibility rules. |
| Extraction validation | The validator checks exact fields, bounded lists, nonempty category/text, importance enum, excerpt substring, and exact casefolded text duplicates. | Different text can overlap semantically; an excerpt need not entail its summary; broad or overlapping excerpts pass. |
| Category | The schema accepts any nonempty string. | English labels, Chinese labels and granularities vary. |
| Matching | The prompt defines MATCH as “full support,” PARTIAL as “incomplete support,” and GAP as “the profile provides no support.” | The prompt gives no material-constraint, equivalent-major, transferable-skill, alternative-route or vague-trait rules. |
| Match validation | The validator checks one status per requirement, reason, active delivered citations, complete evidence delivery for GAP, and education citations for recognized pure education positives. | The validator does not adjudicate semantic sufficiency or bind each material constraint to supporting facts. |
| Scoring | Every extracted requirement receives required weight 2 or preferred weight 1; statuses receive 1, 0.5 or 0. | The scorer has no eligibility field and does not use category, source excerpts, keywords, reasons or number of citations. |

Category has zero direct arithmetic effect. It can affect model interpretation and
the education citation guard. That guard recognizes several education labels and
degree phrases; all recent degree requirements also contain recognized degree text.
No observed score difference requires a category-driven validation change.

## Repeated requirement comparison

The table aligns source-clause meaning, not generated UUIDs. M means MATCH, P means
PARTIAL, G means GAP. Every row receives required importance except the separately
extracted bachelor's exception and engine experience, which receive preferred importance.

| Source meaning | A: 12:19:10 | B: 12:20:31 | C: 12:22:04 | D: 12:23:18 |
|---|---|---|---|---|
| Master's degree + related major | One requirement, M | Two requirements, M + M | One requirement, M | One requirement, M |
| Conditional bachelor's exception | Inside preceding requirement | Separate preferred, M | Separate preferred, M | Separate preferred, M |
| Either LabVIEW or C++ proficiency | G | G | G | G |
| Coordination/communication | M | M | M | M |
| Writing ability | P | P | P | P |
| 身体健康，吃苦耐劳，爱岗敬业 | G | G | P | G |
| Initiative + teamwork | P | M | M | P |
| Engine platform construction/operation | Preferred, G | Preferred, G | Preferred, G | Preferred, G |
| Extracted requirements | 7 | 9 | 8 | 8 |
| Weighted numerator / denominator | 6 / 13 | 10 / 16 | 9 / 14 | 7 / 14 |
| Reconstructed and saved Coverage | 46.2% | 62.5% | 64.3% | 50.0% |

All underlying qualification clauses occur in all four runs. No entirely new
qualification explains the requirement count. Only the separate exception and
separate degree/major items occur in some runs. Splitting degree and major increases
their combined weight from 2 to 4; separately scoring the exception adds weight 1.
The exception overlaps the education decision and incorrectly becomes an independent
preferred qualification, although the JD uses it as an alternative route.

| Meaning | A category | B category | C category | D category |
|---|---|---|---|---|
| Degree/major and exception | education | education | 学历与专业 | education |
| LabVIEW/C++ | technical_skill | technical | 技能要求 | technical_skill |
| Coordination, writing, health/attitudes, initiative/teamwork | soft_skill | soft_skill | 综合素质 | soft_skill |
| Engine experience | experience | experience | 工作经验 | experience |

The four runs have no required/preferred disagreement for separately aligned items.
The exception instead switches between belonging to one required group and becoming
an independently weighted preferred item. Calling that a simple importance flip
would misidentify the actual grouping error. Eligibility has no variable field:
all extracted rows are implicitly scored in every run.

The broader same-snapshot cohort exposes additional instability:

| Start time | Requirements | Numerator / denominator | Coverage | Distinctive observable difference |
|---|---|---|---|---|
| 10:33:24 | 8 | 6 / 14 | 42.9% | Degree/major P; dedication joins initiative/teamwork, which receives P; health/diligence receives G. |
| 10:35:00 | 8 | 9 / 14 | 64.3% | Health/diligence/dedication P; initiative/teamwork M. |
| 10:36:03 | 8 | 8 / 14 | 57.1% | Health/diligence/dedication G; initiative/teamwork M. |
| 10:37:27 | 8 | 7 / 14 | 50.0% | Health/diligence/dedication G; initiative/teamwork P. |
| 12:19:10 | 7 | 6 / 13 | 46.2% | The education exception merges into degree/major. |
| 12:20:31 | 9 | 10 / 16 | 62.5% | Degree and major split; the exception remains separate. |
| 12:22:04 | 8 | 9 / 14 | 64.3% | The categories switch to Chinese; health/attitudes receives P. |
| 12:23:18 | 8 | 7 / 14 | 50.0% | Initiative/teamwork receives P. |

The same-snapshot historical range is therefore 42.9%–64.3%, which exceeds the
four-job range. The earlier 10:33 degree reason questions major compatibility;
later reasons accept the explicit computer-science direction in the unchanged
confirmed evidence. That is an interpretation difference, not evidence loss.

## Observable evidence and reasons

The following table preserves each recent assessment's citation set and summarizes
its observable reason. The local artifact preserves complete original reason text.

| Requirement | A citations and reason | B citations and reason | C citations and reason | D citations and reason |
|---|---|---|---|---|
| Degree/major | E1,E2; master's degree and computer-related major satisfy the clause. | Degree: E1; major: E1,E2; both satisfy their separate clauses. | E1; master's and computer-related major satisfy the clause. | E1,E2; master's and computer-related direction satisfy the clause. |
| Exception | The merged education assessment uses E1,E2. | E1,E2; master's exceeds bachelor's floor. | E1,W; master's makes relaxation unnecessary; work shows ability. | E1,W,P1,P2,P3,P4,P5; degree and work purportedly satisfy the relaxation route. |
| LabVIEW/C++ | None; neither technology appears. | None; neither technology appears. | None; neither technology appears. | None; neither technology appears. |
| Coordination | W,P5,P4,P2; cross-team work and leadership support M. | W,P4,P5; cross-team coordination supports M. | W,P2,P4,P5; team coordination supports M. | W,P5,P2,P4; coordination and leadership support M. |
| Writing | P4,W; delivery/use explanations indirectly support P. | W,P4,P2; design/review/delivery indirectly support P. | W,P4; explanations/design provide indirect support, without explicit writing outputs. | W,P5,P4; design/review/explanations provide indirect support. |
| Health/attitudes | None; records contain no health or attitude facts. | None; records contain no personality facts. | W,P5; leadership allegedly shows dedication/diligence, while health remains unknown. | None; records do not establish health or attitudes. |
| Initiative/teamwork | W,P5,P2; collaboration is supported, but initiative lacks explicit evaluation. | W,P4,P5; initiating projects and cross-team work support M. | W,P5,P2,P4; project ownership and collaboration support M. | W,P5,P2; behaviors exist, but exact trait wording/self-evaluation is absent, so P. |
| Engine experience | None; profile does not document the requested domain. | None; profile does not document the requested domain. | None; profile does not document the requested domain. | None; profile does not document the requested domain. |

C and D disagree about the sufficiency of substantially overlapping W/P5 evidence
for personality claims. The initiative reasons switch between behavioral evidence
and literal trait wording as the standard. The writing reasons sometimes demand
formal reports or agreements that the qualification itself never explicitly names.
These are concrete rubric ambiguities rather than a generic randomness explanation.

## Atomicity and denominator effects

“Atomic” currently has no operational definition beyond the prompt adjective.
The validator does not enforce a relationship between source syntax, material
constraints and scoring groups.

| Clause type | Observed or untested behavior | Consequence |
|---|---|---|
| Degree + major | A/C/D emit one row; B emits two. | Two satisfied constraints receive weight 4 instead of 2 in B. |
| Qualification + exception | A merges the bachelor's exception; B/C/D emit a preferred row. | The denominator changes from 13 to 14 before any degree/major split; the alternative route earns independent credit. |
| Multiple technologies | All recent runs retain “either LabVIEW or C++” as one row. | This cohort shows no technology split; future splitting would incorrectly turn OR into two independently scored requirements. |
| Multiple personality terms | Most runs group health/diligence/dedication separately from initiative/teamwork; 10:33 moves dedication to the latter group. | Group boundaries change what partial support means even when row count stays 8. |
| Whole personality bullet | The pre-fix October 6 22:33 extraction merges all five terms into one required row. | That grouping replaces two weight-2 rows with one weight-2 row; old semantic outcomes remain confounded by delivery. |
| Skill + years | This JD contains no explicit years threshold. | The cohort cannot measure a years/skill split effect. |
| Required qualification OR alternative qualification | The bachelor's relaxation is the concrete example. | An alternative must belong to the education group rather than add an extra preferred scoring opportunity. |

Source excerpts do not solve atomicity. B uses a broad education-plus-exception
excerpt for its degree row and overlapping excerpts for major/exception rows.
D uses each entire numbered bullet as the excerpt for several separate requirements.
The substring check accepts both approaches. Semantically overlapping rows can
therefore survive exact-text duplicate rejection.

## Score eligibility diagnosis

The scorer includes every extracted row. In all four recent jobs, the combined
health/diligence/dedication row contributes required weight 2 to the denominator.
A/B/D award it zero numerator; C awards it one numerator. That single unsupported
personality judgment changes Coverage by 7.14 points at denominator 14.

| Run | Current Coverage | Coverage if only health/diligence/dedication is excluded | Change |
|---|---|---|---|
| A | 46.2% | 54.5% | +8.4 points |
| B | 62.5% | 71.4% | +8.9 points |
| C | 64.3% | 66.7% | +2.4 points |
| D | 50.0% | 58.3% | +8.3 points |

These are counterfactual calculations using the existing formula over a filtered
input set, not implemented eligibility changes. Exclusion reduces the A-to-C spread
from 18.13 to 12.12 unrounded points. That 6.01-point reduction includes denominator
interactions; it must not be added to the 7.14-point status contribution below.

| Diagnostic group | This JD | Proposed treatment |
|---|---|---|
| Objectively scoreable from evidence | Degree, major, named technology proficiency and engine-domain experience | Score explicit material constraints; preserve qualifications and alternatives. |
| Potentially evidence-backed behavioral capability | Coordination and writing | Score demonstrable acts or outputs with a defined rubric; do not demand unsupported extra industry constraints. |
| Vague mixed personality claim | Initiative + teamwork | Separate demonstrable collaboration from an undefined initiative trait; do not infer a universal personality assessment from project success. |
| Non-scorable for Career Evidence | 身体健康，吃苦耐劳，爱岗敬业 | Retain visibly as non-scorable; exclude from Coverage. Health must not be inferred from career accomplishments. |
| User-confirmable logistics | None in this JD | Travel, shifts, relocation, availability and missing driver's-license facts should request confirmation rather than become gaps. |

责任心强 and 良好的职业道德 do not occur in the inspected JD or its recent
requirements. The code would permit them and score them if extracted, but this
cohort provides no measured contribution for those phrases. The report does not
claim every soft skill is unsuitable for matching. Evidence can demonstrate
coordination or writing without establishing health or moral character.

## Frozen-requirement diagnostics

Five historical runs have the same eight logical requirements and unchanged evidence:
10:35, 10:36, 10:37, 12:22 and 12:23. Their extraction strings, category labels,
source-excerpt boundaries and runtime IDs are not byte-identical. Their frequencies
therefore describe aligned historical outcomes rather than a fully controlled trial.

| Aligned requirement | MATCH / 5 | PARTIAL / 5 | GAP / 5 |
|---|---|---|---|
| Degree + major | 5 | 0 | 0 |
| Bachelor's exception | 5 | 0 | 0 |
| Either LabVIEW or C++ | 0 | 0 | 5 |
| Coordination | 5 | 0 | 0 |
| Writing | 0 | 5 | 0 |
| Health/diligence/dedication | 0 | 2 | 3 |
| Initiative/teamwork | 3 | 2 | 0 |
| Engine experience | 0 | 0 | 5 |

An offline replay freezes the 12:23 extraction content and the current confirmed
evidence snapshot, maps those five submitted assessment sets to fixed diagnostic
requirement IDs, and invokes the current match validator and score function. All
five validate and reproduce 64.3%, 57.1%, 50.0%, 64.3% and 50.0%. The replay models
full delivery with a local client stub. It proves that current validation permits
these competing semantic outcomes; it does not measure fresh model frequencies.

Six user-approved live trials then bypassed extraction with the 12:23 extraction
result, reused the same in-memory copy of the confirmed evidence, and executed the
unmodified matching prompt, real coordinator, evidence delivery, validator and scorer
through configured GLM `glm-5.2`. Requirement text, categories, importance, keywords,
source excerpts, job summary and responsibilities were frozen. The normal coordinator
still generated per-run job and requirement UUIDs; these metadata values varied,
so the experiment freezes semantic inputs rather than claiming byte-identical requests.
The evidence digest was checked after every trial and remained unchanged. Every
successful trial received all eight records in full mode.

| Frozen requirement | MATCH / 6 | PARTIAL / 6 | GAP / 6 |
|---|---|---|---|
| Degree + major | 6 | 0 | 0 |
| Bachelor's exception | 6 | 0 | 0 |
| Either LabVIEW or C++ | 0 | 0 | 6 |
| Coordination | 6 | 0 | 0 |
| Writing | 0 | 6 | 0 |
| Health/diligence/dedication | 0 | 1 | 5 |
| Initiative/teamwork | 5 | 1 | 0 |
| Engine experience | 0 | 0 | 6 |

Trial scores were 57.1%, 64.3%, 57.1%, 57.1%, 57.1% and 50.0%. Six of eight
requirements had identical statuses in every trial. Two requirements changed status.
Four trials shared the 57.1% status vector, and two other trials each had a distinct
status vector. The exact all-trial status-vector agreement was therefore
absent, while the modal vector appeared in 4/6 trials. The observed frozen-input
spread was 14.2857 unrounded points, with denominator 14 throughout. The mean was
57.1429%, and the descriptive population standard deviation was 4.124 points.

Trial 2 awarded health/attitudes PARTIAL by inferring dedication/diligence from W/P5
leadership, while acknowledging missing health facts. The five GAP trials rejected
that inference. Trial 6 assigned initiative/teamwork PARTIAL despite citing W/P5/P2
collaboration because the profile lacked literal “teamwork spirit” wording and
traditional-engineering teamwork scenarios. The MATCH trials accepted behavioral
collaboration and initiative evidence without those extra criteria. These fresh
observable reasons reproduce the historical rubric conflict under frozen content.
The six-trial sample is descriptive and does not estimate a population error rate.

The historical unstable cases have different causes:

| Case | Supported cause | Limit of attribution |
|---|---|---|
| Health/diligence/dedication G versus P | Non-scorable compound requirement plus unspecified inference rules; project leadership becomes personality evidence in some reasons. | No deterministic field says whether this row belongs in Coverage. |
| Initiative/teamwork M versus P | Compound trait/capability requirement; behavior-based support competes with a demand for exact trait wording or self-evaluation. | Full delivery rules out missing records, but cannot force consistent interpretation. |
| Related major P versus M in the broader cohort | Degree/major equivalence and inconsistent use of the explicit confirmed specialization. | The later four-job cohort always accepts degree/major; it contributes zero semantic difference to that specific range. |
| Writing P | Weak or indirect writing evidence and an undefined output standard. | This requirement is consistently P in the recent cohort, so ambiguity exists without measured variance. |
| Education exception M | Conditional alternative is mistaken for a preferred standalone achievement. | This semantic mistake is stable in the controlled historical cohort; extraction determines whether it earns extra weight. |
| Years/threshold | The JD has no explicit threshold. | No measured contribution exists. |
| Related versus exact technology | Unrelated web technologies never satisfy LabVIEW/C++ in recent runs. | No observed status variance exists for that requirement. |

The live variation under frozen content demonstrates inconsistent judgments under
an underspecified rubric. These output artifacts do not prove that temperature alone
caused the variation or identify an internal model mechanism.

## Score decomposition

The current formula is `100 × numerator / denominator`, rounded once to one decimal.
Required weight is 2, preferred weight is 1; MATCH/PARTIAL/GAP values are 1/0.5/0.
Repeated offline calculation reproduces all four persisted scores without residuals.

The following exact counterfactual path transforms A into C:

| Step | Numerator / denominator | Unrounded Coverage | Increment |
|---|---|---|---|
| A's original inputs | 6 / 13 | 46.1538% | — |
| Extract a separate preferred exception with C's MATCH | 7 / 14 | 50.0000% | +3.8462 points |
| Change initiative/teamwork P → M | 8 / 14 | 57.1429% | +7.1429 points |
| Change health/diligence/dedication G → P | 9 / 14 | 64.2857% | +7.1429 points |

The total is 18.1319 unrounded points, displayed as an 18.1-point range. In this
stated order, semantic judgments contribute 14.2857 points, or 78.8%, and extraction
contributes 3.8462 points, or 21.2%. Required/preferred flips on common rows,
category arithmetic, PARTIAL↔GAP on other rows, and unexplained arithmetic each
contribute zero to this particular endpoint comparison. The slogan contributes
through semantic G→P, so it must not also be counted as a separate eligibility change.
Its inclusion is a structural enabling cause shared by both endpoints.

The decomposition depends on order because the denominator changes. Averaging the
marginal effects over every ordering of these three changes assigns 3.2967 points
to separate-exception extraction and 7.4176 points to each semantic change. Semantic
matching still explains 81.8% of the endpoint difference under that convention.
These are arithmetic attributions conditional on observed outcomes, not randomized
causal estimates of what a model would do after changing its prompt.

B demonstrates a different extraction effect: starting from D's 7/14, splitting
a satisfied degree/major row into two gives 9/16 = 56.25% (+6.25 points), then
initiative/teamwork P→M gives 10/16 = 62.5% (+6.25 points). Thus degree splitting
materially inflates coverage even though the underlying education facts agree.
No additive endpoint attribution can represent every pair of runs simultaneously.

The five aligned eight-requirement runs span 50.0%–64.3%, with denominator 14 fixed.
Health/attitudes and initiative/teamwork account for the entire 14.2857-point spread.
The broader eight-run cohort spans 42.9%–64.3%; degree/major interpretation and
personality regrouping introduce additional differences. That broader comparison
must not be substituted for the four-job 46.2%–64.3% decomposition.

## Root causes ranked by measured contribution

1. The semantic rubric permits incompatible standards for initiative/teamwork and
   health/diligence/dedication. Each supplies 7.14 points in the reported endpoint
   path, and together they dominate the measured range.
2. Extraction lacks deterministic grouping and alternative-route rules. Separate
   exception scoring supplies 3.85 points in that endpoint path; degree/major
   splitting supplies 6.25 points in the D-to-B path before its status change.
3. Eligibility is implicitly “score everything extracted.” That policy gives the
   health/attitudes row 12.5%–15.4% of total denominator weight across A–D. It enables
   the measured personality-status contribution and depresses reports with GAP.
   Its effect overlaps item 1 rather than adding an independent variance component.
4. Category and provenance contracts are too loose to stabilize meaning. They vary
   visibly, but their direct score contribution is zero in the inspected cohort.
5. The formula deterministically transmits upstream choices. The investigation
   found no arithmetic randomness, evidence loss or unexplained residual.

## Proposed canonical requirement contract

A small constraint-group contract is sufficient for these cases. Fields alone do
not make an LLM extractor deterministic. Validation, stable policy, reviewed gold
examples and reuse of an approved extraction are also necessary.

| Field | Minimal meaning |
|---|---|
| `source_spans` | Offsets plus exact excerpts from an immutable JD version; one group can cite multiple spans. |
| `canonical_text` | A concise faithful statement; it cannot add a qualification from responsibilities or drop a material constraint. |
| `category` | A closed vocabulary: education, experience, skill, certification, language, demonstrated_capability, logistics, personal_trait, other. |
| `importance` | Required or preferred, supported by explicit wording or a documented default; an exception inherits its parent group's importance. |
| `eligibility` | SCORED, NEEDS_CONFIRMATION or NON_SCORABLE, with a short visible policy reason. |
| `constraints` | Material conditions with source references; optional structured operators express ALL, ANY and conditional alternatives. |
| Stable identity | An identity derived from JD version, source spans and grouping policy version; UUIDs remain acceptable storage keys but do not establish semantic identity. |

Each group should own one scoring opportunity. A requirement can contain several
material constraints without earning extra weight for every comma. Degree AND major
can remain one education group. The bachelor's exception is an alternative inside
that group. “Either LabVIEW or C++” is an ANY constraint inside one skill group.
Separate unrelated qualifications receive separate groups. Repeated or paraphrased
qualifications cannot earn additional opportunities.

The education group should represent the JD's normal degree/major route and its
conditional relaxation route without guessing whether the major requirement is
also relaxed. The observed wording explicitly relaxes degree level. Any ambiguous
scope should remain visible for review rather than silently widening the exception.
An alternate route can include a non-scorable phrase such as “outstanding ability”;
that unresolved condition must not become automatic positive credit or an extra row.

A general expression language would exceed the minimum need. A shallow ALL/ANY
structure with an optional conditional alternative covers the observed degree,
exception and technology clauses. Constraints need identifiers for evidence and
unmet-condition explanations, but they need not become independently scored rows.
Mixed scoreable/non-scorable personality clauses should separate their dispositions
before scoring, rather than award half credit to a whole slogan bundle.

Extraction should be keyed by JD content plus extraction/policy version and reused
for repeated matching. An explicit re-extraction can show a requirement diff before
replacing a reviewed set. Stable IDs alone cannot prevent different canonical texts,
grouping or source spans from changing the score.

## Proposed eligibility policy

The three proposed dispositions are sufficient for the current product. They
separate evidence-based comparison, missing user declarations, and unsuitable claims
without multiplying match statuses. Eligibility must be determined before matching
and shown with its reason. The matching model must not change denominator membership.

SCORED includes objective qualifications and demonstrated capabilities with observable
criteria. Missing support can produce GAP after complete evidence delivery. A driver's
license with a documented confirmed fact can be scored as an objective credential.
NEEDS_CONFIRMATION covers unanswered logistics and declarative facts that Career
Evidence cannot establish, including an undocumented license. A confirmed objective
fact can move to SCORED under an explicit policy. A confirmed willingness constraint
can remain a separately reported logistics answer so willingness does not silently
inflate qualification coverage.

NON_SCORABLE includes vague virtue slogans, generic dedication/diligence, unsupported
personality assessments and health assertions that career accomplishments cannot
establish. The UI should retain those JD clauses visibly and explain exclusion.
User self-praise must not automatically turn an unmeasurable trait into scored proof.
Undefined “initiative” belongs here unless the JD provides observable criteria;
documented collaboration can remain an evidence-backed capability.

Only SCORED groups enter the existing formula. NEEDS_CONFIRMATION and NON_SCORABLE
receive no MATCH/PARTIAL/GAP contribution. A job with no scored groups reports
insufficient scoreable information, rather than 0% or 100%. This recommendation
changes future denominator membership, not today's formula or weights.

## Proposed matching rubric

MATCH requires direct factual support for every material constraint in at least one
valid satisfaction route. Related wording can satisfy a constraint when a documented
normalization/equivalence rule establishes the relation; exact trait words are not
required for demonstrated behavior. An irrelevant higher degree does not satisfy
unmet subject or experience constraints, and satisfying the normal route does not
earn separate exception credit.

PARTIAL requires relevant support for a material constraint while another material
constraint is unsupported, weaker or below its stated threshold. The reason must
identify the satisfied and unmet constraints. A citation alone, general project
success, or a vague inference does not establish partial technical proficiency.
An explicitly documented lower degree or shorter duration can be partial support;
unrelated technologies alone cannot satisfy part of a named-technology OR clause.

GAP requires complete applicable evidence delivery and no factual support for a
material constraint or valid route. The reason describes unsupported claims in
this profile, without asserting that the person lacks the capability. Incomplete
delivery remains a validation failure, not GAP. Unanswered logistics remain
NEEDS_CONFIRMATION and excluded traits remain NON_SCORABLE.

Degree/major equivalence needs a reviewed vocabulary or explicit confirmed mapping.
Experience thresholds need a fixed reference date, duration rules, overlap handling,
and evidence for the actual skill rather than total employment tenure. Preferred
importance changes weight, not the standard of support. Adjacent technology needs
a defined relationship and a relevant shared constraint before it can earn PARTIAL.
Writing should be judged against the JD's actual output criterion, without inventing
formal-contract requirements. Behavior can support collaboration without a literal
“teamwork” self-description.

These principles constrain semantic judgment; they cannot guarantee perfectly stable
live-model statuses by themselves. Structured evidence, explicit constraint outcomes,
reviewed equivalences and persisted assessments are the next controls to evaluate
if residual variability remains.

## Gold cases and future verification

A small initial set can contain eight synthetic JD families with Chinese and English
wording variants. Each family should have a fixed source-clause map, reviewed grouping,
importance, eligibility and constraint expectations. Profile variants should change
one material fact at a time and use invented organizations and people.

| Family | Required regression examples |
|---|---|
| Software/AI | Python, RAG and PyTorch; exact technology support versus an adjacent stack; responsibilities without invented qualifications. |
| Traditional enterprise testing | The inspected JD structure with invented facts, master's/related-major, a conditional bachelor's route and engine-domain preference. |
| Education | Degree + major grouped; approved related major; wrong major; bachelor's-only and master's-only evidence; alternate-route conditions. |
| Years | Exactly 3 years, just below 3 years, overlapping roles, missing dates, and skill tenure versus total tenure. |
| Multiple skills | A AND B, A OR B, skill + proficiency + years; punctuation and bullet-layout variants. |
| Importance | Explicit required and preferred wording, Chinese 优先, and a relaxation clause that must not become a preference. |
| Personality and capabilities | Health/diligence/dedication/responsibility/morality excluded; collaboration behavior supported without exact trait wording; writing evidence graded against actual output criteria. |
| Logistics | Travel, shifts, relocation, availability and driver's license; absent declaration, confirmed yes, confirmed no and documented credential. |

Extraction evaluation should hold the JD fixed and measure source-clause recall,
unsupported extra qualifications, group/constraint identity, merge/split rate,
semantic duplicates, importance accuracy, category accuracy and eligibility accuracy.
Repeated extraction should report exact canonical-set agreement and denominator
stability, independently of matching.

Matching evaluation should freeze requirements and evidence, record each constraint's
support, then measure status accuracy, per-requirement MATCH/PARTIAL/GAP frequencies,
status agreement, evidence sufficiency and unsupported-inference rate. Complete
record delivery is a separate invariant. Report score spread only after reporting
those upstream metrics. Scripted offline tests should check contracts and known
counterexamples; they cannot establish live semantic accuracy or repeatability.

The smallest implementation sequence is:

1. Approve the grouping, eligibility and rubric policy and freeze reviewed synthetic
   gold examples for the observed exception, degree/major and personality cases.
2. Add canonical provenance, stable scoring groups and eligibility validation;
   persist/reuse extraction by JD version and show excluded/confirmation clauses.
3. Score only approved SCORED groups using the unchanged arithmetic, with explicit
   alternative-route handling and deterministic merge/duplicate guards.
4. Require constraint-level support and unmet-constraint reasons during matching;
   apply reviewed degree/major and threshold rules and reject unsupported inference.
5. Run separate repeated extraction and frozen-matching evaluations before deciding
   whether further deterministic semantic rules or score-formula work is warranted.

The observed variance gives no reason to retune weights or arithmetic first.
Canonical groups, explicit eligibility and consistent statuses address every
identified input difference. Their live stability still needs measurement after
implementation. This diagnosis stops before those changes.

## Verification and local artifacts

The local audit scripts parsed observable Career artifacts, reconstructed all four
saved scores, replayed five historical assessment sets against fixed requirements,
and completed six approved live matching trials. No extraction or resume-generation
provider call was made. A preliminary sandboxed attempt failed with APIConnectionError
before receiving a response; it contributes no trial outcome. Automatic approval
review initially rejected network export of private evidence. The user explicitly
approved six trials before the successful external calls. Provider settings and
user runtime data were not changed; diagnostic traces and usage stay in `/tmp`.

The local artifacts include:

- `audit_runs.py`, `runs.json` and `jobs.json`, which preserve the local extraction,
  observable assessment and identical-JD audit.
- `replay.py` and `offline_replay.json`, which preserve fixed-requirement validation
  and deterministic score reconstruction.
- `frozen_matching.py` and `frozen_results.json`, which preserve the six live trials,
  requirement fields, actual evidence IDs, observable reasons and scores.
- `frozen-runtime/traces/` and `frozen-runtime/usage.jsonl`, which preserve the isolated
  live coverage audit and provider usage.

The focused job, matching-diagnostic and rulebook suite passed 80 tests. The
investigation added only this diagnosis and its documentation-index entry; it did
not add or change behavior tests because it changed no runtime behavior.
`git diff --check` passed. A full release gate was not needed for these documentation
changes; the focused suite exercises the inspected score and matching contracts.
