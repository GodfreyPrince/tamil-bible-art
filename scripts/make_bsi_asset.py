# -*- coding: utf-8 -*-
"""Convert the jayarathina/Tamil-Bible-Database MySQL dump (Thiruviviliam,
BSI ecumenical Tamil, 2012 print edition; Unlicense) into tamil_bsi.json.

Only the 66 canonical books are kept; deuterocanonical entries are skipped.
Missing verse numbers (critical-text omissions) are padded with "" so that
index == verse number, exactly like the IRV asset.
"""
import re, os, json, collections

BASE = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\bsi")
OUT = os.path.expanduser(r"~\.zcode\workspace\default\TamilBible\app\src\main\assets\tamil_bsi.json")
KJV = os.path.expanduser(r"~\.zcode\workspace\default\KJVBible\app\src\main\assets\kjv.json")

BOOKS = ["GEN","EXO","LEV","NUM","DEU","JOS","JDG","RUT","1SA","2SA","1KI","2KI","1CH","2CH",
         "EZR","NEH","EST","JOB","PSA","PRO","ECC","SNG","ISA","JER","LAM","EZK","DAN","HOS",
         "JOL","AMO","OBA","JON","MIC","NAM","HAB","ZEP","HAG","ZEC","MAL",
         "MAT","MRK","LUK","JHN","ACT","ROM","1CO","2CO","GAL","EPH","PHP","COL","1TH","2TH",
         "1TI","2TI","TIT","PHM","HEB","JAS","1PE","2PE","1JN","2JN","3JN","JUD","REV"]
IDX = {c: i for i, c in enumerate(BOOKS)}
PSA = IDX["PSA"]

# dump OSIS ids (title case, deuterocanon interspersed at bn 40-48) -> our codes
OSIS = {"GEN":"Gen","EXO":"Exod","LEV":"Lev","NUM":"Num","DEU":"Deut","JOS":"Josh","JDG":"Judg",
        "RUT":"Ruth","1SA":"1Sam","2SA":"2Sam","1KI":"1Kgs","2KI":"2Kgs","1CH":"1Chr","2CH":"2Chr",
        "EZR":"Ezra","NEH":"Neh","EST":"Esth","JOB":"Job","PSA":"Ps","PRO":"Prov","ECC":"Eccl",
        "SNG":"Song","ISA":"Isa","JER":"Jer","LAM":"Lam","EZK":"Ezek","DAN":"Dan","HOS":"Hos",
        "JOL":"Joel","AMO":"Amos","OBA":"Obad","JON":"Jonah","MIC":"Mic","NAM":"Nah","HAB":"Hab",
        "ZEP":"Zeph","HAG":"Hag","ZEC":"Zech","MAL":"Mal","MAT":"Matt","MRK":"Mark","LUK":"Luke",
        "JHN":"John","ACT":"Acts","ROM":"Rom","1CO":"1Cor","2CO":"2Cor","GAL":"Gal","EPH":"Eph",
        "PHP":"Phil","COL":"Col","1TH":"1Thess","2TH":"2Thess","1TI":"1Tim","2TI":"2Tim",
        "TIT":"Titus","PHM":"Phlm","HEB":"Heb","JAS":"Jas","1PE":"1Pet","2PE":"2Pet","1JN":"1John",
        "2JN":"2John","3JN":"3John","JUD":"Jude","REV":"Rev"}

MARKERS = re.compile(r"[\u249c-\u24e9\u3251-\u325f\u32b1-\u32bf]")
marker_stats = collections.Counter()

def clean(text):
    marker_stats.update(MARKERS.findall(text))
    text = MARKERS.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def unescape(s):
    return s.replace("''", "'").replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")

def parse_rows(path, ncols=2):
    txt = open(path, encoding="utf-8").read()
    rows = []
    pat = re.compile(r"\((\d+),\s*'((?:[^']|'')*)'\)")
    for m in pat.finditer(txt):
        rows.append((m.group(1), unescape(m.group(2))))
    return rows

def main():
    # ---- book keys: bn -> osis -> canonical index + names ----
    bk_txt = open(os.path.join(BASE, "t_bookkey.sql"), encoding="utf-8").read()
    bks = {}
    pat = re.compile(r"\((\d+),\s*'([A-Za-z0-9]+)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*(?:NULL|'((?:[^']|'')*)')", )
    for m in pat.finditer(bk_txt):
        bn, osis = int(m.group(1)), m.group(2)
        bks[osis] = {
            "bn": bn,
            "en": unescape(m.group(3)),
            "tn_f": unescape(m.group(4)), "tn_s": unescape(m.group(5)),
            "tn_a": unescape(m.group(6)), "tn_o": unescape(m.group(7)) if m.group(7) else None,
        }
    print("bookkey entries:", len(bks))
    missing = [c for c in BOOKS if OSIS[c] not in bks]
    assert not missing, missing

    # ---- verses ----
    canon = {bks[OSIS[c]]["bn"]: IDX[c] for c in BOOKS}
    chapters = [dict() for _ in BOOKS]  # index -> {(c,v): text}
    rows = parse_rows(os.path.join(BASE, "t_verses.sql"))
    print("verse rows:", len(rows))
    used = 0
    for rid, text in rows:
        b, c, v = int(rid[:2]), int(rid[2:5]), int(rid[5:])
        bi = canon.get(b)
        if bi is None:
            continue
        chapters[bi][(c, v)] = text
        used += 1
    print("canonical verses:", used)

    # ---- psalm titles from verseheaders (book 19 only) ----
    ptitles = {}
    try:
        heads = parse_rows(os.path.join(BASE, "t_verseheaders.sql"))
    except FileNotFoundError:
        heads = []
    for rid, title in heads:
        b, c, v = int(rid[:2]), int(rid[2:5]), int(rid[5:])
        if b != bks[OSIS["PSA"]]["bn"] or not title.strip():
            continue
        title = title.split("\u00a7")[0].strip()
        verse = v if v > 0 else 1
        ptitles.setdefault(str(c), {})[str(verse)] = clean(title)
    print("psalm titles:", sum(len(v) for v in ptitles.values()))

    # ---- assemble: chapters as arrays, verse numbers padded ----
    books, diffs = [], []
    for bi, chmap in enumerate(chapters):
        n_ch = max(c for c, v in chmap)
        chs = []
        for c in range(1, n_ch + 1):
            vs = [v for (cc, v) in chmap if cc == c]
            arr = [""] * (max(vs) if vs else 0)
            for v in vs:
                arr[v - 1] = clean(chmap[(c, v)])
            chs.append(arr)
        name = bks[OSIS[BOOKS[bi]]]["tn_f"]
        books.append({"n": name, "s": bks[OSIS[BOOKS[bi]]]["tn_a"],
                      "t": 1 if bi >= 39 else 0, "c": chs})

    with open(KJV, encoding="utf-8") as f:
        kjv = json.load(f)
    for b, kb in zip(books, kjv["books"]):
        if len(b["c"]) != len(kb["c"]):
            diffs.append(f"book {b['n']}: {len(b['c'])} chapters vs KJV {len(kb['c'])}")
            continue
        for ci, (c, kc) in enumerate(zip(b["c"], kb["c"])):
            if len(c) != len(kc):
                diffs.append(f"  {b['n']} {ci+1}: {len(c)} vs KJV {len(kc)}")

    data = {"books": books, "ptitles": ptitles}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("markers stripped:", dict(marker_stats))
    print("diffs vs KJV:", len(diffs))
    for d in diffs[:40]:
        print(d)
    total = sum(1 for b in books for c in b["c"] for t in c if t)
    print(f"TOTAL: {sum(len(b['c']) for b in books)} chapters, {total} verses")
    print("size: %.1f MB" % (os.path.getsize(OUT) / 1e6))
    print("Gen1:1:", books[0]["c"][0][0])
    print("Jn3:16:", books[42]["c"][2][15])
    print("Ps23 title:", ptitles.get("23", {}).get("1"))
    print("sample names:", [(b["n"], b["s"]) for b in books[:3]], books[18]["n"], books[42]["n"], books[65]["n"])

if __name__ == "__main__":
    main()
