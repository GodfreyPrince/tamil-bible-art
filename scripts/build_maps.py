# -*- coding: utf-8 -*-
"""Apply review verdicts to maps_meta.json -> assets/media_maps.json (Tamil-labeled)."""
import os, re, json, hashlib

BASE = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\media")
REV = os.path.join(BASE, "review")
OUT = os.path.expanduser(r"~\.zcode\workspace\default\TamilBible\app\src\main\assets\media_maps.json")

CAT_TA = {
    "Bible": ("பைபிள் வரைபடங்கள்", "பைபிள் காலத்து நாடுகளும் பயணங்களும்"),
    "Biblical maps": ("வேத வரைபடங்கள்", "பைபிள் காலத்து நிலப்படங்கள்"),
}

def main():
    meta = json.load(open(os.path.join(BASE, "maps_meta.json"), encoding="utf-8"))
    rej = set()
    vp = os.path.join(REV, "map_verdicts.txt")
    if os.path.exists(vp):
        for line in open(vp, encoding="utf-8"):
            m = re.match(r"(m\d+) reject:\s*(.*)", line.strip())
            if not m:
                continue
            sp = os.path.join(REV, "map_sheets", m.group(1) + ".json")
            if not os.path.exists(sp) or m.group(2) == "none":
                continue
            mp = {e["n"]: e["lid"] for e in json.load(open(sp, encoding="utf-8"))}
            for n in m.group(2).split(","):
                n = n.strip()
                if n and int(n) in mp:
                    rej.add(mp[int(n)])
    entries = []
    for lid, v in sorted(meta.items()):
        if lid in rej:
            continue
        t = v["t"]
        cat_ta = CAT_TA.get(v.get("cat", ""), ("வரைபடம்", "வேத கால வரைபடம்"))
        entries.append({
            "id": lid,
            "title": t,
            "cat": v.get("cat", ""),
            "ta": {"title": cat_ta[0], "desc": cat_ta[1] + " — " + t},
        })
    json.dump({"v": 1, "maps": entries}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"maps entries={len(entries)} rejected={len(rej)} size={os.path.getsize(OUT)//1024}KB")

if __name__ == "__main__":
    main()
