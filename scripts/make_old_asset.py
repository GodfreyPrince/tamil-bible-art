# -*- coding: utf-8 -*-
"""godlytalias old-version Tamil JSON -> tamil_old.json (app asset schema)."""
import json, os, re

SRC = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\oldver\godly_tamil.json")
OUT = os.path.expanduser(r"~\.zcode\workspace\default\TamilBible\app\src\main\assets\tamil_old.json")
BSI = os.path.expanduser(r"~\.zcode\workspace\default\TamilBible\app\src\main\assets\tamil_bsi.json")
KJV = os.path.expanduser(r"~\.zcode\workspace\default\KJVBible\app\src\main\assets\kjv.json")

d = json.load(open(SRC, encoding="utf-8"))
books_src = d["Book"]
assert len(books_src) == 66

# traditional (old-version) book names + short names from the BSI bookkey tn_o / tn_a
bsi = json.load(open(BSI, encoding="utf-8"))
old_names = [b["n"] for b in bsi["books"]]
old_shorts = [b.get("s") or b["n"] for b in bsi["books"]]

kjv = json.load(open(KJV, encoding="utf-8"))
out = []
diffs = []
for i, b in enumerate(books_src):
    chs = []
    for ch in b["Chapter"]:
        vs = [v["Verse"].strip() for v in ch["Verse"]]
        chs.append(vs)
    # sanity vs KJV chapter/verse counts
    kc = kjv["books"][i]["c"]
    if len(chs) != len(kc):
        diffs.append(f"book {i+1}: {len(chs)} ch vs {len(kc)}")
    else:
        for ci, (c, k) in enumerate(zip(chs, kc)):
            if len(c) != len(k):
                diffs.append(f"  book {i+1} ch {ci+1}: {len(c)} vs {len(k)} verses")
    out.append({"n": old_names[i], "s": old_shorts[i], "t": 1 if i >= 39 else 0, "c": chs})

json.dump({"books": out, "ptitles": {}}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print("books:", len(out), "chapters:", sum(len(b["c"]) for b in out),
      "verses:", sum(len(c) for b in out for c in b["c"]))
print("diffs vs KJV:", len(diffs))
for x in diffs[:15]:
    print(x)
print("size: %.1f MB" % (os.path.getsize(OUT) / 1e6))
print("Gen1:1:", out[0]["c"][0][0])
print("names sample:", [b["n"] for b in out[:3]], out[16]["n"])
