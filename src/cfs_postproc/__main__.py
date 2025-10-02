from __future__ import annotations

import argparse


def main() -> None:
    p = argparse.ArgumentParser(prog="cfs-postproc", description="CFS post-processing tools")
    p.add_argument("--in", dest="infile", help="Input G-code file")
    p.add_argument("--out", dest="outfile", help="Output G-code file")
    p.add_argument("--multiplier", type=float, default=1.0, help="Flush multiplier (e.g., 0.25)")
    args = p.parse_args()

    if args.infile and args.outfile:
        with open(args.infile, encoding="utf-8") as f:
            data = f.read()
        # TODO: anropa dina faktiska transform-funktioner här:
        # data = apply_multiplier(data, args.multiplier)
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"Processed {args.infile} → {args.outfile} (multiplier={args.multiplier})")
    else:
        print(
            "Nothing to do. Try: cfs-postproc --in input.gcode --out output.gcode --multiplier 0.25"
        )


if __name__ == "__main__":
    main()
