# L12D004-R001 known-bad control: remove the NUL guard so a NUL path reaches realpath(3) as a C string.
import pathlib

B = chr(92)
p = pathlib.Path("src/minion_agent/execution/filesystem.py")
t = p.read_text()
old = '    if b"' + B + '0" in encoded:\n        return os.path.realpath(path, strict=True)\n'
assert t.count(old) == 1, "guard not found"
p.write_text(t.replace(old, ""))
print("guard removed")
