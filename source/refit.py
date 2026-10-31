"""Thorough single-frame refit of one puzzle.

Coarse scan of frame angle (edge-direction candidates + every 6°), then
refine the best three angles with a larger node budget.
Writes data/refit/NNN.json so several puzzles can run in parallel.

usage: refit.py N
"""
import json
import os
import sys
import time

import fit2
from fit import mask_for, theta_cands

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "refit")

COARSE_NODES = 400_000
FINE_NODES = 3_000_000


def refit(n):
    m = mask_for(n)
    coarse = sorted(set([round(float(t), 1) for t in theta_cands(m)] + [float(t) for t in range(0, 90, 6)]))

    scored = []
    for th in coarse:
        r = fit2.fit(n, limit=COARSE_NODES, ths=[th])
        if r:
            scored.append(r)

    scored.sort(key=lambda r: r["cost"])
    best = scored[0] if scored else None

    tried = set(coarse)
    for r in scored[:3]:
        for d in (-2, -1, 0, 1, 2):
            th = round((r["theta"] + d) % 90, 1)
            if th in tried and d != 0:
                continue
            tried.add(th)
            cand = fit2.fit(n, limit=FINE_NODES, ths=[th])
            if cand and (best is None or cand["cost"] < best["cost"]):
                best = cand

    return best


if __name__ == "__main__":
    n = int(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()

    try:
        r = refit(n)
    except Exception as e:
        print(f"{n} ERROR {e!r}", flush=True)
        raise

    if r is None:
        print(f"{n} FAIL {time.time() - t0:.0f}s", flush=True)
        sys.exit(1)

    r.pop("grid", None)
    json.dump(r, open(os.path.join(OUT, f"{n:03d}.json"), "w"))
    print(f"{n} iou={r['iou']:.3f} cost={r['cost']} theta={r['theta']} {time.time() - t0:.0f}s", flush=True)
