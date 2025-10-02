#!/usr/bin/env python3
"""
cfs_postproc_rightclick.py
Right-click / CLI wrapper for cfs_postproc.py
"""
import shlex
import subprocess
import sys
from pathlib import Path

INJECTOR = "cfs_postproc.py"


def out_path(p: Path) -> Path:
    if "".join(p.suffixes).lower().endswith(".gcode.pp"):
        base = p.with_suffix("")
        return base.with_name(f"{base.stem}_scaled_precut.gcode")
    if p.suffix.lower() == ".gcode":
        return p.with_name(f"{p.stem}_scaled_precut.gcode")
    return p.with_name(f"{p.name}_scaled_precut.gcode")


def run_one(inp: Path) -> int:
    if not inp.exists():
        print(f"[SKIP] {inp}", file=sys.stderr)
        return 2
    injector = Path(__file__).with_name(INJECTOR)
    if not injector.exists():
        print(f"[ERR] Injector not found: {injector}", file=sys.stderr)
        return 2
    out = out_path(inp)
    cmd = [
        sys.executable,
        str(injector),
        str(inp),
        str(out),
        "--m118-sentinels",
        "--console-summary",
    ]
    print("[RUN]", " ".join(shlex.quote(x) for x in cmd))
    try:
        rc = subprocess.run(cmd).returncode
    except FileNotFoundError:
        print("[ERR] Python not found", file=sys.stderr)
        return 127
    if rc != 0:
        print(f"[WARN] Injector returned {rc} for {inp.name}", file=sys.stderr)
        return rc
    print(f"[OK] -> {out}")
    return 0


def main(argv):
    if not argv:
        print("Usage: cfs_postproc_rightclick.py <file.gcode> [...]", file=sys.stderr)
        return 1
    rc = 0
    for a in argv:
        rc = run_one(Path(a)) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
