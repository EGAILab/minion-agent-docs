"""Python host for the pinned @silvia-odwyer/photon-node 0.3.4 photon_rs_bg.wasm.

Executes the SAME WASM bytes Pi runs under Node, via wasmtime, and mirrors the call glue in
photon-node's own photon_rs.js (the CommonJS entry Pi loads) call for call. Imports that Pi's image
path should never reach are stubs that trap with their own name, so any unexpected path fails
loudly instead of silently diverging.
"""

from __future__ import annotations

import functools
import hashlib
from pathlib import Path

import wasmtime

PINNED_WASM_SHA256 = "10468181565c56004c867f3a4af96f89a0ef5a63a72f2b5fb12c1f1992a3615c"
LANCZOS3 = 5  # photon_rs.js: SamplingFilter = { Nearest:1, Triangle:2, CatmullRom:3, Gaussian:4, Lanczos3:5 }


class PhotonTrap(Exception):
    """A trap or thrown error inside Photon: the host equivalent of the JS exception Pi catches."""


class _Sentinel:
    def __init__(self, label: str) -> None:
        self.label = label

    def __repr__(self) -> str:
        return f"<js {self.label}>"


UNDEFINED, NULL, TRUE, FALSE = (_Sentinel(x) for x in ("undefined", "null", "true", "false"))


class Tracer:
    """Records every Photon API call (instance, args, outputs, traps, console errors) so an
    independent host (the Rust wasmtime replay) can re-execute and byte-compare each one."""

    def __init__(self, blob_dir: str) -> None:
        self.blob_dir = Path(blob_dir)
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []
        self.next_instance = 0

    def blob(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        path = self.blob_dir / digest
        if not path.exists():
            path.write_bytes(data)
        return digest


def _desc(value):
    if isinstance(value, (bytes, bytearray)):
        return {"sha256": hashlib.sha256(value).hexdigest(), "len": len(value)}
    return value


def _traced(method):
    @functools.wraps(method)
    def wrapper(self, *args):
        tracer = self.tracer
        if tracer is None:
            return method(self, *args)
        ev = {"inst": self.instance_id, "op": method.__name__,
              "args": [{"blob": tracer.blob(a)} if isinstance(a, (bytes, bytearray)) else a for a in args]}
        errors_before, self.last_throw = len(self.console_errors), None
        tracer.events.append(ev)
        try:
            result = method(self, *args)
        except PhotonTrap:
            ev["trap"] = {"thrown": self.last_throw}
            raise
        else:
            ev["result"] = _desc(result)
        finally:
            ev["console_errors"] = self.console_errors[errors_before:]
        return result
    return wrapper


class PhotonHost:
    tracer: Tracer | None = None

    @staticmethod
    def compile(wasm_bytes: bytes) -> tuple[wasmtime.Engine, wasmtime.Module]:
        digest = hashlib.sha256(wasm_bytes).hexdigest()
        if digest != PINNED_WASM_SHA256:
            raise RuntimeError(f"photon_rs_bg.wasm sha256 {digest} != pinned {PINNED_WASM_SHA256}")
        engine = wasmtime.Engine()
        return engine, wasmtime.Module(engine, wasm_bytes)

    def __init__(self, compiled: tuple[wasmtime.Engine, wasmtime.Module]) -> None:
        """One fresh instance (and store), like one `require()` of photon-node."""
        self.engine, self.module = compiled
        self.store = wasmtime.Store(self.engine)
        self.console_errors: list[str] = []
        self.unexpected_imports: list[str] = []
        self.last_throw: str | None = None
        self.instance_id = None
        if self.tracer is not None:
            self.instance_id = self.tracer.next_instance
            self.tracer.next_instance += 1
            self.tracer.events.append({"inst": self.instance_id, "op": "instantiate"})
        imports = [self._make_import(imp) for imp in self.module.imports]
        self.instance = wasmtime.Instance(self.store, self.module, imports)
        self.ex = self.instance.exports(self.store)
        self.memory = self.ex["memory"]
        self.ex["__wbindgen_start"](self.store)

    # -- memory helpers -------------------------------------------------------------------------
    def _read(self, ptr: int, length: int) -> bytes:
        return bytes(self.memory.read(self.store, ptr, ptr + length))

    def _write(self, ptr: int, data: bytes) -> None:
        self.memory.write(self.store, data, ptr)

    def _i32(self, value: int) -> int:
        return value & 0xFFFFFFFF

    def _pass_array8(self, data: bytes) -> tuple[int, int]:
        ptr = self._i32(self.ex["__wbindgen_malloc"](self.store, len(data), 1))
        self._write(ptr, data)
        return ptr, len(data)

    def _take_array8(self, pair) -> bytes:
        ptr, length = self._i32(pair[0]), pair[1]
        data = self._read(ptr, length)
        self.ex["__wbindgen_free"](self.store, ptr, length * 1, 1)
        return data

    def _pass_string(self, text: str) -> tuple[int, int]:
        data = text.encode("utf-8")
        ptr = self._i32(self.ex["__wbindgen_malloc"](self.store, len(data), 1))
        self._write(ptr, data)
        return ptr, len(data)

    # -- imports --------------------------------------------------------------------------------
    def _make_import(self, imp):
        name, ftype = imp.name, imp.type
        impl = {
            "__wbindgen_init_externref_table": self._init_externref_table,
            "__wbindgen_throw": self._throw,
            "__wbg_new_abda76e883ba8a5f": lambda: _Sentinel("Error"),
            "__wbg_stack_658279fe44541cf6": self._error_stack,
            "__wbg_error_f851667af71bcfc6": self._console_error,
            "__wbindgen_memory": lambda: _Sentinel("memory"),
        }.get(name)
        if impl is None:
            def impl(*_args, _name=name):
                self.unexpected_imports.append(_name)
                raise wasmtime.Trap(f"UNEXPECTED_IMPORT {_name}")
        return wasmtime.Func(self.store, ftype, impl)

    def _init_externref_table(self) -> None:
        table = self.ex["__wbindgen_export_2"]
        offset = table.grow(self.store, 4, None)
        table.set(self.store, 0, UNDEFINED)
        table.set(self.store, offset + 0, UNDEFINED)
        table.set(self.store, offset + 1, NULL)
        table.set(self.store, offset + 2, TRUE)
        table.set(self.store, offset + 3, FALSE)

    def _throw(self, ptr: int, length: int) -> None:
        self.last_throw = self._read(self._i32(ptr), length).decode("utf-8", "replace")
        raise wasmtime.Trap(self.last_throw)

    def _error_stack(self, retptr: int, _err) -> None:
        # JS writes `new Error().stack`; its exact text is host-specific and only logged.
        ptr, length = self._pass_string("Error\n    at <minion photon host>")
        self._write(self._i32(retptr) + 4, length.to_bytes(4, "little"))
        self._write(self._i32(retptr), ptr.to_bytes(4, "little"))

    def _console_error(self, ptr: int, length: int) -> None:
        ptr = self._i32(ptr)
        try:
            self.console_errors.append(self._read(ptr, length).decode("utf-8", "replace"))
        finally:
            self.ex["__wbindgen_free"](self.store, ptr, length, 1)

    # -- photon API mirror (photon_rs.js) -------------------------------------------------------
    def _call(self, name: str, *args):
        try:
            return self.ex[name](self.store, *args)
        except (wasmtime.Trap, wasmtime.WasmtimeError) as exc:
            raise PhotonTrap(f"{name}: {exc}") from exc

    @_traced
    def new_from_byteslice(self, data: bytes) -> int:
        ptr, length = self._pass_array8(data)
        return self._i32(self._call("photonimage_new_from_byteslice", ptr, length))

    @_traced
    def new(self, raw_pixels: bytes, width: int, height: int) -> int:
        ptr, length = self._pass_array8(raw_pixels)
        return self._i32(self._call("photonimage_new", ptr, length, width, height))

    @_traced
    def get_width(self, img: int) -> int:
        return self._i32(self._call("photonimage_get_width", img))

    @_traced
    def get_height(self, img: int) -> int:
        return self._i32(self._call("photonimage_get_height", img))

    @_traced
    def get_raw_pixels(self, img: int) -> bytes:
        return self._take_array8(self._call("photonimage_get_raw_pixels", img))

    @_traced
    def get_bytes(self, img: int) -> bytes:
        return self._take_array8(self._call("photonimage_get_bytes", img))

    @_traced
    def get_bytes_jpeg(self, img: int, quality: int) -> bytes:
        return self._take_array8(self._call("photonimage_get_bytes_jpeg", img, quality))

    @_traced
    def resize(self, img: int, width: int, height: int, sampling_filter: int) -> int:
        return self._i32(self._call("resize", img, width, height, sampling_filter))

    @_traced
    def fliph(self, img: int) -> None:
        self._call("fliph", img)

    @_traced
    def flipv(self, img: int) -> None:
        self._call("flipv", img)

    @_traced
    def free(self, img: int) -> None:
        self._call("__wbg_photonimage_free", img, 0)
