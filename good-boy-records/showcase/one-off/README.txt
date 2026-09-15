GOOD BOY RECORDS - ONE-OFF BANK

Use this folder for standalone songs that are NOT part of the normal six-cut
metal/pop/country/disco/orchestral/special matrix.

Each one-off gets its own folder:

showcase/one-off/
  johnny-three-fridges/
    johnny-three-fridges.yaml
    johnny-three-fridges.png
    johnny-three-fridges.mp3
    johnny-three-fridges.flac          (optional)
    johnny-three-fridges.lyrics.json   (optional)

The YAML uses the same generation fields as an ordinary version YAML.
Required/recommended:

  title: johnny-three-fridges
  version: murder-ballad   # optional display label; defaults to One-Off
  model: minimax H3
  ... normal generation metadata ...
  inspiration:
  inspirationyt:
  story:
  caption: |
    ...
  lyrics: |
    ...

The folder is a separate public ten-position bank. One-off songs do NOT consume
normal 10 x 6 song positions and do NOT need empty genre variants.

ONE-OFF behaviour:
- selectable from the seventh ONE-OFF control
- desktop/mobile wheel/rail remains ten positions
- previous/next and non-shuffle autoplay stay inside ONE-OFF
- shuffle includes ONE-OFF alongside the normal six genres
- mobile single tap loads; double tap loads/plays as normal
- MP3/FLAC, artwork, lyrics, YAML details and Media Session all work normally
