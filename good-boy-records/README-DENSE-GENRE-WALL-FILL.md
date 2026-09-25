# GBR Dense Genre Wall Fill Patch

This patch fixes the dense wall so it actually fills the scene.

## Changes
- chooses wall rows/columns from the real track count and viewport aspect ratio
- scales sleeves so the wall uses the full height/width instead of bunching at the top
- centres incomplete final rows cleanly
- keeps the selected sleeve enlarged with local ripple displacement
- keeps genre-ordered sequencing from the YAML-derived catalogue sort

## Apply
Extract over the dense genre-wall build and replace the matching files.
