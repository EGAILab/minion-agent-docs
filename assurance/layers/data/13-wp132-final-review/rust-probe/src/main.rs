fn main() {
    let text = format!("{{\"oldText\":\"a\",\"newText\":\"b\",\"extra\":{}}}", "9".repeat(5000));
    let parsed = serde_json::from_str::<serde_json::Value>(&text);
    println!("same valid edits JSON: {}", parsed.unwrap_err());
    println!("Infinity as serde_json::Number: {:?}", serde_json::Number::from_f64(f64::INFINITY));
    println!("negative zero as serde_json::Number: {:?}", serde_json::Number::from_f64(-0.0));
}
