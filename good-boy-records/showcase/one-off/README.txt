GOOD BOY RECORDS — ONE-OFF BANK

Put standalone songs here when they will not participate in the normal six-genre matrix.
The ONE-OFF bank is independent from the normal 10 song positions.

There is NO total one-off limit. The UI presents them in magazines of 10.
Use the compact MAGAZINE x/y control, or keep scrolling the wheel past an edge, to move between pages.
Playback previous/next and autoplay continue across the complete one-off collection, not just the visible page.

Basic single-side example:

showcase/one-off/johnny-three-fridges/
    johnny-three-fridges.yaml
    johnny-three-fridges.png
    johnny-three-fridges.mp3
    johnny-three-fridges.flac        optional
    johnny-three-fridges.lyrics.json optional

A/B/C sides are supported and share one magazine position. You can declare the side in YAML:

    title: johnny-three-fridges
    side: B

or use -a / -b / -c on the YAML filename or containing directory and the importer will infer it.
A practical same-folder layout is:

showcase/one-off/johnny-three-fridges/
    johnny-three-fridges.yaml       # Side A by default
    johnny-three-fridges.mp3
    johnny-three-fridges.png

    johnny-three-fridges-b.yaml     # inferred Side B
    johnny-three-fridges-b.mp3
    johnny-three-fridges-b.png      # optional; can also point cover: at shared artwork

    johnny-three-fridges-c.yaml     # inferred Side C
    johnny-three-fridges-c.mp3
    johnny-three-fridges-c.png

All sides MUST use the same title value if they are meant to share one position.
Version / one_off_label may differ per side if desired.

Supported public sides: A, B, C.
