// Faithful copy of minion-agent-rust/crates/minion-agent/src/execution/filesystem.rs
// lines 534-589 (certified commit 2b309ee8, verified 429368c), for READ-ONLY differential
// oracle purposes. This scratch project does NOT modify minion-agent-rust/** in any way.

use std::collections::VecDeque;
use std::env;
use std::path::{Component, Path, PathBuf};
use url::Url;

pub(crate) fn resolve_local_path(cwd: &Path, raw: &str) -> PathBuf {
    let expanded = expand_path(raw);
    let path = if expanded.is_absolute() {
        expanded
    } else {
        cwd.join(expanded)
    };
    lexical_normalize(&path)
}

fn expand_path(raw: &str) -> PathBuf {
    if let Ok(url) = Url::parse(raw)
        && url.scheme() == "file"
        && let Ok(path) = url.to_file_path()
    {
        return path;
    }
    if raw == "~" || raw.starts_with("~/") || raw.starts_with("~\\") {
        let home = env::var_os("HOME").or_else(|| env::var_os("USERPROFILE"));
        if let Some(home) = home {
            let rest = raw.strip_prefix('~').unwrap_or(raw);
            return PathBuf::from(home).join(rest.trim_start_matches(['/', '\\']));
        }
    }
    PathBuf::from(raw)
}

fn lexical_normalize(path: &Path) -> PathBuf {
    let mut prefix = None;
    let mut root = false;
    let mut parts = VecDeque::new();
    for component in path.components() {
        match component {
            Component::Prefix(value) => prefix = Some(value.as_os_str().to_owned()),
            Component::RootDir => root = true,
            Component::CurDir => {}
            Component::ParentDir => {
                if parts.back().is_some_and(|part| part != "..") {
                    parts.pop_back();
                } else if !root {
                    parts.push_back("..".into());
                }
            }
            Component::Normal(value) => parts.push_back(value.to_owned()),
        }
    }
    let mut result = PathBuf::new();
    if let Some(prefix) = prefix {
        result.push(prefix);
    }
    if root {
        result.push(Path::new(std::path::MAIN_SEPARATOR_STR));
    }
    result.extend(parts);
    result
}

fn main() {
    let cwd = PathBuf::from(r"C:\cwd");
    let cases: Vec<&str> = vec![
        // R002 round-1/2 witnesses
        "file:///C:/%ZZ",
        "file:///C:/a%2Fb",
        "file://%41/share",
        "file:///%ZZ",
        "file://%zz-not-a-valid-escape",
        "file:///C:/Users/test/file.txt",
        "file://localhost/C:/Users/test/file.txt",
        "file:///c:/foo/bar",
        "file://192.168.1.5/share/file.txt",
        "file:///C:/a%20b",
        "file:///C:/a%252Fb",
        "file://%2541/share",
        "file:///C:/%25ZZ",
        "file:///",
        "file://",
        "file:///C:/a%5Cb",
        "file:///C:/a%5cb",
        "file:///C:/a%2fb",
        "file://[::1]/C:/foo",
        "file://./share/file",
        "file:////host/share/file",
        "file:///C:/%",
        "file:///C:/%2",
        "file:///C%3A/foo",
        "file:///C:foo",
        "file:///foo",
        "file:///C:/caf%C3%A9",
        "file:///C:/na%C3%AFve file.txt",
        "file://%25/share",
        "file://a%25b/share",
        "file://a.b.c/share",
        "file://EXAMPLE.COM/share",
        "file://a%23b/share",
        "file://a%40b/share",
        "file:///C:/%e2%98",
        "file:///C:/%ff%fe",
        // R002 round-3 witnesses (punycode/backslash)
        "file://xn--bcher-kva/share",
        "file://xn--/share",
        "file://xn--zzzz/share",
        "file://xn--a/share",
        "file://XN--BCHER-KVA/share",
        "file://host\\share\\file",
        "file://HOST\\Share\\File",
        "file:///C:\\Users\\test",
        // R002 round-5/6 witnesses (IDNA2003 gap, bidi/combining-mark)
        "file://xn--fa-hia.de/share",
        "file://xn--strae-oqa.de/share",
        "file://xn--zca/share",
        "file://xn--abc-ppe/share",
        "file://xn--abc-jdc/share",
        // Additional corpus per reset instructions
        "relative/path.txt",
        "/already/absolute.txt",
        "~",
        "~/x.txt",
        "file:///C:/",
        "file:///C:",
        "file://user_name.example/share",
        "file://-leadinghyphen.example/share",
        "file://trailinghyphen-.example/share",
        "file://a..b/share",
        "file://a.b.c.d.e.f/share",
        "file://0.0.0.0/share",
        "file://256.256.256.256/share",
        "file://1.2.3.4.5/share",
        "file://[::ffff:192.168.1.1]/share",
        "file://%E2%80%8B/share", // zero-width space host
        "not-a-file-url-at-all",
        "file:not-even-slashes",
        "file:/one/slash",
    ];

    for case in cases {
        let resolved = resolve_local_path(&cwd, case);
        println!("{case}\t{}", resolved.display());
    }
}
