"""WP-13.2 canonical scenarios (conformance/agent/builtin-mutation/, builtin-mutation-scenario.schema.json).

    python make_scenarios.py <cases.json> <authority.json> <queue_authority.json> <out dir>

Two sources, neither of them a binding:
  * corpus-*.yaml -- mechanically converted from the pinned-Pi authority run (edit_authority.mjs over cases.json):
    every edit/write/prepare case becomes one case with its own fixture file, and the expectation is the authority's
    result text, final file bytes and details, verbatim;
  * the rest are hand-authored from pinned Pi's write.ts/edit.ts/file-mutation-queue.ts control flow and the
    WP-13.2 contract's templates (spec/tools.md WP-13.2); every queue scenario cites the queue-authority trace
    (queue_authority.mjs) whose ordering it asserts.
Strings are emitted with an explicit escaping (\\uXXXX for BMP, \\UXXXXXXXX for astral, never a surrogate pair),
which YAML 1.1 and 1.2 parsers read identically.
"""
import base64
import json
import sys
from pathlib import Path

PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTH = "minion-agent-docs spec/tools.md WP-13.2 (minion-agent#49); pinned Pi write.ts/edit.ts/file-mutation-queue.ts"
CAUSE = {"not_found": "no such file or directory", "permission_denied": "permission denied",
         "not_directory": "not a directory", "is_directory": "is a directory", "invalid": "invalid path",
         "not_supported": "not supported by this provider", "unknown": "unknown filesystem error"}
ABORTED = "Operation aborted"


# ---------------------------------------------------------------- emitter
def q(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif 0x20 <= o < 0x7F:
            out.append(ch)
        elif o == 0x0A:
            out.append("\\n")
        elif o == 0x09:
            out.append("\\t")
        elif o <= 0xFFFF:
            out.append("\\u%04X" % o)
        else:
            out.append("\\U%08X" % o)
    out.append('"')
    return "".join(out)


def emit(v, ind=0):
    pad = "  " * ind
    if isinstance(v, dict):
        if not v:
            return "{}"
        lines = []
        for k, x in v.items():
            if isinstance(x, (dict, list)) and x:
                lines.append(f"{pad}{k}:\n{emit(x, ind + 1)}")
            else:
                lines.append(f"{pad}{k}: {emit(x, ind + 1)}")
        return "\n".join(lines)
    if isinstance(v, list):
        if not v:
            return "[]"
        lines = []
        for x in v:
            if isinstance(x, dict) and x:
                body = emit(x, ind + 1).split("\n")
                lines.append(f"{pad}- {body[0].lstrip()}")
                lines.extend(body[1:])
            elif isinstance(x, list) and x:
                lines.append(f"{pad}-\n{emit(x, ind + 1)}")
            else:
                lines.append(f"{pad}- {emit(x, ind + 1)}")
        return "\n".join(lines)
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, int):
        return str(v)
    return q(v)


def doc(name, requirements, witnesses, notes, body, authority=AUTH):
    return {"name": name, "family": "agent", "authority": authority, "pi_revision": PI,
            "requirements": requirements, "witnesses": witnesses, "notes": notes, "builtin_mutation": body}


def file(path, text):
    return {"path": path, "file": {"text": text}}


def err(text):
    return {"is_error": True, "text": text, "details": {}}


def ok(text):
    return {"is_error": False, "text": text}


# ---------------------------------------------------------------- hand-authored: cases
def hand_authored():
    docs = []
    W = "Successfully wrote {} bytes to {}"
    docs.append(doc(
        "builtin-write-creates-parents-overwrites-and-reports-utf16-length",
        ["TOOL-029", "TOOL-032"], ["write_success_parents_overwrite_utf16_length"],
        "write inside the queue: registration (canonical_path, falling back to absolute_path on not_found), then in "
        "the lock absolute_path (L13-WP132-R001), create_dir(lexical parent, recursive), write_file. The count is "
        "content's UTF-16 length (Pi's content.length, a known misnomer reproduced verbatim); details {}.",
        {"fixture": [file("f.txt", "old contents\n")], "cases": [
            {"id": "creates-missing-parents", "tool": "write",
             "arguments": {"path": "sub/deep/new.txt", "content": "hello\n"},
             "expect": {**ok(W.format(6, "sub/deep/new.txt")), "details": {},
                        "fs_calls": ["canonical_path sub/deep/new.txt", "absolute_path sub/deep/new.txt",
                                     "absolute_path sub/deep/new.txt", "create_dir sub/deep",
                                     "write_file sub/deep/new.txt"],
                        "files_after": [{"path": "sub/deep/new.txt", "text": "hello\n"}]}},
            {"id": "overwrites-existing", "tool": "write", "arguments": {"path": "f.txt", "content": "new"},
             "expect": {**ok(W.format(3, "f.txt")), "details": {},
                        "fs_calls": ["canonical_path f.txt", "absolute_path f.txt", "create_dir .", "write_file f.txt"],
                        "files_after": [{"path": "f.txt", "text": "new"}]}},
            {"id": "utf16-length-not-byte-length", "tool": "write",
             "arguments": {"path": "u.txt", "content": "é\U0001F600"},
             "expect": {**ok(W.format(3, "u.txt")), "details": {},
                        "files_after": [{"path": "u.txt", "base64": base64.b64encode("é\U0001F600".encode()).decode()}]}},
            {"id": "empty-content", "tool": "write", "arguments": {"path": "e.txt", "content": ""},
             "expect": {**ok(W.format(0, "e.txt")), "details": {}, "files_after": [{"path": "e.txt", "text": ""}]}},
            {"id": "unpaired-surrogate-written-as-replacement-character", "tool": "write",
             "unpaired_surrogate_arguments": True,
             "arguments": {"path": "s.txt", "content": "a\ud800b"},
             "expect": {**ok(W.format(3, "s.txt")), "details": {},
                        "files_after": [{"path": "s.txt", "base64": base64.b64encode(b"a\xef\xbf\xbdb").decode()}]}},
        ]}))

    docs.append(doc(
        "builtin-write-error-sites",
        ["TOOL-029", "TOOL-032", "TOOL-039", "TOOL-026"], ["write_error_sites_r010b_vocabulary"],
        "Every write failure site with its L13-WP132-O1 wrapper and the closed R010-B cause phrase; details {}. "
        "A registration failure happens before the lock; the failing operation owns the site.",
        {"fixture": [file("f.txt", "original\n"), file("notes.txt", "a file, not a directory\n")],
         "provider": {"canonical_path": [{"path": "locked.txt", "error": "permission_denied"},
                                         {"path": "notes.txt/child.md", "error": "not_directory"}],
                      "absolute_path": [{"path": "bad-fallback.txt", "error": "invalid"},
                                        {"path": "./f.txt", "error": "unknown"}],
                      "create_dir": [{"path": "notes.txt", "error": "not_directory"},
                                     {"path": "denied", "error": "permission_denied"}],
                      "write_file": [{"path": "ro.txt", "error": "permission_denied"},
                                     {"path": "full.txt", "error": "unknown"}]},
         "cases": [
            {"id": "registration-canonical-path-fails", "tool": "write",
             "arguments": {"path": "locked.txt", "content": "x"},
             "expect": {**err(f"Cannot resolve locked.txt: {CAUSE['permission_denied']}"),
                        "fs_calls": ["canonical_path locked.txt"],
                        "files_after": [{"path": "locked.txt", "absent": True}]}},
            {"id": "registration-fallback-absolute-path-fails", "tool": "write",
             "arguments": {"path": "bad-fallback.txt", "content": "x"},
             "expect": {**err(f"Cannot resolve bad-fallback.txt: {CAUSE['invalid']}"),
                        "fs_calls": ["canonical_path bad-fallback.txt", "absolute_path bad-fallback.txt"]}},
            {"id": "in-lock-absolute-path-fails", "tool": "write", "arguments": {"path": "./f.txt", "content": "x"},
             "expect": {**err(f"Cannot resolve ./f.txt: {CAUSE['unknown']}"),
                        "fs_calls": ["canonical_path ./f.txt", "absolute_path ./f.txt"],
                        "files_after": [{"path": "f.txt", "text": "original\n"}]}},
            {"id": "not-directory-key-fallback-then-parent-fails", "tool": "write",
             "arguments": {"path": "notes.txt/child.md", "content": "x"},
             "expect": {**err(f"Cannot create parent directory of notes.txt/child.md: {CAUSE['not_directory']}"),
                        "fs_calls": ["canonical_path notes.txt/child.md", "absolute_path notes.txt/child.md",
                                     "absolute_path notes.txt/child.md", "create_dir notes.txt"]}},
            {"id": "parent-create-fails", "tool": "write", "arguments": {"path": "denied/x.txt", "content": "x"},
             "expect": {**err(f"Cannot create parent directory of denied/x.txt: {CAUSE['permission_denied']}"),
                        "fs_calls": ["canonical_path denied/x.txt", "absolute_path denied/x.txt",
                                     "absolute_path denied/x.txt", "create_dir denied"]}},
            {"id": "write-fails-permission", "tool": "write", "arguments": {"path": "ro.txt", "content": "x"},
             "expect": {**err(f"Cannot write ro.txt: {CAUSE['permission_denied']}"),
                        "fs_calls": ["canonical_path ro.txt", "absolute_path ro.txt", "absolute_path ro.txt",
                                     "create_dir .", "write_file ro.txt"]}},
            {"id": "write-fails-unknown", "tool": "write", "arguments": {"path": "full.txt", "content": "x"},
             "expect": err(f"Cannot write full.txt: {CAUSE['unknown']}")},
            {"id": "malformed-file-url-rejected-before-ctx-fs", "tool": "write",
             "arguments": {"path": "file:///%ZZ", "content": "x"},
             "expect": {**err("Cannot access file:///%ZZ: invalid path"), "fs_calls": []}},
        ]}))

    E = "Successfully replaced {} block(s) in {}."
    docs.append(doc(
        "builtin-edit-error-sites",
        ["TOOL-030", "TOOL-032", "TOOL-039", "TOOL-026", "EXEC-009"], ["edit_error_sites_r010b_vocabulary"],
        "edit's sites: empty edits (validateEditInput, before the path pipeline), the R002-A rejection, the access "
        "site (EXEC-009 check_read_write) keeping Pi's frame 'Could not edit file: <path>. <cause>.', the read "
        "site, the write site, and a diagnostic that leaves the file untouched; details {} for every error.",
        {"fixture": [file("f.txt", "alpha\nbeta\n"), file("denied.txt", "alpha\n"), file("unreadable.txt", "alpha\n"),
                     file("ro.txt", "alpha\n"), file("odd.txt", "alpha\n")],
         "provider": {"check_read_write": [{"path": "denied.txt", "error": "permission_denied"},
                                           {"path": "odd.txt", "error": "unknown"}],
                      "read_binary_file": [{"path": "unreadable.txt", "error": "is_directory"}],
                      "write_file": [{"path": "ro.txt", "error": "permission_denied"}]},
         "cases": [
            {"id": "empty-edits", "tool": "edit", "arguments": {"path": "f.txt", "edits": []},
             "expect": {**err("Edit tool input is invalid. edits must contain at least one replacement."),
                        "fs_calls": []}},
            {"id": "malformed-file-url", "tool": "edit",
             "arguments": {"path": "file:///%ZZ", "edits": [{"oldText": "a", "newText": "b"}]},
             "expect": {**err("Cannot access file:///%ZZ: invalid path"), "fs_calls": []}},
            {"id": "missing-file-access-site", "tool": "edit",
             "arguments": {"path": "missing.txt", "edits": [{"oldText": "a", "newText": "b"}]},
             "expect": {**err(f"Could not edit file: missing.txt. {CAUSE['not_found']}."),
                        "fs_calls": ["canonical_path missing.txt", "absolute_path missing.txt",
                                     "check_read_write missing.txt"],
                        "files_after": [{"path": "missing.txt", "absent": True}]}},
            {"id": "access-denied", "tool": "edit",
             "arguments": {"path": "denied.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(f"Could not edit file: denied.txt. {CAUSE['permission_denied']}."),
                        "fs_calls": ["canonical_path denied.txt", "check_read_write denied.txt"],
                        "files_after": [{"path": "denied.txt", "text": "alpha\n"}]}},
            {"id": "access-unknown", "tool": "edit",
             "arguments": {"path": "odd.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": err(f"Could not edit file: odd.txt. {CAUSE['unknown']}.")},
            {"id": "read-fails", "tool": "edit",
             "arguments": {"path": "unreadable.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(f"Cannot read unreadable.txt: {CAUSE['is_directory']}"),
                        "fs_calls": ["canonical_path unreadable.txt", "check_read_write unreadable.txt",
                                     "read_binary_file unreadable.txt"]}},
            {"id": "write-fails", "tool": "edit",
             "arguments": {"path": "ro.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(f"Cannot write ro.txt: {CAUSE['permission_denied']}"),
                        "fs_calls": ["canonical_path ro.txt", "check_read_write ro.txt", "read_binary_file ro.txt",
                                     "write_file ro.txt"],
                        "files_after": [{"path": "ro.txt", "text": "alpha\n"}]}},
            {"id": "diagnostic-never-writes", "tool": "edit",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "gamma", "newText": "G"}]},
             "expect": {**err("Could not find the exact text in f.txt. The old text must match exactly including all "
                              "whitespace and newlines."),
                        "fs_calls": ["canonical_path f.txt", "check_read_write f.txt", "read_binary_file f.txt"],
                        "files_after": [{"path": "f.txt", "text": "alpha\nbeta\n"}]}},
            {"id": "success-call-sequence", "tool": "edit",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "beta", "newText": "BETA"}]},
             "expect": {**ok(E.format(1, "f.txt")),
                        "fs_calls": ["canonical_path f.txt", "check_read_write f.txt", "read_binary_file f.txt",
                                     "write_file f.txt"],
                        "files_after": [{"path": "f.txt", "text": "alpha\nBETA\n"}]}},
        ]}))

    docs.append(doc(
        "builtin-edit-provider-without-exec-009-uses-disclosed-fallback",
        ["TOOL-030", "TOOL-039", "EXEC-009"], ["edit_fallback_without_exec_009"],
        "FALLBACK (spec/execution.md section 13.5; owner-disclosed, never Pi-equivalent): check_read_write answers "
        "not_supported, so the access stage asks check_readable; a readable-but-unwritable file then fails at the "
        "WRITE site, not the access site.",
        {"fixture": [file("f.txt", "alpha\n"), file("denied.txt", "alpha\n"), file("ro.txt", "alpha\n")],
         "provider": {"without_exec_009": True,
                      "check_readable": [{"path": "denied.txt", "error": "permission_denied"}],
                      "write_file": [{"path": "ro.txt", "error": "permission_denied"}]},
         "cases": [
            {"id": "check-readable-fails-at-access-site", "tool": "edit",
             "arguments": {"path": "denied.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(f"Could not edit file: denied.txt. {CAUSE['permission_denied']}."),
                        "fs_calls": ["canonical_path denied.txt", "check_read_write denied.txt",
                                     "check_readable denied.txt"]}},
            {"id": "unwritable-fails-at-write-site", "tool": "edit",
             "arguments": {"path": "ro.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(f"Cannot write ro.txt: {CAUSE['permission_denied']}"),
                        "fs_calls": ["canonical_path ro.txt", "check_read_write ro.txt", "check_readable ro.txt",
                                     "read_binary_file ro.txt", "write_file ro.txt"]}},
            {"id": "success", "tool": "edit",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**ok(E.format(1, "f.txt")), "files_after": [{"path": "f.txt", "text": "A\n"}]}},
        ]}))

    docs.append(doc(
        "builtin-edit-provider-without-exec-009-or-exec-008-skips-access",
        ["TOOL-030", "EXEC-009"], ["edit_fallback_without_exec_009"],
        "FALLBACK with check_readable unsupported too: the access stage is skipped; the read and write sites answer.",
        {"fixture": [file("f.txt", "alpha\n")], "provider": {"without_exec_009": True, "without_exec_008": True},
         "cases": [
            {"id": "access-skipped", "tool": "edit",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**ok(E.format(1, "f.txt")),
                        "fs_calls": ["canonical_path f.txt", "check_read_write f.txt", "check_readable f.txt",
                                     "read_binary_file f.txt", "write_file f.txt"],
                        "files_after": [{"path": "f.txt", "text": "A\n"}]}},
        ]}))

    docs.append(doc(
        "builtin-write-cancellation-checkpoints",
        ["TOOL-029", "TOOL-033"], ["write_cancellation_checkpoints"],
        "No abort listener while the lock is held; the signal is checked after registration+wait, after create_dir "
        "and after write_file (an abort during the in-lock absolute_path is observed after create_dir, where Pi "
        "observes an abort during mkdir, L13-WP132-R001). The tool has no check before the lock: an abort that "
        "arrives after Layer 06 preflight, during registration, still completes registration (fallback key "
        "included) and answers after acquiring the lock. A signal already aborted at the call's start is answered "
        "by Layer 06 preflight, which never invokes execute (L13-WP132-R004). A failing step's own error wins: Pi "
        "checks abort only after a step succeeds.",
        {"fixture": [file("f.txt", "original\n")],
         "provider": {"create_dir": [{"path": "denied", "error": "permission_denied"}],
                      "write_file": [{"path": "ro.txt", "error": "permission_denied"}]},
         "cases": [
            {"id": "pre-aborted-answered-by-layer06-preflight", "tool": "write", "signal": "pre_aborted",
             "arguments": {"path": "f.txt", "content": "x"},
             "expect": {**err(ABORTED), "fs_calls": [],
                        "files_after": [{"path": "f.txt", "text": "original\n"}]}},
            {"id": "abort-during-registration", "tool": "write", "abort_after": "canonical_path",
             "arguments": {"path": "f.txt", "content": "x"},
             "expect": {**err(ABORTED), "fs_calls": ["canonical_path f.txt"],
                        "files_after": [{"path": "f.txt", "text": "original\n"}]}},
            {"id": "abort-during-registration-still-derives-fallback-key", "tool": "write",
             "abort_after": "canonical_path", "arguments": {"path": "new.txt", "content": "x"},
             "expect": {**err(ABORTED), "fs_calls": ["canonical_path new.txt", "absolute_path new.txt"],
                        "files_after": [{"path": "new.txt", "absent": True}]}},
            {"id": "abort-during-in-lock-absolute-path-seen-after-create-dir", "tool": "write",
             "abort_after": "absolute_path", "arguments": {"path": "f.txt", "content": "x"},
             "expect": {**err(ABORTED), "fs_calls": ["canonical_path f.txt", "absolute_path f.txt", "create_dir ."],
                        "files_after": [{"path": "f.txt", "text": "original\n"}]}},
            {"id": "abort-during-create-dir", "tool": "write", "abort_after": "create_dir",
             "arguments": {"path": "f.txt", "content": "x"},
             "expect": {**err(ABORTED), "fs_calls": ["canonical_path f.txt", "absolute_path f.txt", "create_dir ."],
                        "files_after": [{"path": "f.txt", "text": "original\n"}]}},
            {"id": "abort-during-write-still-written", "tool": "write", "abort_after": "write_file",
             "arguments": {"path": "f.txt", "content": "x"},
             "expect": {**err(ABORTED), "files_after": [{"path": "f.txt", "text": "x"}]}},
            {"id": "create-dir-error-wins-over-abort", "tool": "write", "abort_after": "create_dir",
             "arguments": {"path": "denied/x.txt", "content": "x"},
             "expect": err(f"Cannot create parent directory of denied/x.txt: {CAUSE['permission_denied']}")},
            {"id": "write-error-wins-over-abort", "tool": "write", "abort_after": "write_file",
             "arguments": {"path": "ro.txt", "content": "x"},
             "expect": err(f"Cannot write ro.txt: {CAUSE['permission_denied']}")},
        ]}))

    docs.append(doc(
        "builtin-edit-cancellation-checkpoints",
        ["TOOL-030", "TOOL-033", "EXEC-009"], ["edit_cancellation_checkpoints"],
        "edit checks the signal after registration+wait, after the access stage (and BEFORE reporting an access "
        "failure, edit.ts's catch), after the read, after matching and after the write. A read or write failure's "
        "own error wins; an abort during the read wins over a later diagnostic.",
        {"fixture": [file("f.txt", "alpha\n"), file("denied.txt", "alpha\n"), file("unreadable.txt", "alpha\n"),
                     file("ro.txt", "alpha\n")],
         "provider": {"check_read_write": [{"path": "denied.txt", "error": "permission_denied"}],
                      "read_binary_file": [{"path": "unreadable.txt", "error": "permission_denied"}],
                      "write_file": [{"path": "ro.txt", "error": "permission_denied"}]},
         "cases": [
            {"id": "pre-aborted-answered-by-layer06-preflight", "tool": "edit", "signal": "pre_aborted",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(ABORTED), "fs_calls": [],
                        "files_after": [{"path": "f.txt", "text": "alpha\n"}]}},
            {"id": "abort-during-registration", "tool": "edit", "abort_after": "canonical_path",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(ABORTED), "fs_calls": ["canonical_path f.txt"],
                        "files_after": [{"path": "f.txt", "text": "alpha\n"}]}},
            {"id": "abort-during-access", "tool": "edit", "abort_after": "check_read_write",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(ABORTED), "fs_calls": ["canonical_path f.txt", "check_read_write f.txt"]}},
            {"id": "abort-wins-over-access-failure", "tool": "edit", "abort_after": "check_read_write",
             "arguments": {"path": "denied.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": err(ABORTED)},
            {"id": "abort-during-read", "tool": "edit", "abort_after": "read_binary_file",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(ABORTED),
                        "fs_calls": ["canonical_path f.txt", "check_read_write f.txt", "read_binary_file f.txt"],
                        "files_after": [{"path": "f.txt", "text": "alpha\n"}]}},
            {"id": "abort-during-read-wins-over-diagnostic", "tool": "edit", "abort_after": "read_binary_file",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "missing", "newText": "A"}]},
             "expect": err(ABORTED)},
            {"id": "read-error-wins-over-abort", "tool": "edit", "abort_after": "read_binary_file",
             "arguments": {"path": "unreadable.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": err(f"Cannot read unreadable.txt: {CAUSE['permission_denied']}")},
            {"id": "abort-during-write-still-written", "tool": "edit", "abort_after": "write_file",
             "arguments": {"path": "f.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": {**err(ABORTED), "files_after": [{"path": "f.txt", "text": "A\n"}]}},
            {"id": "write-error-wins-over-abort", "tool": "edit", "abort_after": "write_file",
             "arguments": {"path": "ro.txt", "edits": [{"oldText": "alpha", "newText": "A"}]},
             "expect": err(f"Cannot write ro.txt: {CAUSE['permission_denied']}")},
        ]}))
    return docs


# ---------------------------------------------------------------- hand-authored: queue
def queue_docs():
    docs = []
    W = "Successfully wrote {} bytes to {}"
    E = "Successfully replaced {} block(s) in {}."

    def qdoc(name, witness, notes, trace, fixture, queue, requirements=("TOOL-032",)):
        return doc(name, list(requirements), [witness],
                   f"{notes} Ordering authority: queue_authority.json scenario '{trace}' (pinned Pi "
                   "file-mutation-queue.ts, unmodified, Node 22.15.1).",
                   {"fixture": fixture, "queue": queue})

    docs.append(qdoc(
        "builtin-mutation-queue-same-target-registers-in-call-order",
        "queue_same_target_registration_in_call_order",
        "L13-WP132-R001: write A then write B for the same target (A 'f.txt', B './f.txt'), only A's provider calls "
        "delayed. B's canonical_path is not invoked before A's registration settles, and A's write completes before "
        "B's. Negative control: awaiting absolute_path before registration lets B register first.",
        "same-target-registration-in-call-order",
        [file("f.txt", "original\n")],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "f.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "./f.txt", "content": "B"}}],
         "gates": [{"id": "a-key", "operation": "canonical_path", "path": "f.txt"},
                   {"id": "a-abs", "operation": "absolute_path", "path": "f.txt"},
                   {"id": "a-write", "operation": "write_file", "path": "f.txt"}],
         "steps": [{"release": "a-key"}, {"release": "a-abs"}, {"release": "a-write"}],
         "expect": {"results": {"A": ok(W.format(1, "f.txt")), "B": ok(W.format(1, "./f.txt"))},
                    "order": [["p canonical_path f.txt #1 ok", "p canonical_path ./f.txt #1 start"],
                              ["p write_file f.txt #1 ok", "p absolute_path ./f.txt #1 start"],
                              ["p write_file f.txt #1 ok", "p write_file ./f.txt #1 start"]],
                    "logged": ["p write_file ./f.txt #1 ok"],
                    "files_after": [{"path": "f.txt", "text": "B"}]}}))

    docs.append(qdoc(
        "builtin-mutation-queue-fifo-of-three",
        "queue_fifo_per_key",
        "Three calls for one target run strictly in call order, each after the previous one's write settled.",
        "fifo-of-three-on-one-key",
        [file("f.txt", "original\n"), {"path": "sub", "dir": True}],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "f.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "./f.txt", "content": "B"}},
                   {"id": "C", "tool": "write", "arguments": {"path": "sub/../f.txt", "content": "C"}}],
         "gates": [{"id": "a-write", "operation": "write_file", "path": "f.txt"},
                   {"id": "b-write", "operation": "write_file", "path": "./f.txt"}],
         "steps": [{"release": "a-write"}, {"release": "b-write"}],
         "expect": {"results": {"A": ok(W.format(1, "f.txt")), "B": ok(W.format(1, "./f.txt")),
                                "C": ok(W.format(1, "sub/../f.txt"))},
                    "order": [["p write_file f.txt #1 ok", "p absolute_path ./f.txt #1 start"],
                              ["p write_file ./f.txt #1 ok", "p absolute_path sub/../f.txt #1 start"],
                              ["result A", "p write_file ./f.txt #1 ok"]],
                    "logged": ["result C"],
                    "files_after": [{"path": "f.txt", "text": "C"}]}}))

    docs.append(qdoc(
        "builtin-mutation-queue-different-keys-run-concurrently",
        "queue_different_keys_concurrent",
        "Only registration is global: B (another file) completes while A's write is still held.",
        "different-keys-run-concurrently",
        [],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "a.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "b.txt", "content": "B"}}],
         "gates": [{"id": "a-write", "operation": "write_file", "path": "a.txt"}],
         "steps": [{"release": "a-write"}],
         "expect": {"results": {"A": ok(W.format(1, "a.txt")), "B": ok(W.format(1, "b.txt"))},
                    "order": [["result B", "p write_file a.txt #1 ok"]],
                    "files_after": [{"path": "a.txt", "text": "A"}, {"path": "b.txt", "text": "B"}]}}))

    docs.append(qdoc(
        "builtin-mutation-queue-slow-failing-registration-then-proceeds",
        "queue_failed_registration_settles_then_releases",
        "L13-WP132-R003: A's canonical_path is pending and then fails. B (another key) does not begin its key lookup "
        "until A's failure settles, then proceeds; A leaves no entry, so C (A's own target) proceeds too. Negative "
        "controls: starting B early; leaving a lingering entry (C never settles).",
        "slow-failing-registration-delays-later-registration-until-it-settles",
        [file("a.txt", "a\n")],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "a.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "b.txt", "content": "B"}},
                   {"id": "C", "tool": "write", "arguments": {"path": "./a.txt", "content": "C"}}],
         "gates": [{"id": "a-key", "operation": "canonical_path", "path": "a.txt"}],
         "steps": [{"release": "a-key", "error": "permission_denied"}],
         "expect": {"results": {"A": err(f"Cannot resolve a.txt: {CAUSE['permission_denied']}"),
                                "B": ok(W.format(1, "b.txt")), "C": ok(W.format(1, "./a.txt"))},
                    "order": [["p canonical_path a.txt #1 permission_denied", "p canonical_path b.txt #1 start"]],
                    "never": ["p absolute_path a.txt #1 start", "p write_file a.txt #1 start"],
                    "files_after": [{"path": "a.txt", "text": "C"}, {"path": "b.txt", "text": "B"}]}}))

    docs.append(qdoc(
        "builtin-mutation-queue-released-after-error-and-after-abort",
        "queue_release_after_error_and_abort",
        "A's write fails (scripted); B is aborted while it waits in the queue (after Layer 06 preflight and its "
        "registration, L13-WP132-R004). There is no abort listener, so B keeps its place, answers 'Operation "
        "aborted' only after acquiring the lock, and never reaches its in-lock steps; each releases its entry, so C "
        "runs.",
        "same-key-waits-and-is-released-after-an-error",
        [file("f.txt", "original\n")],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "f.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "./f.txt", "content": "B"}},
                   {"id": "C", "tool": "write", "arguments": {"path": "sub/../f.txt", "content": "C"}}],
         "gates": [{"id": "a-write", "operation": "write_file", "path": "f.txt"}],
         "steps": [{"abort": "B"}, {"release": "a-write", "error": "permission_denied"}],
         "expect": {"results": {"A": err(f"Cannot write f.txt: {CAUSE['permission_denied']}"), "B": err(ABORTED),
                                "C": ok(W.format(1, "sub/../f.txt"))},
                    "order": [["p canonical_path ./f.txt #1 ok", "result A"],
                              # R004 (re-review, docs #188): B answers only after acquiring the lock, i.e. after A's
                              # held write settles -- kills a queue-wait abort listener that rejects B early.
                              ["p write_file f.txt #1 permission_denied", "result B"],
                              ["p write_file f.txt #1 permission_denied", "p absolute_path sub/../f.txt #1 start"]],
                    "never": ["p absolute_path ./f.txt #1 start"],
                    "files_after": [{"path": "f.txt", "text": "C"}]}},
        requirements=("TOOL-032", "TOOL-033")))
    docs[-1]["builtin_mutation"]["fixture"].append({"path": "sub", "dir": True})

    docs.append(qdoc(
        "builtin-mutation-queue-aborted-call-holds-lock-until-its-write-settles",
        "queue_abort_keeps_lock_until_inflight_settles",
        "A is aborted while its write_file is in flight: the lock is held until that write settles, then A answers "
        "'Operation aborted' and B starts. Negative control: releasing from an abort listener lets B start early.",
        "same-key-waits-and-is-released-after-an-error",
        [file("f.txt", "original\n")],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "f.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "./f.txt", "content": "B"}}],
         "gates": [{"id": "a-write", "operation": "write_file", "path": "f.txt"}],
         "steps": [{"abort": "A"}, {"release": "a-write"}],
         "expect": {"results": {"A": err(ABORTED), "B": ok(W.format(1, "./f.txt"))},
                    "order": [["p write_file f.txt #1 ok", "p absolute_path ./f.txt #1 start"],
                              ["p write_file f.txt #1 ok", "result A"]],
                    "files_after": [{"path": "f.txt", "text": "B"}]}},
        requirements=("TOOL-032", "TOOL-033")))

    docs.append(qdoc(
        "builtin-mutation-queue-symlink-and-target-share-one-queue",
        "queue_symlink_and_target_share",
        "The key is the canonical (symlink-resolved) path when the target exists: a write through a symlink and a "
        "write to its target serialize.",
        "symlink-and-target-share-one-queue",
        [file("target.txt", "original\n"), {"path": "link.txt", "symlink": "target.txt"}],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "link.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "target.txt", "content": "B"}}],
         "gates": [{"id": "a-write", "operation": "write_file", "path": "link.txt"}],
         "steps": [{"release": "a-write"}],
         "expect": {"results": {"A": ok(W.format(1, "link.txt")), "B": ok(W.format(1, "target.txt"))},
                    "order": [["p write_file link.txt #1 ok", "p absolute_path target.txt #1 start"]],
                    "files_after": [{"path": "target.txt", "text": "B"}]}}))

    docs.append(qdoc(
        "builtin-mutation-queue-providers-do-not-share-queues",
        "queue_scoped_per_provider",
        "MINION_ARCHITECTURAL_MAPPING: queues are keyed by (ctx.fs instance, key). Two provider instances over the "
        "same root, same target: B (provider q) completes while A (provider p) is held. Negative control: a global "
        "key without provider scoping serializes B behind A.",
        "different-keys-run-concurrently",
        [file("f.txt", "original\n")],
        {"providers": ["p", "q"],
         "calls": [{"id": "A", "tool": "write", "provider": "p", "arguments": {"path": "f.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "provider": "q", "arguments": {"path": "f.txt", "content": "B"}}],
         "gates": [{"id": "a-write", "provider": "p", "operation": "write_file", "path": "f.txt"}],
         "steps": [{"release": "a-write"}],
         "expect": {"results": {"A": ok(W.format(1, "f.txt")), "B": ok(W.format(1, "f.txt"))},
                    "order": [["result B", "p write_file f.txt #1 ok"]],
                    "files_after": [{"path": "f.txt", "text": "A"}]}}))

    docs.append(qdoc(
        "builtin-mutation-queue-not-found-fallback-key-serializes-creates",
        "queue_not_found_fallback_key",
        "A not-yet-existing target keys by its lexical absolute path (canonical_path not_found): two creates of the "
        "same new file serialize.",
        "enoent-fallback-key-serializes-creates",
        [],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "new.txt", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "./new.txt", "content": "B"}}],
         "gates": [{"id": "a-write", "operation": "write_file", "path": "new.txt"}],
         "steps": [{"release": "a-write"}],
         "expect": {"results": {"A": ok(W.format(1, "new.txt")), "B": ok(W.format(1, "./new.txt"))},
                    "order": [["p canonical_path new.txt #1 not_found", "p absolute_path new.txt #1 start"],
                              ["p write_file new.txt #1 ok", "p absolute_path ./new.txt #2 start"]],
                    "files_after": [{"path": "new.txt", "text": "B"}]}}))

    docs.append(qdoc(
        "builtin-mutation-queue-not-directory-fallback-key",
        "queue_not_directory_fallback_key",
        "Key derivation falls back on not_directory too ('notes.txt/child.md' under a regular file) -- NOT Layer 12's "
        "resolve(), whose fallback set omits not_directory (minion-agent#78). Both calls register, serialize on the "
        "fallback key, and fail at their own parent-create site. Negative control: a resolve()-based key fails "
        "registration ('Cannot resolve ...') instead.",
        "enotdir-fallback-key-serializes",
        [file("notes.txt", "a file\n")],
        {"calls": [{"id": "A", "tool": "write", "arguments": {"path": "notes.txt/child.md", "content": "A"}},
                   {"id": "B", "tool": "write", "arguments": {"path": "./notes.txt/child.md", "content": "B"}}],
         "gates": [{"id": "a-mkdir", "operation": "create_dir", "path": "notes.txt"}],
         "steps": [{"release": "a-mkdir", "error": "not_directory"}],
         "expect": {"results": {"A": err(f"Cannot create parent directory of notes.txt/child.md: {CAUSE['not_directory']}"),
                                "B": err(f"Cannot create parent directory of ./notes.txt/child.md: {CAUSE['not_directory']}")},
                    "order": [["p create_dir notes.txt #1 not_directory", "p absolute_path ./notes.txt/child.md #2 start"]],
                    "logged": ["p canonical_path notes.txt/child.md #1 not_directory",
                               "p canonical_path ./notes.txt/child.md #1 not_directory"]}}))
    # B's own create_dir is not gated; answer it the same way (scripted, so the result is platform-independent).
    docs[-1]["builtin_mutation"]["provider"] = {
        "canonical_path": [{"path": "notes.txt/child.md", "error": "not_directory"},
                           {"path": "./notes.txt/child.md", "error": "not_directory"}]}
    docs[-1]["builtin_mutation"]["queue"]["gates"].append(
        {"id": "b-mkdir", "operation": "create_dir", "path": "notes.txt", "occurrence": 2})
    docs[-1]["builtin_mutation"]["queue"]["steps"].append({"release": "b-mkdir", "error": "not_directory"})

    docs.append(qdoc(
        "builtin-mutation-queue-write-and-edit-share-the-queue",
        "queue_shared_by_write_and_edit",
        "write and edit use ONE queue: a write issued while an edit of the same file holds the lock waits for it.",
        "same-target-registration-in-call-order",
        [file("f.txt", "alpha\n")],
        {"calls": [{"id": "A", "tool": "edit",
                    "arguments": {"path": "f.txt", "edits": [{"oldText": "alpha", "newText": "A"}]}},
                   {"id": "B", "tool": "write", "arguments": {"path": "./f.txt", "content": "B"}}],
         "gates": [{"id": "a-read", "operation": "read_binary_file", "path": "f.txt"}],
         "steps": [{"release": "a-read"}],
         "expect": {"results": {"A": ok(E.format(1, "f.txt")), "B": ok(W.format(1, "./f.txt"))},
                    "order": [["p write_file f.txt #1 ok", "p absolute_path ./f.txt #1 start"]],
                    "files_after": [{"path": "f.txt", "text": "B"}]}},
        requirements=("TOOL-032", "TOOL-030", "TOOL-029")))
    return docs


# ---------------------------------------------------------------- corpus
GROUPS = [("prepare", "prepare_arguments coercions (edit.ts prepareEditArguments) through the real Layer 06 pipeline"),
          ("write", "write: UTF-16 length and UTF-8 encoding of the written bytes"),
          ("curated", "edit: the curated rules of spec/tools.md WP-13.2 (matching, diagnostics, fuzzy, BOM, line endings, diff)"),
          ("random", "edit: seeded random differential breadth")]


def corpus_docs(cases, results):
    by = {r["id"]: r for r in results}
    grouped = {g: [] for g, _ in GROUPS}
    fuzzy = []
    for c in cases:
        r = by[c["id"]]
        surrogate = any(0xD800 <= ord(ch) <= 0xDFFF for ch in json.dumps(c, ensure_ascii=False))
        if c["kind"] == "fuzzy":
            fuzzy.append({"id": c["id"], "text": c["text"], "normalized": r["normalized"]})
            continue
        if c["kind"] == "write":
            case = {"id": c["id"], "tool": "write", "arguments": {"path": c["path"], "content": c["content"]},
                    "expect": {**ok(r["text"]), "details": {},
                               "files_after": [{"path": c["path"], "base64": r["written_b64"]}]}}
            group = "write"
        else:
            fixture = [{"path": "src/app.txt", "file": {"base64": c["file_b64"]}}]
            if c.get("prepare"):
                args = c["raw_args"]
                if not isinstance(args, dict):
                    # L13-WP132-R005: ToolCall arguments are object-valued at Layer 02/05, so a non-object raw value
                    # cannot enter the integration pipeline; it stays prepare-helper authority evidence only.
                    continue
                if not r["schema_valid"]:
                    expect = {"is_error": True, "argument_validation_failure": True, "fs_calls": []}
                else:
                    expect = edit_expect(r["result"], c)
                group = "prepare"
            else:
                args = c["args"]
                expect = edit_expect(r, c)
                group = "random" if c["id"].startswith("random-") else "curated"
            case = {"id": c["id"], "tool": "edit", "fixture": fixture, "arguments": args, "expect": expect}
        if surrogate:
            case["unpaired_surrogate_arguments"] = True
            case = {k: case[k] for k in ["id", "tool", "fixture", "unpaired_surrogate_arguments", "arguments", "expect"]
                    if k in case}
        grouped[group].append(case)
    docs = []
    for g, title in GROUPS:
        items = grouped[g]
        chunks = [items[i:i + 60] for i in range(0, len(items), 60)] if g == "random" else [items]
        for n, chunk in enumerate(chunks, 1):
            suffix = f"-{n:02d}" if len(chunks) > 1 else ""
            docs.append(doc(
                "builtin-write-corpus" if g == "write" else f"builtin-edit-corpus-{g}{suffix}",
                ["TOOL-030", "TOOL-031"] if g != "write" else ["TOOL-029"],
                ["edit_write_pinned_pi_authority_corpus"],
                f"GENERATED from the pinned-Pi authority run (minion-agent-docs assurance/layers/data/13-wp132-evidence): "
                f"{title}. Expectations are pinned Pi's result text, final file bytes and details, verbatim. Do not "
                "edit by hand; regenerate with harness/make_scenarios.py.",
                {"cases": chunk},
                authority=f"pinned Pi {PI[:8]} edit-diff.ts/utils/text.ts + diff 8.0.4 under Node 22.15.1 (authority corpus)"))
    return docs, fuzzy


def edit_expect(r, c):
    if r["is_error"]:
        return {"is_error": True, "text": r["text"], "details": {},
                "files_after": [{"path": "src/app.txt", "base64": c["file_b64"]}]}
    d = r["details"]
    return {"is_error": False, "text": r["text"],
            "details": {"diff": d["diff"], "patch": d["patch"], "firstChangedLine": d["firstChangedLine"]},
            "files_after": [{"path": "src/app.txt", "base64": r["written_b64"]}]}


def main():
    cases_path, auth_path, _queue_path, out = sys.argv[1:5]
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    results = json.loads(Path(auth_path).read_text(encoding="utf-8"))["results"]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    corpus, fuzzy = corpus_docs(cases, results)
    written = []
    for d in hand_authored() + queue_docs() + corpus:
        text = emit(d) + "\n"
        (out / f"{d['name']}.yaml").write_bytes(text.encode("ascii"))
        written.append(d["name"])
    fixtures = out.parent / "fixtures" / "wp132-fuzzy-normalize"
    fixtures.mkdir(parents=True, exist_ok=True)
    (fixtures / "fuzzy_normalize.json").write_bytes(
        (json.dumps({"authority": f"pinned Pi {PI} edit-diff.ts normalizeForFuzzyMatch under Node 22.15.1 (ICU 76.1, Unicode 16.0)",
                     "cases": fuzzy}, ensure_ascii=True, indent=1) + "\n").encode("ascii"))
    print(f"{len(written)} scenario documents, {len(fuzzy)} fuzzy_normalize cases")


if __name__ == "__main__":
    main()
