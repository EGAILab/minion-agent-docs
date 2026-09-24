use std::cmp::Ordering;
use std::convert::TryFrom;
use std::ffi::CString;

use rust_icu_sys as sys;
use rust_icu_ucol::UCollator;
use serde_json::{json, Value};

fn sign(o: Ordering) -> i32 {
    match o {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

/// ICU root-locale full lowercase via the pinned ICU4C (u_strToLower, locale "").
fn icu_root_lower(s: &str) -> String {
    let src: Vec<u16> = s.encode_utf16().collect();
    let root = CString::new("").unwrap();
    let mut dest = vec![0u16; src.len() * 4 + 16];
    let mut status = sys::UErrorCode::U_ZERO_ERROR;
    let n = unsafe {
        sys::versioned_function!(u_strToLower)(
            dest.as_mut_ptr(),
            dest.len() as i32,
            src.as_ptr(),
            src.len() as i32,
            root.as_ptr(),
            &mut status,
        )
    };
    assert!(status == sys::UErrorCode::U_ZERO_ERROR, "u_strToLower failed: {:?}", status);
    String::from_utf16(&dest[..n as usize]).unwrap()
}

fn run(c: &UCollator, items: &[String]) -> Value {
    let cmp = |a: &str, b: &str| c.strcoll_utf8(a, b).expect("strcoll_utf8");
    let matrix: Vec<Vec<i32>> = items.iter().map(|a| items.iter().map(|b| sign(cmp(a, b))).collect()).collect();
    let mut idx: Vec<usize> = (0..items.len()).collect();
    idx.sort_by(|&i, &j| cmp(&items[i], &items[j]));
    json!({ "matrix": matrix, "stable_sorted_indices": idx })
}

fn main() {
    let path = std::env::args().nth(1).expect("corpus path");
    let d: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    let strings: Vec<String> = d["strings"].as_array().unwrap().iter().map(|s| s.as_str().unwrap().to_owned()).collect();

    let c = UCollator::try_from("en-001").expect("open en-001");
    c.set_attribute(sys::UColAttribute::UCOL_STRENGTH, sys::UColAttributeValue::UCOL_TERTIARY).unwrap();
    c.set_attribute(sys::UColAttribute::UCOL_NUMERIC_COLLATION, sys::UColAttributeValue::UCOL_OFF).unwrap();
    c.set_attribute(sys::UColAttribute::UCOL_CASE_FIRST, sys::UColAttributeValue::UCOL_OFF).unwrap();
    c.set_attribute(sys::UColAttribute::UCOL_NORMALIZATION_MODE, sys::UColAttributeValue::UCOL_ON).unwrap();
    let attr = |a| c.get_attribute(a).map(|v| v as i32).unwrap();
    let mut v: sys::UVersionInfo = [0; 4];
    unsafe { sys::versioned_function!(u_getVersion)(v.as_mut_ptr()) };

    let lower: Vec<String> = strings.iter().map(|s| icu_root_lower(s)).collect();
    println!("{}", json!({
        "engine": "rust_icu_ucol",
        "icu_version_runtime": format!("{}.{}.{}.{}", v[0], v[1], v[2], v[3]),
        "attributes": {
            "STRENGTH": attr(sys::UColAttribute::UCOL_STRENGTH),
            "NUMERIC_COLLATION": attr(sys::UColAttribute::UCOL_NUMERIC_COLLATION),
            "CASE_FIRST": attr(sys::UColAttribute::UCOL_CASE_FIRST),
            "ALTERNATE_HANDLING": attr(sys::UColAttribute::UCOL_ALTERNATE_HANDLING),
            "NORMALIZATION_MODE": attr(sys::UColAttribute::UCOL_NORMALIZATION_MODE),
        },
        "icu_root_lower": lower.iter().map(|s| s.chars().map(|ch| ch as u32).collect::<Vec<u32>>()).collect::<Vec<_>>(),
        "raw": run(&c, &strings),
        "icu_lowercased": run(&c, &lower),
    }));
}
