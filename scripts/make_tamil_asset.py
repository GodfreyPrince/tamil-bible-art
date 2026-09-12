# -*- coding: utf-8 -*-
"""Convert IRV Tamil USFM files into the app's compact bible JSON asset.

Schema (same as the KJV app's kjv.json):
  {"books":[{"n":name,"s":short,"t":0|1,"c":[[verse,...],...]},...],
   "ptitles":{"<chapter>":{"<verse>":title}}}
Verses are stored 1..N contiguous; verse numbers absent from the source
(critical-text omissions) are padded with "" so index == verse number.
Also emits the Verse-of-the-Day table as a Java int[][] snippet.
"""
import re, os, json, glob, collections

SRC = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\ta_irv")
OUT = os.path.expanduser(r"~\.zcode\workspace\default\TamilBible\app\src\main\assets\tamil.json")
KJV = os.path.expanduser(r"~\.zcode\workspace\default\KJVBible\app\src\main\assets\kjv.json")
VOTD_OUT = os.path.expanduser(r"~\.zcode\workspace\default\TamilBible\scripts\votd_table.txt")

BOOKS = ["GEN","EXO","LEV","NUM","DEU","JOS","JDG","RUT","1SA","2SA","1KI","2KI","1CH","2CH",
         "EZR","NEH","EST","JOB","PSA","PRO","ECC","SNG","ISA","JER","LAM","EZK","DAN","HOS",
         "JOL","AMO","OBA","JON","MIC","NAM","HAB","ZEP","HAG","ZEC","MAL",
         "MAT","MRK","LUK","JHN","ACT","ROM","1CO","2CO","GAL","EPH","PHP","COL","1TH","2TH",
         "1TI","2TI","TIT","PHM","HEB","JAS","1PE","2PE","1JN","2JN","3JN","JUD","REV"]
IDX = {c: i for i, c in enumerate(BOOKS)}
NT_FROM = IDX["MAT"]
PSA = IDX["PSA"]

PAIRED_KEEP = {"w","nd","qt","qs","add","dc","pn","or","wj","tl","it","bd","bdit","em","sc","k"}
FOOTNOTE_OPEN = {"f","fe","ef"}
PAIRED_DROP = {"fm","efm","fr","fk","fv","ft","fq","fqa","fl","fp","ex","cat","vp"}
SKIP = {"ide","usfm","id","h","mt","mt1","mt2","mt3","imt","imt1","imt2","is","is1","is2","ip",
        "ipi","im","imi","iq","iq1","iot","io","io1","io2","io3","io4","iex","cl","cp","cd",
        "s","s1","s2","s3","s4","s5","ms","ms1","ms2","ms3","sr","r","sp","sts","rem",
        "toc2","toc3","toca1","toca2","toca3","d","sd","sd1","sd2","sq","sq1","rq","cr","fig"}
BREAK = {"p","m","b","mi","pi","pc","pr","pm","pmo","pmc","qc","qr","q","q1","q2","q3","q4"}

unknown = collections.Counter()
gaps = []

def clean(text):
    text = re.sub(r"x-[a-z-]+=\"[^\"]*\"", " ", text)
    text = text.replace("|", " ")
    return re.sub(r"\s+", " ", text).strip()

def strip_zaln(txt):
    txt = re.sub(r"\\zaln(?:-[se])?\s*\|[^\\]*\\\*", "", txt)
    txt = re.sub(r"\\zaln(?:-[se])?\\\*|\\zaln\\\*", "", txt)
    return txt

PUNCT = set(",.;:!?)]}\u201d\u2019…")

def parse_with_numbers(path):
    name, short = None, None
    chapters = []           # list of dicts {verse_no: text}
    cur = None
    cur_no, buf = None, ""
    pending_break = False
    pending_title = None
    ptitles = {}
    code = os.path.basename(path)[3:6]

    def append_frag(t):
        nonlocal buf, pending_break
        if not t:
            return
        if not buf:
            buf = t
        elif pending_break:
            buf += "\n" + t
            pending_break = False
        elif t[0] in PUNCT:
            buf += t
        else:
            buf += " " + t

    def flush_verse():
        nonlocal cur_no, buf, pending_title
        if cur_no is not None and cur is not None:
            t = re.sub(r"[ \t]+", " ", buf).strip()
            if cur_no not in cur:
                cur[cur_no] = t
        cur_no, buf, pending_title = None, "", pending_title

    txt = strip_zaln(open(path, encoding="utf-8-sig").read())
    pos = 0
    while pos < len(txt):
        at = txt.find("\\", pos)
        if at < 0:
            break
        m = re.match(r"\\([a-z0-9]+)(\*?)", txt[at:])
        if not m:
            pos = at + 1
            continue
        tag, star = m.group(1), m.group(2) == "*"
        nxt = txt.find("\\", at + m.end())
        body = txt[at + m.end(): nxt if nxt >= 0 else len(txt)]
        pos = nxt if nxt >= 0 else len(txt)

        if tag in PAIRED_KEEP:
            if not star:
                append_frag(clean(body.split("|")[0]))
            else:
                append_frag(clean(body))   # punctuation that trails a close token
            continue
        if tag in FOOTNOTE_OPEN:
            if star:
                append_frag(clean(body))   # text after the footnote ends
            continue
        if tag in PAIRED_DROP:
            continue
        if tag == "v":
            flush_verse()
            vm = re.match(r"\s*(\d+)", body)
            if not vm:
                continue
            cur_no = int(vm.group(1))
            buf = clean(body[vm.end():])
            pending_break = False
            if pending_title is not None:
                ptitles.setdefault(str(len(chapters)), {})[str(cur_no)] = pending_title
                pending_title = None
            continue
        if tag == "c":
            flush_verse()
            cm = re.match(r"\s*(\d+)", body)
            if not cm:
                continue
            chapters.append({})
            cur = chapters[-1]
            cur_no = None
            pending_title = None
            continue
        if tag == "toc1":
            name = clean(body); continue
        if tag == "toc2":
            short = clean(body); continue
        if tag == "d":
            if IDX[code] == PSA and clean(body):
                pending_title = clean(body).rstrip(".")
            continue
        if tag in BREAK:
            pending_break = True
            append_frag(clean(body))
            continue
        if tag in SKIP:
            continue
        unknown[tag] += 1
    flush_verse()

    # store per-verse-number, then pad gaps with "" so index == verse number
    out_chapters, n_gaps = [], 0
    for chmap in chapters:
        if not chmap:
            out_chapters.append([])
            continue
        hi = max(chmap)
        arr = [""] * hi
        for n, t in chmap.items():
            arr[n - 1] = t
        n_gaps += sum(1 for t in arr if t == "")
        out_chapters.append(arr)
    if n_gaps:
        gaps.append((code, n_gaps))
    return name, short, out_chapters, ptitles

def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.usfm")))
    assert len(files) == 66, len(files)

    books, all_pt = [], {}
    for path in files:
        code = os.path.basename(path)[3:6]
        name, short, chapters, pt = parse_with_numbers(path)
        full = re.sub(r"^III ", "3 ", re.sub(r"^II ", "2 ", re.sub(r"^I ", "1 ", name)))
        s = re.sub(r"^III ", "3 ", re.sub(r"^II ", "2 ", re.sub(r"^I ", "1 ", short or "")))
        books.append({"n": full, "s": s, "t": 1 if IDX[code] >= NT_FROM else 0, "c": chapters})
        for ch, mp in pt.items():
            all_pt.setdefault(ch, {}).update(mp)
        print(f"{code:4s} {full:24s} ch={len(chapters):4d} vs={sum(len(c) for c in chapters):5d} short={s}")

    with open(KJV, encoding="utf-8") as f:
        kjv = json.load(f)
    diffs = []
    for b, kb in zip(books, kjv["books"]):
        if len(b["c"]) != len(kb["c"]):
            diffs.append(f"book {b['n']}: {len(b['c'])} chapters vs KJV {len(kb['c'])}")
            continue
        for ci, (c, kc) in enumerate(zip(b["c"], kb["c"])):
            if len(c) != len(kc):
                diffs.append(f"  {b['n']} {ci+1}: {len(c)} verses vs KJV {len(kc)}")

    data = {"books": books, "ptitles": all_pt}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("\nUnknown markers:", dict(unknown) or "none")
    print("Gaps (padded empty verses):", gaps or "none")
    print("Verse-count diffs vs KJV:", len(diffs))
    for d in diffs[:50]:
        print(d)
    total = sum(1 for b in books for c in b["c"] for t in c if t)
    print(f"TOTAL: {len(books)} books, {sum(len(b['c']) for b in books)} chapters, {total} verses (+padded)")
    print("Asset size: %.1f MB" % (os.path.getsize(OUT) / 1e6))

    # ---- Verse of the Day table -> Java int[][] ----
    src = open(os.path.expanduser(r"~\.zcode\workspace\default\KJVBible\app\src\main\java\com\godfrey\kjvbible\BibleData.java"), encoding="utf-8").read()
    refs = re.findall(r'"([^"]+ \d+:\d+)"', src)
    en = ["Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel",
          "2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job",
          "Psalm","Proverbs","Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel",
          "Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai",
          "Zechariah","Malachi","Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians",
          "2 Corinthians","Galatians","Ephesians","Philippians","Colossians","1 Thessalonians",
          "2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James","1 Peter",
          "2 Peter","1 John","2 John","3 John","Jude","Revelation"]
    en_idx = {n: i for i, n in enumerate(en)}
    entries = []
    for ref in refs:
        book, rest = ref.rsplit(" ", 1)
        c, v = rest.split(":")
        entries.append((en_idx[book], int(c), int(v)))
    rows = ",".join(f"{{{b},{c},{v}}}" for b, c, v in entries)
    with open(VOTD_OUT, "w", encoding="utf-8") as f:
        for i in range(0, len(rows), 96):
            f.write(rows[i:i+96].rstrip(",") + "\n")
    print("VOTD refs:", len(entries))

if __name__ == "__main__":
    main()
