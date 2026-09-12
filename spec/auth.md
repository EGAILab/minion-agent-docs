# Auth Semantics (Layer 11 Pass 1 -- Auth Foundation)

This document covers the provider-neutral authentication seam: stored credentials, the
credential-store concurrency contract, refresh/ownership authority, and the two generic OAuth
primitives (PKCE, RFC 8628 device-code polling) Pass 1 builds. It does NOT cover any real
provider's own wire-protocol request/response encoding, or any concrete provider's own OAuth
network integration (Codex browser/device-code endpoints, token exchange, the local callback
server) -- those are later Layer 11 passes' own territory (`PROV-011`, `PROV-012`, deferred).

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

`expires` is a Unix-epoch-MILLISECONDS timestamp, not a duration and not seconds. `extra` is an
OPEN escape hatch (mirroring Pi's own `OAuthCredentials`'s `[key: string]: unknown` index
signature), not a closed field set: a provider-specific login flow attaches fields alongside the
three required ones (e.g. Codex's own `accountId`, `PROV-011`, deferred) without widening the core
shape every other provider shares. `CredentialInfo` never carries a secret field (`key`, `access`,
`refresh`, or `extra`) -- it exists only for account/status enumeration. `ModelAuth` is closed to
exactly `api_key`/`headers`/`base_url`: a value that cannot be expressed as one of those three is
provider CONFIG, not auth, and does not belong on this type. `source` on `AuthResult`/`AuthCheck`
is a human-readable status-UI label, not a machine-discriminated enum.

## AuthContext

The environment-access seam for auth resolution (`PROV-006`), injectable for tests:

```text
AuthContext.env(name) -> string|absent
AuthContext.file_exists(path) -> bool
```

`env(name)` returns the named environment value, or absent if the variable is unset OR set to a
blank/whitespace-only value -- a blank value is treated identically to an unset one, not as a
present-but-empty string. `file_exists(path)` reports whether `path` exists, expanding a leading
`~` to the user's home directory. The default, reference implementation reads real process
environment variables and the real filesystem, but reads NO provider-specific credential file (a
Codex CLI credential file, or any other single filesystem source) as part of this generic seam --
that would bake one provider's own storage location into the generic auth API, which this contract
deliberately avoids.

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

This is the property the whole contract exists to guarantee: a caller that needs to refresh a
rotating OAuth token can run its own check-and-refresh sequence entirely inside one `modify()`
callback and be certain no second concurrent caller for the SAME provider id can read the same
stale value and independently commit its own refresh too (see "Refresh authority" below). A bare
`read`/write pair with no `modify` primitive cannot make this guarantee at all.

An in-memory reference implementation proves IN-PROCESS serialization ONLY -- it makes no claim of
cross-process, filesystem, or distributed locking. A concrete backing store MAY provide those
stronger guarantees, but the generic `CredentialStore` contract does not require them, and nothing
in this document should be read as promising more than what the in-memory reference actually
proves.

`AuthOperationOptions.signal`, when supplied and already aborted (or aborted while `fn` is
in-flight, observed once `fn` resolves but before its result commits), causes the operation to
raise a cancellation error instead of completing -- checked before a queued mutation begins, and
again immediately after `fn` resolves.

## Refresh / ownership authority (`PROV-008`)

A stored credential OWNS the provider: this contract grants Minion authority to refresh/mutate an
OAuth credential only through the credential store's own serialized `modify()` -- never by
independently reading a token from some other source (a filesystem, a CLI's own credential file)
and rewriting it outside this seam. There is no silent fallback to an ambient/external credential
source after a failed refresh, or for a credential type without a matching handler.

A refresh triggers only when the stored OAuth credential is within a trigger window of expiring
(a default of five minutes). The actual refresh call happens INSIDE `modify()`'s own callback,
which re-checks expiry under the store's per-provider lock before calling the injected refresh
operation -- this double-checked pattern is what makes two concurrent callers that both observed
"expiring soon" via an outside-the-lock optimistic read refresh EXACTLY ONCE: the second caller's
own callback, running after the first's has already committed, observes the now-current
(no-longer-expiring) credential and returns it unchanged, without calling refresh again. If the
credential has been logged out (or replaced by a non-OAuth credential) by the time the lock is
acquired, the callback returns absent rather than attempting to refresh something that no longer
exists.

Two distinct failure classes are never conflated: the injected refresh operation itself failing
(the provider rejected the refresh) is a different, distinguishable error from the credential
store's own read/modify mechanism failing (a local storage problem) -- a caller can tell "the
provider rejected the refresh" apart from "the local credential store is broken."

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
  interval, that value governs outright (preferred over a fixed increment, since trusting only a
  client-tracked increment risks polling too early forever under clock drift). If the server
  supplies no interval, the current interval increases by a fixed 5 seconds (RFC 8628 section
  3.5's own default increment).
- **Failed**: a terminal protocol error. Polling stops immediately on this attempt -- it is never
  retried.
- **Complete**: the flow succeeded; the loop returns `poll`'s own value unchanged.

The default interval, when the caller supplies none, is 5 seconds (RFC 8628 section 3.2's own
default). Every interval is floored at a minimum of 1 second, regardless of what the caller or a
`slow_down` response requests.

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

## Deferred Codex-specific behavior (`PROV-011`, `PROV-012`)

Pinned Pi's Codex OAuth flow has pure (non-network) semantics this pass characterizes but does not
implement, to avoid losing track of them while real network integration is deferred:

- JWT payload decoding to extract `chatgpt_account_id` -- UNVERIFIED claim extraction only, never
  cryptographic signature validation. The extracted account id rides on `OAuthCredential.extra`
  above, not a separate wrapper type.
- Projecting a resolved OAuth access token to a bearer-style `ModelAuth` for provider-facing
  requests.
- Browser callback state validation, including a documented exception: a user pasting a bare
  authorization code (rather than a full callback URL) is a recognized quirk Pi's own flow
  accommodates, not an error condition.
- The browser/PKCE callback flow and device-code Codex endpoint integration themselves.

These are recorded as `deferred parity` in `pi-parity-manifest.yaml`, each with its own closure
criterion, not as `adopted` and not silently omitted. A future pass implementing real Codex
browser/device network integration must audit pinned Pi source for each of these before writing
any code, and must use only synthetic (never real-account) fixtures for any JWT-shaped test data,
per this project's own security constraint against live secrets in tests/fixtures.
