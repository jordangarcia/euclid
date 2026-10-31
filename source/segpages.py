"""Cut target masks for puzzles 1–59 from the four close-up panel photos.

assets/originals/pages/page{1..4}.png are the yellow sheet panels:
page1 = 1–15, page2 = 16–30, page3 = 31–44, page4 = 45–59.
Silhouettes are found as large dark components and numbered by the panel's
layout (rows top to bottom, left to right, with the per-panel exceptions
below). Writes data/target_masks/NNN.png and a labeled overlay for review.

usage: segpages.py overlay_dir
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "..", "assets", "originals", "pages")
MASKS = os.path.join(HERE, "..", "data", "target_masks")

# Approximate centre(s) of each silhouette in its panel photo; multi-part
# puzzles (8, 20) list one point per part. Numbering follows the sheet:
# 5 arrow, 6 X, 7 parallelogram, 8 diamond pair, 9 notched flag, 10 ribbon.
SPOTS = {
    1: {1: [(85, 145)], 2: [(238, 153)], 3: [(400, 163)], 4: [(588, 145)],
        5: [(103, 252)], 6: [(235, 275)], 7: [(442, 230)], 8: [(365, 320), (362, 385)],
        9: [(570, 290)], 10: [(563, 371)], 11: [(117, 358)], 12: [(110, 468)],
        13: [(253, 467)], 14: [(415, 447)], 15: [(585, 460)]},
    2: {16: [(70, 158)], 17: [(193, 168)], 18: [(325, 162)], 19: [(436, 165)],
        20: [(533, 160), (530, 230)], 21: [(55, 285)], 22: [(170, 280)], 23: [(280, 285)],
        24: [(375, 318)], 25: [(490, 328)], 26: [(62, 423)], 27: [(190, 483)],
        28: [(262, 421)], 29: [(430, 456)], 30: [(535, 460)]},
    3: {31: [(62, 180)], 32: [(190, 180)], 33: [(283, 160)], 34: [(403, 180)],
        35: [(533, 175)], 36: [(122, 325)], 37: [(230, 378)], 38: [(323, 325)],
        39: [(435, 330)], 40: [(553, 335)], 41: [(65, 435)], 42: [(215, 495)],
        43: [(420, 475)], 44: [(553, 485)]},
    4: {45: [(75, 180)], 46: [(175, 215)], 47: [(265, 220)], 48: [(370, 205)],
        49: [(490, 205)], 50: [(575, 295)], 51: [(100, 358)], 52: [(265, 390)],
        53: [(418, 405)], 54: [(575, 425)], 55: [(90, 478)], 56: [(85, 598)],
        57: [(255, 565)], 58: [(420, 570)], 59: [(575, 600)]},
}
PAD = 12


def components(path):
    im = cv2.imread(path)
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    # Silhouettes are dark brown on yellow; Otsu on value adapts to each photo's exposure.
    _, dark = cv2.threshold(hsv[:, :, 2], 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(dark)
    comps = [dict(k=k, area=int(st[k][4]), cx=cen[k][0], cy=cen[k][1]) for k in range(1, n) if st[k][4] >= 200]
    return im, lab, comps


def mask_for_spots(lab, comps, spots):
    """Union of the component containing (or nearest to) each spot, hole-filled and cropped."""
    picked = set()
    for sx, sy in spots:
        k = lab[sy, sx]
        if k == 0 or all(c["k"] != k for c in comps):
            k = min(comps, key=lambda c: (c["cx"] - sx) ** 2 + (c["cy"] - sy) ** 2)["k"]
        picked.add(k)
    m = np.isin(lab, list(picked)).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(m)
    cv2.drawContours(filled, cs, -1, 1, -1)
    ys, xs = np.nonzero(filled)
    crop = filled[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    return np.pad(crop, PAD), picked


def reading_order(comps):
    # group into rows by vertical centre, then left to right
    comps = sorted(comps, key=lambda c: c["cy"])
    rows = []
    for c in comps:
        if rows and abs(c["cy"] - np.mean([r["cy"] for r in rows[-1]])) < 45:
            rows[-1].append(c)
            continue
        rows.append([c])
    return [c for row in rows for c in sorted(row, key=lambda c: c["cx"])]


if __name__ == "__main__":
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    for page, spots in SPOTS.items():
        im, lab, comps = components(os.path.join(PAGES, f"page{page}.png"))
        vis = im.copy()
        used = {}
        for n, pts in spots.items():
            m, picked = mask_for_spots(lab, comps, pts)
            for k in picked:
                used.setdefault(k, []).append(n)
            cv2.imwrite(os.path.join(MASKS, f"{n:03d}.png"), m * 255)
            overlay = np.isin(lab, list(picked))
            vis[overlay] = (0.5 * vis[overlay] + 0.5 * np.array([60, 160, 60])).astype(np.uint8)
            cx, cy = pts[0]
            cv2.putText(vis, str(n), (cx - 10, cy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        shared = {k: ns for k, ns in used.items() if len(ns) > 1}
        if shared:
            print(f"page{page}: components shared between puzzles {list(shared.values())}")
        cv2.imwrite(os.path.join(out_dir, f"page{page}_spots.png"), vis)
        print(f"page{page}: wrote {len(spots)} masks")
