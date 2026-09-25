# GBR Cover Wall Layout Patch

This patch replaces the desktop conveyor browser with a denser CD-wall / cover-wall browser.

## What changed

- desktop conveyor removed in favour of a 5 x 4 cover wall
- the selected browse item expands in place
- nearby covers are pushed outward with a controlled ripple effect
- no text is shown on the small wall covers
- desktop top bar and catalogue bar are hidden to recover vertical space
- desktop layout is compressed so the wall, player and lyrics fit in one view
- the right-side console and bottom lyrics remain in place
- mouse wheel / arrow keys / drag now move the wall selection instead of drifting a conveyor path
- clicking a visible cover still loads that track

## Included files

- `assets/css/studio.css`
- `assets/js/studio.js`
- `tools/test_player.py`

## Apply

Extract over the cleaned GBR project root and replace the matching files.
