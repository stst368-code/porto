# Good Boy Records — Sonic Landscape v2 Fix

Apply this archive at the `porto` repository root.

## Fixed

- Artwork now understands GBR's native `artwork.base` catalogue shape and resolves to `assets/img/sleeves/<base>-1280.webp`.
- Genre map no longer uses hashed/random vertical placement.
- Parent genres occupy stable ordered lanes; child genres advance through taxonomy order left-to-right.
- Tactile GBR controls restored in the Sonic interface:
  - master power switch
  - rotary volume control
  - rotary lights control
  - twin analogue VU meters
  - tactile transport buttons
  - shuffle
  - progress/seek
  - control click sounds
  - power-off darkening/stop behaviour
- Default volume and lights are both 50%.
- The root Pages workflow remains the authoritative deployment path and still makes Sonic Landscape the `/good-boy-records/` index.

## Deploy

Commit/push the extracted files from the `porto` root. GitHub Actions will rebuild the normal GBR catalogue/assets, enrich the catalogue with the taxonomy, and publish `templates/landscape.html` as `good-boy-records/index.html`.
