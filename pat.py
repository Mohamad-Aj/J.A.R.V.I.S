#!/usr/bin/env python3
"""
fix_imports.py ────────────────────────────────────────────────────────────────
Scan every *.py file inside the jarvis package and rewrite
    from wizard import X
    import wizard
…into:
    from jarvis.wizard import X
    import jarvis.wizard as wizard

It detects local modules by looking at the actual filenames present in
jarvis/, so third-party libraries are left untouched.
"""
import pathlib
import re
import sys

ROOT   = pathlib.Path(__file__).parent
PKGDIR = ROOT / "jarvis"

# --------------------------------------------------------------------------- #
# 1 .  build the set of *local* module names (wizard, ReminderSystem, …)
local_modules = {
    p.stem
    for p in PKGDIR.glob("*.py")
    if p.stem not in {"__init__", "__main__"}
}

# Patterns that match the two common import forms
re_from   = re.compile(rf"^(\s*)from\s+({'|'.join(local_modules)})\s+import\s+", re.M)
re_import = re.compile(rf"^(\s*)import\s+({'|'.join(local_modules)})\b",            re.M)

# --------------------------------------------------------------------------- #
def patch_file(path: pathlib.Path) -> bool:
    """Return True if the file was modified."""
    src = path.read_text(encoding="utf-8")
    out = src

    # rewrite 'from wizard import …'
    out = re_from.sub(r"\1from jarvis.\2 import ", out)
    # rewrite 'import wizard'
    out = re_import.sub(r"\1import jarvis.\2 as \2", out)

    if out != src:
        path.write_text(out, encoding="utf-8")
        return True
    return False

changed = sum(patch_file(py) for py in PKGDIR.rglob("*.py"))
print(f"✅  Patched {changed} file(s).")
