import json, sys
corpus, py, rs, node = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:5])
S = corpus["strings"]; n = len(S)
lines, ok = [], True
def check(label, cond):
    global ok
    ok &= bool(cond); lines.append(f"{'PASS' if cond else 'FAIL'}  {label}")
check(f"ICU runtime 78.3 in both (py {py['icu_version']}, rust {rs['icu_version_runtime']})",
      py["icu_version"] == "78.3" and rs["icu_version_runtime"] == "78.3.0.0")
check(f"PyICU 2.16.2 (got {py['pyicu_version']})", py["pyicu_version"] == "2.16.2")
check(f"NORMALIZATION_MODE=ON (17) in both, all attributes identical {py['attributes']}",
      py["attributes"] == rs["attributes"] and py["attributes"]["NORMALIZATION_MODE"] == 17)
lo = [i for i in range(n) if py["icu_root_lower"][i] != rs["icu_root_lower"][i]]
check(f"ICU root lowercase identical across engines for all {n} strings ({len(lo)} differ)", not lo)
for i in lo: lines.append(f"      lower differs {S[i]!a}: py={py['icu_root_lower'][i]} rust={rs['icu_root_lower'][i]}")
nl = [i for i in range(n) if py["icu_root_lower"][i] != node["to_lower_case"][i]]
lines.append(f"INFO  ICU 78.3 root lowercase vs Node {node['node']} (ICU {node['icu']}) toLowerCase: "
             f"{'identical for all ' + str(n) if not nl else str(len(nl)) + ' differ: ' + ', '.join(ascii(S[i]) for i in nl)}")
for mode in ("raw", "icu_lowercased"):
    pm, rm = py[mode]["matrix"], rs[mode]["matrix"]
    d = [(i, j) for i in range(n) for j in range(n) if pm[i][j] != rm[i][j]]
    check(f"{mode}: all {n*n} ordered-pair comparisons identical ({len(d)} disagreements)", not d)
    for i, j in d[:20]: lines.append(f"      disagree {S[i]!a} vs {S[j]!a}: py={pm[i][j]} rust={rm[i][j]}")
    check(f"{mode}: stable sort order identical", py[mode]["stable_sorted_indices"] == rs[mode]["stable_sorted_indices"])
pairs = corpus["extra_witnesses"]["non_fcd_canonical_pairs"]
for k in range(0, len(pairs), 2):
    i, j = S.index(pairs[k]), S.index(pairs[k + 1])
    check(f"canonically-equivalent {pairs[k]!a} vs {pairs[k+1]!a} compare 0 (lowercased mode)",
          py["icu_lowercased"]["matrix"][i][j] == 0 == rs["icu_lowercased"]["matrix"][i][j])
same = py["icu_lowercased"]["stable_sorted_indices"] == node["pi_comparator_stable_sorted_indices"]
lines.append(f"INFO  ICU 78.3 end-to-end order (lowercase + collate, normalization ON) "
             f"{'MATCHES' if same else 'DIFFERS from'} Pi's comparator on Node {node['node']} / ICU {node['icu']} for all {n} strings (informational)")
lines.append("      order: " + ", ".join(ascii(S[k]) for k in py["icu_lowercased"]["stable_sorted_indices"]))
lines.append(f"VERDICT  {'PASS -- no differential disagreement' if ok else 'FAIL'}")
print("\n".join(lines)); sys.exit(0 if ok else 1)
