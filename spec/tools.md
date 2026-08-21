# Tool Semantics

Pipeline:

```text
prepare_arguments -> schema validation -> before hook -> execute -> after hook -> finalized result
```

Every thrown/rejected value crossing this Pi-compatible extension boundary becomes an error tool
result. After-hook failure replaces the prior result.

If assistant stop reason is `length`, execute no tool calls; every call becomes an error result.

Sequential contagion: global sequential or any sequential tool => whole batch sequential; otherwise
parallel is allowed.

Parallel execution-end events follow completion order; conversational tool-result messages preserve
source call order. Late updates after settlement are ignored.

Batch `terminate=true` only when every finalized result terminates. It suppresses only tool-driven
automatic continuation; normal prepare/stop/steering/follow-up remains eligible.

Tool definitions preserve constrained-sampling metadata where implemented.
