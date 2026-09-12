# -*- coding: utf-8 -*-
"""Next review sheet: 48 downloaded-but-unreviewed images -> numbered contact sheet.
Usage: python next_sheet.py  -> prints sheet path and writes sidecar json."""
import os, re, sys, json, time
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\media")
DL = os.path.join(BASE, "dl")
REV = os.path.join(BASE, "review")
SHEETS = os.path.join(REV, "sheets")
os.makedirs(SHEETS, exist_ok=True)
STATE = os.path.join(REV, "state.json")
BATCH = 48

def main():
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"reviewed": [], "n": 0}
    reviewed = set(st["reviewed"])
    files = sorted((f for f in os.listdir(DL) if f.endswith(".jpg")
                    and os.path.getsize(os.path.join(DL, f)) > 5000
                    and f not in reviewed),
                   key=lambda f: os.path.getmtime(os.path.join(DL, f)))
    files = files[:BATCH]
    if not files:
        print("NONE")
        return
    cols, tile = 8, 200
    rows = (len(files) + cols - 1) // cols
    W, H = cols * (tile + 6) + 6, rows * (tile + 26) + 6
    img = Image.new("RGB", (W, H), (16, 16, 16))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arialbd.ttf", 17)
    except Exception:
        font = ImageFont.load_default()
    mapping = []
    for i, f in enumerate(files):
        r, c = divmod(i, cols)
        x, y = 6 + c * (tile + 6), 6 + r * (tile + 26)
        num = str(i + 1)
        try:
            t = Image.open(os.path.join(DL, f)).convert("RGB")
            t.thumbnail((tile, tile))
            img.paste(t, (x + (tile - t.width) // 2, y + (tile - t.height) // 2))
        except Exception:
            d.rectangle([x, y, x + tile, y + tile], fill=(90, 0, 0))
        d.rectangle([x, y + tile + 2, x + 34, y + tile + 24], fill=(255, 220, 120))
        d.text((x + 4, y + tile + 3), num, fill=(0, 0, 0), font=font)
        mapping.append({"n": i + 1, "file": f})
    st["n"] += 1
    sp = os.path.join(SHEETS, f"r{st['n']:04d}.jpg")
    img.save(sp, quality=82)
    json.dump(mapping, open(sp.replace(".jpg", ".json"), "w", encoding="utf-8"), indent=0)
    st["reviewed"].extend(files)
    json.dump(st, open(STATE, "w", encoding="utf-8"))
    print(sp)

if __name__ == "__main__":
    main()
