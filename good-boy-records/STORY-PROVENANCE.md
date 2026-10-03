# Behind the Song provenance

The catalogue now preserves two creative layers for every normal showcase track:

- `provenance.song`: `story`, `inspiration`, `inspirationUrl`, and the composition YAML URL.
- `provenance.version`: the same fields from the selected genre/version YAML.

The player exposes these through the **Story** button. The drawer renders **The Song** first and **This Version** second. Empty fields are omitted and version text identical to song-level text is not repeated.

Existing `story` and `style.inspiration` fields remain in the catalogue for backward compatibility.

No YAML schema changes are required.
