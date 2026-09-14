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

AuthInteraction{signal?, prompt(AuthPrompt)->string, notify(AuthEvent)->None}
ProviderAuthInteraction{signal, prompt(AuthPrompt)->string, notify(AuthEvent)->None}

ApiKeyAuth{name, resolve, login?, check?}
OAuthAuth{name, login, refresh, to_auth, is_subscription?, login_label?}
ProviderAuth{api_key?, oauth?}   # at least one of the two REQUIRED
```

`AuthPrompt` is the shape of a prompt shown to the user during login: `text`/`secret` are
free-text/masked entry (identical shape, differing only in display treatment); `select` presents a
fixed option set, and its OWN resolved value is the CHOSEN OPTION'S `id`, never its `label`;
`manual_code` is a fallback entry prompt used when an interactive callback (e.g. a local OAuth
server) is racing this same prompt -- the prompt's own `signal` is what that race cancels it
through, matching Pi's own doc comment naming exactly this pattern ("a `manual_code` prompt raced
against a callback server, aborted when the callback wins"). The racing mechanics themselves are a
concrete login flow's own concern (`PROV-012`), not part of this vocabulary.

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
time a caller has already normalized an absent top-level signal into a real one.

`ApiKeyAuth`/`OAuthAuth` are the per-provider auth-METHOD vocabulary a concrete provider registers.
`ApiKeyAuth.login` is optional (absent means ambient-only, no interactive setup); `check` is an
optional side-effect-free availability probe (used when `resolve` itself may perform request-time
work); `resolve` is required. `OAuthAuth.login`/`refresh`/`to_auth` are all required -- the
`refresh`/`to_auth` split lets an orchestration layer own the locked-refresh pattern: `refresh`
produces a credential, `to_auth` derives request auth from whatever credential ends up stored
(already-certified `PROV-011`'s own Codex `credentials_from_token`/`to_auth` is a concrete instance
of exactly this split). `ProviderAuth` MUST carry at least one of `api_key`/`oauth` -- a real,
enforced constraint, not merely a convention: even an ambient-credential or keyless provider
supplies `api_key` auth whose own `resolve()` reports configuration status.

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
