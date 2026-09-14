# Auth Semantics (Layer 11 Pass 1 -- Auth Foundation; Pass 2 Slice A -- Codex account-id
projection)

This document covers the provider-neutral authentication seam: stored credentials, the
credential-store concurrency contract, refresh/ownership authority, the two generic OAuth
primitives (PKCE, RFC 8628 device-code polling) Pass 1 builds, and Codex's own pure (non-network)
account-id projection (`PROV-011`, Pass 2 Slice A, adopted -- below). It does NOT cover any real
provider's own wire-protocol request/response encoding, Codex's own OAuth NETWORK integration
(browser/device-code endpoints, token exchange, the local callback server, `PROV-012`), or the
generic `AuthPrompt`/`AuthEvent`/`AuthInteraction`/`OAuthAuth`/`ApiKeyAuth`/`ProviderAuth`
interaction vocabulary those slices consume -- currently still attributed, together with the
`Models`-level orchestration built on top of it, to the single bundled `PROV-013` row (see
"Deferred generic auth/provider orchestration surface" below); splitting the interaction
vocabulary out into its own row is a separately-reviewed Slice B contract, not yet performed.

```text
ApiKeyCredential{type=api_key,key?,env?}
OAuthCredential{type=oauth,access,refresh,expires,extra?}
Credential = ApiKeyCredential|OAuthCredential

CredentialInfo{provider_id,type}
AuthOperationOptions{signal?}

ModelAuth{api_key?,headers?,base_url?}
AuthResult{auth:ModelAuth,env?,source?}
AuthCheck{type,source?}
```

`expires` is a Unix-epoch-MILLISECONDS timestamp, not a duration and not seconds. `env`'s own
domain is pinned Pi's own `ProviderEnv = Record<string, string>` (`types.ts:113`) -- a FLAT
string-to-string mapping, never recursive JSON (`L11-R010`). `extra` is a SEPARATE, OPEN escape
hatch (mirroring Pi's own `OAuthCredentials`'s `[key: string]: unknown` index signature), not a
closed field set and NOT limited to flat strings: a provider-specific login flow attaches fields
of ANY JSON shape alongside the three required ones (e.g. Codex's own `accountId`, `PROV-011`,
adopted -- see "Codex account-id projection" below) without widening the core shape every other
provider shares. `env` and `extra` are
therefore two DIFFERENT domains, not the same rule applied to two fields -- evidence for one must
never be constructed using the other's own domain. `CredentialInfo` never carries a secret field
(`key`, `access`, `refresh`, or `extra`) -- it exists only for account/status enumeration.
`ModelAuth` is closed to exactly `api_key`/`headers`/`base_url`: a value that cannot be expressed
as one of those three is provider CONFIG, not auth, and does not belong on this type. `source` on
`AuthResult`/`AuthCheck` is a human-readable status-UI label, not a machine-discriminated enum.

**Credential value/reference semantics (`L11-R006`/`L11-R009`, resolved by explicit owner
governance decision under `agent-workflow.md` §11.7/§11.8 -- NO intentional divergence approved).**
Pi stores plain, mutable credential objects with no freezing or defensive copying anywhere, at ANY
field, and `read`/`modify` expose direct references into the SAME backing store. This project
adopts that exact observable behavior IN FULL, not only for `env`/`extra`:

- A credential's SCALAR fields (`key`; `access`, `refresh`, `expires`) are directly reassignable,
  and a later access -- including through `CredentialStore.read()` -- observes the reassignment.
- Mutating the ORIGINAL mapping/list passed to a constructor for `env`/`extra` remains observable
  through the credential afterward.
- Assigning a BRAND-NEW top-level key directly on `credential.env`/`credential.extra` itself
  succeeds and is observed by a later access, matching a plain Pi object field assignment.
- For `extra` specifically (never `env`, per its own flat domain above): mutating a NESTED dict/
  list value reached through `credential.extra` itself persists and is observed by a later access,
  recursively, not only at the outer mapping.

Two prior candidate revisions instead attempted an intentional deep-immutable-value divergence
without the required owner approval, implemented it only shallowly (outer-mapping protection with
nested values still aliased), and left the credential dataclasses themselves non-reassignable at
the scalar-field level even after adopting the owner's Pi-parity decision for `env`/`extra` -- all
three gaps are corrected by this fully-adopted, owner-decided resolution.

`CredentialStore.modify()` remains the documented, INTENDED sole mutation authority (`PROV-007`) --
this aliasing behavior does not weaken or reinterpret that guarantee. A caller that instead mutates
a retained credential reference directly, bypassing `modify()`, can do so -- exactly as Pi's own
plain-object credential type permits, including Pi's own documented bypassability. This is an
accepted characteristic of the adopted design, not a new gap introduced by matching Pi.

## AuthContext

The environment-access seam for auth resolution (`PROV-006`), injectable for tests:

```text
AuthContext.env(name) -> string|absent
AuthContext.file_exists(path) -> bool
```

`env(name)` returns the named environment value, or absent if the variable is genuinely unset.
This protocol-level contract permits ANY implementation to resolve a present-but-blank value
(e.g. an empty string) unchanged -- blank-to-absent normalization is NOT part of the protocol
itself (`L11-R003`). Only the DEFAULT reference implementation additionally treats a
whitespace-only value as absent; that normalization is a property of the default implementation,
not a requirement every conforming `AuthContext` must satisfy.

`file_exists(path)` reports whether `path` exists, expanding a leading `~` to the user's home
directory. UNLIKE `env`'s own blank-normalization, leading-`~` support IS part of the PROTOCOL
contract itself (`L11-R008`; Pi's own interface places this exact behavior directly on the
`fileExists` method's own doc comment, distinct from `env`, which carries no interface-level
comment about blank values at all) -- every conforming `AuthContext` implementation, not only the
default one, must interpret a leading `~` as the user's home directory rather than a literal
relative path segment. Pi's own interface comment also states `fileExists` is "always false in
browsers"; this project has no browser runtime target, so that clause is architecturally
inapplicable here rather than weakened or silently dropped.

**The default reference implementation's own exact `file_exists` behavior (`L11-R013`).** Two
properties, both specific to the default implementation (not a protocol-level requirement, unlike
the general leading-`~` rule above, which any implementation must satisfy in SOME form):

1. Tilde expansion is LITERAL STRING CONCATENATION -- Pi's own `homedir() + path.slice(1)` -- not
   path-join, and not a `~username` other-user lookup. Only the leading `~` character itself is
   replaced; everything after it is appended UNCHANGED, with no separator inserted. `~/foo`
   therefore resolves as expected (the home directory typically has no trailing slash, so
   concatenating `/foo` directly reads naturally), but a non-separator suffix like `~foo` resolves
   to `<homedir>foo` (home directory string with `foo` appended directly, not `<homedir>/foo` and
   not another user's own home directory) -- a deliberately naive rule, not full path-normalization
   or username-lookup semantics.
2. The WHOLE operation -- INCLUDING home-directory resolution itself (rule 1 above), not only the
   filesystem check that follows it -- is one failure boundary that resolves `False` on ANY error,
   filtered to no particular exception type (Pi's own bare `try { ... } catch { return false; }`),
   not only "the target does not exist." A failure resolving the home directory, a permission
   error, or any other filesystem failure all report `False`, identically to a genuinely missing
   path -- none of them ever propagates an exception to the caller. `L11-R013` (remediated twice):
   a first remediation wrapped only the filesystem check in `try`/`except`, leaving home-directory
   resolution OUTSIDE that boundary, and narrowed the caught exception type -- both are contrary to
   this rule, which this sentence now states explicitly enough to prevent that exact recurrence.

The default, reference implementation reads real process environment variables and the real
filesystem, but reads NO provider-specific credential file (a Codex CLI credential file, or any
other single filesystem source) as part of this generic seam -- that would bake one provider's own
storage location into the generic auth API, which this contract deliberately avoids.

## CredentialStore (`PROV-007`)

One serialized read-modify-write path per provider id:

```text
CredentialStore.read(provider_id, options?) -> Credential|absent
CredentialStore.list(options?) -> [CredentialInfo]
CredentialStore.modify(provider_id, fn, options?) -> Credential|absent
CredentialStore.delete(provider_id, options?) -> void
```

`read` resolves absent for a missing entry -- it never raises for "not found." `modify` is the
ONLY write path: `fn` sees the CURRENT credential (or absent) and returns either the new
credential to store, or absent to leave the entry UNCHANGED -- this is NOT the same operation as
deletion; `delete` is the separate, dedicated removal primitive. Every `modify`/`delete` call is
serialized per `provider_id`: two concurrent calls for the SAME provider id never run their own
`fn` concurrently, and the second call's own `fn` observes whatever the first call's own `fn`
committed (or, if the first call's own `fn` raised, the value from before that failed attempt --
a raising `fn` leaves the stored credential untouched, and its own exception propagates to the
caller unchanged). `modify` returns the post-write credential: the new one if `fn` returned one,
otherwise whatever was already stored. `read`/`list` are explicitly NOT serialized against
`modify`/`delete` -- a `read` racing an in-flight `modify` observes whatever is currently stored
at the moment it runs, from either side of the mutation.

`list()` enumerates providers in INSERTION order of each provider's own CURRENT entry (`L11-R007`)
-- a provider deleted and later given a fresh credential re-appears at the END of that order, not
its original position. This is a normative production-API rule, not merely an incidental property
of one language's map/dict type: an implementation using a hash-based collection with no stable
iteration order does not satisfy this contract on its own and must track insertion order
separately.

This is the property the whole contract exists to guarantee: a caller that needs to refresh a
rotating OAuth token can run its own check-and-refresh sequence entirely inside one `modify()`
callback and be certain no second concurrent caller for the SAME provider id can read the same
stale value and independently commit its own refresh too (see "Refresh authority" below). A bare
`read`/write pair with no `modify` primitive cannot make this guarantee at all.

An in-memory reference implementation proves IN-PROCESS serialization ONLY -- it makes no claim of
cross-process, filesystem, or distributed locking. A concrete backing store MAY provide those
stronger guarantees, but the generic `CredentialStore` contract does not require them, and nothing
in this document should be read as promising more than what the in-memory reference actually
proves. Per-provider ordering is a FIFO chain: a `modify`/`delete` call queued behind an earlier
one for the same provider id does not begin until the earlier one has settled (successfully or by
raising), and one call's own failure never blocks a later queued call from proceeding.

**Cancellation (`AuthOperationOptions.signal`, `L11-R001`).** `read`/`list` check the signal once,
immediately, before doing anything else. `modify`/`delete` check it at up to three distinct
points, and this contract requires all three, not merely the union's overall effect:

1. Immediately, if the signal is already aborted before a queued call even begins waiting.
2. Once a queued call's own turn begins -- i.e. once every EARLIER call for the same provider id
   has itself settled -- and BEFORE its own `fn`/removal runs at all. An abort observed here means
   `fn` (for `modify`) or the removal (for `delete`) never runs.
3. For `modify` only, again immediately after `fn` resolves but before its result would commit:
   an abort observed here means `fn`'s own result is DISCARDED, never written to the store, even
   though `fn` itself ran to completion.

Independently of all three checkpoints above, the CALLER'S OWN WAIT for a `modify`/`delete` call
races against the signal separately: an abort observed while the caller is still waiting -- even
while `fn` is already running past checkpoint 2 -- makes the caller's own call raise a cancellation
error PROMPTLY, without waiting for the underlying operation to finish. This does NOT stop the
underlying operation itself; it keeps running in the background to its own natural conclusion
(settling checkpoint 3 above on its own timetable). A caller that races away a `modify` call this
way must not assume the credential was left unchanged merely because it saw a cancellation -- it
was, in fact, left unchanged (checkpoint 3 discards a too-late result), but that is a consequence
of checkpoint 3, not of the caller's own race having "stopped" anything.

## Refresh / ownership authority (`PROV-008`)

A stored credential OWNS the provider: this contract grants Minion authority to refresh/mutate an
OAuth credential only through the credential store's own serialized `modify()` -- never by
independently reading a token from some other source (a filesystem, a CLI's own credential file)
and rewriting it outside this seam. There is no silent fallback to an ambient/external credential
source after a failed refresh, or for a credential type without a matching handler.

A refresh triggers when the stored OAuth credential is within an EFFECTIVE trigger window of
expiring: `max(default_five_minutes, explicit_caller_minimum_or_zero)`. This SAME effective
threshold -- never the raw, un-maxed caller value alone -- governs THREE separate checks, not just
the first: the initial (optimistic, outside-the-lock) trigger decision, the re-check performed
under the store's per-provider lock before actually calling the injected refresh operation, and
(when the caller supplied an explicit minimum) the POST-refresh validation of the newly-refreshed
credential (`L11-R011`; an earlier revision incorrectly post-validated against the raw, un-maxed
caller value, which could accept a refreshed credential still expiring within the DEFAULT window
whenever the caller's own explicit minimum was smaller than that default). There is only ever ONE
threshold value in play for a given call, reused identically across all three checks.

The actual refresh call happens INSIDE `modify()`'s own callback, which re-checks expiry under the
store's per-provider lock (against that same effective threshold) before calling the injected
refresh operation -- this double-checked pattern is what makes two concurrent callers that both
observed "expiring soon" via an outside-the-lock optimistic read refresh EXACTLY ONCE: the second
caller's own callback, running after the first's has already committed, observes the now-current
(no-longer-expiring) credential and returns it unchanged, without calling refresh again. If the
credential has been logged out (or replaced by a non-OAuth credential) by the time the lock is
acquired, the callback returns absent rather than attempting to refresh something that no longer
exists.

Two distinct failure classes are never conflated: the injected refresh operation itself failing
(the provider rejected the refresh) is a different, distinguishable error from the credential
store's own read/modify mechanism failing (a local storage problem) -- a caller can tell "the
provider rejected the refresh" apart from "the local credential store is broken."

**An explicit `NaN` caller-supplied minimum suppresses refresh entirely (`L11-R015`).** Combining
the caller's own explicit minimum with the five-minute default (the `max` this section already
describes) must match Pi's own special-number semantics, not an ordinary numeric implementation's
incidental behavior: if EITHER operand is `NaN`, the combined result is `NaN` too (Pi's own
`Math.max`'s documented rule -- an ordinary two-argument comparison-based `max`, by contrast,
silently discards a `NaN` operand and returns the OTHER value instead, which is the wrong answer
here). A `NaN` effective threshold then makes every subsequent expiry comparison resolve to
`False` (a comparison against `NaN` is always `False`, in every language this contract targets) --
so a stored credential is returned UNCHANGED, with no refresh attempted at all, regardless of how
close to its own real expiry it is. An implementation whose combined-threshold arithmetic instead
silently falls back to the five-minute default for a `NaN` explicit minimum incorrectly grants
refresh authority Pi itself withholds for this exact input.

**Refresh cancellation/timeout (`L11-R002`).** The refresh operation itself receives a live,
abort-observable signal as a second argument, alongside the expiring credential -- it is not
called with the credential alone. That signal aborts when EITHER the caller's own cancellation
fires OR a fixed budget (15 seconds) elapses on its own, independent of whether the caller ever
cancels anything at all. This composed signal exists specifically so a hung refresh call cannot
hold this credential's own store lock forever; the refresh operation is expected to honor it
cooperatively (poll it and stop), the same cooperative contract every other abort-aware operation
in this seam follows -- this module does not forcibly interrupt a refresh call that ignores it.

## PKCE (`PROV-009`)

Generic RFC 7636 code-verifier/challenge generation, with no real OAuth request performed by this
contract:

```text
PkcePair{verifier,challenge}
```

The verifier is 32 bytes of entropy, base64url-encoded without padding -- exactly RFC 7636 section
4.1's own MINIMUM allowed verifier length (43 characters) once encoded, not an arbitrary choice.
The challenge is `BASE64URL(SHA256(verifier))`, deterministic given the same verifier (the same
verifier always derives the same challenge; different verifiers derive different challenges).
Verifier generation itself is non-deterministic (fresh entropy per call); challenge DERIVATION
from a known verifier is deterministic and independently testable against RFC 7636 Appendix B's
own published worked vector.

## Device-code polling (`PROV-010`)

A provider-neutral RFC 8628 device-authorization poll state machine. The only transport seam is a
caller-supplied `poll` operation, invoked once per attempt, reporting exactly one of:

```text
DevicePollPending
DevicePollSlowDown{interval_seconds?}
DevicePollFailed{message}
DevicePollComplete{value}
```

`poll` reports ONLY what one attempt found -- it never decides to retry, never sleeps, never
checks a deadline; every interval/backoff/deadline/cancellation decision belongs to the poll loop
itself, not to `poll`. This separation is what makes the poll loop's own state machine a genuine,
independently specifiable contract rather than something each transport implementation would
otherwise have to reimplement itself.

State transitions:

- **Pending**: retry at the current interval.
- **SlowDown**: increase the interval before the next attempt. If the server supplies an explicit
  interval that is FINITE and positive, that value governs outright (preferred over a fixed
  increment, since trusting only a client-tracked increment risks polling too early forever under
  clock drift). A non-finite value (e.g. positive infinity) is treated exactly like an absent one
  (`L11-R004`) -- it must never be scheduled as an actual sleep duration. If the server supplies no
  interval, or a non-finite/non-positive one, the current interval increases by a fixed 5 seconds
  (RFC 8628 section 3.5's own default increment).
- **Failed**: a terminal protocol error. Polling stops immediately on this attempt -- it is never
  retried.
- **Complete**: the flow succeeded; the loop returns `poll`'s own value unchanged.

The default interval, when the caller supplies none, is 5 seconds (RFC 8628 section 3.2's own
default). Every interval is floored at a minimum of 1 second, regardless of what the caller or a
`slow_down` response requests.

**Millisecond flooring (`L11-R012`).** Before the 1-second minimum is applied, BOTH the caller's
own initial interval and a finite/positive server-provided `slow_down` interval are first FLOORED
to whole milliseconds (Pi's own `Math.floor(seconds * 1000)`) -- a fractional-second interval
(e.g. `1.2349` seconds) schedules exactly `1.234` seconds, never the raw fractional value. This is
a normative scheduling rule, not merely a floating-point-representation detail: two implementations
that both satisfy every other rule in this section can still schedule observably different wait
durations for a fractional interval unless both apply this exact floor. The fixed `slow_down`
fallback increment (5 seconds) is already a whole-millisecond quantity and needs no additional
flooring when added to an already-floored current interval.

**Non-finite initial intervals must not fail setup (`L11-R014`).** UNLIKE the server-provided
`slow_down` interval (which the finite/positive guard above explicitly gates), the CALLER's own
initial interval carries NO such guard in Pi -- an `Infinity` or `NaN` initial interval is
accepted at setup and never causes an error on its own. If the very first poll attempt reports
`DevicePollComplete`, the loop returns that value immediately, without ever computing or
attempting to schedule a sleep at all -- so a non-finite initial interval that is never actually
used to sleep must never prevent that immediate success from being returned. An implementation
whose own flooring/clamping arithmetic raises for non-finite input at setup time, before any poll
has even run, narrows this contract incorrectly; flooring for a non-finite value must be a
no-op/pass-through, not an error.

**Two separate boundaries, two different rules (`L11-R017`, `L11-R018`).** Pi exposes TWO
independently-observable seams that a non-finite (or otherwise out-of-range) interval can reach,
and they do NOT apply the same clamp:

1. **The poll loop's own upstream normalization.** Before scheduling any sleep,
   `pollOAuthDeviceCodeFlow` itself computes `Math.max(MINIMUM_INTERVAL_MS, Math.floor(...))` on
   the interval it is about to use. This is ORDINARY arithmetic, not a validity check -- it
   resolves correctly, with no special-casing, for every value except `NaN` (which fails every
   comparison and so is not resolved by `Math.max` at all; see the paragraph below). A value that
   has already passed through this normalization is, by construction, an ordinary valid delay by
   the time it could ever reach the second boundary.
2. **The exported `abortableSleep` function itself.** Called directly -- which the poll loop does,
   but which any other caller may also do, bypassing step 1's normalization entirely -- it performs
   NO normalization of its own and hands its `ms` argument straight to `setTimeout`. Node's own
   `setTimeout` then applies its own documented delay-bounds contract, independent of anything the
   poll loop does.

**`NaN`, the ONLY value the poll loop's own normalization cannot resolve, must still make progress,
at Pi's own magnitude (`L11-R014`, resolved by §11.8 convergence agreement, revision 2).** If the
first poll attempt does NOT report `DevicePollComplete`, the interval is actually consulted to
schedule a sleep before the next attempt. `NaN` fails every comparison `Math.max` would otherwise
use to resolve it, so it survives that computation unchanged and reaches `setTimeout` as an
out-of-range delay -- clamped, per that host's own documented contract, to exactly ONE
MILLISECOND, independently confirmed live against a real Node process during review. (Positive AND
negative `Infinity` both need no special-casing at this boundary at all: `Math.max` already
resolves both correctly via ordinary comparison, see the two paragraphs below -- this paragraph's
subject is `NaN` alone, not "every non-finite value.")

A revision 1 of this rule adopted the project's own PRE-EXISTING one-second minimum-interval floor
(the SAME constant every too-small but otherwise ordinary finite interval already clamps to) as the
fallback for this case too -- three orders of magnitude larger than Pi's own real value, and an
UNAPPROVED observable departure from Pi once examined closely: it is not "good enough progress,"
it is a materially different, undisclosed-as-such replacement value, while `PROV-010` continued to
claim `adopted` (Pi-parity) disposition. The corrected rule: `NaN`, when actually used to schedule
a sleep by the poll loop, clamps to Pi's own real magnitude -- one millisecond -- using a DEDICATED
constant distinct from the ordinary minimum-interval floor (the two concepts are unrelated: one is
RFC 8628's own "never poll faster than this" rule for ordinary finite intervals; the other is a
fallback for a value that cannot be scheduled at all). The EXACT sub-millisecond precision Pi's own
host runtime would produce is still not made normative (Python's own scheduler cannot guarantee it
either) -- only the MAGNITUDE (roughly one millisecond, not roughly one second) is adopted as the
portable, cross-language observable rule.

**Negative `Infinity`, reached through the poll loop's own normalization, is a DIFFERENT case from
`NaN` (`L11-R016`).** Pi's own pure arithmetic (`Math.max(MINIMUM_INTERVAL_MS, Math.floor(-Infinity
* 1000))`) resolves this case ORDINARILY, to the plain one-second RFC-8628 floor -- negative
`Infinity` is a valid, comparable number that simply LOSES every `Math.max` comparison against a
finite value, so it NEVER reaches `setTimeout` as an "invalid delay" the way `NaN` does when routed
through this SAME boundary. An implementation that treats every non-finite value identically at
THIS boundary (routing negative `Infinity` through the SAME one-millisecond clamp `NaN` takes)
diverges from Pi in the OPPOSITE direction this section's own earlier revision did: Pi actually
waits the FULL one-second floor for this specific input at this boundary, not one millisecond. The
observable rule, scoped to the poll loop's own normalization: negative `Infinity`, when actually
used to schedule a sleep THROUGH THE POLL LOOP, resolves to the SAME ordinary one-second
minimum-interval floor every other too-small-but-ordinary value resolves to -- only `NaN`, at this
boundary, takes the separate, one-millisecond clamp path above.

**The exported `abortableSleep`/`abortable_sleep` seam applies Node's FULL `setTimeout` bounds
check, uniformly, to every invalid value including negative `Infinity` (`L11-R017`).** This is a
SEPARATE boundary from the poll loop's own normalization above, and reaches a DIFFERENT answer for
negative `Infinity` specifically: called directly -- bypassing the poll loop's own `Math.max`
normalization entirely, which a caller of the exported function is free to do -- a raw negative
`Infinity` (or `NaN`, positive `Infinity`, zero, any other negative number, or any positive
sub-millisecond number) reaches `setTimeout` as an out-of-range delay and is clamped, per Node's own
documented contract ("If delay is larger than 2147483647 or less than 1, the delay will be set to
1"), to exactly ONE MILLISECOND -- the SAME magnitude `NaN` receives when it reaches this boundary,
regardless of sign. An implementation of the exported function that excludes negative `Infinity`
from this clamp (treating it as if it were an ordinary, schedulable delay, or performing zero
sleep at all) diverges from Pi: Pi's own exported `abortableSleep` has no such exclusion, because it
has no normalization step of its own to begin with. The poll loop's own call into this function
never actually exercises this case for negative `Infinity` in practice, since the poll loop's own
upstream normalization (above) has already turned it into an ordinary, valid delay by the time this
function is called -- but the function itself, callable independently, must still honor Node's full
bounds check on whatever raw value it is given.

**A VALID delay is still truncated to a whole millisecond before scheduling (`L11-R019`).** Node's
real `setTimeout` does not schedule an accepted delay (one already inside `[1, 2147483647]`
milliseconds, i.e. one the rule above does not touch at all) at its own exact fractional value --
it internally truncates ANY accepted delay to a whole integer millisecond count first. This is a
THIRD rule, independent of both the poll loop's own explicit millisecond flooring (the first
rule in this section) and the invalid-delay clamp immediately above: it governs an already-VALID
delay at the exported `abortableSleep`/`abortable_sleep` seam specifically. A delay of `1.9`
milliseconds, passed directly to `abortableSleep`, is neither invalid nor out of range -- it
schedules at exactly `1` millisecond, not `1.9`. A poll-loop-sourced delay is already
whole-millisecond by construction (the poll loop's own explicit flooring already produced it, per
the first rule above), so this rule is a no-op for that path in practice; it is observable only
through a direct call to the exported function with a raw fractional-millisecond delay.

**Expiry.** A caller may supply a deadline (elapsed seconds from the loop's own start); absent one,
the loop never expires on its own. Reaching the deadline with no successful poll raises a timeout.
The timeout carries one of two distinct messages: a plain timeout message if no `slow_down`
response was ever observed during this run, or a more specific, actionable message (naming clock
drift as a likely cause) if at least one `slow_down` response was seen first -- a slow_down-then-
expire pattern is a specific, diagnosable symptom, not a generic timeout, and the two cases must
remain distinguishable to a caller/operator.

**Abort.** A caller may supply a cancellation signal. The loop observes it before the very first
poll attempt (raising immediately if already aborted) and again at each interval's own sleep-step
boundaries between attempts -- it never races an in-flight `poll()` call itself: an abort signaled
while `poll()` is already running is only observed at the NEXT loop-top check, once that one
attempt has itself returned. A poll-based cancellation signal (one with only an `aborted` property,
no push/event mechanism) is checked "promptly enough" for this contract by slicing a long
inter-attempt sleep into short polling steps and checking the signal between them -- a disclosed
difference from an instant-interrupt signal's own behavior, immaterial to this contract's own
success/failure/timeout observable outcomes.

## Pass-1 network exclusions

Explicitly out of scope for this pass, characterized nowhere as implemented: real requests to any
OAuth authorization/token endpoint, real token exchange, a local OAuth callback HTTP server,
browser launching or interactive browser login, live device-code HTTP calls against a real
provider endpoint, a Codex CLI credential-file loader, and any real provider transport. `PROV-009`/
`PROV-010` above are the generic, provider-neutral primitives a future pass's real OAuth
integration will consume as its own transport-injected seam -- this pass does not itself perform
any provider's specific endpoint calls.

## Deferred generic auth/provider orchestration surface (`PROV-013`)

Pinned Pi's public auth vocabulary extends well beyond what Pass 1 builds: `AuthPrompt`,
`AuthInfoLink`, `AuthEvent`, `AuthInteraction`, `ProviderAuthInteraction` (the login-interaction/
prompt/notification vocabulary a provider's own login flow uses), `ApiKeyAuth`, `OAuthAuth`,
`ProviderAuth` (the per-provider auth-METHOD vocabulary -- `login`/`resolve`/`check`/`refresh`/
`toAuth` callables a concrete provider registers), and the `Models` collection's own orchestration
entry points (`checkAuth`, `getAuth`, `login`, `logout`) built on top of `resolveProviderAuth`
(`L11-R005`).

This is EXPLICITLY NOT a demand to implement any of this in Pass 1 -- interactive login flows,
provider-method registration, and top-level auth orchestration are real provider-integration
concerns with no generic-seam content of their own until a concrete provider exists to exercise
them. It IS a demand not to silently lose track of this discovered Pi surface: without an explicit
disposition, two independent future implementers could reasonably make incompatible choices (one
building the vocabulary extensible for login interactions now, one omitting it entirely), each
individually consistent with Pass 1's own artifacts but incompatible with each other.

Closure criterion (binding on whichever future pass closes this row): a future Layer-11 pass
integrating a real provider's own login flow (Codex OAuth network integration, slice 11B, or a
later provider) must audit this exact Pi vocabulary and either adopt it directly or document a
deliberate, disclosed divergence -- it must not invent an unrelated ad hoc login/prompt shape
without first comparing it against Pi's own `AuthPrompt`/`AuthEvent`/`AuthInteraction` vocabulary.

## Codex account-id projection (`PROV-011`, Pass 2 Slice A, adopted)

Pinned Pi's Codex OAuth flow's pure (non-network) half -- JWT decode for `chatgpt_account_id` and
the resulting bearer `ModelAuth` projection. This is provider-specific behavior, not a generic
primitive, but it is fully self-contained and independently observable without any real network
call, so it is adopted directly rather than deferred alongside `PROV-012`'s own network
integration below.

```text
decode_jwt(token) -> JsonValue        # whatever json.loads produces; NOT necessarily an object
get_account_id(access_token) -> string|absent
credentials_from_token(access, refresh, expires) -> OAuthCredential   # raises if no account id
to_auth(credential) -> ModelAuth      # {api_key: credential.access}
```

`decode_jwt` is UNVERIFIED claim extraction only -- it decodes the JWT's own payload segment, and
never performs cryptographic signature validation. No signature verification may be added where
Pi performs only unverified decoding; treating an unverified claim as authenticated identity would
be a false strengthening of this contract, not a hardening of it.

`decode_jwt` reproduces two Pi/JS-specific decode quirks EXACTLY, not approximately:

1. The payload segment is decoded as STANDARD base64 only -- a base64url alphabet character
   (`-`/`_`) makes the whole token fail to decode (returns absent), while a MISSING padding
   character does not. An implementation that is lenient about `-`/`_` (e.g. silently discarding
   them rather than rejecting the token) diverges observably from Pi's own `atob`, which throws
   for exactly this input.
2. The decoded payload bytes are interpreted as LATIN-1, never UTF-8. A JWT claim VALUE containing
   a non-ASCII character (encoded as UTF-8 bytes before base64, the universal way JWTs are built)
   therefore decodes to MOJIBAKE, not the original character. This is the correct, Pi-faithful
   observable behavior for this unverified-decode path, not a defect to silently repair by
   decoding as UTF-8 instead -- doing so would itself be an unapproved observable divergence from
   Pi. `decode_jwt` itself does not validate that the decoded/parsed payload is an object; a
   non-object result (array, string, number, or the JSON literal `null`) is tolerated by
   `get_account_id`'s own graceful lookup, not rejected earlier -- a payload segment that decodes
   to the JSON literal `null` is therefore indistinguishable from a malformed token, matching Pi's
   own `JSON.parse("null") === null` ambiguity.

`get_account_id` returns the `chatgpt_account_id` claim under the `"https://api.openai.com/auth"`
namespace, or absent if the token is malformed, the decoded payload (or that namespace) is not an
object, or the claim itself is not a non-empty string.

`credentials_from_token` raises if no usable account id can be extracted, matching Pi's own
`throw new Error("Failed to extract accountId from token")` -- this is not a recoverable, in-band
outcome.

**Minion-specific mapping, not direct Pi parity.** Pinned Pi's own `OAuthCredential` type carries
`accountId` as a literal top-level field. This project's own `OAuthCredential` (above) instead
keeps it under the OPEN `extra` escape hatch (`extra["account_id"]`), rather than widening the
shared credential shape every other provider's own OAuth flow also uses, for one Codex-specific
field. This is a disclosed architectural mapping, not a claimed direct-parity field placement.

## Deferred Codex network integration (`PROV-012`)

Pinned Pi's Codex OAuth NETWORK behavior remains deferred to a later Pass-2 slice:

- Browser callback state validation, including a documented exception: a user pasting a bare
  authorization code (rather than a full callback URL) is a recognized quirk Pi's own flow
  accommodates, not an error condition.
- The browser/PKCE callback flow (local OAuth callback HTTP server, authorization-URL construction
  and the `auth_url` notification event -- browser LAUNCHING itself remains out of scope; this
  layer only emits the notification, matching Pi exactly) and device-code Codex endpoint
  integration (consuming the already-certified `PROV-010` poller), plus token exchange/refresh
  against `auth.openai.com` (consuming the already-certified `PROV-008` refresh authority).

This is recorded as `deferred parity` in `pi-parity-manifest.yaml`, with its own closure criterion,
not as `adopted` and not silently omitted. The pass implementing it must audit pinned Pi source for
each of these before writing any code, must use only synthetic (never real-account) fixtures for
any JWT-shaped test data, and must not perform any live network call or use any real secret in the
committed test suite, per this project's own security constraint.
