# Target-Model Message Transformation

Mandatory stage:

```text
session projection -> AgentMessage-to-Message -> target-model transform -> provider encoder
```

Rules:

1. null/undefined legacy content -> empty content list first.
2. unsupported user image -> `(image omitted: model does not support images)`.
3. unsupported tool-result image -> `(tool image omitted: model does not support images)`.
4. adjacent equivalent placeholders are deduplicated.
5. same model + signed thinking -> retain, even empty.
6. same model + unsigned non-empty thinking -> retain.
7. same model + unsigned empty thinking -> remove.
8. different model + non-redacted non-empty thinking -> ordinary text, signature discarded.
9. different model + non-redacted empty thinking -> remove.
10. different model + redacted thinking -> omit.
11. cross-model text loses `text_signature`.
12. cross-model tool call loses `thought_signature`.
13. normalize foreign tool-call IDs for target API and rewrite matching tool-result IDs consistently.
14. unresolved tool call before later user/assistant or end-of-history -> synthetic error result
    with text `No result provided`.
15. historical assistant `error|aborted` messages are excluded from provider replay.

Conformance runners MUST invoke the real library path; they may not implement these rules.
