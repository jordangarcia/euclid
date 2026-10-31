# Euclid (NOB Puzzle Series) — web game handoff

A browser/PWA version of **NOB Euclid** (ユークリッド), a Japanese wooden silhouette puzzle from the NOB Puzzle Series, © 1991 NOB. The player builds each of 101 target silhouettes from the same 7 pieces. This document covers everything done so far, how the pipeline works, where it stands, and what's left.

**Owner:** Jordan, Head of AI at Gamma. Preferences: concise answers, push back when something's wrong, and don't be overconfident.

---

## 1. Folder map

```
euclid-handoff/
├── HANDOFF.md                 ← this file
├── game/
│   ├── euclid.html            ← CURRENT game, single file, puzzle data inlined (this is what's live)
│   └── pwa/                   ← same game as an installable PWA (index.html, manifest, sw.js, icons)
├── source/                    ← all scripts (Python + C) and the HTML template
├── data/
│   ├── puzzles.json           ← puzzle data currently inside the game (96 puzzles, OLD numbering — see §6)
│   ├── f3.json                ← raw fitter output behind the live game (frame coords, old numbering)
│   ├── manual.json            ← hand-designed solutions (override f3.json)
│   ├── f_new.json             ← refit of 1–58 on the cleaner photos (NEW numbering, NOT merged — see §6)
│   ├── puzzles_new_preview.json ← f_new.json run through export (preview only)
│   ├── target_masks/NNN.png   ← the binary target silhouette used by the fitter for each puzzle 1–101
│   ├── label_arrays/*.npz     ← connected-component label images the masks were cut from (key 'a')
│   └── comps*.json            ← component bounding boxes for those label arrays
└── assets/
    ├── originals/             ← every image the user supplied (see §3)
    └── derived/               ← crops, segmentation overlays, review sheets, screenshots
```

**Live artifact:** https://claude.ai/artifact/CwM5fLu5sQ9emvgJgNZWsU (claude.ai published page; same content as `game/euclid.html`).

---

## 2. The physical puzzle (ground truth)

- **Tray:** a √5 × √5 square, total area 5. This is the classic Pythagorean dissection, which is why it's called "Euclid".
- **7 pieces**, all edges with slope 0, ∞, ±½ or ±2:

| code | piece | canonical vertices | area | count |
|---|---|---|---|---|
| `S` | unit square | (0,0)(1,0)(1,1)(0,1) | 1 | 1 |
| `B` | big right triangle, legs 2 and 1 | (0,0)(2,0)(0,1) | 1 | 2 |
| `T` | right trapezoid | (0,0)(1,0)(1,.5)(0,1) | 0.75 | 2 |
| `s` | small right triangle, legs 1 and .5 | (0,0)(1,0)(0,.5) | 0.25 | 2 |

- `T` + `s` = a `B` cut at the midpoint of its long leg. `T` + `s` also make a unit square.
- **Piece counts** (1 S, 2 B, 2 T, 2 s) come from reading the tray photo and checking that the area sums to 5. The user confirmed the piece shapes and dimensions, not the counts.
- Pieces may be flipped. `B`, `T` and `s` are chiral, so flipping matters.

---

## 3. Source material and its limits

`assets/originals/`:
- **`dccb…c03.jpeg`** — the original listing photo: tray, box, the yellow silhouette sheet (front side), and the white answer sheet. It's low-res; each answer drawing is about 50 px.
- **`IMG_7668–7671.PNG`** — phone screenshots zoomed into the same photo. They're sharper and cover the yellow sheet, puzzles 1–59 (7668 = 1–15, 7670 = 16–30, 7669 = 31–44, 7671 = 45–59).
- **`FullSizeRender.jpeg`** — box cover art. Sampled colours: green `#39805E`, dark navy `#22252E`, off-white type `#DADCCF`, piece grey `#96978B`.

What the sheets contain:
- **Yellow sheet front:** puzzles **1–59** as filled silhouettes, numbered. The back side (60–101) was never photographed.
- **White answer sheet:** all **101** solutions as line drawings in a 10-row grid: 9, 10, 10, 10, 10, 10, 11, 11, 10, 10 per row. Order is roughly numeric. It's the only source for **60–101**, and the drawings are small and blurry.
- **Japanese text** on the sheet: "シルエット集の101種の図形をつくってください" ("make the 101 silhouettes").

**Numbering fact discovered late:** on the yellow sheet, **No. 5 = arrow/house-with-stem, No. 6 = X, No. 7 = long thin parallelogram**. The live game has these three rotated (it shows the parallelogram as 5, the arrow as 6 and the X as 7). The new mask mapping in `newmask.py` uses the correct numbers. See §6.

---

## 4. Pipeline (how puzzles were generated)

All scripts are in `source/`. Paths are **hard-coded to `/home/claude/…` and `/mnt/user-data/uploads/…`**, so fix them or recreate those dirs.

1. **Segmentation → target masks**
   - `seg2.py` → `seg3.py`: answer sheet. It finds line pixels, dilates, flood-fills the outside, erodes, then opens with a 17 px kernel to remove the paper fold lines. This produced `lab3` (component labels).
   - `segy.py`: yellow sheet from the original photo, `laby0–3`. Mostly superseded.
   - `segnew.py`: yellow sheet from the sharper screenshots, `labn_A–D`. These are the best masks for 1–58.
   - `targets.py`: maps puzzle number → answer-sheet component ids (`ans`), with a few yellow overrides (`yel`).
   - `newmask.py`: maps 1–58 → screenshot components. `fit.mask_for(n)` checks `newmask` first, then `MANUAL` polygons (65 and 97 were hand-traced because fold lines ruined them), then `targets.get`.
   - The exported masks are in `data/target_masks/`. Puzzle 4 and 59–101 come from the answer sheet; 1–3 and 5–58 from the screenshots.

2. **Fitter** (finds an exact 7-piece arrangement that best covers a mask)
   - Target is rasterised at **8 cells per unit**. Pieces are placed on a **0.5-unit lattice** in a single frame rotated by θ. All pieces use 0/90/180/270° rotations plus flips within that frame.
   - `bb.c` (compiled to `./bb`) is a **branch-and-bound exact-cover tiler**. Cost = target cells left uncovered + cells covered outside the target. The bound is |remaining target − remaining piece area|. It tries all 16 lattice phases under a node limit.
   - `fit2.py` writes the input, runs `bb` and decodes the result.
   - `fit3.py` coarse-scans θ (currently 0–90° step 4.5°, 600k nodes each), then refines the top 2 θ by ±1.5° with 6M nodes. About 10–60 s per puzzle on one core.
   - `sa.c` / `fit.py:fit` is an earlier simulated-annealing fitter. It was abandoned in favour of `bb`, but `fit.py` still holds the shared helpers (`mask_for`, `theta_cands`, `target_grid`, `PM`, `OR`).
   - **Inherent limit:** single frame only. Originals that mix pieces at 26.57° relative to each other (the star, the X, some birds and figures) can't be reproduced exactly. The fitter returns the best single-frame approximation, which tends to look lumpy.

3. **Manual solutions:** `manual.py` → `manual.json`. These are hand-designed exact solutions in frame coords (y-down), with a `theta`. Done so far: **3, 11, 12, 13, 18, 22, 23** (read from zoomed answer-sheet crops, `assets/derived/c1.png` and `c2.png`). *Caution:* these use **old numbering**; 3, 11, 12, 13, 18, 22 and 23 are all outside the 5–7 swap, so they're fine.

4. **Export:** `export.py fits.json out.html`.
   - Merges `manual.json` over the fits.
   - Validates each solution (piece congruence, counts 1/2/2/2, no overlap, area 5). **Validation is done in frame coordinates**, because Shapely/GEOS gave a false "overlap = 1.0" after rotating by 63.43°.
   - Rotates by φ = the "nice" angle nearest θ (from {0, 26.565, 45, 63.435} + k·90) to straighten the photo skew.
   - Unions the pieces into an outline, centres it, and converts each piece to the game's transform `{t, a (deg), f (bool), x, y (centroid)}`.
   - Injects the JSON into `game_template.html` at `/*DATA*/[]`.

5. **Tests:** `test_game.py path/to/game.html` (Playwright, headless Chromium).
   - For every puzzle:
     - every solution angle is reachable with the turn button;
     - the exact solution is detected as solved even when the whole shape is translated;
     - shifting one piece 0.35 units is **not** solved (except for multi-part puzzles, by design);
     - pieces dropped near their spot snap exactly into place, one at a time.
   - It also runs a real mouse drag-and-tap solve of puzzle 2, a flip-handle drag test on all 7 piece types, the full-screen thumbnail, and checks the picker. It saves screenshots.
   - `pwatest.py` checks the service worker, manifest, icons and an offline reload. It needs `python3 -m http.server 8765` running in `pwa/`.
   - **Last full run:** 96 of 96 puzzles passed, and all interaction tests passed.

6. **Review tools:** `review.py` (mask vs fitted outline sheet), `render.py` (fits in frame coords), `crop.py out.png N N …` (enlarged answer-sheet crops for given puzzle numbers, very useful for manual redesign).

---

## 5. The game (`game_template.html` → `game/euclid.html`)

Single self-contained HTML/SVG/JS file. No framework. Font: Google "Zen Kaku Gothic New", with a system fallback.

**Look:** the user chose the earlier style and rejected the navy cover-art palette ("revert to previous aesthetic").
- Light mode: off-white `#F3F2EE` with a green NOB band `#1D6B45` and black silhouettes.
- Dark mode: black with grey silhouettes.
- Pieces have a wood gradient.
- Header: green "NOB / PUZZLE SERIES" block, "Euclid ユークリッド", and ‹ No.N › navigation.

**Interaction:**
- **Target:** shown only as a **thumbnail at the top right**. Tap it for full screen; tap anywhere or press Esc to close. The user explicitly did *not* want the target overlaid on the board ("too easy").
- **Drag** a piece to move it.
- **Tap** a piece to turn it to the next allowed angle. The allowed set is {0, puzzle offsets} + k·90, built from the solution's piece angles.
- **Flip:** tapping selects a piece and shows a **green dashed flip axis** with a round **handle**. Drag the handle across the axis to flip. The piece squashes live as you drag. Release past the axis to commit; release before it and the piece springs back. The user rejected double-tap.
- **Backups:** the Turn and Flip buttons, and the R / Shift-R / F keys.
- **No Answer button.** The user asked for it to be removed ("that's for wimps"). The solution is still in the data (`P.pieces`).
- **Reset** returns the pieces to the tray. The number button opens a picker grid of all silhouettes.

**Snapping** (`snapPiece`):
- Pieces snap **only to other pieces**, since there's no outline on the board.
- Candidate translations: vertex→vertex, vertex→edge and edge→vertex within 0.24 units. Positions along an edge are quantised to 1/8 of the edge length.
- Candidates that overlap another piece are rejected (tested with probe points).
- The winner maximises the number of coinciding vertices or vertices on edges.

**Win check** (`coverage` / `check`):
- **Translation-invariant:** the shape can be built anywhere on the board.
- Pieces are grouped into touching clusters. Each target component (outline polygon) must be matched by a cluster with the same bounding-box size (±0.03). Sample points (0.045 grid) are then tested; ≥ 99.2 % coverage counts as solved.
- Multi-part puzzles (**9, 20, 47**) are checked per part, so the parts can be any distance apart. A whole-bbox fallback also applies.
- On a solve, a toast offers "Next puzzle".

**State:**
- `localStorage['euclid-v2'] = {solved: [puzzle numbers], cur: index}`.
- Piece positions are **not** persisted.
- **Known fragility:** `cur` is an *index* into PUZZLES, not a puzzle number, so inserting puzzles shifts it. Switching to a number is a one-line change.

**Test hooks:** `window.__euclid` exposes `load`, `count`, `isSolved`, `coverage`, `place`, `solution`, `pieces`, `angles`, `snap`, `svgPoint`, `sel`, `handle`, `axis` and `parts`.

**PWA** (`game/pwa/`):
- `manifest.webmanifest` (standalone, theme `#1D6B45`), `sw.js` (network-first for navigation, cache-first for everything else), and icons: the √5 dissection in wood on green, at 192, 512, maskable 512 and Apple 180.
- Must be hosted on any HTTPS static host (Vercel, Netlify, GitHub Pages). A claude.ai artifact can't be a PWA: it's a single file, and there's no service-worker scope.
- The installed app keeps its own localStorage, separate from the artifact.

---

## 6. Status — what's done, what's not

**Live game: 96 puzzles** = 1–101 minus **32, 85, 99, 100, 101**.
- 32 failed in the fitter.
- 85 and 99–101 were never fitted; their masks exist in `data/target_masks/`.

**Quality of the live 96:** every one is a valid, exactly solvable 7-piece silhouette, but fidelity varies.
- **Good** (looked right in review): 1, 2, 4, 5(old #), 6(old #), 8, 9, 10, 16, 19, 26, 29, 30, 34, 37, 38, plus the manual 3, 11, 12, 13, 18, 22 and 23.
- **Poor** (lumpy or off): 7(old # = the X), 14 (star), 15, 17, 20, 21, 24, 25, 27, 28, 31, 33, 35, 36, 39, and many of 40–101. Those weren't individually reviewed; see `assets/derived/review0.png` for 1–39.

**Unmerged work:**
- **`f_new.json`:** a refit of 1–58 (except 4) against the sharper screenshot masks, in new numbering. **14, 32 and 43 failed.**
- **Important:** it is generally *not* better. `assets/derived/compare_1_58.png` shows three columns per puzzle: new mask | new fit | live fit. Most new fits look worse than the live ones despite the cleaner masks. Don't merge it wholesale; the screenshot masks may still be useful for manual design.
- **Numbering fix 5↔6↔7 is not applied.** Correct mapping from old live numbers: old 6 (arrow) → **5**, old 7 (X) → **6**, old 5 (parallelogram) → **7**. Easiest fix: remap the keys in `f3.json` before export, and bump the localStorage key (e.g. `euclid-v3`) so saved solves don't mismatch.

**Suggested next steps** (the user's last request before handoff was "redo the ones that look off", then "stop"):
1. Apply the 5/6/7 renumber.
2. Hand-design the clearly geometric "poor" ones using `crop.py` crops of the answer sheet plus the sharper screenshot masks. The 7 manual ones show the approach works.
3. Fit or design 85 and 99–101, and retry 32.
4. Consider a two-frame fitter (pieces at θ and θ + 26.565°) for the star, X and birds. That's hard: lattices in different frames rarely meet flush, so it probably needs vertex-graph construction rather than raster tiling.
5. Possibly persist in-progress boards, and change `cur` to a puzzle number.
6. Re-run `test_game.py` after any data change. It's the safety net.

---

## 7. Gotchas learned the hard way

- **Background processes die between conversation turns** in the sandbox. Long fits had to be restarted. Use `setsid nohup … &` and poll within a turn.
- **Don't export while a fit is writing `f3.json`.** It's rewritten after every puzzle, and an export mid-write read a truncated JSON. Copy it to a snapshot first.
- **Google Fonts are blocked in the sandbox,** so tests log one harmless `ERR_NAME_NOT_RESOLVED`.
- **Shapely `intersection` can return nonsense** on rotated polygons that share edges, as noted in §4.
- **Mouse tests need ~400 ms between taps,** left over from when double-tap was a gesture. That's harmless now.
- **Every `load(n)` in test hooks takes an index (1-based), not a puzzle number.** Index n ≠ puzzle n after 31 because 32 is missing.
