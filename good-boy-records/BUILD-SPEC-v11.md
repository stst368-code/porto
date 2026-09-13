# Good Boy Records v11 — Clean Rebuild Specification

## 1. Objective

Rebuild the Good Boy Records showcase player as a coherent, stable studio instrument rather than continuing the v10 patch stack. The visual baseline is the older v9 brown/brass hi-fi design, but the implementation is new and must retain the useful v10 catalogue, build, analysis, lyrics, Side A/B, Parameter Lab and curated-showcase functionality.

The finished site must feel deliberate at 1920×1080 and remain usable down through laptop widths without panels overlapping, controls collapsing into one another, canvases painting outside their own modules, or the rotary magazine turning into dead space.

## 2. Non-negotiable user requirements

1. Return to the older Good Boy Records visual language: dark brown/black chassis, warm brass/amber hardware, analogue hi-fi / studio equipment character.
2. The page must not be bland. It needs depth, tactile hardware, engraved legends, bezels, panel divisions, indicator lamps, physical knobs/switches and restrained texture.
3. The rotary magazine represents **10 songs**, not 60 versions.
4. Six genre bank buttons select which version of those ten songs is shown: Metal, Pop, Country, Disco, Orchestral, Special.
5. Changing genre is a **browse action only**. It must not pause, seek, reload, replace or otherwise disturb the currently playing audio.
6. When the browse genre changes, the artwork shown on every populated magazine slot changes to that genre's corresponding album artwork.
7. The currently playing master is playback state, not browse state. It remains clearly identified even if the user browses another genre.
8. Album artwork must be visible on the magazine cards. Missing artwork must fall back to the GBR placeholder rather than an empty black card.
9. The rotary magazine must have enough room for its artwork cards. It must not be cramped or visually dominated by empty centre area.
10. The primary loaded album cover remains large and readable.
11. The song description/story lives directly under the loaded album cover. It is not hidden behind a Story tab and is not placed only on a reverse face.
12. Technical generation details remain accessible without replacing the description. YAML remains directly accessible.
13. Reference and Unreleased/ATR content remain available in contained drawers/panels. They must never appear behind or over unrelated modules because of stacking bugs.
14. Program spectrum, stereo VU meters, five-band EQ and output volume are separate physical modules. The spectrum/EQ visualisation must never paint inside the VU meters.
15. Five EQ controls: 60, 250, 1K, 4K, 12K, with FLAT reset and actual Web Audio filtering when available.
16. Volume is presented as a styled physical control, not a naked browser slider. A visible level/scale must communicate current volume.
17. Lyrics are always on. No lyrics enable/disable toggle.
18. Lyrics display one current word prominently, with the current line in smaller text underneath.
19. MP3/FLAC selection, shuffle, previous, play/pause, next, seek and optional Side A/B selection remain available.
20. Folder/document navigation (About, Origin, Tech, Music Workflow, Output Analysis, Parameter Lab, Requests) remains, with buttons spaced and readable rather than bunched together.
21. Parameter Lab and workflow/document viewers remain functional.
22. Responsive layout must deliberately change modes rather than merely shrinking desktop geometry until it breaks.
23. No cumulative legacy CSS overrides. v11 player styling is one new stylesheet with a documented layout contract.
24. No cumulative legacy player JS. v11 player behaviour is one new controller with explicit browse state and playback state.

## 3. Source and storage architecture

### 3.1 Authoritative media

`showcase/` is the only authoritative local copy of curated MP3/FLAC/ATR media.

Normal local build and preview must not copy song audio into `assets/audio/tracks`, `assets/audio/showcase`, `assets/audio/atr`, or `_site`.

### 3.2 Local preview

Catalogue audio URLs point directly into `showcase/...`.

`START-SITE.bat`:
1. cleans stale deployment output and legacy audio caches;
2. imports metadata/artwork/lyrics only;
3. builds catalogue and page;
4. runs tests/checks;
5. serves repository root.

### 3.3 Deployment

`BUILD-PAGES.bat` deliberately creates `_site/` and copies only the audio files referenced by `data/catalogue.json`, preserving their catalogue-relative paths.

Expected copies:
- local development: 1 authoritative audio copy;
- staged deployment: source + `_site` copy;
- never a permanent third middle copy.

## 4. Data contract

Retain the v10.5 catalogue shape:

- `variantSlots`: `metal`, `pop`, `country`, `disco`, `orchestral`, `special`
- maximum ten compositions/songs
- `song.sideIds[slot].A/B`
- track generation/model metadata
- MP3/FLAC sources
- artwork base/alt/placeholder
- raw lyrics + optional `gbr-word-lyrics-v1` timing sidecar
- song common story/inspiration
- ATR archive entries

The UI must work when only some songs or genres exist. Missing cuts are shown as unavailable magazine slots, never fabricated.

## 5. State model

The controller has four deliberately separate state domains:

### Browse state
- `browseGenre`
- `wheelIndex`

Genre changes and wheel rotation alter only browse state.

### Playback state
- `playingTrackId`
- `playingSongId`
- `playingGenre`
- `playingSide`
- `isPlaying`
- `quality`
- `shuffle`

Browse state must never implicitly mutate playback state.

### Audio/control state
- volume
- five EQ gain values
- power state
- lamp brightness

### Content-panel state
- technical details open/closed
- reference drawer open/closed
- ATR drawer open/closed
- top folder drawer state

## 6. Desktop layout contract

Target: ≥ 1281px wide.

The page is a two-column instrument, following v9's successful hierarchy:

```
┌─────────────────────────────────────────────────────────────┐
│ BRAND / STATUS                                              │
├─────────────────────────────────────────────────────────────┤
│ FOLDER NAV                                                  │
├──────────────────┬──────────────────────────────────────────┤
│                  │ PROGRAM SPECTRUM                         │
│ ROTARY MAGAZINE  ├──────────────────────┬───────────────────┤
│                  │ LOADED RELEASE       │ OUTPUT / VU       │
│ genre bank       │ large artwork        │ 2 analogue meters │
│ lamp             │ title / description  │                   │
│ 10 art cards     │ ref / ATR            ├───────────────────┤
│                  │                      │ EQ                │
│                  │                      ├───────────────────┤
│                  │                      │ VOLUME            │
│                  ├──────────────────────┴───────────────────┤
│                  │ TRANSPORT                                │
│                  ├──────────────────────────────────────────┤
│                  │ CURRENT WORD                             │
│                  │ current lyric line                       │
└──────────────────┴──────────────────────────────────────────┘
```

Geometry rules:
- magazine column: `clamp(490px, 34vw, 620px)`;
- rack gets the remaining width;
- rack uses grid rows: spectrum / working row / transport / lyrics;
- working row uses `minmax(420px, 1.2fr)` for loaded release and `minmax(330px, .85fr)` for console;
- canvases live in fixed, overflow-hidden instrument wells;
- no absolute-positioned module may cross a module boundary;
- artwork uses `aspect-ratio: 1` and `object-fit: cover`;
- page may scroll vertically when viewport height is short. Do not crush modules to force one-screen fit.

## 7. Magazine design

- Round physical carousel with ten equally spaced album-art cartridges.
- Cards are portrait-ish, approximately 112×142 at normal desktop scale.
- Artwork fills each card behind a readable lower label strip.
- Wheel radius is calculated from its container so adjacent cards cannot overlap.
- Wheel has a restrained centre hub, not a giant blank disc.
- Selected/browse position sits at the right-side load gate.
- Mouse wheel, drag and previous/next rotation supported.
- Clicking a populated card loads that browsed genre cut for playback.
- A populated card can indicate A/B availability without becoming two wheel positions.
- Empty/unbuilt cuts are dimmed and disabled.
- Genre bank buttons sit above the wheel and have generous separation and hit areas.
- Lamp control is large enough to see and manipulate.

## 8. Loaded release panel

Default view:
- artwork
- song title
- variant + side
- description/story directly beneath artwork
- inspiration summary
- Reference and Unreleased buttons

Technical metadata is opened by a DETAILS control into a contained internal panel/drawer. It must include model, DIT, text encoder, encoder CFG/seed, Top K, sampler, scheduler, sampler CFG/seed and steps when present.

YAML is a normal external/open-file link when present.

## 9. Audio console

### Program spectrum
A dedicated top module. 24 segmented bands. It uses only its own canvas bounds.

### VU meters
Two analogue meters rendered side by side in their own dedicated canvas/module.

### EQ
Separate panel below VU. Five physical vertical faders. FLAT reset. No spectrum bars, canvas or analyser drawing inside this section.

### Volume
Separate panel below EQ. Large rotary knob plus a horizontal segmented level strip/readout. The native input may remain visually hidden as an accessible state/control source.

### Power
Small hardware toggle in console area. Power-off dims visual instruments but must not corrupt catalogue/player state.

## 10. Transport and lyrics

Transport is one row with comfortable spacing:
- Now Playing identity
- Shuffle
- Previous
- Play/Pause
- Next
- optional Side A/B
- seek track with elapsed/total
- MP3/FLAC

Lyrics module is always visible below transport:
- current word is the dominant element;
- current full line below;
- no lyric-history columns, no enable toggle;
- if word timing is unavailable, use line/word fallback timing rather than leaving the module empty.

## 11. Genre visual identity

All genres remain recognisably the same Good Boy Records machine, but physical treatment changes beyond colour:

- Metal: blackened steel, rivets, stamped legends, square controls.
- Pop: polished champagne/cream metal, softer corners, illuminated acrylic controls.
- Country: walnut veneer, aged brass, cream labels, radio-console detailing.
- Disco: smoked acrylic, chrome edges, segmented illumination, reflective faceplates.
- Orchestral: dark timber, engraved brass, ivory/cream instrument faces, slower visual damping.
- Special: laboratory/prototype treatment, grid marks, patch-panel cues, mismatched test-equipment hardware.

Artwork itself is never recoloured or filtered by genre.

## 12. Responsive modes

### 900–1280px
- magazine above or beside loaded release depending available width;
- console gets full-width row;
- no tiny desktop controls.

### <900px
- rotary wheel replaced with a horizontal snap rail of ten artwork cards for the selected genre;
- loaded release, analyser, VU, EQ, volume, transport and lyrics stack vertically;
- folder nav remains horizontally scrollable;
- every control retains at least a practical touch hit area.

## 13. Visual quality rules

- Hardware depth from borders, bevels, subtle highlight/shadow and restrained grain.
- No huge black dead zones.
- No text below ~10px equivalent at normal desktop rendering.
- No six-button groups squeezed into unusably tiny cells.
- No module relies on `z-index` to cover a neighbouring module.
- No decorative element may obscure an interactive control.
- Control labels must remain legible at 1366×768.

## 14. Testing / acceptance gates

Automated tests must cover:

1. catalogue six-slot contract;
2. maximum ten songs;
3. wheel has exactly ten physical positions;
4. wheel cards use catalogue artwork;
5. genre browse does not call audio load/play/pause/source mutation;
6. clicking a wheel card does load the matching browsed-genre track;
7. Side A/B stays on one physical song slot;
8. story/description exists below artwork;
9. spectrum, VU, EQ and volume are distinct modules;
10. one main audio element;
11. MP3/FLAC switch retained;
12. lyrics current-word/current-line elements retained;
13. audio storage check rejects local mirrored audio caches;
14. staging copies only referenced audio;
15. all existing Parameter Lab tests continue to pass.

Visual smoke tests must render screenshots at:
- 1920×1080
- 1680×1050
- 1440×900
- 1366×768
- 1024×768
- 390×844

At each desktop size:
- no overlaps;
- no clipped active controls;
- wheel art is visible;
- spectrum cannot overlap VU;
- all genre buttons readable;
- album art remains square;
- lyrics word/line visible.

## 15. Build discipline

v11 is not implemented by appending override sections to v10 CSS.

The player uses:
- `assets/css/studio-v11.css`
- `assets/js/studio-v11.js`
- one v11 template

Old v10 player styles/scripts are not loaded by the page. They may remain in an archive folder only if needed for historical comparison, but they must not participate in runtime cascade or behaviour.

The build is considered complete only when automated tests pass **and** the rendered screenshots have been visually inspected against this specification.

## v11.1 layout/audio revision

The desktop studio is a strict three-column top row: rotary magazine, loaded release, and output console. The output console contains the EQ/program visualiser, VU meters, and volume module at one identical column width. The transport spans all columns below them, and live lyrics span the full machine width as the final row.

There are no user EQ faders in v11.1. The visualiser is display-only. Removing the fader bank also removes all BiquadFilter processing from the playback graph.

Playback must never depend on the visual analyser. `HTMLAudioElement.play()` is attempted first. Only after native playback succeeds may the optional Web Audio analyser attach. When it attaches, the MediaElementAudioSource is connected to an analyser and the analyser to `AudioContext.destination` immediately, before optional stereo metering is created. Failure of the analyser must leave ordinary native playback usable.

Release actions are grouped beneath the album description in one four-button shelf: Details, YAML, Reference, Unreleased. Transport options group Side A/B and MP3/FLAC together rather than scattering them around the player.


## v11.3 physical-control revision

The bottom lyrics instrument displays one complete current line, not a separate giant current-word readout. Each timed word is rendered as an inline token. Only the active token is illuminated, and it remains active through any timing gap until the next token begins.

Transport controls must read as physical hardware: previous, play/pause and next use large symbols, have visible press travel, and emit a short synthesized mechanical clunk on activation. The sound is generated at runtime and must not add another media asset or song copy.

POWER is a real master control. Switching it off pauses the main programme and ATR playback, suspends the analyser route, extinguishes instrument illumination and leaves only enough ambient cabinet visibility to locate the switch. Switching power back on never resumes audio automatically.

The DISPLAY LAMP controls a continuous luminous ring around the rotary cassette wheel plus a softer internal wash. With power on and the analyser active, the ring may pulse subtly with RMS programme level. With power or lamp at zero the ring is fully dark.
