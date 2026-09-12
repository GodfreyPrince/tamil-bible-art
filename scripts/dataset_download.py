# -*- coding: utf-8 -*-
"""Dataset -> download queue + parallel thumb downloader (background worker)."""
import os, re, json, time, urllib.request, urllib.parse
import concurrent.futures as cf

BASE = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\media")
DS = os.path.join(BASE, "dataset")
DL = os.path.join(BASE, "dl")
os.makedirs(DL, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TamilBibleArtCurator/1.0 (personal dev)"}

def load():
    arts = {}
    for line in open(os.path.join(DS, "artworks.jsonl"), encoding="utf-8"):
        a = json.loads(line)
        arts[a["artwork_slug"]] = a
    maps = [json.loads(l) for l in open(os.path.join(DS, "verified-mappings.jsonl"), encoding="utf-8")]
    return arts, maps


def special_filepath_thumb(u, w=900):
    """Direct upload.wikimedia.org thumb URL via the MD5 scheme (avoids redirector 429s)."""
    import hashlib
    name = urllib.parse.unquote(u.split("Special:FilePath/")[-1].split("?")[0])
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    stem, ext = os.path.splitext(name)
    el = ext.lower()
    base = f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/"
    tb = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/"
    if el in (".tif", ".tiff"):
        return tb + urllib.parse.quote(name) + f"/{w}px-" + urllib.parse.quote(stem) + ".jpg"
    if el == ".png":
        return tb + urllib.parse.quote(name) + f"/{w}px-" + urllib.parse.quote(name)
    if el in (".jpg", ".jpeg"):
        return tb + urllib.parse.quote(name) + f"/{w}px-" + urllib.parse.quote(name)
    return tb + urllib.parse.quote(name) + f"/{w}px-" + urllib.parse.quote(stem) + ".jpg"

def thumb_url(a, w=900):
    u = a["image_url"]
    host = a.get("image_host", "")
    if "Special:FilePath" in u:
        return special_filepath_thumb(u, w)
    if "iiif" in u and "/full/" in u:
        return re.sub(r"/full/[^/]*/", f"/full/{w},/", u, count=1)
    if "upload.wikimedia.org" in u:
        m = re.match(r"(https://upload\.wikimedia\.org/wikipedia/commons/[^/]/[^/]/)(.+)$", u)
        if m:
            fn = m.group(2)
            stem, ext = os.path.splitext(urllib.parse.unquote(fn))
            thumb_ext = ".jpg" if ext.lower() in (".tif", ".tiff") else ext
            return (m.group(1).replace("/commons/", "/commons/thumb/") + urllib.parse.quote(fn)
                    + f"/{w}px-" + urllib.parse.quote(stem) + thumb_ext)
    return u

def main():
    arts, maps = load()
    cand = {}
    for m in maps:
        if m.get("suppressed"):
            continue
        s = m["artwork_slug"]
        a = arts.get(s)
        if not a:
            continue
        e = cand.setdefault(s, {"a": a, "maps": []})
        e["maps"].append({"b": m["book"], "c": m["chapter"], "vs": m["verse_start"],
                          "ve": m["verse_end"], "ref": m["reference"], "rel": m["relationship_type"],
                          "score": m.get("relevance_score", 0)})
    print("candidates:", len(cand), flush=True)
    queue = []
    for s, e in sorted(cand.items()):
        p = os.path.join(DL, s.replace("/", "_") + ".jpg")
        if not (os.path.exists(p) and os.path.getsize(p) > 5000):
            au = e["a"]["image_url"]
            urls = [thumb_url(e["a"])]
            if "CRDImages" in au and "/original/" in au:
                urls.insert(0, au.replace("/original/", "/web-large/"))
            if "Special:FilePath" in au:
                urls.append(au)
            queue.append((s, p, urls))
    print("to download:", len(queue), flush=True)

    st = {"ok": 0, "fail": []}
    def grab(it):
        s, p, urls = it
        for attempt in range(4):
            u = urls[min(attempt, len(urls) - 1)]
            try:
                req = urllib.request.Request(u, headers=UA)
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read(60_000_000)
                if len(data) < 5000:
                    time.sleep(1)
                    continue
                open(p, "wb").write(data)
                return (s, True)
            except Exception:
                time.sleep(2 + 2 * attempt)
        return (s, False)

    done_ct = 0
    with cf.ThreadPoolExecutor(10) as ex:
        for s, ok in ex.map(grab, queue):
            done_ct += 1
            if ok:
                st["ok"] += 1
            else:
                st["fail"].append(s)
            if done_ct % 100 == 0:
                print(f"downloaded {done_ct}/{len(queue)} ok={st['ok']}", flush=True)
    json.dump({"candidates": {s: {"maps": e["maps"]} for s, e in cand.items()},
               "fail": st["fail"]},
              open(os.path.join(BASE, "cand_maps.json"), "w", encoding="utf-8"), indent=0)
    print("DOWNLOAD PHASE DONE ok=", st["ok"], "fail=", len(st["fail"]), flush=True)

if __name__ == "__main__":
    main()
