// Result-domain representability witness using the locked serde_json implementation.
#[test]
fn exact_pi_details_cannot_enter_the_certified_result_value() {
    let actual = serde_json::from_str::<serde_json::Value>(
        r#"{"diff":"-1 a\n+1 \ud800","firstChangedLine":1,"patch":"--- f.txt\n+++ f.txt\n@@ -1,1 +1,1 @@\n-a\n+\ud800\n"}"#,
    );
    let error = actual.unwrap_err();
    println!("exact pinned Pi result rejected: {error}");
    assert!(error.to_string().contains("unexpected end of hex escape"));
}

#[test]
fn controls_for_genuinely_scalar_results() {
    for json in [r#"{"diff":"\ufffd"}"#, r#"{"diff":"\ud83d\ude00"}"#] {
        assert!(serde_json::from_str::<serde_json::Value>(json).is_ok());
    }
}
