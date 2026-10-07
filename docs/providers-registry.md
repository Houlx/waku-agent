# Provider registry

Career Agent resolves providers from `waku/providers.toml`. Each table specifies
wire format, credential variable, default model pair, catalog URL, key URL,
regional endpoints and compatible metadata. `waku/loop/models.py` builds frozen
provider adapters from these rows. Career Settings uses masked provider readiness
and explicit configuration transactions.

To add a compatible provider, add its table and run
`python scripts/generate_env_example.py --write`. Deterministic registry checks
validate required fields, wire formats, endpoint scoping, model defaults and
credential variables. No logo is required or distributed.

Catalog responses preserve free/tool/reasoning/context and price metadata when
supplied by the endpoint. Career retains saved pins and default-model reads for
compatibility. No spend aggregation or model-cutoff reporting remains.

The hidden `waku-platform` row retains scoped credentials, visibility, dynamic
catalog endpoints and model overrides for existing provider adapters. This fork
supplies no hosted deployment. Provider SDKs and `WAKU_*` names retain their
existing behavior. A new wire format requires an architecture proposal.

## Termination and stage-scoped tool choice

OpenAI-compatible responses expose `raw_stop_reason` from the original `finish_reason`,
including streaming completion. The normalized `stop_reason` is `tool_use` for tool
calls, `max_tokens` for length termination without calls, `end_turn` for known normal
stops, and `unknown` otherwise. Unknown raw values remain available. Native Anthropic responses already expose their
termination reason as `stop_reason`. Loop LLM events retain both fields; no assistant
prose or hidden reasoning is added to tracing. Generic response text remains unchanged.

Fresh Career extraction and full-evidence matching request the named `submit_stage_result` function through
OpenAI-compatible adapters and the native Anthropic tool-choice shape through Anthropic
SDK clients, including compatible endpoints. Inventory matching, resume generation
and ordinary loop calls do not force submission. Each wrapped stage releases the choice after
validation so final confirmation can finish normally.

A stage disables forcing after an explicit HTTP 400/422 rejection naming unsupported
or invalid tool choice, then retries without that option. Authentication, transport,
rate-limit and unrelated errors propagate. Third-party injected clients receive the
existing call signature. Each stage retains one corrective no-submit attempt even
when an endpoint silently ignores tool choice. A rejected capability request does not
consume a loop iteration, but its extra HTTP request is recorded as a submission event.

Endpoint/model support varies. The [OpenRouter tool-choice documentation](https://openrouter.ai/docs/guides/features/tool-calling#tool-choice-configuration)
shows named function choice. The [Anthropic tool definition documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)
describes forced choice and model/thinking restrictions. Runtime rejection handling
covers explicit unsupported choices without claiming universal model support.
