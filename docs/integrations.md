# Retired general integrations

Career Agent uses provider configuration through [Career Settings](career.md).
The general Waku integration walkthroughs and MCP example configuration are retired.
Git history preserves their instructions.

Batch C1 removes general tools, MCP, messaging, voice and conversational stores,
along with their feature tests and exclusive extras. Batch B2 removes bundled skills.
Batch C2 removes the integration/provider facade and its dashboard-only OTel
health probe. Optional OTel tracing remains in the shared tracer.
Career runs do not connect MCP servers or general gateways. Provider credentials,
model catalogs and endpoint behavior remain shared infrastructure.
