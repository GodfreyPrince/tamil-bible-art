# -*- coding: utf-8 -*-
"""Build numbered contact sheets for downloaded maps."""
import os, json
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\media")
MAPS = os.path.join(BASE, "maps")
OUT = os.path.join(BASE, "review", "map_sheets")
os.makedirs(OUT, exist_ok=True)

meta = json.load(open(os.path.join(BASE, "maps_meta2.json"), encoding="utf-8"))
lids = sorted(meta.keys())
cols, tile, batch = 6, 250, 60
try:
    font = ImageFont.truetype("arialbd.ttf", 18)
except Exception:
    font = ImageFont.load_default()

for si in range(0, len(lids), batch):
    chunk = lids[si:si + batch]
    rows = (len(chunk) + cols - 1) // cols
    W, H = cols * (tile + 6) + 6, rows * (tile + 28) + 6
    img = Image.new("RGB", (W, H), (14, 14, 14))
    d = ImageDraw.Draw(img)
    mapping = []
    for i, lid in enumerate(chunk):
        r, c = divmod(i, cols)
        x, y = 6 + c * (tile + 6), 6 + r * (tile + 28)
        try:
            t = Image.open(meta[lid]["p"]).convert("RGB")
            t.thumbnail((tile, tile))
            img.paste(t, (x + (tile - t.width) // 2, y + (tile - t.height) // 2))
        except Exception:
            d.rectangle([x, y, x + tile, y + tile], fill=(90, 0, 0))
        num = str(si + i + 1)
        d.rectangle([x, y + tile + 2, x + 40, y + tile + 26], fill=(255, 220, 120))
        d.text((x + 5, y + tile + 3), num, fill=(0, 0, 0), font=font)
        mapping.append({"n": si + i + 1, "lid": lid})
    sp = os.path.join(OUT, f"m{si//batch + 1:03d}.jpg")
    img.save(sp, quality=84)
    json.dump(mapping, open(sp.replace(".jpg", ".json"), "w"), indent=0)
    print(sp)
print("total:", len(lids))
