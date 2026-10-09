"""Apply the PLANNED L12-D005 Python correction to a scratch copy (contract-stage evidence only; the
implementation candidate will carry its own reviewed version). Usage: python planned_fix.py <copy>/minion-agent-python"""

import pathlib
import sys

target = pathlib.Path(sys.argv[1]) / "src/minion_agent/execution/filesystem.py"
text = target.read_text(encoding="utf-8")


def sub(old: str, new: str) -> None:
    global text
    assert text.count(old) == 1, old[:60]
    text = text.replace(old, new)


sub('''def _name_the_failing_path(function: Callable[..., Any], path: str, exc: BaseException) -> None:
    """`CE-L12-D001-01`: a recursive removal's failure names the path of the call that failed,
    as pinned Node's `rimraf` (v22.15.1 `lib/internal/fs/rimraf.js`, git blob
    `24bf3f46b878e711beadcdc8e1b08700d10aa3c5`) reports it -- an entry INSIDE the tree, not the
    removal's own target. `rmtree` passes that path here; its fd-relative calls name only a part."""
    if isinstance(exc, OSError):''', '''def _clear_readonly(path: str) -> bool:
    """`L12-D005`: pinned Pi's Windows deletion (libuv 1.49.2 `unlink`/`rmdir`) ignores the entry's own
    read-only attribute. True when that attribute was set and is now cleared -- or the entry vanished
    meanwhile -- so one retry of the failed deletion is due. Never follows a symlink."""
    if sys.platform != "win32":
        return False
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    if not st.st_file_attributes & _stat.FILE_ATTRIBUTE_READONLY:
        return False
    try:
        os.chmod(path, _stat.S_IWRITE, follow_symlinks=False)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def _delete_ignoring_readonly(function: Callable[[str], Any], path: str) -> None:
    try:
        function(path)
    except PermissionError:
        if not _clear_readonly(path):
            raise
        try:
            function(path)
        except FileNotFoundError:
            pass


def _name_the_failing_path(function: Callable[..., Any], path: str, exc: BaseException) -> None:
    """`CE-L12-D001-01`: a recursive removal's failure names the path of the call that failed,
    as pinned Node's `rimraf` (v22.15.1 `lib/internal/fs/rimraf.js`, git blob
    `24bf3f46b878e711beadcdc8e1b08700d10aa3c5`) reports it -- an entry INSIDE the tree, not the
    removal's own target. `rmtree` passes that path here; its fd-relative calls name only a part."""
    if (
        isinstance(exc, PermissionError)
        and getattr(function, "__name__", "") in ("unlink", "remove", "rmdir")
        and _clear_readonly(path)
    ):
        try:
            function(path)
            return
        except FileNotFoundError:
            return
        except OSError as retry:
            exc = retry
    if isinstance(exc, OSError):''')
sub('''        # symlink rather than recursing into its target.
        os.remove(path)
        return''', '''        # symlink rather than recursing into its target.
        _delete_ignoring_readonly(os.remove, path)
        return''')
sub('''            raise failure.error from None
        return
    os.remove(path)
''', '''            raise failure.error from None
        return
    _delete_ignoring_readonly(os.remove, path)
''')
if "\nimport sys\n" not in text:
    sub("\nimport shutil\n", "\nimport shutil\nimport sys\n")
target.write_text(text, encoding="utf-8")
print("planned fix applied")
