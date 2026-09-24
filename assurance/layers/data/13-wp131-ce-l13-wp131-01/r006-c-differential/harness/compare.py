import json, sys
corpus, py, rs = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:4])
names = corpus["enumeration_order"]
lines, ok = [], True
def check(label, cond):
    global ok
    ok &= bool(cond); lines.append(f"{'PASS' if cond else 'FAIL'}  {label}")
check(f"PyICU version == 2.16.2 (got {py['pyicu_version']})", py["pyicu_version"] == "2.16.2")
check(f"PyICU runtime ICU == 78.3 (got {py['icu_version']})", py["icu_version"] == "78.3")
check(f"Rust runtime ICU == 78.3.0.0 (got {rs['icu_version_runtime']})", rs["icu_version_runtime"] == "78.3.0.0")
check(f"identical effective collator attributes {py['attributes']}", py["attributes"] == rs["attributes"])
for mode in ("raw", "lowercased_by_harness"):
    pm, rm = py[mode]["matrix"], rs[mode]["matrix"]
    diffs = [(i, j) for i in range(len(pm)) for j in range(len(pm)) if pm[i][j] != rm[i][j]]
    check(f"{mode}: all {len(pm)**2} ordered-pair comparisons identical ({len(diffs)} disagreements)", not diffs)
    for i, j in diffs[:20]: lines.append(f"      disagree {names[i]!a} vs {names[j]!a}: py={pm[i][j]} rust={rm[i][j]}")
    check(f"{mode}: stable sort order identical", py[mode]["stable_sorted_indices"] == rs[mode]["stable_sorted_indices"])
    lines.append(f"      {mode} order: " + ", ".join(ascii(names[k]) for k in py[mode]["stable_sorted_indices"]))
# Informational only: ICU 78.3 (lowercased, like Pi) vs this session's recorded Node 22.15.1 / ICU 76.1 order.
got = [corpus["enumeration_order"][k] for k in py["lowercased_by_harness"]["stable_sorted_indices"]]
norm = lambda xs: [x.replace("é", "é") for x in xs]
same = norm(got) == corpus["node_v22_15_1_icu_76_1_recorded_sorted_informational"]
lines.append(f"INFO  ICU 78.3 lowercased order {'matches' if same else 'DIFFERS from'} the recorded Node 22.15.1 / ICU 76.1 order (not a pass criterion)")
lines.append(f"VERDICT  {'PASS -- no differential disagreement' if ok else 'FAIL'}")
print("\n".join(lines)); sys.exit(0 if ok else 1)
