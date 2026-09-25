# GBR Dense Genre Wall

This replaces the spaced 5x4 wall with a dense sleeve mosaic closer to the supplied reference.

## Layout

- desktop sleeve wall fills the entire browser panel
- album covers touch edge-to-edge with no decorative gutters
- the number of columns/rows is calculated from the live panel dimensions
- outer tiles can crop slightly so the wall reads as continuous rather than framed
- the selected cover expands to 1.72x in-place
- surrounding covers are displaced outward in a 3-ring ripple
- right-side player/console remains intact
- lyrics remain pinned into the bottom row so the full player stays in one viewport

## Genre ordering

Genre ordering is now derived from each source YAML rather than filename order.

`tools/import_showcase.py` analyses:

- `genre`
- `version`
- `caption`
- `story`

The caption carries most of the musical information, so hybrid descriptions receive a weighted position between broad families. The continuum is roughly:

orchestral/classical -> folk/acoustic -> country/Americana -> rock -> punk/ska -> metal -> industrial/dark -> electronic/club -> disco -> pop -> R&B/soul -> funk -> hip-hop/trap/grime/drill -> jazz/crooner -> theatre/experimental

The importer writes `genreFamily`, `genrePosition`, and `genreTags` into generated track metadata. `build_catalogue.py` then sorts by that continuum. Tracks with no useful style metadata inherit the median genre position of other versions of the same composition.

## Files

- `assets/css/studio.css`
- `assets/js/studio.js`
- `tools/import_showcase.py`
- `tools/build_catalogue.py`
- `tools/test_player.py`

## Apply

Extract over the current cleaned GBR project root, replacing the matching files.

Then run the normal `BUILD-SHOWCASE.bat` so the source YAMLs are re-imported and the catalogue is rebuilt in genre order.
