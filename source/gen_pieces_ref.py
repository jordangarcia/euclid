# Renders the 7 Euclid pieces as a reference sheet for image-model prompting.
import cv2, numpy as np, sys
from lib import CANON

LAYOUT = [
    ("S", (0.3, 0.3)),
    ("B", (1.8, 0.3)),
    ("B", (4.3, 0.3)),
    ("T", (0.3, 1.9)),
    ("T", (1.8, 1.9)),
    ("s", (3.3, 1.9)),
    ("s", (4.8, 1.9)),
]
U = 160
img = np.full((int(3.4 * U), int(6.6 * U), 3), (205, 236, 245), np.uint8)

for t, (ox, oy) in LAYOUT:
    pts = np.array([[(ox + x) * U, (oy + 1 - y) * U] for x, y in CANON[t]], np.int32)
    cv2.fillPoly(img, [pts], (35, 45, 60))

cv2.imwrite(sys.argv[1], img)
