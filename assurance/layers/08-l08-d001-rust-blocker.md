# L08-D001 Rust implementation checkpoint: header integration gap

Status: BLOCKED; not review-ready, not certified.

Baselines: code `db63adcff1f3bc65edd7c8f03e5ae5b7ddb54eb9`, docs
`31847c606c78119d44d3dd7fd5133014293776ac`; Pi
`b7bb00b936dbe21b8e160b3e89efdec361846699`.

## L08D001-RUST-C001 — CONTRACT_ASSURANCE_DEFECT

The approved Optional prompt assembler contract requires request headers to
record the assembled system text, calling that mechanism unchanged. It also
requires the no-assembler path to retain exactly the certified behavior.

The Rust baseline does not invoke `Session::record_header` from the driver (or
any other production caller). A real `AgentLoop::prompt` with a registered
ScriptedAdapter and no assembler sends one request and records zero
`request/header` events. `l08d001_baseline_header_gap_characterization` executes
that observation. Its zero-header assertion characterizes the gap, not correct
behavior. The optional-assembler production patch does not change this path.

Consequently an implementation cannot both preserve the no-assembler baseline
and record the header required by the delta without deciding the scope of the
existing missing integration. Do not count vacuous no-header failure tests as
proof of correct header behavior.

Required shared-owner action: determine and record whether the existing Rust
request-header integration is authorized as an existing-contract correction in
this pass, or requires a separately coordinated correction. Clarify the
no-assembler regression boundary. No normative text has been changed here.

## Preserved partial work

The driver has a synchronous, fallible `PromptAssembler` collaborator over
`&[Arc<ToolDefinition>]`, default absent, override bypass including empty text,
and a distinct `PromptAssemblyError` that reaches normal failure settlement.
There are three passing focused tests: snapshot/order/base identity, override
bypass, and first-request failure settlement. The characterization also passes.
No new dependency, Python change, or shared semantic change was made.

Full regression gates, later-turn/replacement/growth/concurrency witnesses,
header reconstruction and discriminating source controls remain outstanding.
This checkpoint is explicitly not an implementation approval or certification.
