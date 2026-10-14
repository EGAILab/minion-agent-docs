//! Scoping-only observer. No path below is used for a filesystem operation.
use super::{FsPath, LocalFileSystem};
use std::{env, path::Path};

#[tokio::test]
async fn characterize() {
    let inputs: Vec<String> = serde_json::from_str(&env::var("L12D012_INPUTS").expect("inputs"))
        .expect("input list");
    let cwd = if cfg!(windows) { "C:\\x" } else { "/x" };
    let fs = LocalFileSystem::new(cwd);
    let mut rows = Vec::new();
    for input in inputs {
        let raw = FsPath::from(input.as_str());
        let actual = fs.absolute_path(raw.clone(), None).await.expect("absolute_path");
        let logical = super::path::resolve(Path::new(cwd), &raw);
        let scalar = super::filesystem::resolve_local_path(Path::new(cwd), &input);
        let draft_lossless: Option<FsPath> = None; // DRAFT_ENTRY
        rows.push(serde_json::json!({
            "input": input,
            "absolute_path": actual.code_units(),
            "logical": logical.code_units(),
            "native_scalar": scalar.to_string_lossy().encode_utf16().collect::<Vec<_>>(),
            "draft_lossless": draft_lossless.map(|v| v.code_units().to_vec())
        }));
    }
    // var_os uses the OS getter, not a runner-supplied expected value.
    let hidden = ["=E:", "=A:", "=X:"].map(|name| {
        (name, env::var_os(name).map(|v| v.to_string_lossy().into_owned()))
    });
    println!("SCOPING_JSON {}", serde_json::json!({
        "provider_cwd": cwd, "process_cwd": env::current_dir().expect("cwd"),
        "hidden_env": hidden, "rows": rows
    }));
}
