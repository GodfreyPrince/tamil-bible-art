# -*- coding: utf-8 -*-
"""Build the app-facing media manifest:
   - reads dataset metadata + verified scripture mappings
   - applies human review verdicts (rejects) from review/verdicts.txt + sheet sidecars
   - emits manifest entries with English metadata + Tamil title/description (template-based)
   - splits maps into a separate section
"""
import os, re, json, urllib.parse

BASE = os.path.expanduser(r"~\.zcode\workspace\default\tamil_build\media")
DS = os.path.join(BASE, "dataset")
DL = os.path.join(BASE, "dl")
REV = os.path.join(BASE, "review")
OUT_APP = os.path.expanduser(r"~\.zcode\workspace\default\TamilBible\app\src\main\assets")

# ---------------- Tamil scene/title vocabulary ----------------
# scene slug -> (tamil scene name, tamil one-line description template)
SCENES_TA = {
    "nativity": ("இயேசுவின் பிறப்பு", "பெத்தலெகேமில் இயேசு குழந்தை பிறந்த நிகழ்வு"),
    "adoration-of-the-shepherds": ("மேய்ப்பவர்களின் வணக்கம்", "மேய்ப்பவர்கள் குழந்தை இயேசுவை வணங்கும் நிகழ்வு"),
    "adoration-of-the-magi": ("மூவர்களின் வணக்கம்", "கிழக்கின் ஞானிகள் குழந்தை இயேசுவுக்கு பரிசுகள் சமர்ப்பிக்கும் நிகழ்வு"),
    "annunciation": ("வானதூதர் பணிவிடை", "வானதூதர் கபிரியேல் மரியாளிடம் இயேசுவின் பிறப்பை அறிவிக்கும் நிகழ்வு"),
    "visitation": ("எலிசபெத்தைச் சந்தித்தல்", "மரியாள் எலிசபெத்தைச் சந்திக்கச் சென்ற நிகழ்வு"),
    "presentation-in-the-temple": ("கோவிலில் சமர்ப்பித்தல்", "குழந்தை இயேசு கோவிலில் கர்த்தருக்கு சமர்ப்பிக்கப்பட்ட நிகழ்வு"),
    "baptism-of-christ": ("இயேசுவின் ஞானஸ்நானம்", "யோர்த்தான் ஆற்றில் யோவானால் இயேசு ஞானஸ்நானம் பெற்ற நிகழ்வு"),
    "transfiguration": ("மாற்றுருவாக்கம்", "மலையில் இயேசு மாற்றுருவாக்கம் அடைந்த நிகழ்வு"),
    "last-supper": ("இறுதி இரவு உணவு", "சிலுவைக்கு முன் சீடர்களுடன் இயேசு உண்ட இறுதி உணவு"),
    "washing-of-the-feet": ("பாதம் கழுவுதல்", "சீடர்களின் கால்களை இயேசு கழுவிய நிகழ்வு"),
    "agonY-in-the-garden": ("எக்கேமனி தோப்பில் வேதனை", "எக்கேமனி தோப்பில் இயேசு ஜெபித்த நிகழ்வு"),
    "arrest-of-christ": ("இயேசு கைது", "கெத்சமனி தோப்பில் இயேசு கைது செய்யப்பட்ட நிகழ்வு"),
    "trial-of-christ": ("இயேசுவின் விசாரணை", "பிலாத்து முன் இயேசு விசாரிக்கப்பட்ட நிகழ்வு"),
    "flagellation": ("சவடியடி", "இயேசு சவடியால் அடிப்பட்ட நிகழ்வு"),
    "crowning-with-thorns": ("முள்ளெலும்பு கிரீடம்", "இயேசுவுக்கு முள் கிரீடம் அணிவித்த நிகழ்வு"),
    "way-of-the-cross": ("சிலுவைச் சுமந்தோட்டம்", "கல்கத்தா மலைக்கு இயேசு சிலுவையைச் சுமந்த பயணம்"),
    "crucifixion": ("சிலுவை மரணம்", "கல்வரி மலையில் இயேசு சிலுவையில் மரணம் அடைந்த நிகழ்வு"),
    "pieta": ("பியேத்தா", "சிலுவையிலிருந்து இறங்கிய இயேசுவை மரியாள் அணைத்தல்"),
    "lamentation": ("இரங்கல்", "இயேசுவின் உடலுக்காக மக்கள் இரங்கிய நிகழ்வு"),
    "entombment": ("அடக்கம்", "இயேசுவின் உடல் கல்லறையில் அடக்கம் செய்யப்பட்ட நிகழ்வு"),
    "resurrection": ("உயிர்த்தெழுதல்", "மூன்றாம் நாளில் இயேசு உயிர்த்தெழுந்த நிகழ்வு"),
    "noli-me-tangere": ("மரியாளைச் சந்தித்தல்", "உயிர்த்த பின் இயேசு மரியா மகதலேனாவைச் சந்தித்த நிகழ்வு"),
    "ascension": ("விண்ணேற்றம்", "இயேசு விண்ணுலகில் ஏறிய நிகழ்வு"),
    "pentecost": ("பெந்தெகொஸ்தே", "சீடர்கள் மேல் பரிசுத்த ஆவியானவர் இறங்கிய நிகழ்வு"),
    "last-judgment": ("இறுதித் தீர்ப்பு", "இறுதித் தீர்ப்பு நாளின் காட்சி"),
    "dormition": ("மரியாளின் இறப்பு", "மரியாள் உறங்கிய நிகழ்வு"),
    "assumption": ("மரியாளின் விண்ணேற்பு", "மரியாள் விண்ணுலகில் ஏற்றுக்கொள்ளப்பட்ட நிகழ்வு"),
    "creation": ("படைப்பு", "தேவன் உலகைப் படைத்த நிகழ்வு"),
    "expulsion": ("ஏதேனிலிருந்து வெளியேற்றம்", "ஆதாமும் ஏவாளும் ஏதேன் தோட்டத்திலிருந்து வெளியேற்றப்பட்ட நிகழ்வு"),
    "cain-and-abel": ("காயினும் ஏபேலும்", "காயினும் ஏபேலும் செய்த நிகழ்வு"),
    "noahs-ark": ("நோவாவின் பேழை", "நோவா பேழையில் வெள்ளத்திலிருந்து காப்பாற்றப்பட்ட நிகழ்வு"),
    "tower-of-babel": ("பாபேல் கோபுரம்", "பாபேல் கோபுரம் கட்டிய நிகழ்வு"),
    "covenant-of-the-rainbow": ("வானவில்லை உடன்படிக்கை", "நோவாவுக்கு தேவன் வானவில்லை உடன்படிக்கை அளித்த நிகழ்வு"),
    "sacrifice-of-isaac": ("இஸாக்கை பலி ஒப்புக்கொடுத்தல்", "ஆபிரகாம் இஸாக்கை பலி ஒப்புக்கொடுக்கப் போன நிகழ்வு"),
    "jacobs-ladder": ("யாக்கோபின் ஏணி", "யாக்கோபுக்கு வானில் ஏணி காட்சியளித்த நிகழ்வு"),
    "joseph": ("யோசேப்பின் கதை", "யோசேப்பின் வாழ்க்கை நிகழ்வுகள்"),
    "finding-of-moses": ("மோசே கண்டெடுக்கப்படல்", "நைல் ஆற்றில் மோசே குழந்தை கண்டெடுக்கப்பட்ட நிகழ்வு"),
    "burning-bush": ("எரியும் புதர்", "மோசேக்கு எரியும் புதரில் தேவன் தோன்றிய நிகழ்வு"),
    "plagues-of-egypt": ("எகிப்தின் பலிகள்", "எகிப்து மீது விழுந்த பத்து பாதகங்கள்"),
    "passover": ("பஸ்கா", "இஸ்ரவேலர் பஸ்கா கொண்டாடிய நிகழ்வு"),
    "exodus": ("எகிப்திலிருந்து வெளியேற்றம்", "இஸ்ரவேல் மக்கள் எகிப்திலிருந்து வெளியேறிய பயணம்"),
    "crossing-the-red-sea": ("செங்கடல் கடத்தல்", "மோசே செங்கடலைப் பிளந்து மக்களை கடத்திய நிகழ்வு"),
    "manna": ("மன்னா", "பாலைவனத்தில் வானத்திலிருந்து மன்னா பொழிந்த நிகழ்வு"),
    "water-from-the-rock": ("பாறையில் நீர்", "பாறையைத் தட்டி மக்களுக்கு நீர் ஊற்றிய நிகழ்வு"),
    "ten-commandments": ("பத்துக் கட்டளைகள்", "சீனாய் மலையில் மோசே பத்துக் கட்டளைகளைப் பெற்ற நிகழ்வு"),
    "golden-calf": ("பொன் கன்று", "இஸ்ரவேலர் பொன் கன்று உருவாக்கி வணங்கிய நிகழ்வு"),
    "brazen-serpent": ("வெண்கலப் பாம்பு", "பாம்பு கடித்தவர்களுக்காக வெண்கலப் பாம்பு உயர்த்தப்பட்ட நிகழ்வு"),
    "fall-of-jericho": ("எரிகோ வீழ்ச்சி", "எரிகோ நகர மதில்கள் விழுந்த நிகழ்வு"),
    "david-and-goliath": ("தாவீதும் கோலியாத்தும்", "இளைஞன் தாவீது கோலியாத்தை வீழ்த்திய நிகழ்வு"),
    "david-plays-the-harp": ("தாவீது இசை", "தாவீது சௌலுக்கு இசை வாசித்த நிகழ்வு"),
    "solomon": ("சாலமோனின் ஞானம்", "மன்னன் சாலமோனின் ஞானம் நிகழ்வுகள்"),
    "elijah": ("எலியா தீர்க்கதரிசி", "எலியா தீர்க்கதரிசியின் நிகழ்வுகள்"),
    "elijah-fed-by-ravens": ("காகங்களால் உணவு", "காகங்கள் எலியாவுக்கு உணவு கொண்டு வந்த நிகழ்வு"),
    "chariot-of-fire": ("நெருப்பு ரதம்", "எலியா நெருப்பு ரதத்தில் விண்ணேறிய நிகழ்வு"),
    "jonah": ("யோனா", "யோனா தீர்க்கதரிசியின் நிகழ்வுகள்"),
    "jonah-and-the-whale": ("யோனா மீனின் வயிற்றில்", "யோனா பெரும் மீனின் வயிற்றில் மூன்று நாட்கள் இருந்த நிகழ்வு"),
    "daniel-in-the-lions-den": ("சிங்கங்கள் குகையில் தானியேல்", "தானியேல் சிங்கங்கள் குகையில் காப்பாற்றப்பட்ட நிகழ்வு"),
    "fiery-furnace": ("எரியும் சூளை", "மூவரும் எரியும் சூளையில் காப்பாற்றப்பட்ட நிகழ்வு"),
    "writing-on-the-wall": ("சுவரில் எழுத்து", "பெல்சசர் அரண்மனை சுவரில் கை எழுதிய நிகழ்வு"),
    "esther": ("எஸ்தர்", "ராணி எஸ்தரின் தைரியம் நிகழ்வுகள்"),
    "judith": ("யூதித்", "யூதித் ஒலோபெர்னை வென்ற நிகழ்வு"),
    "job": ("யோபு", "யோபு துன்பத்தில் தேவனுக்கு விசுவாசமாக இருந்த நிகழ்வுகள்"),
    "prophets": ("தீர்க்கதரிசிகள்", "தீர்க்கதரிசிகளின் நிகழ்வுகள்"),
    "parables": ("உவமைகள்", "இயேசு சொன்ன உவமைக் கதைகள்"),
    "good-samaritan": ("நல்ல சமாரியன்", "நல்ல சமாரியன் உவமை"),
    "prodigal-son": ("புறமுதுகிட்ட குமாரன்", "புறமுதுகிட்ட குமாரன் உவமை"),
    "the-sower": ("விதைப்பவன்", "விதைப்பவன் உவமை"),
    "miracles": ("அதிசயங்கள்", "இயேசு செய்த அதிசயங்கள்"),
    "calming-the-storm": ("காற்றை அடக்கியது", "இயேசு கடல் கொந்தளிப்பை அடக்கிய நிகழ்வு"),
    "walking-on-water": ("நீர் மேல் நடந்தது", "இயேசு கடல் நீரின் மேல் நடந்த நிகழ்வு"),
    "feeding-the-five-thousand": ("ஐயாயிரம் பேருக்கு உணவு", "ஐந்து அப்பங்களால் ஐயாயிரம் பேரை திருப்திப்படுத்திய நிகழ்வு"),
    "raising-of-lazarus": ("லாசருவை உயிர்ப்பித்தல்", "இயேசு லாசருவை மரணத்திலிருந்து உயிர்ப்பித்த நிகழ்வு"),
    "healing-the-blind": ("குருடர் குணமாக்கல்", "இயேசு குருடருக்குக் கண் திறந்த நிகழ்வு"),
    "sermon-on-the-mount": ("மலைப் பிரசங்கம்", "இயேசு மலையில் அருள் உரையாற்றிய நிகழ்வு"),
    "lord-prayer": ("கர்த்தரின் ஜெபம்", "இயேசு சீடர்களுக்கு ஜெபம் கற்பித்த நிகழ்வு"),
    " cleansing-the-temple": ("கோவிலை சுத்தப்படுத்தல்", "இயேசு கோவிலில் வியாபாரிகளை வெளியேற்றிய நிகழ்வு"),
    "entry-into-jerusalem": ("எருசலேமில் நுழைவு", "கழுதையில் இயேசு எருசலேமில் நுழைந்த நிகழ்வு"),
    "emmaus": ("எம்மாவுஸ் பயணம்", "உயிர்த்த இயேசு எம்மாவுஸ் பயணிகளுக்குத் தோன்றிய நிகழ்வு"),
    "doubting-thomas": ("தோமாவின் விசுவாசம்", "தோமா இயேசுவின் காயங்களைத் தொட்ட நிகழ்வு"),
    "conversion-of-paul": ("பவுலின் மனமாற்றம்", "தமஸ்கு வழியில் பவுல் கடவுளைக் கண்ட நிகழ்வு"),
    "paul": ("அப்போஸ்தலன் பவுல்", "அப்போஸ்தலன் பவுலின் பணி நிகழ்வுகள்"),
    "apocalypse": ("வெளிப்படுத்துதல்", "யோவானுக்கு கிடைத்த வெளிப்படுத்துதல் காட்சிகள்"),
}

# book name -> tamil name (short)
BOOK_TA = {
    "Genesis":"ஆதியாகமம்","Exodus":"யாத்திராகமம்","Leviticus":"லேவியராகமம்","Numbers":"எண்ணாகமம்",
    "Deuteronomy":"உபதேசவாகமம்","Joshua":"யோசுவா","Judges":"நியாயாதிபதிகள்","Ruth":"ரூத்",
    "1 Samuel":"1 சாமுவேல்","2 Samuel":"2 சாமுவேல்","1 Kings":"1 இராஜாக்கள்","2 Kings":"2 இராஜாக்கள்",
    "1 Chronicles":"1 நாளாகமம்","2 Chronicles":"2 நாளாகமம்","Ezra":"எஸ்றா","Nehemiah":"நெகேமியா",
    "Esther":"எஸ்தர்","Job":"யோபு","Psalms":"சங்கீதம்","Proverbs":"நீதிமொழிகள்","Ecclesiastes":"பிரசங்கி",
    "Song of Solomon":"இன்றைய பாடல்","Isaiah":"யெசயா","Jeremiah":"எரேமியா","Lamentations":"புலம்பல்",
    "Ezekiel":"எசேக்கியேல்","Daniel":"தானியேல்","Hosea":"ஓசே","Joel":"யோவேல்","Amos":"ஆமோஸ்",
    "Obadiah":"ஒபதியா","Jonah":"யோனா","Micah":"மீகா","Nahum":"நாகூம்","Habakkuk":"ஆபகூக்",
    "Zephaniah":"செப்பனியா","Haggai":"ஆகாய்","Zechariah":"சகரியா","Malachi":"மலாக்கி",
    "Matthew":"மத்தேயு","Mark":"மாற்கு","Luke":"லூக்கா","John":"யோவான்","Acts":"அப்போஸ்தலர்",
    "Romans":"ரோமர்","1 Corinthians":"1 கொரிந்தியர்","2 Corinthians":"2 கொரிந்தியர்","Galatians":"கலாத்தியர்",
    "Ephesians":"எபேசியர்","Philippians":"பிலிப்பியர்","Colossians":"கொலோசெயர்","1 Thessalonians":"1 தெசலோனிக்கேயர்",
    "2 Thessalonians":"2 தெசலோனிக்கேயர்","1 Timothy":"1 தீமோத்தேயு","2 Timothy":"2 தீமோத்தேயு","Titus":"தீத்து",
    "Philemon":"பிலேமோன்","Hebrews":"எபிரெயர்","James":"யாக்கோபு","1 Peter":"1 பேதுரு","2 Peter":"2 பேதுரு",
    "1 John":"1 யோவான்","2 John":"2 யோவான்","3 John":"3 யோவான்","Jude":"யூதா","Revelation":"வெளிப்படுத்துதல்",
}

ERA_TA = {"renaissance":"மறுமலர்ச்சி","baroque":"பரோக்","medieval":"இடைக்கால","gothic":"கோதிக்",
          "northern-renaissance":"வடக்கு மறுமலர்ச்சி","printmaking":"அச்சுக்கலை","drawing":"வரைபடம்",
          "manuscript":"கையெழுத்து","sculpture":"சிற்பம்","modern":"நவீன","19th century":"19ஆம் நூற்றாண்டு"}

def ta_scene(slug_list):
    for s in slug_list or []:
        if s in SCENES_TA:
            return SCENES_TA[s]
    return None

def load_rejects():
    """rejected file slugs (download filenames) from verdicts + sheet sidecars."""
    rej = set()
    vp = os.path.join(REV, "verdicts.txt")
    if not os.path.exists(vp):
        return rej
    for line in open(vp, encoding="utf-8"):
        m = re.match(r"(r\d+) reject:\s*(.*)", line.strip())
        if not m:
            continue
        sheet, nums = m.group(1), m.group(2)
        sp = os.path.join(REV, "sheets", sheet + ".json")
        if not os.path.exists(sp) or nums == "none":
            continue
        mp = {e["n"]: e["file"] for e in json.load(open(sp, encoding="utf-8"))}
        for n in nums.split(","):
            n = n.strip()
            if n and int(n) in mp:
                rej.add(mp[int(n)])
    return rej

def main():
    arts = {}
    for line in open(os.path.join(DS, "artworks.jsonl"), encoding="utf-8"):
        a = json.loads(line)
        arts[a["artwork_slug"]] = a
    maps = [json.loads(l) for l in open(os.path.join(DS, "verified-mappings.jsonl"), encoding="utf-8")]
    cand = {}
    for m in maps:
        if m.get("suppressed"):
            continue
        e = cand.setdefault(m["artwork_slug"], {"maps": []})
        e["maps"].append({"b": m["book"], "c": m["chapter"],
                          "ref": m["reference"], "rel": m["relationship_type"]})
    rejects = load_rejects()
    st = json.load(open(os.path.join(REV, "state.json"), encoding="utf-8"))
    reviewed = set(st["reviewed"])

    entries = []
    skipped_unreviewed = skipped_rejected = 0
    for slug, e in sorted(cand.items()):
        fn = slug + ".jpg"
        p = os.path.join(DL, fn)
        if not (os.path.exists(p) and os.path.getsize(p) > 5000):
            continue
        if slug in rejects or fn in rejects:
            skipped_rejected += 1
            continue
        if fn not in reviewed:
            skipped_unreviewed += 1
            continue
        a = arts[slug]
        sc = ta_scene(a.get("scene_slugs"))
        ta_title, ta_desc = (sc[0], sc[1]) if sc else (a["title"], None)
        refs = []
        for m in e["maps"]:
            refs.append({"book": m["b"], "ch": m["c"],
                         "ta_book": BOOK_TA.get(m["b"], m["b"]),
                         "ref": m["ref"], "rel": m["rel"]})
        ta_desc_full = ta_desc or ""
        if refs and ta_desc_full:
            ta_desc_full += " — " + BOOK_TA.get(refs[0]["book"], refs[0]["book"]) + " " + str(refs[0]["ch"])
        entries.append({
            "id": slug,
            "title": a["title"],
            "artist": a["artist_name"],
            "year": a.get("year"),
            "era": a.get("era"),
            "license": a.get("rights_code"),
            "source": a.get("source"),
            "srcPage": a.get("source_record_url"),
            "img": a.get("image_url"),
            "scenes": a.get("scene_slugs") or [],
            "ta": {"title": ta_title,
                   "desc": ta_desc_full,
                   "era": ERA_TA.get(a.get("era") or "", "")},
            "refs": refs,
        })
    man = {"v": 1, "art": entries}
    os.makedirs(OUT_APP, exist_ok=True)
    with open(os.path.join(OUT_APP, "media_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, separators=(",", ":"))
    print(f"manifest entries={len(entries)} rejected_skipped={skipped_rejected} pending_review={skipped_unreviewed}")
    print("size: %.1f MB" % (os.path.getsize(os.path.join(OUT_APP, "media_manifest.json")) / 1e6))

if __name__ == "__main__":
    main()
