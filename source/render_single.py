# Renders verified single-silhouette puzzles: GPT draft | exact puzzle | piece solution.
import json, math, sys
from pathlib import Path
import cv2, numpy as np
from lib import A

ROOT = Path(__file__).resolve().parent.parent / "assets" / "generated" / "single"
SUBJECTS = json.load(open(ROOT / "subjects.json"))
PAPER = (176, 222, 240)
INK = (30, 34, 40)
COLS = {"S": (90, 170, 90), "B": (200, 130, 60), "T": (70, 150, 220), "s": (170, 90, 190)}

def upright(pieces, theta):
    # Rotate the fit frame by the nice angle nearest the photo angle so edges land on 0/26.57/45/63.43.
    nice = [k * 90 + o for k in range(-1, 5) for o in (0, A, 45, 90 - A)]
    phi = math.radians(min(nice, key=lambda a: abs(a - theta)))
    c, s = math.cos(phi), math.sin(phi)
    return [(t, [(c * x - s * y, s * x + c * y) for x, y in pts]) for t, pts in pieces]

def to_px(pieces, size, pad):
    xs = [x for _, pts in pieces for x, _ in pts]
    ys = [y for _, pts in pieces for _, y in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    k = (size - 2 * pad) / span
    ox = (size - (max(xs) - min(xs)) * k) / 2 - min(xs) * k
    oy = (size - (max(ys) - min(ys)) * k) / 2 - min(ys) * k
    return [(t, np.array([[x * k + ox, y * k + oy] for x, y in pts], np.int32)) for t, pts in pieces]

def panel_puzzle(pieces, size=1024):
    img = np.full((size, size, 3), PAPER, np.uint8)
    for _, p in to_px(pieces, size, 170):
        cv2.fillPoly(img, [p], INK, lineType=cv2.LINE_AA)
    return img

def panel_solution(pieces, size=1024):
    img = np.full((size, size, 3), (245, 245, 242), np.uint8)
    for t, p in to_px(pieces, size, 170):
        cv2.fillPoly(img, [p], COLS[t], lineType=cv2.LINE_AA)
        cv2.polylines(img, [p], True, INK, 4, lineType=cv2.LINE_AA)
    return img

def label(img, text):
    cv2.putText(img, text, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, INK, 3, cv2.LINE_AA)
    return img

if __name__ == "__main__":
    keep = sys.argv[1:] or sorted(p.stem for p in (ROOT / "fits").glob("*.json"))
    rows = []
    for stem in keep:
        r = json.load(open(ROOT / "fits" / f"{stem}.json"))
        pieces = upright(r["pieces"], r["theta"])
        raw = cv2.resize(cv2.imread(str(ROOT / "raw" / f"{stem}.png")), (1024, 1024))
        row = np.hstack([
            label(raw, f"{stem} {SUBJECTS[int(stem)]} (gpt)"),
            label(panel_puzzle(pieces), f"puzzle  iou={r['iou']:.2f}"),
            label(panel_solution(pieces), f"proof ok={r['proof']['ok']}"),
        ])
        rows.append(cv2.resize(row, None, fx=0.3, fy=0.3))
    cv2.imwrite(str(ROOT / "review.png"), np.vstack(rows))
