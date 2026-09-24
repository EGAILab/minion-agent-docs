import functools, json, sys
import icu

strings = json.load(open(sys.argv[1], encoding="utf-8"))["strings"]
A, V = icu.UCollAttribute, icu.UCollAttributeValue
c = icu.Collator.createInstance(icu.Locale("en-001"))
c.setAttribute(A.STRENGTH, V.TERTIARY)
c.setAttribute(A.NUMERIC_COLLATION, V.OFF)
c.setAttribute(A.CASE_FIRST, V.OFF)
c.setAttribute(A.NORMALIZATION_MODE, V.ON)
root = icu.Locale.getRoot()
lower = [str(icu.UnicodeString(s).toLower(root)) for s in strings]


def run(items):
    cmp = lambda a, b: int(c.compare(a, b))
    return {"matrix": [[cmp(a, b) for b in items] for a in items],
            "stable_sorted_indices": sorted(range(len(items)), key=functools.cmp_to_key(lambda i, j: cmp(items[i], items[j])))}


print(json.dumps({
    "engine": "PyICU", "pyicu_version": icu.VERSION, "icu_version": icu.ICU_VERSION,
    "root_locale_name": root.getName(),
    "attributes": {n: int(c.getAttribute(getattr(A, n))) for n in
                   ("STRENGTH", "NUMERIC_COLLATION", "CASE_FIRST", "ALTERNATE_HANDLING", "NORMALIZATION_MODE")},
    "icu_root_lower": [[ord(ch) for ch in s] for s in lower],
    "raw": run(strings), "icu_lowercased": run(lower),
}, ensure_ascii=True))
