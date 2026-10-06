# Maintainers

Career Agent retains Waku's package name, upstream copyright and shared runtime.
Contributors follow [AGENTS.md](../../AGENTS.md); maintainers also verify builds
and installed startup before merging distribution changes.

## Review and merge

Review the requested change in an isolated worktree with a temporary runtime home.
Run deterministic checks, lint and environment validation. Interface changes also
need the scripted Chromium journey. Package changes need wheel/sdist builds and
isolated installation checks. Do not point evaluation at a real user's runtime.

The historical `skills-and-evals` job ID and `validate-skills.yml` filename remain
for branch-protection compatibility. They run Career and shared-runtime checks;
no bundled-skill validator remains. Merge through a reviewed PR with passing CI.
A review or implementation request does not authorize remote publication.

## Releases

`waku/__init__.py` owns the version. The release workflow compares it with the tag,
runs deterministic checks, builds distributions and validates their metadata.
An explicitly authorized version tag triggers PyPI Trusted Publishing and a
GitHub release. Verify the installed package version and Career assets afterward.
Do not handle publishing tokens or push release tags without authorization.

## Styling and licenses

Career owns independent system-font styling. Protected Waku design synchronization
is retired. Preserve MIT attribution and the Waku names notice; no marks, copied
design files or bundled fonts ship.
