//! DISPOSABLE characterization probe for L12-D005 (#126); lives only in a scratch copy, never committed.
#![cfg(windows)]
use std::{path::Path, process::Command};

use minion_agent::execution::{FileSystem, LocalFileSystem};

fn user() -> String {
    std::env::var("USERNAME").unwrap()
}
fn icacls(p: &Path, args: &[&str]) {
    Command::new("icacls").arg(p).args(args).output().unwrap();
}
fn deny(p: &Path, rights: &str) {
    icacls(p, &["/deny", &format!("{}:({rights})", user())]);
}
fn undeny(p: &Path) {
    icacls(p, &["/remove:d", &user()]);
}
fn file(p: &Path) {
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    std::fs::write(p, "x").unwrap();
}
fn readonly(p: &Path) {
    let mut perm = std::fs::metadata(p).unwrap().permissions();
    perm.set_readonly(true);
    std::fs::set_permissions(p, perm).unwrap();
}
fn left(dir: &Path, base: &Path, out: &mut Vec<String>) {
    let mut names: Vec<_> = match std::fs::read_dir(dir) {
        Ok(r) => r.map(|e| e.unwrap().path()).collect(),
        Err(_) => return,
    };
    names.sort();
    for p in names {
        let rel = p.strip_prefix(base).unwrap().to_string_lossy().replace('\\', "/");
        let md = std::fs::symlink_metadata(&p).unwrap();
        if md.file_type().is_symlink() {
            out.push(rel + "@");
        } else if md.is_dir() {
            out.push(rel + "/");
            left(&p, base, out);
        } else {
            out.push(rel);
        }
    }
}

#[tokio::test]
async fn l12d005_probe() {
    let scratch = std::env::var("L12D005_SCRATCH").unwrap();
    type Setup = fn(&Path, &Path) -> (&'static str, bool, Vec<std::path::PathBuf>);
    let cases: Vec<(&str, Setup)> = vec![
        ("child-readonly-file", |c, _| { file(&c.join("t/sub/f")); readonly(&c.join("t/sub/f")); ("t", true, vec![]) }),
        ("target-readonly-file-recursive", |c, _| { file(&c.join("f")); readonly(&c.join("f")); ("f", true, vec![]) }),
        ("target-readonly-file-nonrecursive", |c, _| { file(&c.join("f")); readonly(&c.join("f")); ("f", false, vec![]) }),
        ("nested-readonly-files", |c, _| {
            for f in ["t/a", "t/s/b", "t/s/u/c", "t/z"] { file(&c.join(f)); readonly(&c.join(f)); }
            ("t", true, vec![])
        }),
        ("readonly-directory-attribute", |c, _| {
            file(&c.join("t/d/f")); Command::new("attrib").arg("+R").arg(c.join("t/d")).output().unwrap();
            ("t", true, vec![])
        }),
        ("chmod-denied-readonly-file", |c, _| { let f = c.join("t/f"); file(&f); readonly(&f); deny(&f, "WA"); ("t", true, vec![f]) }),
        ("retry-fails-readonly-file", |c, _| {
            let d = c.join("t"); let f = d.join("f"); file(&f); readonly(&f); deny(&f, "D"); deny(&d, "DC");
            ("t", true, vec![d, f])
        }),
        ("acl-denied-file", |c, _| {
            let d = c.join("t"); let f = d.join("f"); file(&f); deny(&f, "D"); deny(&d, "DC");
            ("t", true, vec![d, f])
        }),
        ("acl-denied-directory", |c, _| {
            let t = c.join("t"); let d = t.join("d"); std::fs::create_dir_all(&d).unwrap(); deny(&d, "D"); deny(&t, "DC");
            ("t", true, vec![t, d])
        }),
        ("acl-denied-top-level-file", |c, _| {
            let f = c.join("f"); file(&f); deny(&f, "D"); deny(c, "DC");
            ("f", true, vec![c.to_path_buf(), f])
        }),
    ];
    let mut lines = Vec::new();
    for (id, setup) in cases {
        let root = Path::new(&scratch).join(format!("l12d005-rs-{id}"));
        let _ = std::fs::remove_dir_all(&root);
        let cwd = root.join("cwd");
        let ext = root.join("external");
        std::fs::create_dir_all(&cwd).unwrap();
        std::fs::create_dir_all(&ext).unwrap();
        let (target, recursive, acl) = setup(&cwd, &ext);
        let fs = LocalFileSystem::new(&cwd);
        let r = fs.remove(target, recursive, false, None).await;
        let observed = match &r {
            Ok(()) => "ok".to_owned(),
            Err(e) => format!(
                "{:?} path={}",
                e.code,
                e.path.as_ref().map(|p| {
                    let s = p.to_string();
                    Path::new(&s).strip_prefix(&cwd).map(|x| x.to_string_lossy().replace('\\', "/")).unwrap_or(s)
                }).unwrap_or_default()
            ),
        };
        let mut l = Vec::new();
        left(&cwd, &cwd, &mut l);
        lines.push(format!("{id}: {observed} left={l:?}"));
        for p in acl {
            undeny(&p);
        }
    }
    let out = lines.join("\n");
    std::fs::write(format!("{scratch}/rust-win32.txt"), &out).unwrap();
    println!("{out}");
}
