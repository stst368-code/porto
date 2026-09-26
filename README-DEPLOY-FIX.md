# Porto / Good Boy Records deploy fix

Copy this package into the **porto repository root**, not into `good-boy-records` alone.

It fixes two deployment problems:

1. Sonic Landscape is stored as a stable source file at `good-boy-records/templates/landscape.html`, so deleting/rebuilding `_site` no longer deletes the only copy.
2. After the normal GBR build, the workflow deliberately overwrites both `_site/landscape.html` **and `_site/index.html`** with Sonic Landscape. Therefore `/porto/good-boy-records/` loads Sonic Landscape rather than the previous generated player.

## Files

- `.github/workflows/portfolio-pages.yml` — repo-root Pages workflow
- `good-boy-records/templates/landscape.html` — Sonic source page
- `good-boy-records/BUILD-SONIC-LANDSCAPE.bat` — corrected local builder
- `good-boy-records/tools/build_genre_catalogue.py`
- `good-boy-records/templates/music_genre_taxonomy.csv`
- `CLEAN-PORTO-LEGACY.ps1` — conservative cleanup script

## Local verification

From `porto\good-boy-records`:

```bat
BUILD-SONIC-LANDSCAPE.bat
py -3 -m http.server 8000
```

Open `http://localhost:8000/_site/`.

The page title should be `Good Boy Records — Sonic Landscape`.

## Cleanup

From the porto root, preview first:

```powershell
.\CLEAN-PORTO-LEGACY.ps1
```

Then remove the obvious legacy files:

```powershell
.\CLEAN-PORTO-LEGACY.ps1 -Apply
```

To also remove generated `_site` / `_pages` before a completely fresh rebuild:

```powershell
.\CLEAN-PORTO-LEGACY.ps1 -Apply -CleanGenerated
```
