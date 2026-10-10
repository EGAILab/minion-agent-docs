"""L12-D006 planned Python correction, applied to a DISPOSABLE copy of minion-agent-python for the
contract-stage controls (the contract candidate itself carries no production change).

    python planned_fix.py <copy of minion-agent-python>
"""

import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
path = root / "src/minion_agent/execution/filesystem.py"
text = path.read_text(encoding="utf-8")


def patch(old: str, new: str, count: int = 1) -> None:
    global text
    assert text.count(old) == count, (old[:70], text.count(old))
    text = text.replace(old, new)


patch("import errno as _errno\n", "import errno as _errno\nimport functools\n")
patch("from typing import Any, Protocol\n", "from typing import Any, Concatenate, Protocol\n")

HELPERS = '''
_NUL = "\\x00"


def _nul_rejected(exc: ValueError, *arguments: object) -> bool:
    """`L12-D006`: a host rejection of a NUL-containing path argument -- CPython's `ValueError`
    "embedded null character / byte" -- and nothing else: an unrelated `ValueError` still raises."""
    return "embedded null" in str(exc) and any(
        isinstance(argument, str) and _NUL in argument for argument in arguments
    )


def _nul_failure(exc: ValueError, logical: str | None) -> FsError:
    """Pinned Node rejects the argument with `ERR_INVALID_ARG_VALUE`, which carries no `err.path`,
    so Pi's `toFileError` answers `unknown` with its LOGICAL fallback path (never projected)."""
    return FsError(FsErrorCode.UNKNOWN, str(exc), logical, exc)


def _contain_nul[**P, T](
    method: Callable[Concatenate[LocalFileSystem, str, P], Coroutine[Any, Any, Result[T, FsError]]],
) -> Callable[Concatenate[LocalFileSystem, str, P], Coroutine[Any, Any, Result[T, FsError]]]:
    """`L12-D006` (spec section 18): the native call whose path argument carries a NUL fails, at
    that call -- earlier calls of the same operation keep their effects (`write_file`'s parent
    creation) -- as `unknown` naming the operation's logical path (`rename_file`: the source)."""

    async def contained(
        self: LocalFileSystem, path: str, /, *args: P.args, **kwargs: P.kwargs
    ) -> Result[T, FsError]:
        try:
            return await method(self, path, *args, **kwargs)
        except ValueError as exc:
            # The RESOLVED path arguments (L12D006-C001): a `file://` URL's `%00` decodes to the NUL
            # the native call rejects, with no literal NUL in the caller's string. `rename_file` has
            # a second path, its destination; every other operation's other arguments are not paths.
            logical = resolve_local_path(self.cwd, path)
            resolved = [logical]
            if method.__name__ == "rename_file":
                destination = args[0] if args else kwargs.get("destination")
                if isinstance(destination, str):
                    resolved.append(resolve_local_path(self.cwd, destination))
            if not _nul_rejected(exc, *resolved):
                raise
            return Err(_nul_failure(exc, logical))

    functools.update_wrapper(contained, method)
    return contained

'''
patch("\nclass LocalFileSystem", HELPERS + "\nclass LocalFileSystem")

for name in ("read_text_file", "read_text_lines", "read_binary_file", "write_file", "append_file",
             "rename_file", "file_info", "list_dir", "list_dir_raw", "probe_dir_entry", "check_readable",
             "check_read_write", "canonical_path", "create_dir", "remove"):
    # The LocalFileSystem implementation (8-space indented after the class), not the Protocol stub.
    pattern = re.compile(rf"\n    async def {name}\(\n        self,", re.M)
    matches = list(pattern.finditer(text))
    impl = [m for m in matches if text.rfind("class LocalFileSystem", 0, m.start()) > text.rfind("class FileSystem", 0, m.start())]
    assert len(impl) == 1, (name, len(impl))
    m = impl[0]
    text = text[: m.start()] + f"\n    @_contain_nul\n    async def {name}(\n        self," + text[m.end():]

# canonical_path: Node's realpath validates its whole argument before any component walk.
patch(
    '''        resolved = resolve_local_path(self.cwd, path)
        native = native_path(resolved)
        try:
            real = await asyncio.to_thread(_realpath, native)''',
    '''        resolved = resolve_local_path(self.cwd, path)
        if _NUL in resolved:
            return Err(_nul_failure(ValueError("embedded null character in path"), resolved))
        native = native_path(resolved)
        try:
            real = await asyncio.to_thread(_realpath, native)''',
)
# Temp creation: no logical path for the directory; the would-be file path for the file.
patch(
    '''            path = await asyncio.to_thread(tempfile.mkdtemp, prefix=prefix)
        except OSError as exc:
            return Err(to_fs_error(exc))''',
    '''            path = await asyncio.to_thread(tempfile.mkdtemp, prefix=prefix)
        except OSError as exc:
            return Err(to_fs_error(exc))
        except ValueError as exc:
            if not _nul_rejected(exc, prefix):
                raise
            return Err(_nul_failure(exc, None))''',
)
patch(
    '''            await asyncio.to_thread(_write_file_sync, file_path, "")
        except OSError as exc:
            return Err(to_fs_error(exc, file_path))''',
    '''            await asyncio.to_thread(_write_file_sync, file_path, "")
        except OSError as exc:
            return Err(to_fs_error(exc, file_path))
        except ValueError as exc:
            if not _nul_rejected(exc, file_path):
                raise
            return Err(_nul_failure(exc, file_path))''',
)
path.write_text(text, encoding="utf-8")
print("planned fix applied")
