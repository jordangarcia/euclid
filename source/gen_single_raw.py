# Asks gpt-image for one silhouette per image, using the piece sheet and a scan as references.
import base64, os, sys, json, urllib.request, urllib.error
import concurrent.futures as cf
from pathlib import Path

KEY = os.environ["OPENAI_API_KEY"]
MODEL = "gpt-image-2.5-sunburst"
ROOT = Path(__file__).resolve().parent.parent / "assets" / "generated" / "single"
REFS = [ROOT / "pieces_ref.png", Path.home() / "Downloads" / "page1.png"]

SUBJECTS = [
    "a sitting cat", "a swimming fish", "a sailboat", "a house with a chimney",
    "a bird in flight", "a rocket", "a running man", "a duck",
    "a fox head", "a pine tree", "a candle", "a hammer",
    "a kneeling figure", "a whale", "a crown", "a seated dog",
]

def prompt_for(subject):
    return f"""The first reference image shows the ONLY 7 pieces of a wooden tiling puzzle: one 1x1 square, two right triangles with legs 2 and 1, two right trapezoids (1 wide, heights 1 and 0.5), and two small right triangles with legs 1 and 0.5.
The second reference is a page of puzzle silhouettes made from these pieces.

Draw ONE single solid silhouette of {subject}, formed by placing ALL 7 pieces edge to edge with no gaps and no overlaps, then filling it in one flat dark color.
Rules: straight edges only; every edge must be horizontal, vertical, or a 1:2 slope (about 26.6 or 63.4 degrees) — NOT 45 degrees; keep it chunky and compact (total area is just 5 unit squares), no thin limbs.
Center it, large, on plain flat cream background. No text, no internal lines, no shading, no paper texture."""

def call(i):
    subject = SUBJECTS[i]
    boundary = "----euclidsingle"
    parts = []

    def field(name, val):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'.encode())

    field("model", MODEL)
    field("prompt", prompt_for(subject))
    field("size", "1024x1024")
    field("quality", "high")
    for r in REFS:
        head = f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="{r.name}"\r\nContent-Type: image/png\r\n\r\n'
        parts.append(head.encode() + r.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        "https://api.openai.com/v1/images/edits",
        data=b"".join(parts),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        return f"[{i}] {subject}: HTTP {e.code} {e.read()[:300]}"
    except Exception as e:
        return f"[{i}] {subject}: failed {e}"

    path = ROOT / "raw" / f"{i:02d}.png"
    path.write_bytes(base64.b64decode(body["data"][0]["b64_json"]))
    return f"[{i}] {subject} -> {path.name}"

json.dump(SUBJECTS, open(ROOT / "subjects.json", "w"))
with cf.ThreadPoolExecutor(16) as ex:
    for line in ex.map(call, range(len(SUBJECTS))):
        print(line, flush=True)
