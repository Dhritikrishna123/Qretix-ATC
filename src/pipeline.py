"""Lightweight DAG orchestrator.

Each phase is a module exposing ``NAME``, ``DEPENDS_ON``, ``CONFIG``, ``run(**opts)`` and
``validate() -> list[str]``. Phases are executed in topological order of their dependencies, so any
phase (with its prerequisites) can be re-run independently.

Usage::

    python -m src.pipeline --phase 1                       # full Phase 1 + acceptance check
    python -m src.pipeline --phase 1 --only depmap,geo     # selected acquisition tasks
    python -m src.pipeline --phase 1 --validate-only       # acceptance criteria only
"""
from __future__ import annotations

import argparse
import importlib
import sys
from graphlib import TopologicalSorter
from types import ModuleType

# phase number -> module path. Later phases are registered here as they are implemented.
PHASE_MODULES: dict[int, str] = {
    1: "src.phase1",
}


def load(phase: int) -> ModuleType:
    if phase not in PHASE_MODULES:
        raise SystemExit(f"Phase {phase} is not implemented yet (available: {sorted(PHASE_MODULES)})")
    return importlib.import_module(PHASE_MODULES[phase])


def execution_order(targets: list[int]) -> list[int]:
    """Topologically sorted phases needed to run ``targets`` (prerequisites first)."""
    by_name = {load(n).NAME: n for n in PHASE_MODULES}
    graph: dict[int, set[int]] = {}
    stack = list(targets)
    while stack:
        n = stack.pop()
        if n in graph:
            continue
        deps = {by_name[d] for d in load(n).DEPENDS_ON}
        graph[n] = deps
        stack.extend(deps)
    return list(TopologicalSorter(graph).static_order())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="QRETIX-ATC pipeline")
    ap.add_argument("--phase", type=int, action="append", required=True, help="phase number (repeatable)")
    ap.add_argument("--only", help="comma-separated task keys within the phase")
    ap.add_argument("--skip", help="comma-separated task keys to skip")
    ap.add_argument("--force", action="store_true", help="re-download existing files")
    ap.add_argument("--gdc-download", action="store_true", help="download TCGA-THCA files (manifest only by default)")
    ap.add_argument("--no-supplementary", action="store_true", help="skip GEO supplementary files")
    ap.add_argument("--no-broad-pubmed", action="store_true", help="skip the ~30k-article thyroid corpus")
    ap.add_argument("--validate-only", action="store_true", help="only run acceptance checks")
    args = ap.parse_args(argv)

    split = lambda s: [x.strip() for x in s.split(",") if x.strip()] if s else None  # noqa: E731
    rc = 0
    for n in execution_order(args.phase):
        mod = load(n)
        if not args.validate_only:
            mod.run(
                only=split(args.only), skip=split(args.skip), force=args.force,
                gdc_download=args.gdc_download, supplementary=not args.no_supplementary,
                broad_pubmed=not args.no_broad_pubmed,
            )
        problems = mod.validate()
        print(f"\n== {mod.NAME} acceptance: {'PASS' if not problems else 'FAIL'} ==")
        for p in problems:
            print(f"  - {p}")
        rc = rc or (1 if problems else 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
