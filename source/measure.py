"""Print a target mask's outline as edges in puzzle units (area = 5).

usage: measure.py N [N ...]
"""
import math
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MASKS = os.path.join(HERE, "..", "data", "target_masks")


def measure(n, eps=0.025):
    m = cv2.imread(os.path.join(MASKS, f"{n:03d}.png"), cv2.IMREAD_GRAYSCALE) > 127
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    unit = math.sqrt(m.sum() / 5.0)
    lines = [f"{n}: {len(cs)} part(s), {unit:.1f} px/unit"]
    for c in sorted(cs, key=cv2.contourArea, reverse=True):
        ap = cv2.approxPolyDP(c, eps * unit, True)[:, 0, :]
        for i in range(len(ap)):
            a = ap[i]
            b = ap[(i + 1) % len(ap)]
            d = b - a
            # angle measured with y up, so 90 = straight up
            ang = math.degrees(math.atan2(-d[1], d[0]))
            lines.append(f"   ({(a[0]) / unit:5.2f},{(a[1]) / unit:5.2f})  len {math.hypot(*d) / unit:4.2f}  ang {ang:6.1f}")
    return "\n".join(lines)


if __name__ == "__main__":
    for n in map(int, sys.argv[1:]):
        print(measure(n))
