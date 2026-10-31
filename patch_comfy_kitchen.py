"""Patch comfy_kitchen builtin list[T] to typing.List[T] for torch<2.9 infer_schema.

Run once at image build time, after pip install, before handler starts ComfyUI.
Idempotent: safe to run multiple times.
"""
import os
import re
import sys

try:
    import comfy_kitchen
except ImportError:
    print("[compat] comfy_kitchen not installed, skipping patch")
    sys.exit(0)

root = os.path.dirname(os.path.abspath(comfy_kitchen.__file__))
patched = 0
for dirpath, _dirnames, filenames in os.walk(root):
    for fname in filenames:
        if not fname.endswith(".py"):
            continue
        full = os.path.join(dirpath, fname)
        with open(full, "r", encoding="utf-8") as f:
            code = f.read()
        if "list[" not in code:
            continue
        fixed = re.sub(r"\blist\[", "typing.List[", code)
        if "import typing" not in fixed:
            fixed = "import typing\n" + fixed
        with open(full, "w", encoding="utf-8") as f:
            f.write(fixed)
        patched += 1

print(f"[compat] patched {patched} comfy_kitchen files (list[T] -> typing.List[T])")
