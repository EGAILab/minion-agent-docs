import { fileURLToPath } from "node:url";
const cases = [
  "file://xn--n3h/share", "file://xn--ls8h/share",
  "file://xn--lzg/share", "file://xn--59g/share",
  "file://xn--a/share",
  "file://xn--0y0c/share",
  "file://xn--zva/share",
  "file://xn--abc-ppe/share", "file://xn--abc-jdc/share",
  "file://xn---bbk/share",
  "file://xn--/share", "file://xn--a-/share", "file://xn--zzzz/share",
  "file://xn---abc-/share", "file://xn--abc--/share",
  "file://xn--e-xbb/share",
  "file://xn--ll-0ea/share", "file://xn--aa-0ea/share",
  "file://xn--11b6iy14e/share", "file://xn--a-ugn/share",
  "file://xn--a-4ba/share", "file://xn--a-vca/share",
  "file://xn--a-0gn/share", "file://xn--a-jv3s/share",
  "file://xn--fa-hia/share", "file://xn--bcher-kva/share", "file://xn--zca/share",
];
for (const c of cases) {
  try {
    console.log(c + "\t" + JSON.stringify(fileURLToPath(c, {windows: true})));
  } catch (e) {
    console.log(c + "\tERROR: " + e.message);
  }
}
