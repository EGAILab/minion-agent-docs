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
leaves no committed trace. Atomic means logically indivisible: no caller ever observes a half-written
event, and validation failure and commit are mutually exclusive outcomes of one append. It does not
by itself mandate a specific thread-safety mechanism; an implementation whose supported execution
model has no concurrent-caller hazard for this operation (for example, a single-threaded cooperative
scheduler where the operation never yields mid-append) satisfies this rule without additional
synchronization. An implementation whose supported execution model does admit concurrent callers
(for example, genuine OS threads) must still produce the same observable result -- unique, gapless,
commit-ordered sequence numbers, and no interleaved half-committed state -- by whatever mechanism its
language provides.

Session owns the log itself, the surface/log-only classification, and the three log-only kinds this
spec's own operations define (session/forked, session/reset, session/compaction) plus request/header.
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

Fork references source + boundary without copying. The boundary must be a committed point: `0 <=
boundary <= source's committed tip` at fork time. A boundary beyond the tip does not name committed
history yet, so accepting it cannot fix what the child sees -- a later source append that happens to
land at or before that not-yet-existing sequence would become visible in the child once appended,
violating "later writes to either side stay private to that side." Implementations reject a
future boundary rather than accept and silently leak it. Reset appends a reset marker in the same
session. Compaction supersedes an effective range with a summary plus retained-tail provenance and
must avoid double inclusion under repeated/overlapping/nested/fork-local cases.

In an execution model that admits concurrent Session mutation, a compaction's effective-surface and
retained-provenance snapshot plus its compaction-event commit form one linearizable operation
relative to append, reset, and other compaction operations. No append, reset, or compaction may
commit between a compaction's snapshot and its marker in that operation's observable serialization
order: events committed before that linearization point participate in the snapshot's derivation as
normal, and events committed after it do not alter the recorded compaction provenance. This does not
require every Session implementation to expose thread-safe simultaneous mutation -- an implementation
whose execution model serializes Session mutation for this operation (for example, a single-threaded
cooperative scheduler where compact's snapshot read and marker append never yield to another caller in
between) satisfies the requirement by construction, matching the append paragraph's own scoping above.
The requirement applies whenever concurrent mutation is admitted by that implementation.

Dispatch and reconstruction use the same canonical composition. Content-addressed artifacts are a
Minion storage divergence permitted only when model-visible bytes are equivalent.
