"""Build the static PWA into docs/ (served by GitHub Pages).

docs/index.html = game_template.html with data/puzzles.json inlined.
web/* is copied alongside; sw.js gets a content hash as its cache name so
installed apps pick up new builds.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "source" / "game_template.html"
PUZZLES = ROOT / "data" / "puzzles.json"
WEB = ROOT / "web"
OUT = ROOT / "docs"


def build():
    puzzles = json.loads(PUZZLES.read_text())
    template = TEMPLATE.read_text()
    if template.count("/*DATA*/[]") != 1:
        raise SystemExit("template must contain exactly one /*DATA*/[] marker")

    data = json.dumps(puzzles, separators=(",", ":"))
    html = template.replace("/*DATA*/[]", data)

    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(html)

    assets = sorted(p for p in WEB.iterdir() if p.is_file())
    digest = hashlib.sha256(html.encode())
    for asset in assets:
        digest.update(asset.read_bytes())
    build_id = digest.hexdigest()[:10]

    for asset in assets:
        if asset.name == "sw.js":
            sw = asset.read_text().replace("__BUILD__", build_id)
            (OUT / "sw.js").write_text(sw)
            continue
        shutil.copy2(asset, OUT / asset.name)

    # GitHub Pages runs Jekyll by default; skip it so files are served as-is.
    (OUT / ".nojekyll").write_text("")

    print(f"built {len(puzzles)} puzzles -> {OUT.relative_to(ROOT)} (cache euclid-{build_id})")


if __name__ == "__main__":
    build()
