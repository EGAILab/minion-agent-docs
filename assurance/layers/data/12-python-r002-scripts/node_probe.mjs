import { fileURLToPath } from "node:url";
import { isAbsolute, resolve, join } from "node:path";
import { homedir } from "node:os";

const cwd = "C:\\cwd";

function resolvePath(cwd, path) {
  let normalized = path;
  if (normalized === "~") {
    normalized = homedir();
  } else if (normalized.startsWith("~/") || normalized.startsWith("~\\")) {
    normalized = join(homedir(), normalized.slice(2));
  } else if (normalized.startsWith("file://")) {
    try {
      normalized = fileURLToPath(normalized);
    } catch (e) {
      // fall through
    }
  }
  return isAbsolute(normalized) ? resolve(normalized) : resolve(cwd, normalized);
}

const cases = [
  "file:///C:/%ZZ","file:///C:/a%2Fb","file://%41/share","file:///%ZZ",
  "file://%zz-not-a-valid-escape","file:///C:/Users/test/file.txt",
  "file://localhost/C:/Users/test/file.txt","file:///c:/foo/bar",
  "file://192.168.1.5/share/file.txt","file:///C:/a%20b","file:///C:/a%252Fb",
  "file://%2541/share","file:///C:/%25ZZ","file:///","file://",
  "file:///C:/a%5Cb","file:///C:/a%5cb","file:///C:/a%2fb","file://[::1]/C:/foo",
  "file://./share/file","file:////host/share/file","file:///C:/%","file:///C:/%2",
  "file:///C%3A/foo","file:///C:foo","file:///foo","file:///C:/caf%C3%A9",
  "file:///C:/na%C3%AFve file.txt","file://%25/share","file://a%25b/share",
  "file://a.b.c/share","file://EXAMPLE.COM/share","file://a%23b/share",
  "file://a%40b/share","file:///C:/%e2%98","file:///C:/%ff%fe",
  "file://xn--bcher-kva/share","file://xn--/share","file://xn--zzzz/share",
  "file://xn--a/share","file://XN--BCHER-KVA/share","file://host\\share\\file",
  "file://HOST\\Share\\File","file:///C:\\Users\\test","file://xn--fa-hia.de/share",
  "file://xn--strae-oqa.de/share","file://xn--zca/share","file://xn--abc-ppe/share",
  "file://xn--abc-jdc/share",
  "relative/path.txt","/already/absolute.txt","~","~/x.txt",
  "file:///C:/","file:///C:","file://user_name.example/share",
  "file://-leadinghyphen.example/share","file://trailinghyphen-.example/share",
  "file://a..b/share","file://a.b.c.d.e.f/share","file://0.0.0.0/share",
  "file://256.256.256.256/share","file://1.2.3.4.5/share",
  "file://[::ffff:192.168.1.1]/share","file://%E2%80%8B/share",
  "not-a-file-url-at-all","file:not-even-slashes","file:/one/slash",
  "file://%E2%98%83.com/share","file://%F0%9F%92%A9.com/share",
];

for (const c of cases) {
  const r = resolvePath(cwd, c);
  console.log(c + "\t" + r);
}
