# Session Semantics

The log is append-only and sequence-numbered.

> Model-visible means logged.

Anything reaching a model request must be reconstructable from committed state.

Core surface events are user/message, assistant/message, and tool/result. Open event identity does
not imply model visibility; plugin events remain log-only unless explicitly projected. An event's
name is its identity, compared by value: a literal string and its language constant are the same
event, and every lookup that matches by kind (reset, compaction, surface membership) matches on the
string, never on object/enum identity.

Append is validation -> atomic seq allocation + append -> committed publication. Rejected validation
leaves no committed trace.

Session owns the log itself, the surface/log-only classification, and the three log-only kinds this
spec's own operations define (session/forked, session/reset, compaction) plus request/header.
Whatever else a producer appends as log-only data -- run/turn/step lifecycle markers, streaming
fidelity, tool-call bookkeeping -- Session stores and classifies uniformly by the same rule, without
asserting ownership of what that data means: the producing layer (for example the agent loop) owns
the semantics, naming, and timing of its own lifecycle vocabulary. Session's own obligation ends at
storing it validly and excluding it from surface projection. This is deliberate, not an omission: a
second implementation's Session layer must reproduce the surface/log-only split and the
value-identity rule exactly, but is not required to know what any particular log-only kind a caller
invents is for.

Session projection ends at the message vocabulary Layer 02 defines. The Pi-compatible target-model
transformation is a distinct, later stage that runs after session projection, not part of it.

Fork references source + boundary without copying. Reset appends a reset marker in the same session.
Compaction supersedes an effective range with a summary plus retained-tail provenance and must avoid
double inclusion under repeated/overlapping/nested/fork-local cases.

Dispatch and reconstruction use the same canonical composition. Content-addressed artifacts are a
Minion storage divergence permitted only when model-visible bytes are equivalent.
