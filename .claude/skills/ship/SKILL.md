---
name: ship
description: Prepare and publish Career Agent changes when the user explicitly requests a commit, push or pull request, following the authorized publication scope.
---

Run lint, the offline deterministic release gate and environment validation before
publishing. Run Chromium for interface changes and isolated wheel/sdist startup
checks for packaging changes. Live evaluation requires separate authorization;
the release gate never runs a paid judge.

Inspect status and diffs for unintended changes, runtime data and credentials.
Write a concrete commit subject and explain changed behavior and verification.
Use a branch and reviewed PR rather than pushing directly to protected main.
The historical `skills-and-evals` CI identifier remains compatible.

Perform only the publication actions the user authorized. A commit request does
not authorize merging or releasing. Do not push version tags or merge a PR merely
because local checks pass. Follow `docs/context/maintainers.md` for release behavior.
