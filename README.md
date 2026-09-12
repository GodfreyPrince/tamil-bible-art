# Tamil Bible Art Index (தமிழ் பைபிள் கலைப் படங்கள்)

A curated, scripture-linked index of **2,077 public-domain Biblical artworks + 228 Biblical maps** with
Tamil titles and descriptions, built for the **தமிழ் பைபிள் (Tamil Bible)** Android app.

- **Source dataset:** [jaedenschafer/bible-art-scripture-index](https://github.com/jaedenschafer/bible-art-scripture-index) (CC0)
- **Human review:** every included image was visually inspected; ~82 low-quality or
  non-biblical items were rejected out of 3,056 candidates.
- **Scripture links:** from the source dataset's *verified* tier (3,142 mappings),
  resolved to book + chapter so readers can pull up art while reading any chapter.
- **Tamil metadata:** auto-composed from scene + passage (title/description in Tamil,
  era label in Tamil where known).

## Files
- `manifest/media_manifest.json` — the app-facing manifest (one entry per artwork:
  id, title, artist, year, era, license, source, image URL, scenes, refs, `ta.*` Tamil strings)
- `scripts/` — the pipeline used to build it:
  - `dataset_download.py` — dataset → filtered candidates → parallel thumb download
  - `next_sheet.py` — incremental 48-up contact sheets for human visual QA
  - `build_manifest.py` — applies review verdicts + composes Tamil metadata → manifest
  - `make_tamil_asset.py` / `make_bsi_asset.py` — the Bible text assets (IRV + BSI)

## How the app uses this
The manifest ships inside the APK (metadata is fully offline). **Images are only
loaded while online**, straight from the public-domain institutions that host them
(Met Museum, Rijksmuseum, Wikimedia, Yale, museums' IIIF endpoints...). Users can
flip a switch ("படங்களைக் கைபேசியில் சேமி") to keep every viewed image stored on the
device; otherwise images live in a private cache only.

## Licenses
Artwork metadata and selection logic: CC0. Each image keeps its original rights
(`rights_code` in the manifest: PDM-1.0, CC0, CC-BY, etc.) — all are open-license or
public domain as recorded by the source institutions.
