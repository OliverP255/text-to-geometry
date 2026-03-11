#!/usr/bin/env python3
"""End-to-end: DSL string -> compile -> optimize -> output."""

import argparse
import sys
from pathlib import Path

# Add parent for build/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

import text_to_geometry_bindings as t2g
from optimise_params import optimise_params
from target_sdf import sphere_target


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimize FlatIR params to match target SDF")
    parser.add_argument("dsl", help="DSL string or path to .dsl file")
    parser.add_argument("--steps", type=int, default=500, help="Optimization steps")
    parser.add_argument("--target", choices=["sphere"], default="sphere", help="Target SDF")
    parser.add_argument("--radius", type=float, default=1.0, help="Target sphere radius")
    parser.add_argument("--output", "-o", help="Output FlatIR (pickle) path")
    args = parser.parse_args()

    dsl = args.dsl
    if Path(dsl).exists():
        dsl = Path(dsl).read_text()

    flatir = t2g.compile(dsl)

    if args.target == "sphere":
        target = sphere_target(radius=args.radius)
    else:
        print("Unknown target", args.target, file=sys.stderr)
        return 1

    result = optimise_params(flatir, target, steps=args.steps)
    dsl = t2g.unparseDSL(result)
    print(dsl)

    if args.output:
        if args.output.endswith(".dsl"):
            Path(args.output).write_text(dsl)
        else:
            import pickle
            Path(args.output).write_bytes(pickle.dumps(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
