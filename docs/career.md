# Career Agent

The local dashboard's **Career Agent** workspace collects your career facts and
organizes them into a profile. It analyzes pasted job descriptions and explains
which requirements your confirmed profile supports. You can then explicitly
generate a tailored resume from confirmed Career evidence.

## Create your profile

Start `waku dashboard`, configure a provider through Waku's existing setup, and
open **Career Agent**. Enter basic contact information and add work, project,
education or other career records. Describe what you actually did, the problems
you solved and the results you remember. You do not need polished resume bullets.

Save your information, then select **Normalize Profile**. The agent uses Waku's
configured model to organize each source record into a title, description and
skills. Review the result, edit any inaccurate wording, and select
**Confirm & Continue**. Confirmation saves your edits and confirms the entire
profile. The Career dashboard lets you reopen the profile or original input.

## Analyze a job

Paste a job description and select **Analyze Job**. The agent extracts required
and preferred requirements, formulates searches over your Career records, and
inspects the evidence before assessing each requirement as MATCH, PARTIAL or GAP.
The report shows explanations, strengths, gaps and recommended resume focus.
Expand **View Evidence** to inspect the original information, explicit corrections,
normalized description, skills and evidence ID. Saved reports survive reload.

**JD Requirement Coverage** measures support in your current profile. Required
requirements carry weight 2; preferred requirements carry weight 1. MATCH counts
as full coverage, PARTIAL as half and GAP as zero. Python calculates the weighted
percentage and rounds to one decimal. This score does not predict interviews or
hiring. A JD without usable requirements displays **Insufficient information**.

Profile changes mark saved reports outdated. Their original evidence remains
inspectable. Confirm your edited profile, then choose **Re-run Analysis** and
**Re-run Job Analysis** to replace a report. A failed run retains the pasted JD
and any earlier successful report; the earlier report remains outdated.

## Generate and review a resume

Review the Match Report, choose English, Chinese or Japanese, and select
**Generate Tailored Resume**. The language defaults to a simple estimate of the
JD language; you can override it. Analysis never generates a resume automatically.
Generation requires a confirmed profile, completed current analysis and usable
requirements. Profile changes require confirmation and reanalysis.

The resume review displays factual record headings and cited summaries, skills
and bullets. Expand **View Evidence** to inspect the source behind a claim.
**Download Markdown** exports the saved draft without calling the model again.
**Print / Save as PDF** uses browser printing and hides navigation, buttons,
activity and evidence annotations. Chinese and Japanese use system-font fallbacks.

Each job retains one current draft. A successful generation replaces that draft;
a failed generation retains it. Profile edits and successful reanalysis mark an
older draft outdated until you generate a replacement. Career Activity displays
stage/tool status, evidence IDs, token usage and elapsed stage time. It does not
display model reasoning.

## Understand the data

Career stores the current raw input separately from its normalized representation
in `state.db` under `WAKU_HOME`. Explicit profile edits are stored separately as
user-provided facts. Each coherent career record has a stable evidence ID and
retains its original input. Replacing onboarding input clears confirmation and
requires normalization again. Saving profile edits also clears confirmation until
you confirm them.

Career uses its own tables and a scoped tool registry. It does not retrieve
conversational memory, log Career facts into chat, or consolidate them into Waku's
ordinary memory. Normalization and job analysis use the existing loop, provider
client and tracing; trace files include submitted data, tool events and model usage.

The application validates structure and source IDs and rejects new numeric claims
during normalization. These checks cannot verify every semantic paraphrase. Review
technologies, responsibilities and outcomes before confirming your profile.
Job analysis validates JD excerpts, complete requirement coverage and inspected
evidence IDs. These checks establish provenance; they do not prove that every
semantic match or report summary is correct. Review the explanations and evidence.

Career endpoints are blocked on hosted Waku. This workspace currently supports
only a single person's local dashboard.

## Continue development

Read the [approved product requirements](career-agent/PRODUCT_SPEC.md),
[implementation plan](career-agent/IMPLEMENTATION_PLAN.md), and
[current handoff](career-agent/HANDOFF.md) before changing Career functionality.
Days 1–3 are implemented. Optional Day 4 requires explicit user approval.
