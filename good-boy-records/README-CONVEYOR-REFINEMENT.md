# GBR Conveyor Refinement Patch

This patch refines the conveyor layout to address the latest feedback:

- tighter entry/exit throat into the main loop
- higher album density on the conveyor
- smaller small-cover size for a cleaner browse loop
- smoother-looking idle crawl
- desktop top bar removed to reclaim vertical space
- desktop layout compressed so the lyrics remain visible in a single view

## Included files

- `assets/css/studio.css`
- `assets/js/studio.js`
- `tools/test_player.py`

## Apply

Extract over the cleaned GBR project root and replace the matching files.

## Main tuning changes

- conveyor visible window: `20`
- idle speed: `0.06`
- focus slot moved deeper into the loop for a better right-side reading point
- slimmer conveyor track geometry
- desktop console width reduced slightly
- lyrics row reduced to `118px` (`106px` on shorter desktop heights)
- desktop top bar hidden
