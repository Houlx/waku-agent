# Matching rubric

Career evaluates material constraints under `matching-v1` before assigning one
MATCH/PARTIAL/GAP result to each SCORED canonical group. The rubric leaves
[groups-v1](REQUIREMENT_GROUPS.md), eligibility, extraction reuse, evidence delivery,
FTS and Coverage arithmetic unchanged. `career_rubric.py` owns the matching prompt,
schema, reviewed major mappings and structural validation.

Full-evidence matching supplies every active compact record and exposes only submission.
The model can cite those stable IDs directly. Inventory matching retains search and
complete-record inspection. Both modes credit evidence only after successful provider
delivery and retain the 48,000-byte initial selection and 64,000-byte request limits.

## Submission reliability

Matching retains raw provider termination reasons. A normal no-tool completion or
length termination without a valid submission permits one concise submit-only
correction within the existing ten-iteration cap. The correction removes only that
unsubmitted assistant response. Initial canonical/evidence inputs, earlier tools,
server-owned delivery and snapshot checks remain intact. A repeated missing submission
returns an explicit submission error; length termination returns an actionable truncation
error. Neither prose nor absent assessments become a report or GAP.

Full mode requests named submission when the configured adapter supports tool choice.
An explicit unsupported-choice rejection disables enforcement for that stage. Inventory
mode keeps retrieval autonomy. Accepted submissions retain the existing final confirmation.
The [provider contract](../providers-registry.md#termination-and-stage-scoped-tool-choice)
records metadata, scope and fallback behavior. Validator feedback reports a wrong result
type, missing group IDs and the offending invalid citation without weakening validation.

## Constraint contract

The coordinator adds a matching-only `matching_routes` overlay to copied groups.
The primary route uses the existing ALL/ANY constraints. An education alternative
uses its existing operator and items plus its explicit verbatim condition. The
condition may contain a stronger qualification than abbreviated route items.
Python assigns local IDs `primary:0`, `primary:1`, `alternative:0` and so on, with
`alternative:condition` reserved for that condition. IDs belong to their enclosing
group. The overlay changes neither cached extraction nor semantic identity.

Every assessment includes `requirement_id`, `status`, `evidence_ids`, `reason`,
`constraint_results` and `satisfied_routes`. Every constraint result includes:

| Field | Contract |
|---|---|
| `constraint_id` | The result names exactly one constraint in this group. |
| `status` | The model selects SATISFIED, PARTIALLY_SUPPORTED or UNSUPPORTED. |
| `evidence_ids` | Positive support cites unique records delivered to the model; UNSUPPORTED has no supporting citations. |
| `reason` | The model states a concise factual explanation; weaker support identifies supported facts and unmet material. |

SATISFIED means sufficient factual support for the actual material criterion.
PARTIALLY_SUPPORTED means relevant support remains indirect, weaker or below an
explicit threshold. UNSUPPORTED means confirmed Career Evidence does not establish
that criterion. The model must evaluate unused alternatives too. Their unsupported
constraints do not diminish a fully satisfied primary route.

## Group contract and validation

An ALL route needs every item SATISFIED. An ANY route needs at least one SATISFIED
item. An alternative also needs its condition SATISFIED. Conditions from different
routes cannot combine into a complete route. `satisfied_routes` lists exactly the
complete route IDs (`primary`, `alternative`).

MATCH requires at least one complete route. PARTIAL requires positive material
support without a complete route; its reason identifies supported and unmet/weaker
material. GAP requires no positive material support and complete applicable evidence
delivery. Reasons describe what confirmed evidence establishes, without asserting
that the person objectively lacks a capability. Uncertainty alone earns no credit.

Python rejects missing, duplicate or foreign group/constraint IDs, invalid support
statuses, empty reasons, missing positive citations, unsupported citations, incomplete
route claims and group statuses inconsistent with route algebra. Group citations
must equal the union of constraint citations. Positive degree/major constraints
require education citations individually, in addition to the existing group-level
education guard. Unknown/inactive/undelivered citations remain invalid. Excluded and
confirmation groups cannot receive matching assessments. Incomplete delivery remains
a validation failure rather than GAP. Failed reanalysis retains the previous report.

Python enforces structure; the model still interprets semantic sufficiency. A model
can mislabel a fact SATISFIED while satisfying every structural check. Python does
not attempt to prove natural-language reasons or encode an academic ontology.

## Reviewed semantic rules

Degree level and major remain separate. Confirmed bachelor's, master's and doctorate
levels form a narrow ordered set. A higher degree satisfies a lower level only;
the remaining constraints of the selected route still apply. Exact majors and
explicit confirmed equivalence mappings can support field requirements. When the
constraint allows a related field, the reviewed set permits computer science and
software engineering for computing. No transitive or arbitrary academic equivalence
is allowed. A supported master's level with an unsupported major earns PARTIAL;
a materially relevant bachelor's below a master's threshold supplies partial support.

Explicit numeric/duration thresholds use SATISFIED at or above the threshold,
PARTIALLY_SUPPORTED for relevant evidence below it, and UNSUPPORTED for no relevant
evidence. Employment tenure does not imply skill tenure. Ambiguous dates cannot
supply invented exact durations; simultaneous intervals cannot be counted twice.

Named technologies require relevant evidence for that technology. Either LabVIEW or
C++ can satisfy the existing ANY group. React, JavaScript, Java and general software
work establish neither side. This policy approves no adjacent-technology equivalences.
Named-technology learning/prototype evidence can remain partial when it falls below
an explicit proficiency requirement.

SCORED demonstrated capabilities use observable coordination, ownership, communication,
leadership, reviews and writing outputs. Literal trait slogans are unnecessary.
Project delivery alone cannot establish a broad personality trait. Existing exclusions
for health, morality, vague initiative and teamwork spirit remain outside matching.
Writing evidence is judged against the actual canonical output criterion; the model
cannot silently demand contracts, publication or regulatory writing. Bare writing
ability already excluded by groups-v1 remains excluded.

Every group retains one scoring opportunity. Alternative routes earn no bonus.
Required/preferred weights remain 2/1; MATCH/PARTIAL/GAP values remain 1/0.5/0.

## Persistence and evaluation

Saved `report_json` records `matching_policy_version: matching-v1` and complete
constraint assessments. Historical reports without this field remain historical
artifacts; the rubric adds no report-history UI or forced report migration.

`career_matching_rubric.json` freezes 25 reviewed group/evidence pairs with invented
Morgan Vale, Cedar Labs and Cedar Institute identities. Cases cover related/exact/wrong
majors, higher/lower degrees, complete/incomplete alternative conditions, cross-route
mixing, exact technologies, either OR side, unrelated stacks, exact/above/below/missing
and ambiguous/overlapping durations, documented/limited/absent collaboration and
explicit/indirect/absent writing outputs. Tests never invoke extraction for these cases.

`evals.career_matching.repeated_matching` runs fresh matching stages with frozen groups,
one confirmed evidence snapshot and one policy version. It checks snapshot continuity
and returns a requirement fingerprint, reports and separate metrics:

- Per-group agreement compares status equality over every pair of trials.
- Full-vector agreement compares entire status vectors over every pair of trials.
- Status frequencies count MATCH/PARTIAL/GAP separately for each group.
- Unsupported-inference rate counts assessments with gold-incompatible positive
  material/status/citation claims; it returns null without reviewed gold.
- Coverage spread subtracts minimum Coverage from maximum Coverage.

The oracle does not judge arbitrary prose. Gold disagreement can reveal overclaims,
but equal statuses do not prove correct reasons. Natural-language explanations need
not be byte-identical. Six scripted trials per gold pair give 100% group/vector
agreement, zero gold overclaims and zero Coverage spread across 150 matching stages.
These results establish deterministic enforcement and experiment wiring, not live
model accuracy or semantic repeatability. Live trials are optional and were not run.
Related-major boundaries, exceptional experience, ambiguous duration and indirect
behavior/output sufficiency remain semantic judgments requiring live review.
