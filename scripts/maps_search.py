# -*- coding: utf-8 -*-
"""Find LIVE map files via Commons full-text search (server-rendered), download 960px thumbs."""
import os, re, json, time, hashlib, urllib.parse, urllib.request
import concurrent.futures as cf

BASE = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\media")
MAPS_DL = os.path.join(BASE, "maps")
CACHE = os.path.join(BASE, "html")
os.makedirs(MAPS_DL, exist_ok=True)
UA = {"User-Agent": "TamilBibleArtBot/1.0 (https://github.com/GodfreyPrince/tamil-bible-art; contact: godfreyprince@users.noreply.github.com)"}

QUERIES = [
    "twelve tribes of Israel map", "ancient Israel map", "Palestine map vintage",
    "Jerusalem map old", "Exodus route map", "Paul missionary journey map",
    "Holy Land map 19th century", "Canaan map", "biblical Jerusalem temple map",
    "ancient Near East map bible", "Kingdom of Israel Judah map", "Synoptic Gospels Palestine map",
    "Tabernacle plan", "Solomon temple plan", "Assyria Babylon empire map",
    "Roman Palestine map", "Galilee map old", "tribal allotments map",
]

def search(query, n=40):
    p = os.path.join(CACHE, "srch_" + re.sub(r"[^A-Za-z0-9]", "_", query) + ".html")
    if os.path.exists(p) and os.path.getsize(p) > 1000:
        h = open(p, encoding="utf-8", errors="replace").read()
    else:
        url = ("https://commons.wikimedia.org/w/index.php?search="
               + urllib.parse.quote(query) + "&title=Special:Search&ns6=1&limit=" + str(n))
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as r:
            h = r.read(4_000_000).decode("utf-8", "replace")
        if len(h) > 1000:
            open(p, "w", encoding="utf-8").write(h)
        time.sleep(1)
    files = []
    for m in re.finditer(r'href="/wiki/File:([^"]+)"', h):
        t = urllib.parse.unquote(m.group(1)).replace("_", " ")
        if re.search(r"\.(jpe?g|png|tif|tiff|gif)$", t, re.I) and t not in files:
            files.append(t)
    return files

def sf_thumb(title, w=960):
    name = title.replace("_", " ")
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    stem, ext = os.path.splitext(name)
    el = ext.lower()
    pre = (f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/"
           + urllib.parse.quote(name) + "/")
    if el in (".svg",):
        return pre + f"{w}px-{urllib.parse.quote(stem)}.png"
    if el in (".tif", ".tiff"):
        return pre + f"lossy-page1-{w}px-{urllib.parse.quote(stem)}.jpg"
    if el == ".gif":
        return pre + f"{w}px-{urllib.parse.quote(name)}.png"
    return pre + f"{w}px-{urllib.parse.quote(name)}"

def grab(item):
    t, c = item
    lid = "MP" + hashlib.md5(t.encode()).hexdigest()[:6].upper()
    p = os.path.join(MAPS_DL, lid + ".jpg")
    if os.path.exists(p) and os.path.getsize(p) > 4000:
        return (lid, t, c, p, True)
    for attempt in range(4):
        try:
            req = urllib.request.Request(sf_thumb(t), headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                d = r.read(40_000_000)
            if len(d) > 4000:
                open(p, "wb").write(d)
                time.sleep(0.5)
                return (lid, t, c, p, True)
            break
        except Exception:
            time.sleep(3 + 3 * attempt)
    return (lid, t, c, p, False)

def main():
    seen = {}
    for q in QUERIES:
        got = search(q)
        for t in got:
            if t not in seen:
                seen[t] = q
        print(f"[{len(got):3d}] {q}  (unique so far {len(seen)})", flush=True)
    seen = {t: q for t, q in seen.items()
            if not re.search(r"Connecticut|Massachusetts|Virginia|county|town of", t, re.I)}
    items = sorted(seen.items(), key=lambda kv: kv[1])
    meta, ok = {}, 0
    with cf.ThreadPoolExecutor(4) as ex:
        for lid, t, c, p, good in ex.map(grab, list(items)):
            if good:
                ok += 1
                meta[lid] = {"t": t, "cat": c, "p": p}
    json.dump(meta, open(os.path.join(BASE, "maps_meta.json"), "w", encoding="utf-8"), indent=0)
    print(f"DONE ok={ok}/{len(items)} usable={len(meta)}", flush=True)

if __name__ == "__main__":
    main()
