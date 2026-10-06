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
