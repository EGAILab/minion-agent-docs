# Session Semantics

The log is append-only and sequence-numbered.

> Model-visible means logged.

Anything reaching a model request must be reconstructable from committed state.

Core surface events are user/message, assistant/message, and tool/result. Open event identity does
not imply model visibility; plugin events remain log-only unless explicitly projected.

Append is validation -> atomic seq allocation + append -> committed publication. Rejected validation
leaves no committed trace.

Fork references source + boundary without copying. Reset appends a reset marker in the same session.
Compaction supersedes an effective range with a summary plus retained-tail provenance and must avoid
double inclusion under repeated/overlapping/nested/fork-local cases.

Dispatch and reconstruction use the same canonical composition. Content-addressed artifacts are a
Minion storage divergence permitted only when model-visible bytes are equivalent.
