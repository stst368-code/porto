# Good Boy Records — Sonic Landscape

This is a working build of the supplied Sonic Landscape concept, upgraded from a visual demo into a real GBR player.

## What is included

- `_site/landscape.html` — interactive genre landscape player
- `_site/index.html` — same player, usable as a standalone site root
- `tools/build_genre_catalogue.py` — enriches the existing GBR manifest/catalogue with taxonomy metadata
- `templates/music_genre_taxonomy.csv` — the current 2026-09-26 taxonomy
- `BUILD-SONIC-LANDSCAPE.bat` — Windows build entry point

## What was fixed from the supplied concept

- real `<audio>` playback rather than a fake play state
- real Web Audio analyser data for the spectrum and level displays
- catalogue schema tolerance: top-level track lists and `{ "tracks": [...] }` catalogues both work
- audio/artwork URL discovery across the common GBR field shapes
- actual track duration/progress and volume control
- click, mouse wheel, keyboard, shuffle and mobile swipe navigation
- genre sorting driven by the taxonomy order
- stable genre-space positioning rather than every track being evenly spaced around one circle
- same-composition variants are visually related in the landscape
- taxonomy matching reports unmatched variants instead of silently pretending everything matched

## Build inside the existing GBR repository

Copy this package over the root of `good-boy-records`, then run:

```bat
BUILD-SONIC-LANDSCAPE.bat
```

The script looks for the catalogue input in this order:

1. `showcase-manifest.json`
2. `data/catalogue.json`
3. `catalogue.json`

If `tools/import_showcase.py` already exists, it is run first.

Then serve the repository root:

```bat
py -3 -m http.server 8000
```

Open:

`http://localhost:8000/_site/landscape.html`

## Catalogue output

`_site/catalogue.json` preserves the existing track fields and adds:

- `genre.parent_genre`
- `genre.child_genre`
- `genre.cluster`
- `genre.parent_colour`
- `genre.child_colour`
- `genre.position`
- `genre.taxonomy_order`
- `audio_url`
- `artwork_url`
- `variants`

The frontend will still load if a few genres are unmatched; those tracks are marked `Unclassified` and listed in `unmatched_genres` in the generated JSON.
