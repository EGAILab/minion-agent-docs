use minion_agent::{Runtime, llm::{StopReason, ToolCall}, tools::{PreparedValue, ToolDefinition, ToolExecutionOptions, ToolExecutionRequest, execute_tool_calls}};
use serde_json::json;

#[tokio::main(flavor = "current_thread")]
async fn main() {
    let node = PreparedValue::from(json!({"k": 1}));
    if std::env::args().any(|arg| arg == "cycle") {
        node.set("self", node.clone());
    }
    let cloned = node.structured_clone();
    if let Some(child) = cloned.get("self") {
        assert!(cloned.as_object().unwrap().same_identity(child.as_object().unwrap()));
        assert!(!cloned.as_object().unwrap().same_identity(node.as_object().unwrap()));
    }
    println!("structured_clone PASS; entering real execution/validation");
    let runtime = Runtime::new();
    runtime.tools().register_for_scope(None, ToolDefinition::new(
        "probe", "probe", serde_json::from_value(json!({"type": "object", "properties": {}})).unwrap(), "probe",
        |_request: ToolExecutionRequest| { println!("EXECUTE reached"); Box::pin(async { Ok(minion_agent::tools::AgentToolResult { content: vec![], details: json!({}).into(), usage: None, added_tool_names: None, terminate: None }) }) },
    ).with_prepare_raw_arguments(move |_| Ok(node.clone()))).unwrap();
    let outcome = execute_tool_calls(&runtime.context(), &[ToolCall::new_raw("c", "probe", json!({}).into())], ToolExecutionOptions::new(StopReason::ToolUse, 0.0)).await;
    println!("execution outcome {:?}", outcome.is_ok());
}
