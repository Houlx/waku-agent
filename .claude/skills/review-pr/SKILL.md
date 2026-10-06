---
name: review-pr
description: Review a requested Career Agent pull request or issue with concrete behavior, verification evidence and a merge or revision recommendation.
---

Inspect the requested revision in an isolated worktree using the `pr-worktree`
skill. Read `AGENTS.md` and current product status before assessing the change.
Check actual Career/provider/runtime consumers rather than restoring retired
implementations to satisfy stale assumptions.

Explain the concrete problem, changed behavior, useful verification commands and
one recommendation. Distinguish checks you ran from checks the reviewer still
needs to run. Include a browser preview for interface changes, using a temporary
runtime home and a second port. Synthetic Chromium checks do not establish live
model quality.

Preserve Career grounding, provenance, schema/FTS5 and user-data boundaries.
Check distribution members and notices for asset or packaging changes. Report
unrelated dependency updates and gaps in validation.

A review request authorizes inspection and testing. It does not authorize merging,
publishing, sending messages or running paid evaluation. Follow the user's
existing authorization when deciding the next action.
