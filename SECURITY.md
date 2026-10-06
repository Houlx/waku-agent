# Security

Career Agent runs locally with your provider credentials, profile and saved jobs.
The HTTP server binds to localhost by default and provides no authentication.

## Report a vulnerability

Use upstream [private vulnerability reporting](https://github.com/ShenSeanChen/waku-agent/security/advisories/new)
for retained Waku code. Do not disclose credentials or personal artifacts in a
public issue. Identify the affected Career fork and revision in the report.

## Security boundaries

Career sends stage inputs to the provider you configure. Keys remain on the server;
provider readiness exposes masked status. Explicit provider settings and catalog
requests may contact that provider. Career treats profile, JD and evidence text as
untrusted data and validates submitted results and resume citations.

The static/API allowlist, request limits, credential scoping, provider rollback,
SQL/path confinement and grounding checks have deterministic regressions.
Traces contain factual tool inputs/results; keep runtime homes and dotenv files
out of source control. Existing legacy data remains user-owned.

General gateways, calendar tools, experimental delegation and bundled skills are
retired. Career never loads them. Review generated claims and translations before
using a resume.
