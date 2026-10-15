//! Characterization ONLY. No resolver replacement and no filesystem mutation.
use super::*;
use serde_json::{Value, json};
use std::os::windows::ffi::OsStringExt;

#[link(name = "kernel32")]
unsafe extern "system" {
    fn GetCurrentDirectoryW(size: u32, buffer: *mut u16) -> u32;
}

fn raw_cwd() -> Vec<u16> {
    let mut size = unsafe { GetCurrentDirectoryW(0, std::ptr::null_mut()) };
    loop {
        assert_ne!(size, 0, "raw cwd read failed");
        let mut buffer = vec![0; size as usize];
        let count = unsafe { GetCurrentDirectoryW(size, buffer.as_mut_ptr()) };
        assert_ne!(count, 0, "raw cwd read failed");
        if count < size {
            buffer.truncate(count as usize);
            return buffer;
        }
        size = count;
    }
}

fn mappings(path: &Path) -> Value {
    json!({
        "raw": native_units(path).code_units(),
        "provider": logical_provider_path(path).code_units(),
        "display": from_native(path).code_units(),
        "view_raw": native_view(&native_units(path)).code_units(),
        "actual_cwd_view": view_native_cwd_read(Ok(path.to_owned())).unwrap().code_units(),
    })
}

#[tokio::test]
#[ignore = "read-only CE-L12D012-02 child; explicit launcher only"]
async fn observe() {
    let payload: Value = serde_json::from_str(&env::var("CE02_INPUT").unwrap()).unwrap();
    let base: Vec<u16> = serde_json::from_value(payload["provider"].clone()).unwrap();
    let provider = PathBuf::from(std::ffi::OsString::from_wide(&base));
    let fs = super::super::LocalFileSystem::new(&provider);
    let inputs: Vec<Vec<u16>> = serde_json::from_value(payload["inputs"].clone()).unwrap();
    let mut rows = Vec::new();
    for input in inputs {
        let input = FsPath::from_code_units(input);
        rows.push(json!({
            "input": input.code_units(),
            "absolute_path": fs.absolute_path(&input, None).await.unwrap().code_units(),
            "logical": resolve(&provider, &input).unwrap().code_units(),
        }));
    }
    let cwd = env::current_dir().unwrap();
    let entries = ["E:", "A:", "X:"].map(|device| {
        let raw = env::var_os(format!("={device}"));
        json!({"device":device,"raw":raw.as_ref().map(|v|native_units(Path::new(v)).code_units().to_vec()),
            "selected_view":inherited_drive_view(&device.encode_utf16().collect::<Vec<_>>()).map(|v|v.code_units().to_vec())})
    });
    let injected: Vec<Vec<u16>> = serde_json::from_value(payload["mapping_inputs"].clone()).unwrap();
    let injected: Vec<_> = injected.into_iter().map(|u| mappings(Path::new(&std::ffi::OsString::from_wide(&u)))).collect();
    println!("CE02 {}", json!({"raw_getcwd":raw_cwd(),"cwd":mappings(&cwd),"entries":entries,"rows":rows,"injected_mappings":injected}));
}
