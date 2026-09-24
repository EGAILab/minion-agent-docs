use std::cmp::Ordering;
use std::convert::TryFrom;

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

fn run(c: &UCollator, items: &[String]) -> Value {
    let cmp = |a: &str, b: &str| c.strcoll_utf8(a, b).expect("strcoll_utf8");
    let matrix: Vec<Vec<i32>> = items
        .iter()
        .map(|a| items.iter().map(|b| sign(cmp(a, b))).collect())
        .collect();
    let mut idx: Vec<usize> = (0..items.len()).collect();
    idx.sort_by(|&i, &j| cmp(&items[i], &items[j])); // stable, like Array.prototype.sort
    json!({ "matrix": matrix, "stable_sorted_indices": idx })
}

fn strings(v: &Value, key: &str) -> Vec<String> {
    v[key].as_array().unwrap().iter().map(|s| s.as_str().unwrap().to_owned()).collect()
}

fn main() {
    let path = std::env::args().nth(1).expect("corpus path");
    let d: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    let raw = strings(&d, "enumeration_order");
    let lower = strings(&d, "lowercased_by_harness");

    let c = UCollator::try_from("en-001").expect("open en-001");
    c.set_attribute(sys::UColAttribute::UCOL_STRENGTH, sys::UColAttributeValue::UCOL_TERTIARY).unwrap();
    c.set_attribute(sys::UColAttribute::UCOL_NUMERIC_COLLATION, sys::UColAttributeValue::UCOL_OFF).unwrap();
    c.set_attribute(sys::UColAttribute::UCOL_CASE_FIRST, sys::UColAttributeValue::UCOL_OFF).unwrap();

    let attr = |a| c.get_attribute(a).map(|v| v as i32).unwrap();
    let mut v: sys::UVersionInfo = [0; 4];
    unsafe { sys::versioned_function!(u_getVersion)(v.as_mut_ptr()) };

    println!(
        "{}",
        json!({
            "engine": "rust_icu_ucol",
            "icu_version_runtime": format!("{}.{}.{}.{}", v[0], v[1], v[2], v[3]),
            "attributes": {
                "STRENGTH": attr(sys::UColAttribute::UCOL_STRENGTH),
                "NUMERIC_COLLATION": attr(sys::UColAttribute::UCOL_NUMERIC_COLLATION),
                "CASE_FIRST": attr(sys::UColAttribute::UCOL_CASE_FIRST),
                "ALTERNATE_HANDLING": attr(sys::UColAttribute::UCOL_ALTERNATE_HANDLING),
                "NORMALIZATION_MODE": attr(sys::UColAttribute::UCOL_NORMALIZATION_MODE),
            },
            "raw": run(&c, &raw),
            "lowercased_by_harness": run(&c, &lower),
        })
    );
}
