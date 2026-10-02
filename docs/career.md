# Career Agent

The local dashboard's **Career Agent** workspace collects your career facts and
organizes them into a profile. This first delivery supports onboarding, profile
normalization, editing and confirmation. Job analysis and resume generation are
not available yet.

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

## Understand the data

Career stores the current raw input separately from its normalized representation
in `state.db` under `WAKU_HOME`. Explicit profile edits are stored separately as
user-provided facts. Each coherent career record has a stable evidence ID and
retains its original input. Replacing onboarding input clears confirmation and
requires normalization again. Saving profile edits also clears confirmation until
you confirm them.

Career uses its own tables and a scoped tool registry. It does not retrieve
conversational memory, log Career facts into chat, or consolidate them into Waku's
ordinary memory. Normalization uses the existing loop, provider client and tracing;
trace files include submitted profile data, tool events and model usage.

The application validates structure and source IDs and rejects new numeric claims
during normalization. These checks cannot verify every semantic paraphrase. Review
technologies, responsibilities and outcomes before confirming your profile.

Career endpoints are blocked on hosted Waku. This workspace currently supports
only a single person's local dashboard.

## Continue development

Read the [approved product requirements](career-agent/PRODUCT_SPEC.md),
[implementation plan](career-agent/IMPLEMENTATION_PLAN.md), and
[current handoff](career-agent/HANDOFF.md) before changing Career functionality.
Day 2 requires explicit user approval.
