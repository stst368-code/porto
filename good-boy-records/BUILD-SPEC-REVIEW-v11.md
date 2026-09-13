# Review of Good Boy Records v11 Build Specification

## Review result

The specification is internally consistent and directly addresses the failures visible in the v10 screenshots: overlapping modules, album art not appearing on the wheel, insufficient magazine geometry, controls compressed into tiny button groups, accidental coupling between genre browsing and playback, and repeated CSS patches fighting one another.

## Decisions confirmed

### 1. Use v9 as visual direction, not as implementation
The v9 hierarchy is stronger than the v10 three-column experiments, but copying its implementation wholesale would reintroduce old constraints. The rebuild therefore keeps the v9 two-column magazine/rack concept while using new markup, new layout CSS and a new player controller.

### 2. Keep vertical scrolling on short screens
Trying to force every studio module above the fold caused most of the v10 compression. The rebuilt desktop may extend below one viewport. A music interface being 150 pixels taller is preferable to turning every control into a postage stamp.

### 3. Genre selection is definitively browse-only
This is the most important behavioural boundary. UI theme and magazine art may change with browse genre, but the current audio source remains untouched until a song card is explicitly selected.

### 4. Do not use a flip interaction for the song description
The description is persistent below the album cover. Technical metadata can be shown in a contained details panel. This removes the conflict between “artwork-first” and “description should be readable without flipping”.

### 5. Separate every visual analyser from every control panel
One canvas per visual purpose, each inside an overflow-hidden well. EQ is DOM controls only. This directly prevents the “EQ visualiser inside the VU meters” failure mode.

### 6. The magazine must prioritise artwork
The track cards are album-art cartridges, not text labels. The wheel centre is deliberately small and the cards are sized from available circumference. Ten slots are the invariant.

### 7. Audio dedupe remains part of v11, not an optional optimisation
The authoritative-local-copy rule is architecture, not cleanup. Tests must fail if normal imported track audio reappears under `assets/audio/tracks` or `assets/audio/showcase`.

## Risks and mitigations

### Unknown real catalogue breadth
The local test archive contains fewer releases than the user's live showcase. The renderer therefore must be data-driven and tested with a synthetic ten-song/six-genre catalogue in addition to the real fixture.

### Browser-dependent Web Audio behaviour
Direct `file://` playback cannot reliably use `createMediaElementSource`. Local preview is already HTTP through `tools/serve.py`; EQ is enabled there and gracefully disabled on unsupported contexts.

### Artwork paths
The imported catalogue points to prepared artwork under `assets/img/sleeves`, while audio points directly into `showcase`. The wheel and loaded release must use the prepared artwork path and never attempt to infer artwork beside the audio file.

### Existing document/folder feature surface
The rebuild must not rewrite Parameter Lab or workflow viewer unless required. Their existing content-generation code remains isolated from the new player controller.

## Specification amendment after review

One additional requirement is added: the desktop magazine should show all ten positions physically but does **not** need all ten labels to be simultaneously readable. The active/load-gate card and its nearest neighbours receive visual priority. This prevents making the cards too small merely to show ten full labels at once.

No other requirement is removed or weakened.

## Visual QA amendment

The synthetic ten-song / six-genre stress render exposed one final geometry issue: keeping every card perfectly upright made the wheel read as crowded even when the cards did not mathematically collide. The final magazine therefore rotates non-selected artwork cartridges tangentially around the wheel and keeps only the load-gate selection upright. The magazine desktop minimum was raised to 490 px and the single-column breakpoint moved to 1280 px. This gives the ten physical positions enough circumference instead of shrinking them into labels.

The final renders were inspected at 1920×1080, 1680×1050, 1440×900, 1366×768, 1024×768 and 390×844. The intended behaviour is vertical page scrolling on short viewports, never module compression or overlap.

## v11.1 review

The v11.0 screenshot review showed three remaining structural problems: the wide visualiser forced the loaded release down, the EQ controls consumed a second right-column module without adding useful browsing value, and the transport/action buttons lacked a clear grouping. v11.1 removes the EQ controls, moves the visualiser into the same fixed-width output column as the VU meters, raises the loaded release into the top row, and makes lyrics a full-width bottom instrument.

Playback was also hardened. The analyser is now optional and attached only after native audio playback succeeds; its audible route is established before optional metering branches. This specifically prevents a partial Web Audio setup from taking ownership of the media element and leaving it silent.
