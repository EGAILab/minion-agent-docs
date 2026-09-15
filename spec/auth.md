# Auth Semantics (Layer 11 Pass 1 -- Auth Foundation; Pass 2 Slice A -- Codex account-id
projection; Pass 2 Slice B -- provider-auth interaction/auth-method vocabulary)

This document covers the provider-neutral authentication seam: stored credentials, the
credential-store concurrency contract, refresh/ownership authority, the two generic OAuth
primitives (PKCE, RFC 8628 device-code polling) Pass 1 builds, Codex's own pure (non-network)
account-id projection (`PROV-011`, Pass 2 Slice A, adopted -- below), and the generic
login-interaction/prompt/notification and per-provider auth-method VOCABULARY (`PROV-014`, Pass 2
Slice B, adopted -- below) a provider's own login flow consumes. It does NOT cover any real
provider's own wire-protocol request/response encoding, Codex's own OAuth NETWORK integration
(browser/device-code endpoints, token exchange, the local callback server, `PROV-012`), or the
real `resolveProviderAuth`/`Models`-level dispatch ORCHESTRATION built on top of the `PROV-014`
vocabulary (`PROV-013`, still deferred -- see "Deferred generic auth/provider orchestration
surface" below) -- those remain later Layer 11 Pass 2 slices' own territory.

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

## Provider-auth interaction and auth-method vocabulary (`PROV-014`, Pass 2 Slice B, adopted)

Pinned Pi's public auth vocabulary a provider's own login flow uses, split out of the previously-
bundled `PROV-013` row (owner-approved, 2026-09-14, durably recorded verbatim at
`https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5659001629`) because `PROV-012`'s
own Codex `login()` contract consumes it directly, with no dependency on the still-deferred
`Models`-level orchestration below. VOCABULARY ONLY -- no `Models`-equivalent dispatcher, no
`LlmService` extension, no new generic `AuthService`/`AuthManager` architecture.

```text
AuthPromptText{message,placeholder?,signal?}
AuthPromptSecret{message,placeholder?,signal?}
AuthPromptOption{id,label,description?}
AuthPromptSelect{message,options:AuthPromptOption[],signal?}
AuthPromptManualCode{message,placeholder?,signal?}
AuthPrompt = AuthPromptText|AuthPromptSecret|AuthPromptSelect|AuthPromptManualCode

AuthInfoLink{url,label?}
AuthEventInfo{message,links?:AuthInfoLink[]}
AuthEventUrl{url,instructions?}
AuthEventDeviceCode{user_code,verification_uri,interval_seconds?,expires_in_seconds?}
AuthEventProgress{message}
AuthEvent = AuthEventInfo|AuthEventUrl|AuthEventDeviceCode|AuthEventProgress

AuthInteraction{
    signal?,
    prompt(AuthPrompt) -> string (async; raises/rejects on cancel/abort),
    notify(AuthEvent) -> None (SYNCHRONOUS, direct call -- NOT fire-and-forget/detached; a
                                synchronous throw propagates to notify()'s own caller exactly like
                                any other synchronous statement, it is not swallowed or queued)
}
ProviderAuthInteraction{
    signal,   # REQUIRED here; SAME two methods as AuthInteraction
    prompt(AuthPrompt) -> string,
    notify(AuthEvent) -> None
}
# ProviderAuthInteraction IS-A AuthInteraction: any value satisfying the former (signal always
# present) also satisfies the latter (signal optionally present) -- ordinary structural subtyping,
# not two unrelated shapes that merely happen to look similar.

ApiKeyAuth{
    name: string,
    resolve(ctx: AuthContext, credential: ApiKeyCredential|absent, signal) -> AuthResult|absent,   # REQUIRED, async; MAY raise/reject
    login(interaction: ProviderAuthInteraction) -> ApiKeyCredential,   # OPTIONAL; async, raises/rejects on failure
    check(ctx: AuthContext, credential: ApiKeyCredential|absent, signal) -> AuthCheck|absent   # OPTIONAL, async; MAY raise/reject
}
OAuthAuth{
    name: string,
    login(interaction: ProviderAuthInteraction) -> OAuthCredential,          # REQUIRED; async, raises/rejects on failure
    refresh(credential: OAuthCredential, signal) -> OAuthCredential,         # REQUIRED; async, raises on failure (invalid_grant etc.), no separate error channel
    to_auth(credential: OAuthCredential) -> ModelAuth,                      # REQUIRED; async, side-effect-free but MAY still raise/reject on an unexpected/malformed credential
    is_subscription?: boolean,   # THREE-valued: absent | false | true, all independently observable
    login_label?: string
}
ProviderAuth{api_key?, oauth?}   # at least one of the two REQUIRED
```

**Failure and delivery semantics (`L11-SB-R003`, second independent review; call-site accuracy
corrected per `L11-SB-R007`, third independent review).** Every async callable above
(`ApiKeyAuth.login`/`check`/`resolve`, `OAuthAuth.login`/`refresh`/`to_auth`) MAY raise/reject, but
pinned Pi's own real call sites do NOT uniformly wrap that rejection -- confirmed directly against
Pi, distinguishing the two groups explicitly rather than stating one blanket rule for all six:

- `check` (`models.ts:495-504`), `resolve` (`resolve.ts:188-192`), `to_auth` (`resolve.ts:174-178`),
  and `refresh` (`resolve.ts:127-179`) are each `await`ed inside their own real call site's own
  `try`/`catch`, with a rejection wrapped into a typed failure.
- `ApiKeyAuth.login`/`OAuthAuth.login` are NOT wrapped at their own real call site.
  `Models.login()` (`models.ts:565-575`) calls `method.login({...interaction, signal})` and awaits
  the result through `raceWithAbortSignal(loginOperation, signal)` directly, with no enclosing
  `try`/`catch` around that call -- a login rejection propagates straight out of `Models.login()`
  itself. (`Models.login()` DOES have a later `try`/`catch`, `models.ts:591-613`, but that covers
  only the SUBSEQUENT credential-store mutation step, not the login call itself -- an earlier
  revision of this paragraph incorrectly generalized that later, unrelated wrapping to `login` too.)

None of these callables carries an error-suppression contract of its own; a caller CONSUMING one of
them (the still-deferred `PROV-013` orchestration, not this row) owns deciding how a raised
exception is wrapped/reported -- for `login` specifically, that includes deciding whether/how to
wrap what Pi itself leaves unwrapped, since there is no existing Pi wrapping convention to mirror.
`to_auth` being side-effect-free describes what it does to the WORLD (no I/O, no stored-state
mutation), not whether it can fail -- those are independent properties, and an earlier revision of
this section incorrectly conflated them.

`AuthInteraction.notify()` is a DIRECT SYNCHRONOUS call, not fire-and-forget/detached delivery --
confirmed directly against pinned Pi's own real call sites
(`packages/ai/src/auth/oauth/openai-codex.ts:429`, `:456`): `interaction.notify({...})` is an
ordinary, un-awaited, un-wrapped statement with no enclosing `try`/`catch` and no detachment
mechanism. A synchronous throw from `notify()` propagates directly out of its own caller, exactly
like any other synchronous statement -- it is never silently swallowed or queued for later
delivery.

`AuthPrompt` is the shape of a prompt shown to the user during login: `text`/`secret` are
free-text/masked entry (identical shape, differing only in display treatment); `select` presents a
fixed option set, and its OWN resolved value -- once some concrete `AuthInteraction`
implementation actually resolves a `select` prompt -- is the CHOSEN OPTION'S `id`, never its
`label` (this vocabulary itself defines no such implementation; the behavioral claim belongs to
whichever slice first supplies one); `manual_code` is a fallback entry prompt used when an
interactive callback (e.g. a local OAuth server) is racing this same prompt -- the prompt's own
`signal` is what that race cancels it through, matching Pi's own doc comment naming exactly this
pattern ("a `manual_code` prompt raced against a callback server, aborted when the callback
wins"). The racing mechanics themselves are a concrete login flow's own concern (`PROV-012`), not
part of this vocabulary.

`AuthEvent` is the shape of a notification a login flow may emit: `info` (optionally with
supporting links), `auth_url` (a URL the user should open to continue login -- emitting this is
NOT the same as opening a browser; browser LAUNCHING is confirmed architecturally out of scope for
this layer entirely, a CLI-layer concern Minion has no equivalent of yet), `device_code` (RFC 8628
device-code display details, the notification counterpart to the already-certified `PROV-010`
poll state machine's own outcomes), and `progress` (a free-text update with no further structure).

`AuthInteraction` is the login-interaction callback surface serving both api-key and OAuth flows:
`prompt()` returns the entered/selected string; `notify()` emits an `AuthEvent`; `signal` cancels
the WHOLE login flow (distinct from a specific `AuthPrompt`'s own per-prompt `signal`).
`ProviderAuthInteraction` is the identical shape with `signal` REQUIRED rather than optional -- the
normalized interaction a concrete provider's own login implementation actually receives, by the
time a caller has already normalized an absent top-level signal into a real one. Because a value
with `signal` always present trivially satisfies "`signal` optionally present," `ProviderAuthInteraction`
is a genuine SUBTYPE of `AuthInteraction`: anywhere `AuthInteraction` is accepted, a
`ProviderAuthInteraction` value must also be usable -- an implementation that cannot statically
express this relationship (e.g. two unrelated shapes a checker treats as merely coincidentally
similar) diverges from Pi's own intersection-type semantics, even if every individual field type
is otherwise correct.

`ApiKeyAuth`/`OAuthAuth` are the per-provider auth-METHOD vocabulary a concrete provider registers,
and every one of their own callables has a FULLY SPECIFIED input bundle and result shape (not left
to be inferred from the field-level summary above): `ApiKeyAuth.check`/`resolve` each take Pi's own
same three logical inputs (`ctx`, an OPTIONAL stored `credential`, and a REQUIRED `signal`) and
return an async, optional result (`AuthCheck`/`AuthResult`, `absent` meaning "not configured"); a
language MAY represent these three inputs as one structured bundle or as separate parameters
however is idiomatic for it (a disclosed MAPPING -- see `PROV-014`'s own row in the parity
manifest for the exact language used), but must change no input's own optionality, requiredness,
or the result's own shape in doing so. `ApiKeyAuth.login` is OPTIONAL (absent means ambient-only,
no interactive setup) and takes the normalized interaction, returning a new credential or
raising/rejecting. `OAuthAuth.login`/`refresh`/`to_auth` are all REQUIRED, each with ONE
unambiguous argument list (no bundling question, unlike `ApiKeyAuth.check`/`resolve`) -- the
`refresh`/`to_auth` split lets an orchestration layer own the locked-refresh pattern: `refresh`
produces a credential (raising on failure, e.g. `invalid_grant`, with no separate error channel),
`to_auth` derives request auth from whatever credential ends up stored, side-effect-free and not
expected to raise for a valid credential (already-certified `PROV-011`'s own Codex
`credentials_from_token`/`to_auth` is a concrete instance of exactly this split). `is_subscription`
is GENUINELY three-valued (absent / `false` / `true`), matching Pi's own optional-boolean field
exactly -- an implementation collapsing "absent" into "`false`" narrows this contract observably.
`ProviderAuth` MUST carry at least one of `api_key`/`oauth` -- a real, enforced constraint, not
merely a convention: even an ambient-credential or keyless provider supplies `api_key` auth whose
own `resolve()` reports configuration status.

**Mutability.** Every field on every type in this section is ORDINARILY ASSIGNABLE after
construction, matching pinned Pi's own public object/interface shapes, none of which are
`readonly` -- ONLY the two collection fields (`AuthPromptSelect.options`, `AuthEventInfo.links`)
are `readonly` in Pi, a narrower restriction on replacing a collection's own elements, distinct
from an ordinary field being freely reassignable. An implementation that makes any OTHER field of
these types immutable (e.g. a frozen/read-only value object) introduces an unapproved observable
divergence from Pi's own assignable-property semantics, the same question this project already
resolved for Layer-11 credentials (`PROV-006`) by adopting Pi's assignable fields in full.

ONE NAMED EXCEPTION: `AuthInteraction.signal`/`ProviderAuthInteraction.signal`'s own assignability
through a value STATICALLY TYPED as either of those two interfaces specifically -- an intentional,
narrow, owner-approved language-binding divergence, not part of this section's own general
mutability rule. See `PROV-015` immediately below.

## Interaction-type assignability divergence (`PROV-015`, intentional divergence)

Pinned Pi's own TypeScript type system permits BOTH of the following simultaneously for
`AuthInteraction`/`ProviderAuthInteraction`'s own `signal` field: (1) `ProviderAuthInteraction` is
a genuine SUBTYPE of `AuthInteraction` (usable anywhere the wider, optional-`signal` type is
expected -- the relationship `PROV-014`'s own `AuthInteraction`/`ProviderAuthInteraction` section
above states normatively); and (2) `signal` is a plain, non-`readonly` property on BOTH types,
assignable through either.

A sound static type system cannot express both properties simultaneously when the two interfaces'
own `signal` type genuinely differs (optional vs. required) -- this is a real, unavoidable
consequence of TypeScript's own well-documented UNSOUNDNESS for exactly this mutable-property-
variance combination, not an implementation gap any amount of cleverer code closes. Owner
governance (recorded verbatim as the `GOVERNANCE_SOURCE` at
`https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5664609556`) explicitly chose to
preserve property (1) -- the subtyping relationship, and the guarantee that a provider's own
`login()` always receives a present `signal` -- over property (2), after confirming that no actual
pinned-Pi call site anywhere ever reassigns an interaction's own `signal` after construction; the
sacrificed capability is a static permission Pi's own real code never exercises.

**Scope, exactly:** a value statically typed as `AuthInteraction`/`ProviderAuthInteraction`
specifically cannot have `.signal` assigned through that reference in an implementation choosing
this trade-off. This divergence does NOT extend to runtime behavior or to any concrete
implementation backing either interface: a concrete provider's own object remains free to expose
its own mutable `signal` field or setter through its OWN concrete type, matching Pi's own real
object behavior exactly -- only what a generic, vocabulary-consuming caller can do THROUGH the
widened interface type is affected. No runtime immutability is introduced anywhere by this
divergence, and it must not be used to justify one.

**For a future Rust implementation:** this divergence is NOT itself a mechanism to replicate.
Rust must preserve the language-neutral semantic contract -- `ProviderAuthInteraction` specializes
`AuthInteraction`; a provider's own `login()` receives a guaranteed-present `signal` -- using
whatever mutability representation is idiomatic and sound for Rust's own type system. That
representation is reviewed independently when Rust implements this row; this document does not
prescribe Rust mechanics.

## Deferred generic auth/provider orchestration surface (`PROV-013`)

The real dispatcher/orchestration built ON TOP of `PROV-014`'s own vocabulary: `resolveProviderAuth`
(stored-OAuth vs. api-key vs. ambient-env dispatch) and the `Models` collection's own orchestration
entry points (`checkAuth`, `getAuth`, `login`, `logout`, `getAvailable`) (`L11-R005`, originally
discovered bundled with the vocabulary now split into `PROV-014` above).

This is EXPLICITLY NOT a demand to implement any of this in Pass 2 either -- extending `LlmService`
or inventing a replacement orchestration service is explicitly out of scope (owner-approved,
2026-09-14, same durable record as the split above). It requires a real
`Provider{id, auth: ProviderAuth, getModels()}`-shaped registry Minion's own `LlmService`
(`register`/`models`/`stream` only, confirmed absent during the Pass-2 restart audit) does not have
yet. `Models.login`'s own commit-race-safety semantics (an abort-vs-mutation-started race) will
additionally need their own careful design when this row is eventually closed, not a trivial
wire-up.

Closure criterion (binding on whichever future pass closes this row, unchanged from the original
`L11-R005` discovery other than the vocabulary split above): a future pass that introduces the
provider/auth composition surface actually needing `Models`-equivalent orchestration must design
the integration contract-first against pinned Pi, consuming `PROV-014`'s own already-adopted
vocabulary directly rather than inventing an ad hoc replacement shape.

## Codex account-id projection (`PROV-011`, Pass 2 Slice A, adopted)

Pinned Pi's Codex OAuth flow's pure (non-network) half -- JWT decode for `chatgpt_account_id` and
the resulting bearer `ModelAuth` projection. This is provider-specific behavior, not a generic
primitive, but it is fully self-contained and independently observable without any real network
call, so it is adopted directly rather than deferred alongside `PROV-012`'s own network
integration below.

```text
decode_jwt(token) -> JS-JSON.parse-equivalent value | absent   # NOT necessarily an object
get_account_id(access_token) -> string|absent
credentials_from_token(access, refresh, expires) -> OAuthCredential   # raises if no account id
to_auth(credential) -> ModelAuth      # {api_key: credential.access}
```

`decode_jwt` is UNVERIFIED claim extraction only -- it decodes the JWT's own payload segment, and
never performs cryptographic signature validation. No signature verification may be added where
Pi performs only unverified decoding; treating an unverified claim as authenticated identity would
be a false strengthening of this contract, not a hardening of it.

`decode_jwt`'s own decode boundary is a language-neutral equivalent of pinned Pi's `atob(payload)`
followed by `JSON.parse(...)` -- EXACTLY, not approximately, and its result type is whatever value
that equivalent produces, not merely "parsed JSON" in the general sense. Four binding rules,
each independently confirmed against a live Node process before being adopted here:

1. **Base64 decoding follows the WHATWG "forgiving-base64 decode" algorithm** (the algorithm
   `atob` itself implements), not an implementation's own base64 library defaults:
   - every ASCII whitespace code point (tab, line feed, form feed, carriage return, space)
     anywhere in the payload segment -- leading, trailing, or interior -- is removed before
     decoding; a segment containing one is not thereby invalid.
   - a trailing `=` is accepted ONLY when the whitespace-stripped segment's own length is a
     multiple of 4 AND it ends in EXACTLY one or two `=` characters; that padding is then
     stripped before decoding the remaining content. Any other placement or count of `=`
     characters -- including a segment whose length is not a multiple of 4 to begin with, or one
     ending in three or more `=` -- makes the WHOLE segment invalid. A segment with NO trailing
     `=` at all decodes normally (padding is optional, not required); a segment with GENUINELY
     malformed padding (e.g. one `=` where two are required) must be REJECTED, never silently
     repaired by adding the padding it appears to be missing.
   - after that stripping, a resulting length leaving remainder 1 (mod 4) is invalid; every
     remaining character must be in the standard base64 alphabet (`A-Za-z0-9+/`) -- base64url's
     `-`/`_` alphabet characters are therefore always invalid, covered by this same rule, not a
     separate check.
2. **The decoded bytes are interpreted as LATIN-1, never UTF-8.** A JWT claim VALUE containing a
   non-ASCII character (encoded as UTF-8 bytes before base64, the universal way JWTs are built)
   therefore decodes to MOJIBAKE, not the original character. This is the correct, Pi-faithful
   observable behavior for this unverified-decode path, not a defect to silently repair by
   decoding as UTF-8 instead -- doing so would itself be an unapproved observable divergence.
3. **The bare tokens `NaN`, `Infinity`, and `-Infinity` are INVALID at any position a JSON value is
   expected**, matching JavaScript's own `JSON.parse` (which rejects all three as non-JSON) rather
   than the broader "JSON plus numeric-constant extensions" grammar some JSON parsers accept by
   default. A payload segment containing one of these bare tokens anywhere fails to decode as a
   whole, exactly like any other JSON syntax error.
4. **Every JSON number literal -- including integers -- is coerced through IEEE-754 double
   precision**, matching JavaScript's own single numeric type: a literal beyond `2**53` silently
   loses precision to the nearest representable double (e.g. the literal `9007199254740993`
   becomes the value `9007199254740992`), and the literal `-0` produces a genuine, sign-preserving
   negative zero distinct from `+0`. An implementation that instead preserves exact,
   arbitrary-precision integers, or that collapses `-0` to an unsigned zero, diverges observably
   from this contract for any claim carrying such a value, even though it is "more correct" or
   "more precise" by an ordinary JSON reader's own standard.

`decode_jwt` itself does not validate that the decoded/parsed payload is an object; a non-object
result (array, string, number, or the JSON literal `null`) is tolerated by `get_account_id`'s own
graceful lookup, not rejected earlier -- a payload segment that decodes to the JSON literal `null`
is therefore indistinguishable from a malformed token, matching Pi's own `JSON.parse("null") ===
null` ambiguity.

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

## Codex OAuth network integration (`PROV-012`, Pass 2 Slice C, contract)

Pinned Pi's Codex OAuth NETWORK half (`packages/ai/src/auth/oauth/openai-codex.ts`,
`packages/ai/src/auth/oauth/pkce.ts`, `packages/ai/src/auth/oauth/device-code.ts` (already certified
as `PROV-009`/`PROV-010`), `packages/ai/src/utils/abort.ts`) -- consuming the interaction/auth-method
vocabulary (`PROV-014`) and the Codex account-id projection (`PROV-011`) already adopted above.

This section is the SHARED CONTRACT for this slice, produced contract-first per the owner's own
Pass-2 scope decision (`GOVERNANCE_SOURCE`,
`https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5659001629`): "Slice C: PROV-012,
Codex OAuth network integration consuming Slice B vocabulary." Python implementation, tests, and
gates for this contract are a separate, following pass; this section alone is not itself a claim
that Python or Rust code implementing it yet exists.

### Fixed identity/endpoint constants

These are literal values sent to or compared against a real third-party OAuth server -- part of the
OBSERVABLE contract, not implementation mechanics, and MUST be reproduced exactly, not merely
"some client id"/"some URL":

```text
CLIENT_ID                  = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTH_BASE_URL               = "https://auth.openai.com"
AUTHORIZE_URL                = AUTH_BASE_URL + "/oauth/authorize"
TOKEN_URL                     = AUTH_BASE_URL + "/oauth/token"
REDIRECT_URI (browser flow)    = "http://localhost:1455/auth/callback"
DEVICE_USER_CODE_URL             = AUTH_BASE_URL + "/api/accounts/deviceauth/usercode"
DEVICE_TOKEN_URL                  = AUTH_BASE_URL + "/api/accounts/deviceauth/token"
DEVICE_VERIFICATION_URI            = AUTH_BASE_URL + "/codex/device"
DEVICE_REDIRECT_URI (device flow)   = AUTH_BASE_URL + "/deviceauth/callback"
DEVICE_CODE_TIMEOUT_SECONDS          = 900        # 15 minutes, fixed
SCOPE                                 = "openid profile email offline_access"
LOGIN_METHOD_BROWSER                   = "browser"       # select-prompt option id, default
LOGIN_METHOD_DEVICE_CODE                = "device_code"   # select-prompt option id
```

The local callback server always LISTENS on port `1455` (not configurable) at a HOST that IS
configurable (`PI_OAUTH_CALLBACK_HOST` environment variable) -- read directly from the process
environment, NOT through the `AuthContext` seam `ApiKeyCheck`/`ApiKeyResolve` use (Pi's own
`OAuthLogin`/`OAuthRefresh`/`OAuthToAuth` callables never receive an `AuthContext` parameter at all;
this is a genuine, disclosed asymmetry in Pi's own design, not an omission to correct).

**The default-fallback rule is a JAVASCRIPT-TRUTHINESS check, NOT a "blank normalizes to absent"
rule** (`L11-SC-R006`, independent review -- corrects an earlier revision's own inaccurate "absent
or blank" wording): pinned Pi's own `getCallbackHost()` is `getProviderEnvValue(...) ||
"127.0.0.1"`, and `getProviderEnvValue` itself (`utils/provider-env.ts`) performs NO trimming or
blank-normalization of any kind at any point in its own lookup chain -- confirmed by reading it in
full. Only a LITERALLY EMPTY string (or a genuinely absent/undefined value) is falsy and falls back
to the default; a WHITESPACE-ONLY value (e.g. `"   "`) is TRUTHY in JavaScript and is used VERBATIM,
unstripped, as the actual bind host. This is a DIFFERENT rule from this same codebase's own
`DefaultAuthContext.env()` (`PROV-006`), which DOES treat a whitespace-only value as absent -- the
two functions are genuinely different Pi call sites with genuinely different behavior, and this row
must NOT reuse `DefaultAuthContext`'s own blank-normalization convention merely because both happen
to read an environment variable.

`REDIRECT_URI`'s own HOSTNAME is always the literal string `"localhost"` regardless of the
configured callback host -- it is the value sent to the remote authorize/token endpoints, distinct
from the local socket's own bind address.

### Login method selection

`OAuthAuth.login` first prompts a `select` (`PROV-014`'s own `AuthPromptSelect`) with message
`"Select OpenAI Codex login method:"` and exactly two options, in this order:

```text
{id: "browser", label: "Browser login (default)"}
{id: "device_code", label: "Device code login (headless)"}
```

**This specific `select` prompt carries NO `signal`** (`L11-SC-R006`, independent review) -- unlike
the browser flow's own `manual_code` prompt (which explicitly sets `signal` to its own dedicated
abort controller), pinned Pi's own real call site constructs this `select` prompt with no `signal`
member at all, so `AuthPromptSelect.signal` is absent/`None` here specifically. Cancelling the whole
login flow does NOT cancel this specific pending prompt through any signal wired to it by this row
-- whatever cancellation (if any) applies is entirely the concrete `AuthInteraction`
implementation's own concern for an un-signalled prompt, not something this row's own contract
provides. An implementation that attaches the whole-flow `signal` to this prompt "for consistency"
diverges observably from Pi and MUST NOT do so.

then dispatches to the browser flow or the device-code flow by the returned id (`PROV-014`'s own
select-returns-`id` rule). Any OTHER returned id raises/rejects with EXACTLY the message
`"Unknown OpenAI Codex login method: {method}"` (`L11-SC-R006`, independent review -- the prior
"raise/reject" wording did not pin the exact text, unlike every other error message this contract
otherwise specifies verbatim) -- a contract violation by the `AuthInteraction` implementation, not a
recognized login method; do not silently fall back to either flow.

### Browser/PKCE flow

1. Generate a PKCE pair (`PROV-009`'s own `generate_pkce()`) and a random state: 16 cryptographically
   random bytes, hex-encoded (32 lowercase hex characters) -- Pi's own `randomBytes(16).toString
   ("hex")`.
2. Build the authorization URL from `AUTHORIZE_URL` with these EXACT query parameters, in this
   order, all always present:

   ```text
   response_type=code
   client_id=<CLIENT_ID>
   redirect_uri=<REDIRECT_URI>
   scope=<SCOPE>
   code_challenge=<PKCE challenge>
   code_challenge_method=S256
   state=<generated state>
   id_token_add_organizations=true
   codex_cli_simplified_flow=true
   originator=pi
   ```

   `originator` is a FIXED literal `"pi"` -- pinned Pi's own single real call site never varies it;
   this is not a configurable per-provider value.
3. Start a local HTTP callback server bound to the configured callback host (see above) on port
   `1455`. Binding is NOT infallible: if the port is already in use (or any other bind error
   occurs), the server MUST NOT raise/crash the login flow -- it silently becomes a permanently-empty
   source (its own "wait for code" outcome resolves to absent immediately and forever), so the
   flow falls through entirely to the manual-code path below. This is a real, easily-missed Pi
   behavior (`startLocalOAuthServer`'s own `.on("error", ...)` handler), not a hypothetical edge
   case -- a discriminating test MUST exercise it (e.g. by first occupying the port).
4. The server handles exactly one route, `/auth/callback`, with these EXACT response rules (every
   other route is `404`):

   ```text
   path != "/auth/callback"                        -> 404, error page ("Callback route not found.")
   query "state" != the state generated in step 1   -> 400, error page ("State mismatch.")
   query "code" absent                              -> 400, error page ("Missing authorization code.")
   otherwise                                         -> 200, success page; yields {code} to the flow
   ```

   The response body content itself (the HTML success/error pages) is presentation, not part of
   this contract's own observable surface -- what matters is the status code and that the SAME
   `code`/`state` query-parameter extraction and validation order above is followed exactly.
5. Emit an `auth_url` notification (`PROV-014`'s own `AuthEventUrl`) carrying the built URL and the
   fixed instructions text `"A browser window should open. Complete login to finish."` -- emitting
   this event is NOT the same as opening a browser (browser LAUNCHING remains explicitly OUT OF
   SCOPE for this row, confirmed by the owner's own Pass-2 scope decision; this layer only emits the
   notification, matching Pi's own `packages/ai` boundary exactly, since Pi's own browser-opening
   utility lives entirely in a separate CLI-layer package).

   **This notification happens BEFORE the flow's own cleanup boundary begins, not inside it**
   (`L11-SC-R001`, independent review): pinned Pi's own `interaction.notify({type: "auth_url", ...})`
   call (`openai-codex.ts:456-460`) executes strictly BEFORE the surrounding `try`/`finally` block
   (`openai-codex.ts:462-505`) is ever entered -- the abort-listener registration (step 3 above), the
   server, and the manual-prompt abort controller are all set up earlier still, but the CLEANUP
   itself (listener removal, `manualAbort.abort()`, `server.close()`) lives ONLY inside that
   `finally`. `notify()` is a DIRECT SYNCHRONOUS call whose throw propagates immediately
   (`PROV-014`'s own established rule) -- if it throws HERE, execution never reaches the `try` at
   all, so the local server is left listening, the flow-level abort listener is left registered, and
   the manual-prompt abort controller is never aborted. This is a genuine, confirmed Pi behavior, not
   a defect to silently harden away: an implementation must reproduce this EXACT boundary (no cleanup
   on a `notify()` failure at this specific point) unless the owner explicitly approves an
   intentional, disclosed hardening divergence instead. A discriminating test MUST exercise a
   `notify()` failure at this exact point and assert that cleanup does NOT occur, not merely that
   the flow's own call raises.
6. Concurrently with waiting for the server's own callback, prompt a `manual_code` prompt
   (`PROV-014`'s own `AuthPromptManualCode`) with message `"Complete login in your browser, or paste
   the authorization code / redirect URL here:"` and `placeholder` set to `REDIRECT_URI`, racing it
   against the server callback with this EXACT precedence, discriminating every combination
   explicitly (this is a genuinely concurrent, multi-source race -- not one happy-path example;
   extended per `L11-SC-R002`, independent review, to cover three cases the first contract pass
   omitted):

   ```text
   server yields a code FIRST                                  -> use the server's code; cancel the
                                                                    still-pending manual prompt
   manual entry resolves with a NON-EMPTY value FIRST           -> stop waiting on the server;
                                                                    parse the manual input (below);
                                                                    use its own code
   manual entry resolves with an EMPTY/WHITESPACE-ONLY value
     FIRST (`L11-SC-R002` point 1)                              -> stop waiting on the server (the
                                                                    empty resolution itself cancels
                                                                    it, exactly like a non-empty one
                                                                    does); the empty value is then
                                                                    treated as ABSENT by the SAME
                                                                    truthiness check step 7's own
                                                                    "otherwise" case relies on, so no
                                                                    code is extracted from it -- the
                                                                    server is NOT waited on any
                                                                    further after being cancelled, so
                                                                    this combination raises/rejects
                                                                    `"Missing authorization code"`
                                                                    even if the server would have
                                                                    legitimately yielded a real code
                                                                    moments later; this is a real,
                                                                    confirmed Pi behavior (the empty
                                                                    manual resolution's own
                                                                    cancel-the-server side effect is
                                                                    unconditional, not gated on the
                                                                    value being non-empty), not a
                                                                    hypothetical edge case
   manual entry itself raises/rejects (e.g. its own signal
     aborts) BEFORE the server yields anything                  -> propagate that error; do not fall
                                                                    back to the server
   the WHOLE login flow's own `signal` aborts while BOTH the
     server and the manual prompt are still pending
     (`L11-SC-R002` point 2)                                    -> this cancels ONLY the server's own
                                                                    wait (resolving it absent,
                                                                    functionally identical to a
                                                                    bind-failure); it does NOT abort
                                                                    the manual prompt's own SEPARATE
                                                                    per-prompt signal at this point --
                                                                    that only happens in the flow's own
                                                                    final cleanup (step 6's own
                                                                    unconditional-cleanup note below),
                                                                    which is not reached until the
                                                                    manual prompt itself settles. A
                                                                    flow-level abort therefore does
                                                                    NOT promptly resolve this operation
                                                                    while a manual prompt remains
                                                                    outstanding -- the operation keeps
                                                                    waiting on the manual prompt's own
                                                                    eventual settlement (whatever the
                                                                    concrete `AuthInteraction`
                                                                    implementation's own `prompt()`
                                                                    does when its OWN, separate
                                                                    per-prompt signal is never fired),
                                                                    exactly like the fallback rule
                                                                    below. An implementation must NOT
                                                                    assume a flow-level abort settles
                                                                    this operation promptly merely
                                                                    because a signal fired.
   the server's own "wait for code" resolves ABSENT (bind
     failure, or the flow-level `signal` aborted per above)
     with no manual code yet either                             -> wait for the still-pending manual
                                                                    prompt to settle rather than
                                                                    failing immediately; only if THAT
                                                                    also yields no usable (non-empty)
                                                                    code is `"Missing authorization
                                                                    code"` raised
   neither source ever yields a usable code                     -> raise/reject
     ("Missing authorization code")
   ```

   **Manual state validation is a TRUTHINESS check, not a presence check** (`L11-SC-R002` point 3):
   if the parsed `state` is a non-empty (truthy) string AND it does not equal the state generated in
   step 1, raise/reject `"State mismatch"` before ever attempting a token exchange. An EMPTY parsed
   `state` (e.g. the manual input `"code#"`, which step 7's own `"#"`-split rule below parses to
   `{code: "code", state: ""}`) is treated EXACTLY like an absent one -- validation is SKIPPED, not
   triggered as a mismatch -- because Pi's own `parsed.state && parsed.state !== state` check is
   short-circuited by the falsy empty string before the inequality is ever evaluated. An
   implementation that instead treats "parsed `state` is not `None`/undefined" as sufficient to
   REQUIRE a match diverges observably for exactly this input shape and MUST NOT do so.

   The manual prompt is always cancelled (its own per-prompt signal aborted) once the server yields
   a code, and the server is always closed and the flow-level abort listener always detached, once
   the flow's own cleanup boundary is reached and concludes by ANY path (success, error, or
   cancellation) WITHIN that boundary -- see step 5's own note above for the one case (a `notify()`
   failure) that never reaches this boundary at all, and is NOT covered by this cleanup guarantee.
7. **Manual input parsing** (`parse_authorization_input`) accepts three shapes, tried in this exact
   order, and is a documented, intentional accommodation, not an error condition:

   ```text
   empty/whitespace-only input                        -> {code: absent, state: absent}
   parses as an absolute URL                           -> {code, state} from its own query string
                                                           (either may be absent)
   contains "#"                                        -> split on the FIRST "#" into exactly two
                                                           parts: code = everything before it,
                                                           state = everything STRICTLY BETWEEN the
                                                           first "#" and a SECOND "#" if one exists,
                                                           or the whole remainder if it does not --
                                                           a Pi-observable split-with-limit-2
                                                           behavior (content after a SECOND "#", if
                                                           present, is DISCARDED, never appended to
                                                           `state`); an implementation using a plain
                                                           "keep everything after the first split
                                                           point" split (a common host-language
                                                           default, unlike Pi's own limited split)
                                                           diverges observably for an input
                                                           containing two or more "#" characters and
                                                           MUST be corrected to match Pi's own
                                                           discard-the-remainder behavior exactly
   contains "code="                                    -> parsed as a bare query string (no leading
                                                           "?" required) -> {code, state} from it
   otherwise                                           -> {code: the whole trimmed input, state:
                                                           absent} -- a bare pasted authorization
                                                           code with no URL/query wrapper at all
   ```

   State validation for this parsed result is the SAME truthiness-based rule step 6 already states
   in full (see its own "Manual state validation" note above) -- not restated here to avoid two
   sources of truth for the identical rule.
8. Exchange the resolved authorization code for tokens (below), using the ORIGINAL `REDIRECT_URI`
   (not the device-flow's own redirect URI) and the PKCE verifier from step 1.

### Device-code flow

1. POST `DEVICE_USER_CODE_URL` with a JSON body `{client_id: CLIENT_ID}`, using the SAME
   cancellation-translation transport behavior as token exchange (see "Token exchange and refresh"
   below -- `L11-SC-R004`, independent review: this request shares that exact translation, not a
   rule scoped only to exchange). On a non-`2xx` response: a `404` status raises EXACTLY the fixed
   message `"OpenAI Codex device code login is not enabled for this server. Use browser login or
   verify the server URL."`; any OTHER non-`2xx` status raises EXACTLY
   `"OpenAI Codex device code request failed with status {status}"` with a CONDITIONAL suffix
   (`L11-SC-R006`, independent review -- the prior "generic status+body message" wording did not pin
   this exact, easily-missed format): `": {body}"` is appended ONLY when the response body is
   non-empty (read with the SAME empty-string-on-failure fallback token exchange itself uses below);
   when the body is empty/unreadable, there is NO trailing colon at all -- not even an empty one --
   the message ends immediately after the status code. This differs from token exchange's OWN
   non-`2xx` message (below), which falls back to the response's own status-text reason phrase
   instead of omitting the suffix entirely -- the two messages are NOT the same template reused.

   On a `2xx` response, the body is first parsed as JSON; **a JSON-parse failure itself propagates
   as that raw parse error, UNCHANGED** -- it is never converted into this step's own "invalid
   response" message below (`L11-SC-R004`; see "Token exchange and refresh" for the identical rule
   restated once for all four outbound calls in this row). Only once the body successfully parses as
   JSON does field-level validation apply, and that validation is a JAVASCRIPT TRUTHINESS check, NOT
   a string-type check (`L11-SC-R003`, independent review: pinned Pi's own TypeScript field
   annotations -- `device_auth_id?: string`, `user_code?: string` -- are ERASED at runtime; the
   actual guard is `!json?.device_auth_id || !json.user_code`, which accepts ANY truthy value of ANY
   type, not only a non-empty string -- a truthy JSON number or object for either field is NOT
   rejected by Pi's own real code, even though it would violate the DECLARED type). A future
   implementation MUST reproduce this truthy-of-any-type acceptance (representing these two fields
   as an open `JsonValue`-shaped check rather than a strict string type) UNLESS the owner explicitly
   approves a stricter, disclosed validation divergence instead (`agent-workflow.md` §11.10) -- do
   not silently narrow this to "must be a string" and call the row Pi-faithful.

   `interval` uses a THIRD validation rule, distinct from both fields above: `typeof intervalSeconds
   !== "number" || !Number.isFinite(intervalSeconds) || intervalSeconds < 0` is the actual guard,
   where `intervalSeconds` is EITHER the raw JSON value of `interval` (when it is not itself a JSON
   string -- ANY non-string JSON type reaching this point, including a boolean or object, simply
   fails the `typeof ... !== "number"` check and is rejected) OR, when `interval` IS a JSON string,
   the result of JavaScript's own `Number(interval.trim())` coercion -- EMPIRICALLY CONFIRMED live
   against Node (matching this project's own established `L11-SA-R001` discipline of verifying
   assumed JS coercion behavior rather than assuming it), this coercion is NOT equivalent to a naive
   `float(trimmed)` parse:

   - an EMPTY string (after trimming) coerces to `0`, a valid, ACCEPTED interval -- NOT rejected,
     and NOT the same as an absent/`None` interval; a Python `float("")`, by contrast, raises,
     making a naive port incorrectly REJECT a whitespace-only `interval` value Pi's own real code
     silently accepts as zero.
   - ordinary decimal notation (optional leading sign, optional fractional part, optional exponent,
     e.g. `"5"`, `"-5"`, `".5"`, `"5."`, `"1e3"`) parses as the equivalent number.
   - a HEXADECIMAL (`0x`/`0X`), OCTAL (`0o`/`0O`), or BINARY (`0b`/`0B`) integer-literal PREFIX is
     also recognized and parsed in that base (e.g. `"0x1A"` coerces to `26`) -- a naive decimal-only
     parser diverges observably for this input shape.
   - the literal tokens `"Infinity"`/`"+Infinity"`/`"-Infinity"` coerce to the corresponding
     infinite value, which then FAILS the surrounding `Number.isFinite` check (so these are
     ultimately rejected, but via the finiteness check, not the coercion step itself).
   - any other content (trailing garbage, non-numeric characters, e.g. `"5abc"`) coerces to `NaN`,
     which also fails the `typeof ... !== "number"` check (`typeof NaN === "number"` is TRUE in
     JavaScript, so `NaN` is rejected by the SEPARATE `Number.isFinite(NaN)` check instead, not the
     `typeof` check -- both checks matter, for different reasons, and an implementation must
     reproduce both, not collapse them into one "is it a valid positive number" test that happens to
     reject `NaN` for the wrong stated reason).

   A permanent implementation witness MUST cover, at minimum: an empty/whitespace-only interval
   string (accepted as `0`), a hex/octal/binary-prefixed string (accepted, parsed in that base), and
   a garbage string (rejected).
2. Emit a `device_code` notification (`PROV-014`'s own `AuthEventDeviceCode`) carrying the returned
   `user_code`, the FIXED `DEVICE_VERIFICATION_URI`, the returned interval as `interval_seconds`,
   and the FIXED `DEVICE_CODE_TIMEOUT_SECONDS` as `expires_in_seconds`.
3. Poll `DEVICE_TOKEN_URL` through the already-certified `PROV-010` device-authorization poll state
   machine, with the server-returned interval as the initial interval, `DEVICE_CODE_TIMEOUT_SECONDS`
   as the deadline, and NO initial pre-poll wait (polling begins immediately). Each poll attempt POSTs
   a JSON body `{device_auth_id, user_code}`, using the SAME cancellation-translation transport
   behavior as token exchange (`L11-SC-R004`; see "Token exchange and refresh" below -- this request
   ALSO shares that exact translation), and maps the HTTP response to `PROV-010`'s own poll outcomes
   EXACTLY as follows -- no other mapping is conforming:

   ```text
   2xx, body FAILS to parse as JSON                          -> that raw JSON-parse error propagates
                                                                 UNCHANGED (`L11-SC-R004`) -- it is
                                                                 NOT converted into either the
                                                                 FAILED-outcome message below or a
                                                                 PENDING/SLOW_DOWN outcome
   2xx, body parses as JSON, has BOTH authorization_code and
     code_verifier (JAVASCRIPT-TRUTHY, any type -- `L11-SC-R003`,
     same truthiness rule as step 1's own fields, NOT a
     string-type check)                                       -> COMPLETE, value = {authorization_code,
                                                                    code_verifier}
   2xx, body parses as JSON but is missing either field
     (falsy or absent)                                        -> FAILED ("Invalid ... token response:
                                                                    <body>")
   403 or 404                                                  -> PENDING
   other status, error body FAILS to parse as JSON             -> FAILED (status+body message) -- an
                                                                    unparseable error body is folded
                                                                    into the generic FAILED case, NOT
                                                                    propagated as a raw parse error
                                                                    (unlike the 2xx success-path parse
                                                                    failure above, which propagates
                                                                    unchanged -- the two are genuinely
                                                                    different Pi behaviors, not the
                                                                    same rule applied twice)
   other status, error body parses as JSON with
     error === "deviceauth_authorization_pending"
     (or error.code === that string)                           -> PENDING
   other status, error body parses as JSON with
     error === "slow_down" (or error.code === that string)      -> SLOW_DOWN, with NO server-provided
                                                                    interval override -- this
                                                                    endpoint never supplies one, so
                                                                    `PROV-010`'s own fixed +5-second
                                                                    increment ALWAYS applies here,
                                                                    never the server-interval branch
   other status, error body parses as JSON but matches
     neither error code above                                   -> FAILED (status+body message)
   ```

4. Exchange the returned `authorization_code`/`code_verifier` for tokens (below), using
   `DEVICE_REDIRECT_URI` (NOT the browser flow's own `REDIRECT_URI`) and the RETURNED
   `code_verifier` (NOT a locally-generated PKCE verifier -- the device flow's own verifier is
   server-issued, unlike the browser flow's own client-generated one).

### Token exchange and refresh

Both POST `TOKEN_URL` with `Content-Type: application/x-www-form-urlencoded`:

```text
exchange: grant_type=authorization_code, client_id, code, code_verifier, redirect_uri
refresh:  grant_type=refresh_token, refresh_token, client_id
```

The response is parsed identically for both operations: a non-`2xx` status raises
`"OpenAI Codex token {exchange|refresh} failed ({status}): {body text, or the status's own reason
phrase if the body is empty/unreadable}"`. On a `2xx` response, the body is first parsed as JSON;
**a JSON-parse failure itself propagates as that raw parse error, UNCHANGED** (`L11-SC-R004`,
independent review -- this exact rule, stated once here, also governs the device-flow start and
poll requests above: `response.json()`'s own rejection on a `2xx`/success-path response is never
caught anywhere in pinned Pi's own code for ANY of these three success-path parses, and so is never
converted into a field-validation message; contrast the device-poll's own SEPARATE, deliberately
DIFFERENT rule for an UNPARSEABLE ERROR body on its non-2xx path, which IS caught and folded into a
generic failure, not propagated raw -- these are two different Pi behaviors for two different
response paths, not the same rule restated). Only once the body successfully parses as JSON does
field-level validation apply: a `2xx` body MUST supply a JAVASCRIPT-TRUTHY (any type, NOT
necessarily a string -- `L11-SC-R003`, same erased-runtime-type-annotation rule as the device-flow
fields above) `access_token` and a JAVASCRIPT-TRUTHY `refresh_token`, PLUS an `expires_in` that
passes an EXPLICIT `typeof expires_in !== "number"` check -- this THIRD field is validated
differently from the first two: pinned Pi's own guard is `!json?.access_token || !json.refresh_token
|| typeof json.expires_in !== "number"`, a genuine MIX of two truthiness checks and one real
runtime type check within the SAME validation, not three checks of the same kind. Any failing field
(by ITS OWN applicable rule) raises `"OpenAI Codex token {exchange|refresh} response missing fields:
{the parsed body}"`. On success, the resulting token's own `expires` is the CURRENT wall-clock time
in Unix-epoch milliseconds PLUS `expires_in * 1000` (matching `OAuthCredential.expires`'s own
existing epoch-milliseconds contract, `PROV-006`) -- computed at response-parse time, not at
request-send time.

**Cancellation and error-wrapping differ between exchange/device-start/device-poll as one group and
refresh alone, and this asymmetry is itself part of the contract, not an oversight to harmonize**
(`L11-SC-R004`, independent review -- the grouping below CORRECTS an earlier revision of this
section, which incorrectly assigned the FIRST rule only to exchange):

- **Exchange, device-start, and device-poll** (all three of this row's own OUTBOUND requests other
  than refresh) share the IDENTICAL transport-level cancellation translation, via pinned Pi's own
  shared `fetchWithLoginCancellation` helper each of the three real call sites uses: a network
  failure caused by the caller's OWN cancellation is distinguished from every other network failure
  -- if the underlying request fails WHILE the given signal is already aborted, the operation raises
  the FIXED message `"Login cancelled"`, discarding the underlying transport error entirely; any
  OTHER network failure (the signal not aborted) propagates the underlying error unchanged. This
  rule governs a request-LEVEL failure (the request never completed at all), a materially different
  concern from either JSON-parse-failure rule above, which governs a response body that DID arrive.
- **Refresh alone** applies NO such translation: ANY network-level failure (not a non-2xx HTTP
  response, which is handled by the shared response-parsing rule above, but a failure to complete
  the request at all) is wrapped as `"OpenAI Codex token refresh error: {the underlying error's own
  message}"`, with no cancellation-specific message, regardless of whether the signal was the cause.
  This asymmetry is NOT because refresh's own caller supplies "a fixed time budget, not a
  user-driven cancellation" -- an earlier revision of this section stated that, and it is
  INACCURATE (`L11-SC-R004`): the already-certified `PROV-008`'s own `refresh_if_expiring` supplies
  refresh with a `CombinedSignal` that combines BOTH an optional caller-supplied signal AND a fixed
  timeout budget (`signal.py`'s own `CombinedSignal`, aborting when EITHER the caller's own signal
  aborts OR the budget elapses) -- a genuine user-driven cancellation CAN reach refresh through that
  caller-supplied half, contrary to "not user-driven." The OBSERVABLE rule itself (refresh wraps
  every request-level failure UNIFORMLY, with no cancellation-specific carve-out, regardless of
  cause) remains correct and unchanged; only the STATED REASON for it was wrong, and must not be
  repeated as a rationale for reproducing this behavior.

**Cancellation mechanism -- disclosed mapping, not a new observable behavior.** Pinned Pi's own
`fetch` natively aborts its own underlying connection when the SAME `AbortSignal` object passed to
it fires (push-based, no polling). This project's own established `Abortable`/`RunSignal`
abstraction (Layer 09) is POLL-BASED BY CERTIFIED DESIGN and has no push/event mechanism -- exactly
the same already-disclosed constraint `abortable_sleep` (`PROV-010`) works within for timers. An
HTTP transport implementation MUST reproduce the same OBSERVABLE effect (an in-flight request that
is genuinely torn down, not merely "stopped being awaited while it keeps running unobserved in the
background," and whose caller sees an error promptly after the signal aborts, not only after the
request would have finished or timed out on its own) using this project's own poll-based
primitives -- e.g. running the request as a cancellable task and polling the signal at a short,
fixed interval, the same idiom `abortable_sleep` already establishes for a different primitive.
This is a disclosed, narrow language/architecture mapping (poll-based cancellation reproducing a
push-based primitive's observable effect), not new behavior invented for this contract, and MUST
NOT be confused with `Models`-level `raceWithAbortSignal`'s own, materially DIFFERENT and NARROWER
behavior (`PROV-013`, deferred, out of scope for this row): pinned Pi's own `raceWithAbortSignal`
(`packages/ai/src/utils/abort.ts:17-50`) does NOT cancel the underlying operation at all -- it only
stops WAITING for it while continuing to observe the abandoned promise in the background, a
narrower guarantee this row's own transport-level cancellation must not be conflated with.

### Injectable HTTP transport (implementation mechanics, owner-approved)

Per the owner's own Pass-2 scope decision, `httpx` is approved as the Python implementation
mechanism for every network call in this row, subject to these constraints, none of which are
optional:

- the language-neutral contract above describes HTTP behavior (status codes, body shapes, header
  content-type, cancellation semantics), never `httpx`-specific behavior;
- provider/auth code depends on an INJECTABLE transport seam -- a concrete `httpx`-backed
  implementation is one conforming implementation of that seam, never the only one a caller can
  supply;
- every test in the committed suite uses a deterministic fake/scripted transport; no test performs
  a live network call or depends on a real `auth.openai.com` response;
- no live secret (a real Codex access/refresh token, a real device/authorization code) appears
  anywhere in the committed test suite -- synthetic fixtures only, matching `PROV-011`'s own
  established constraint;
- `httpx`'s own request/response/client types do not appear in any shared, language-neutral type
  (the transport seam's own request/response shapes are this project's own minimal types, not
  `httpx.Request`/`httpx.Response` re-exported);
- cancellation and timeout map through this project's own existing `Abortable`/`RunSignal` contract
  (see above), never becoming `httpx`-defined timeout/cancellation semantics a caller must learn
  separately.

The local OAuth callback HTTP server (browser flow, step 3 above) is a SEPARATE concern from the
outbound-request transport seam above -- it is an inbound listener, not a client, and Pi's own
equivalent uses Node's raw `http` module directly with no injectable-transport abstraction of its
own; a Python implementation MAY use `httpx`, the standard library, or any other mechanism for this
inbound listener, subject to the same testability constraint (no test binds a real, non-loopback
port or depends on an externally-reachable server).

### `OAuthAuth` composite

```text
name             = "OpenAI (ChatGPT Plus/Pro)"
is_subscription  = true
login(interaction)      -> select method, then dispatch (above)
refresh(credential, signal) -> exchange credential.refresh via the refresh operation above, then
                                project through the ALREADY-ADOPTED `PROV-011` `credentials_from_token`
to_auth(credential)      -> the ALREADY-ADOPTED `PROV-011` `to_auth`, reused unchanged, not
                             reimplemented for this row
```

### Out of scope for this row (owner-confirmed, restated)

- Browser LAUNCHING itself (this row only emits the `auth_url` notification).
- The `codex-responses` LLM wire adapter.
- `PROV-013` generic `Models`-level orchestration (`resolveProviderAuth`, `Models.checkAuth`/
  `getAuth`/`login`/`logout`, provider-registry race semantics) -- this row's own `login`/`refresh`/
  `to_auth` are the PER-PROVIDER auth-method vocabulary `PROV-013`'s own deferred orchestration
  would eventually CONSUME, not that orchestration itself.
- A Codex CLI credential-file loader (reading an existing `~/.codex/...`-shaped file directly) --
  explicitly out of scope per the owner's own Pass-2 scope decision.

If implementation discovers that this contract cannot be expressed through the already-certified
`PROV-008`/`PROV-009`/`PROV-010` seams without changing their own observable semantics, that is an
`IMPLEMENTATION_DISCOVERED_CONTRACT_DEFECT` requiring owner governance before proceeding -- those
seams' own certified contracts are not silently widened to accommodate this row.
