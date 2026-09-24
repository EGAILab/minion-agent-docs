//! Replays a Photon API call trace (recorded by the Python wasmtime host while running Pi's image
//! pipeline over the R005-A corpus) against the pinned photon_rs_bg.wasm through the Rust
//! `wasmtime` crate, and byte-compares every result, trap and console.error with the recording.
//! Host glue mirrors photon-node 0.3.4's photon_rs.js call for call.

use wasmtime::error::{bail, format_err as anyhow, Context, Result};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use wasmtime::*;

const PINNED_WASM_SHA256: &str = "10468181565c56004c867f3a4af96f89a0ef5a63a72f2b5fb12c1f1992a3615c";
const STACK_TEXT: &str = "Error\n    at <minion photon host>"; // same text as the Python host

#[derive(Default)]
struct State {
    console_errors: Vec<String>,
    unexpected_imports: Vec<String>,
    last_throw: Option<String>,
    // Caller::get_export resolves only memories and functions, so the host keeps the table.
    externref_table: Option<Table>,
}

fn sha(data: &[u8]) -> String {
    hex::encode(Sha256::digest(data))
}

fn export_func(caller: &mut Caller<'_, State>, name: &str) -> Result<Func> {
    caller.get_export(name).and_then(|e| e.into_func()).ok_or_else(|| anyhow!("missing export {name}"))
}

fn memory(caller: &mut Caller<'_, State>) -> Result<Memory> {
    caller.get_export("memory").and_then(|e| e.into_memory()).ok_or_else(|| anyhow!("missing memory"))
}

fn read_string(caller: &mut Caller<'_, State>, ptr: i32, len: i32) -> Result<String> {
    let mem = memory(caller)?;
    let mut buf = vec![0u8; len as u32 as usize];
    mem.read(&mut *caller, ptr as u32 as usize, &mut buf)?;
    Ok(String::from_utf8_lossy(&buf).into_owned())
}

fn set_label(caller: &mut Caller<'_, State>, table: &Table, idx: u64, label: &'static str) -> Result<()> {
    let r = ExternRef::new(&mut *caller, label)?;
    table.set(&mut *caller, idx, Ref::Extern(Some(r)))
}

fn define_import(linker: &mut Linker<State>, imp: &ImportType<'_>) -> Result<()> {
    let (module, name) = (imp.module().to_string(), imp.name().to_string());
    let ExternType::Func(ty) = imp.ty() else { bail!("unexpected non-function import {name}") };
    let n = name.clone();
    linker.func_new(&module, &name, ty, move |mut caller, args, results| {
        match n.as_str() {
            "__wbindgen_init_externref_table" => {
                let table = caller.data().externref_table.ok_or_else(|| anyhow!("missing externref table"))?;
                let offset = table.grow(&mut caller, 4, Ref::Extern(None))?;
                set_label(&mut caller, &table, 0, "undefined")?;
                set_label(&mut caller, &table, offset, "undefined")?;
                set_label(&mut caller, &table, offset + 1, "null")?;
                set_label(&mut caller, &table, offset + 2, "true")?;
                set_label(&mut caller, &table, offset + 3, "false")?;
                Ok(())
            }
            "__wbindgen_throw" => {
                let msg = read_string(&mut caller, args[0].unwrap_i32(), args[1].unwrap_i32())?;
                caller.data_mut().last_throw = Some(msg.clone());
                Err(anyhow!(msg))
            }
            "__wbg_new_abda76e883ba8a5f" => {
                results[0] = Val::ExternRef(Some(ExternRef::new(&mut caller, "Error")?));
                Ok(())
            }
            "__wbg_stack_658279fe44541cf6" => {
                let retptr = args[0].unwrap_i32() as u32 as usize;
                let text = STACK_TEXT.as_bytes();
                let malloc = export_func(&mut caller, "__wbindgen_malloc")?;
                let mut out = [Val::I32(0)];
                malloc.call(&mut caller, &[Val::I32(text.len() as i32), Val::I32(1)], &mut out)?;
                let ptr = out[0].unwrap_i32() as u32;
                let mem = memory(&mut caller)?;
                mem.write(&mut caller, ptr as usize, text)?;
                mem.write(&mut caller, retptr + 4, &(text.len() as u32).to_le_bytes())?;
                mem.write(&mut caller, retptr, &ptr.to_le_bytes())?;
                Ok(())
            }
            "__wbg_error_f851667af71bcfc6" => {
                let (ptr, len) = (args[0].unwrap_i32(), args[1].unwrap_i32());
                let msg = read_string(&mut caller, ptr, len);
                let free = export_func(&mut caller, "__wbindgen_free")?;
                free.call(&mut caller, &[Val::I32(ptr), Val::I32(len), Val::I32(1)], &mut [])?;
                caller.data_mut().console_errors.push(msg?);
                Ok(())
            }
            "__wbindgen_memory" => {
                results[0] = Val::ExternRef(Some(ExternRef::new(&mut caller, "memory")?));
                Ok(())
            }
            other => {
                caller.data_mut().unexpected_imports.push(other.to_string());
                Err(anyhow!("UNEXPECTED_IMPORT {other}"))
            }
        }
    })?;
    Ok(())
}

/// One photon-node instance: a fresh store + instance, like one `require()` of the package.
struct Host {
    store: Store<State>,
    instance: Instance,
}

enum Arg {
    Bytes(Vec<u8>),
    Int(i32),
}

impl Host {
    fn new(engine: &Engine, module: &Module) -> Result<Self> {
        let mut linker = Linker::new(engine);
        for imp in module.imports() {
            define_import(&mut linker, &imp)?;
        }
        let mut store = Store::new(engine, State::default());
        let instance = linker.instantiate(&mut store, module)?;
        let table = instance.get_table(&mut store, "__wbindgen_export_2").context("externref table")?;
        store.data_mut().externref_table = Some(table);
        let mut host = Host { store, instance };
        host.raw("__wbindgen_start", &[])?;
        Ok(host)
    }

    fn raw(&mut self, name: &str, args: &[Val]) -> Result<Vec<Val>> {
        let f = self.instance.get_func(&mut self.store, name).ok_or_else(|| anyhow!("missing export {name}"))?;
        let mut out = vec![Val::I32(0); f.ty(&self.store).results().len()];
        f.call(&mut self.store, args, &mut out)?;
        Ok(out)
    }

    fn pass_array8(&mut self, data: &[u8]) -> Result<(i32, i32)> {
        let ptr = self.raw("__wbindgen_malloc", &[Val::I32(data.len() as i32), Val::I32(1)])?[0].unwrap_i32();
        let mem = self.instance.get_memory(&mut self.store, "memory").context("memory")?;
        mem.write(&mut self.store, ptr as u32 as usize, data)?;
        Ok((ptr, data.len() as i32))
    }

    fn take_array8(&mut self, pair: &[Val]) -> Result<Vec<u8>> {
        let (ptr, len) = (pair[0].unwrap_i32(), pair[1].unwrap_i32());
        let mem = self.instance.get_memory(&mut self.store, "memory").context("memory")?;
        let mut buf = vec![0u8; len as u32 as usize];
        mem.read(&self.store, ptr as u32 as usize, &mut buf)?;
        self.raw("__wbindgen_free", &[Val::I32(ptr), Val::I32(len), Val::I32(1)])?;
        Ok(buf)
    }

    fn bytes_op(&mut self, export: &str, args: &[Val]) -> Result<Value> {
        let pair = self.raw(export, args)?;
        let b = self.take_array8(&pair)?;
        Ok(json!({"sha256": sha(&b), "len": b.len()}))
    }

    fn handle_op(&mut self, export: &str, args: &[Val]) -> Result<Value> {
        Ok(json!(self.raw(export, args)?[0].unwrap_i32() as u32))
    }

    /// The photon_rs.js API surface Pi's image path uses. Returns the traced result shape.
    fn op(&mut self, op: &str, args: &[Arg]) -> Result<Value> {
        let int = |i: usize| match &args[i] {
            Arg::Int(v) => Ok(Val::I32(*v)),
            Arg::Bytes(_) => Err(anyhow!("{op}: arg {i} not int")),
        };
        let bytes = |i: usize| match &args[i] {
            Arg::Bytes(b) => Ok(b.clone()),
            Arg::Int(_) => Err(anyhow!("{op}: arg {i} not bytes")),
        };
        match op {
            "new_from_byteslice" => {
                let (p, l) = self.pass_array8(&bytes(0)?)?;
                self.handle_op("photonimage_new_from_byteslice", &[Val::I32(p), Val::I32(l)])
            }
            "new" => {
                let (p, l) = self.pass_array8(&bytes(0)?)?;
                self.handle_op("photonimage_new", &[Val::I32(p), Val::I32(l), int(1)?, int(2)?])
            }
            "get_width" => self.handle_op("photonimage_get_width", &[int(0)?]),
            "get_height" => self.handle_op("photonimage_get_height", &[int(0)?]),
            "get_raw_pixels" => self.bytes_op("photonimage_get_raw_pixels", &[int(0)?]),
            "get_bytes" => self.bytes_op("photonimage_get_bytes", &[int(0)?]),
            "get_bytes_jpeg" => self.bytes_op("photonimage_get_bytes_jpeg", &[int(0)?, int(1)?]),
            "resize" => self.handle_op("resize", &[int(0)?, int(1)?, int(2)?, int(3)?]),
            "fliph" | "flipv" => self.raw(op, &[int(0)?]).map(|_| Value::Null),
            "free" => self.raw("__wbg_photonimage_free", &[int(0)?, Val::I32(0)]).map(|_| Value::Null),
            other => bail!("untraceable op {other}"),
        }
    }
}

fn main() -> Result<()> {
    let argv: Vec<String> = std::env::args().collect();
    let (wasm_path, trace_dir) = (&argv[1], &argv[2]);
    let wasm = std::fs::read(wasm_path)?;
    if sha(&wasm) != PINNED_WASM_SHA256 {
        bail!("photon_rs_bg.wasm sha256 {} != pinned {PINNED_WASM_SHA256}", sha(&wasm));
    }
    let engine = Engine::default();
    let module = Module::new(&engine, &wasm)?;
    let trace: Vec<Value> = serde_json::from_slice(&std::fs::read(format!("{trace_dir}/trace.json"))?)?;
    let mut hosts: HashMap<i64, Host> = HashMap::new();
    let (mut compared, mut traps, mut mismatches) = (0usize, 0usize, Vec::new());
    for (i, ev) in trace.iter().enumerate() {
        let inst = ev["inst"].as_i64().context("inst")?;
        let op = ev["op"].as_str().context("op")?;
        if op == "instantiate" {
            hosts.insert(inst, Host::new(&engine, &module)?);
            continue;
        }
        let host = hosts.get_mut(&inst).context("unknown instance")?;
        let args = ev["args"]
            .as_array()
            .context("args")?
            .iter()
            .map(|a| -> Result<Arg> {
                Ok(match a.get("blob") {
                    Some(b) => Arg::Bytes(std::fs::read(format!("{trace_dir}/blobs/{}", b.as_str().context("blob")?))?),
                    None => Arg::Int(a.as_i64().context("int arg")? as i32),
                })
            })
            .collect::<Result<Vec<_>>>()?;
        let errors_before = host.store.data().console_errors.len();
        host.store.data_mut().last_throw = None;
        let mut got = json!({"inst": inst, "op": op, "args": ev["args"]});
        match host.op(op, &args) {
            Ok(v) => got["result"] = v,
            Err(_) => {
                traps += 1;
                got["trap"] = json!({"thrown": host.store.data().last_throw});
            }
        }
        got["console_errors"] = json!(host.store.data().console_errors[errors_before..]);
        compared += 1;
        if &got != ev {
            mismatches.push(format!("event {i}: recorded={ev} rust={got}"));
        }
    }
    let unexpected: Vec<String> = hosts.values().flat_map(|h| h.store.data().unexpected_imports.clone()).collect();
    println!(
        "rust replay: {} instances, {compared} calls compared, {traps} traps reproduced, unexpected imports: {unexpected:?}",
        hosts.len()
    );
    for m in mismatches.iter().take(20) {
        println!("  MISMATCH {m}");
    }
    let ok = mismatches.is_empty() && unexpected.is_empty();
    let verdict = if ok { "IDENTICAL to recorded trace".to_string() } else { format!("{} mismatch(es)", mismatches.len()) };
    println!("VERDICT rust: {verdict}");
    std::process::exit(if ok { 0 } else { 1 });
}
