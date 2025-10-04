#!/usr/bin/env python3
"""
cfs_postproc.py
- If present: read `; flush_multiplier = ...` and `; flush_volumes_matrix = ...`,
  scale the 16 matrix values (round to int), and rewrite the matrix line.
- Always: inject safe pre-cut retracts around real tool changes (from != to).
- Never: inject CFS_PURGE, never remove tower.

Behavior when flush comments are missing:
- If either `flush_multiplier` or `flush_volumes_matrix` is absent,
  the script does not modify any flush comments and only injects the pre-cut sequence.

Additional safety:
- The output file will always contain `; flush_multiplier = 1.0` to prevent
  accidental double-scaling if firmware starts honoring the multiplier.
  The actual applied multiplier is recorded in the header comments.

Assumptions:
- 4 tools (T0..T3) → 4×4 matrix (16 integers).
- Filament Ø 1.75 mm is irrelevant here; we do not convert mm³.

Console markers:
- Pass `--m118-sentinels` to emit M118 markers for transitions, parking, and pre-cut.

Usage:
  python3 cfs_postproc.py input.gcode output.gcode --m118-sentinels --console-summary
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------- Regexes ----------
RE_FLUSH_MULT = re.compile(r"^\s*;\s*flush_multiplier\s*=\s*([0-9]*\.?[0-9]+)\s*$", re.I)
RE_FLUSH_MATRIX = re.compile(r"^\s*;\s*flush_volumes_matrix\s*=\s*([0-9,\s]+)\s*$", re.I)
RE_PRIME_VOLUME = re.compile(r"^\s*;\s*prime_volume\s*=\s*([0-9]+)\s*$", re.I)
RE_ENABLE_PRIME_TOWER = re.compile(r"^\s*;\s*enable_prime_tower\s*=\s*([01])\s*$", re.I)

WT_STARTS = [
    re.compile(p, re.I)
    for p in (
        r"^\s*;+\s*WIPE_TOWER_START\b",
        r"^\s*;+\s*PRIME_TOWER_START\b",
        r"^\s*;+\s*CP\s+WIPE_TOWER\s*START\b",
        r"^\s*;+\s*TYPE:\s*WIPE\s*TOWER\b",
    )
]
WT_ENDS = [
    re.compile(p, re.I)
    for p in (
        r"^\s*;+\s*WIPE_TOWER_END\b",
        r"^\s*;+\s*PRIME_TOWER_END\b",
        r"^\s*;+\s*CP\s+WIPE_TOWER\s*END\b",
        r"^\s*;+\s*END\s*WIPE\s*TOWER\b",
    )
]

T_RE = re.compile(r"^\s*T([0-3])\s*(?:;.*)?$")


def atomic_write_text(path: Path, text: str, encoding="utf-8"):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)


def parse_matrix_16(payload: str):
    nums = [n for n in payload.replace(" ", "").split(",") if n != ""]
    if len(nums) != 16:
        return None
    try:
        return [int(x) for x in nums]
    except ValueError:
        return None


def find_tower_center(lines):
    in_scan = False
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for ln in lines:
        if any(p.search(ln) for p in WT_STARTS):
            in_scan = True
            continue
        if in_scan and any(p.search(ln) for p in WT_ENDS):
            in_scan = False
            continue
        if in_scan:
            mx = re.search(r"\bX(-?\d+\.?\d*)", ln)
            my = re.search(r"\bY(-?\d+\.?\d*)", ln)
            if mx:
                x = float(mx.group(1))
                minx = min(minx, x)
                maxx = max(maxx, x)
            if my:
                y = float(my.group(1))
                miny = min(miny, y)
                maxy = max(maxy, y)
    if minx == float("inf") or miny == float("inf"):
        return None
    return ((minx + maxx) / 2.0, (miny + maxy) / 2.0)


def main():
    ap = argparse.ArgumentParser(
        description="Rewrite flush_volumes_matrix by applying in-file flush_multiplier; inject safe pre-cut retracts."
    )
    ap.add_argument("infile", type=str, help="Input G-code")
    ap.add_argument("outfile", type=str, help="Output G-code")
    ap.add_argument("--precut-mm", type=float, default=80.0, help="Pre-cut retract amount (mm)")
    ap.add_argument("--precut-f", type=int, default=600, help="Pre-cut retract feedrate")
    ap.add_argument("--zhop-mm", type=float, default=0.6, help="Depart Z-hop before moving to park")
    ap.add_argument("--zhop-f", type=int, default=3000, help="Feedrate for depart Z-hop")
    ap.add_argument("--travel-f", type=int, default=18000, help="Feedrate for XY travel to park")
    ap.add_argument(
        "--precut-park-xy",
        type=str,
        default=None,
        help='Override park "X,Y" (else autodetect tower center)',
    )
    ap.add_argument(
        "--m118-sentinels",
        action="store_true",
        help="Print M118 start/end markers around transitions and pre-cuts",
    )
    ap.add_argument("--console-summary", action="store_true", help="Print header summary to stderr")
    args = ap.parse_args()

    text = Path(args.infile).read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    flush_mult = None
    flush_mult_idx = None
    matrix_line_idx = None
    matrix_nums = None
    prime_volume = None
    enable_prime_tower = 0  # Default to 0 (disabled)

    for i, ln in enumerate(lines):
        if flush_mult is None:
            m = RE_FLUSH_MULT.match(ln)
            if m:
                try:
                    flush_mult = float(m.group(1))
                except ValueError:
                    flush_mult = None
                flush_mult_idx = i
        if matrix_line_idx is None:
            mm = RE_FLUSH_MATRIX.match(ln)
            if mm:
                parsed = parse_matrix_16(mm.group(1))
                if parsed:
                    matrix_line_idx = i
                    matrix_nums = parsed
        if prime_volume is None:
            pv = RE_PRIME_VOLUME.match(ln)
            if pv:
                try:
                    prime_volume = int(pv.group(1))
                except ValueError:
                    prime_volume = None

        # Check for enable_prime_tower setting
        ep = RE_ENABLE_PRIME_TOWER.match(ln)
        if ep:
            try:
                enable_prime_tower = int(ep.group(1))
            except ValueError:
                enable_prime_tower = 0

    park_xy = None
    if args.precut_park_xy:
        try:
            xs, ys = args.precut_park_xy.split(",")
            park_xy = (float(xs), float(ys))
        except Exception:
            park_xy = None
    if park_xy is None:
        auto_center = find_tower_center(lines)
        if auto_center:
            park_xy = auto_center

    orig_matrix = matrix_nums[:] if matrix_nums else None
    scaled_matrix = None
    matrix_rewritten = False
    applied_mult = None

    if (matrix_nums is not None) and (flush_mult is not None):
        applied_mult = flush_mult
        scaled_matrix = [max(0, int(round(v * applied_mult))) for v in matrix_nums]

        # If prime tower is enabled and prime_volume is found, subtract it from scaled matrix values
        if enable_prime_tower == 1 and prime_volume is not None and prime_volume > 0:
            # Subtract prime_volume from each value, but never go below 100 and skip zeros
            final_matrix = []
            for v in scaled_matrix:
                if v == 0:
                    final_matrix.append(0)
                else:
                    subtracted = v - prime_volume
                    final_matrix.append(max(100, subtracted))
            scaled_matrix = final_matrix

        new_payload = ", ".join(str(v) for v in scaled_matrix)
        lines[matrix_line_idx] = f"; flush_volumes_matrix = {new_payload}"
        matrix_rewritten = True

    # Force output multiplier to 1.0 if present
    if flush_mult_idx is not None:
        lines[flush_mult_idx] = "; flush_multiplier = 1.0"

    out = []
    current_tool = None

    def m118(msg):
        if args.m118_sentinels:
            out.append(f"M118 {msg}")

    def inject_precut(next_tool: int):
        if park_xy is not None:
            px, py = park_xy
            out.append(f"; [INJECT] depart-hop before park: Z+{args.zhop_mm:.2f}")
            out.append("G91")
            out.append(f"G1 Z{args.zhop_mm:.2f} F{args.zhop_f}")
            out.append("G90")
            out.append(f"; [INJECT] park before pre-cut: X{px:.3f} Y{py:.3f}")
            m118(f"[INJECT] PARK X{px:.1f} Y{py:.1f}")
            out.append(f"G0 X{px:.3f} Y{py:.3f} F{args.travel_f}")
        out.append(
            f"; [INJECT] pre-cut retract before T{next_tool} ({args.precut_mm:.1f}mm @ F{args.precut_f})"
        )
        m118(f"[INJECT] PRECUT T{next_tool} E-{int(args.precut_mm)}; Start")
        out.append(f"G1 E-{args.precut_mm:.1f} F{args.precut_f}")
        m118(f"[INJECT] PRECUT T{next_tool} E-{int(args.precut_mm)}; End")

    for ln in lines:
        s = ln.strip()
        mt = T_RE.match(s)
        if mt:
            to_tool = int(mt.group(1))
            fr = current_tool
            if fr is not None and fr != to_tool:
                m118(f"[INJECT] TRANSITION T{fr} -> T{to_tool}; Start")
                inject_precut(to_tool)
                out.append(f"; [INJECT] selecting tool T{to_tool}")
                out.append(ln)
                m118(f"[INJECT] TRANSITION T{fr} -> T{to_tool}; End")
            else:
                out.append(ln)
            current_tool = to_tool
            continue
        out.append(ln)

    hdr = [f"; Post-processed by cfs_postproc on {datetime.now().isoformat(timespec='seconds')}"]
    if applied_mult is not None:
        hdr.append(f"; applied_flush_multiplier: {applied_mult:.6f}")
    if enable_prime_tower == 1 and prime_volume is not None:
        hdr.append(f"; prime_volume subtracted: {prime_volume} mm^3 (prime tower enabled)")
    elif prime_volume is not None:
        hdr.append(f"; prime_volume found: {prime_volume} mm^3 (but prime tower disabled)")
    if matrix_rewritten:
        hdr.append("; original flush_volumes_matrix (mm^3):")
        for r in range(4):
            hdr.append(";   " + ", ".join(f"{orig_matrix[r*4+c]:4d}" for c in range(4)))
        hdr.append("; scaled flush_volumes_matrix (mm^3) written:")
        for r in range(4):
            hdr.append(";   " + ", ".join(f"{scaled_matrix[r*4+c]:4d}" for c in range(4)))
    else:
        if applied_mult is None and orig_matrix is None:
            hdr.append("; no Creality flush comments found → only injected pre-cut retracts")
        elif applied_mult is None:
            hdr.append(
                "; flush_multiplier not found → matrix left unchanged; injected pre-cut retracts"
            )
        elif orig_matrix is None:
            hdr.append(
                "; flush_volumes_matrix not found → nothing to scale; injected pre-cut retracts"
            )

    hdr.append(f"; pre-cut: {args.precut_mm:.1f}mm @ F{args.precut_f}")
    if park_xy:
        hdr.append(
            f"; park XY: X{park_xy[0]:.3f} Y{park_xy[1]:.3f} (tower-center autodetect{' (override)' if args.precut_park_xy else ''})"
        )
    else:
        hdr.append("; park XY: not found (no tower detected and no override)")

    out_text = "\n".join(hdr) + "\n\n" + "\n".join(out) + "\n"
    atomic_write_text(Path(args.outfile), out_text, encoding="utf-8")

    if args.console_summary:
        sys.stderr.write("\n".join(hdr) + "\n")


if __name__ == "__main__":
    main()
