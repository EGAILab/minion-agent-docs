import functools, json, sys
import icu

corpus = json.load(open(sys.argv[1], encoding="utf-8"))["enumeration_order"]
c = icu.Collator.createInstance(icu.Locale("en-001"))
A, V = icu.UCollAttribute, icu.UCollAttributeValue
c.setAttribute(A.STRENGTH, V.TERTIARY)            # Intl sensitivity: "variant"
c.setAttribute(A.NUMERIC_COLLATION, V.OFF)        # Intl numeric: false
c.setAttribute(A.CASE_FIRST, V.OFF)               # Intl caseFirst: "false"


def run(items):
    cmp = lambda a, b: int(c.compare(a, b))
    return {
        "matrix": [[cmp(a, b) for b in items] for a in items],
        "stable_sorted_indices": sorted(range(len(items)), key=functools.cmp_to_key(lambda i, j: cmp(items[i], items[j]))),
    }


lower = json.load(open(sys.argv[1], encoding="utf-8"))["lowercased_by_harness"]
print(json.dumps({
    "engine": "PyICU",
    "pyicu_version": icu.VERSION,
    "icu_version": icu.ICU_VERSION,
    "unicode_version": icu.UNICODE_VERSION,
    "actual_locale": str(c.getLocale(icu.ULocDataLocaleType.ACTUAL_LOCALE)),
    "attributes": {name: int(c.getAttribute(getattr(A, name))) for name in
                   ("STRENGTH", "NUMERIC_COLLATION", "CASE_FIRST", "ALTERNATE_HANDLING", "NORMALIZATION_MODE")},
    "raw": run(corpus),
    "lowercased_by_harness": run(lower),
    "lowercased_inputs": lower,
}, ensure_ascii=True))
