# LLM Semantics

Canonical serialization uses snake_case.

```text
TextBlock{text,text_signature?}
ThinkingBlock{thinking,thinking_signature?,redacted=false}
ImageBlock{mime_type,data|reference}
ToolCall{id,name,arguments,thought_signature?,namespace?}

UserMessage{role=user,content:string|[TextBlock|ImageBlock],timestamp}

AssistantMessage{
  role=assistant,content:[TextBlock|ThinkingBlock|ToolCall],api,provider,model,response_model?,
  response_id?,diagnostics?,usage,stop_reason,deferred?,error_message?,raw_stop_reason?,end_turn?,
  timestamp
}

ToolResultMessage{
  role=tool_result,tool_call_id,tool_name,content:[TextBlock|ImageBlock],details?,usage?,
  added_tool_names?,is_error,timestamp
}

DeferredHandle{provider,model_id,api,id,expires_at?,poll_after_ms?,data?}
DiagnosticError{message,name?,stack?,code?}
AssistantMessageDiagnostic{type,timestamp,error?,details?}
```

`StopReason = pending|stop|length|tool_use|error|aborted|deferred`.

`Usage` contains input/output/cache_read/cache_write/cache_write_1h?/reasoning?/total_tokens and
cost input/output/cache_read/cache_write/total.

Model compatibility identity is exactly `provider + api + model_id`.

Once a provider stream exists, expected provider/network/model/cancellation/runtime streaming
failures settle in-band. Public shape is `non-terminal* -> exactly one terminal -> EOF`; premature
raw EOF synthesizes one error terminal preserving partial assistant state; the public stream is then fused.

Responses replay uses content-owned opaque strings: retained same-model `thinking_signature` replays;
same-model unsigned thinking emits no reasoning replay item. `text_signature` preserves response
message identity/phase where supported.

The request carried into `stream()` gains one optional, additive field: the active run's own
cancellation signal (`AI-027`, Layer 09 -- `runtime/signal.py::RunSignal`, absent for every
request outside an Agent-driven run). This project has no real network transport yet, so `stream()`
itself never inspects or acts on it -- it is carried through to the adapter unexamined, exactly like
every other request field, and an adapter MAY poll it to represent `StopReason.ABORTED` in its own
returned stream, cooperatively, matching pinned Pi's own `streamFunction(model, context, {...config,
signal})`. Actual transport cancellation remains deferred to `PROV-004`. See `spec/agent.md`'s own
"Active abort propagation" section for the complete consumer/settlement matrix this signal serves.
