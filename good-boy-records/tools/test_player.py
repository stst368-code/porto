#!/usr/bin/env python3
"""Regression checks for the Good Boy Records studio runtime."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")
template = (ROOT / "templates/index.html").read_text(encoding="utf-8")
css = (ROOT / "assets/css/studio.css").read_text(encoding="utf-8")
js = (ROOT / "assets/js/studio.js").read_text(encoding="utf-8")
importer = (ROOT / "tools/import_showcase.py").read_text(encoding="utf-8")
builder = (ROOT / "tools/build_catalogue.py").read_text(encoding="utf-8")
stager = (ROOT / "tools/stage_pages.py").read_text(encoding="utf-8")
build_bat = (ROOT / "BUILD-SHOWCASE.bat").read_text(encoding="utf-8")
cat = json.loads((ROOT / "data/catalogue.json").read_text(encoding="utf-8"))

checks = []
def check(name, ok): checks.append((name, bool(ok)))

# Catalogue and curated-source contract
check("catalogue format retained", cat.get("format") == "gbr-showcase-v10.5")
check("genres are dynamic metadata", "variantSlots" not in cat and isinstance(cat.get("genres"), list))
check("wheel has no fixed song capacity", "MAX_SONGS = 24" not in builder)
check("nested showcase directories scanned", 'DROP.rglob("*.yaml")' in importer)
check("MP3 and FLAC first-class", '".mp3"' in importer and '".flac"' in importer)
check("Side metadata retained", "sideIds" in builder)
check("version suffixes are not side metadata", 'Never infer cassette side' in importer)
check("word timing support retained", "gbr-word-lyrics-v1" in importer and "lyrics.json" in importer)
check("composition metadata retained", all(k in (cat.get("songs") or [{}])[0] for k in ["story", "style", "yamlUrl", "atr"]))

# Single authoritative local audio copy
sources = []
for track in cat.get("tracks") or []:
    sources.extend(v for v in ((track.get("audio") or {}).get("sources") or {}).values() if v)
check("catalogue audio points directly at showcase", all(str(v).startswith("showcase/") for v in sources))
check("legacy track cache is cleaned", "for legacy in (AUDIO_OUT, ATR_AUDIO_OUT)" in importer)
check("local build never stages _site", "stage_pages.py" not in build_bat)
check("local build removes stale deployment output", "clean_local_stage.py" in build_bat)
check("deployment stages referenced audio only", "def referenced_audio()" in stager and "for source in sorted(media)" in stager)
for legacy in [ROOT / "assets" / "audio" / "tracks", ROOT / "assets" / "audio" / "atr"]:
    check(f"no mirrored audio in {legacy.name}", not any(p.is_file() and p.name != ".gitkeep" for p in legacy.rglob("*")) if legacy.exists() else True)

# Clean runtime, not cumulative v10 CSS/JS
check("single player stylesheet loaded", 'assets/css/studio.css' in template and 'assets/css/studio.css' in html)
check("single player controller loaded", 'assets/js/studio.js' in template and 'assets/js/studio.js' in html)
check("v10 player styles not loaded", all(name not in template for name in ["base-v10.css", "showcase-v10.css", "hardware-v102.css", "classic-v9.css"]))
check("v10 player scripts not loaded", all(name not in template for name in ["showcase-v10.js", "hardware-v102.js", "v7.js"]))
check("legacy player CSS removed from clean tree", all(not (ROOT / "assets" / "css" / name).exists() for name in ["base-v10.css", "showcase-v10.css", "hardware-v102.css", "classic-v9.css"]))
check("legacy player JS removed from clean tree", all(not (ROOT / "assets" / "js" / name).exists() for name in ["showcase-v10.js", "hardware-v102.js", "v7.js"]))
check("layout contract documented", "Layout contract" in css and "Short viewports scroll vertically" in css)

# Old visual hierarchy, new implementation
check("desktop conveyor instrument layout", 'grid-template-areas:\n      "magazine console"\n      "lyrics lyrics"' in css)
check("brown brass baseline", all(token in css for token in ["--gbr-bg", "--gbr-line", "--gbr-accent", "--gbr-hot", "--gbr-meter-face"]))
check("magazine is independent panel", 'class="gbr-magazine gbr-panel"' in html)
check("desktop release column is folded into conveyor center", '.gbr-release {\n    display:none!important;' in css and '.gbr-wheel-center {' in css)
check("console starts in top row", 'grid-area:console' in css and 'class="gbr-console-stack"' in html)
check("magazine and console share desktop top row", '"magazine console"' in css)
check("standalone transport row removed", 'grid-area:transport' not in css and 'class="gbr-panel gbr-transport"' not in html)
check("lyrics span full machine width", '"lyrics lyrics"' in css)
check("lyrics sit below all player controls", html.index('id="gbr-lyric-line"') > html.index('id="gbr-progress"'))
check("desktop main UI is two rows", '"magazine console"' in css and '"lyrics lyrics"' in css)

# Browse/playback separation
check("browse state exists", "browseGenre:" in js)
check("playback state exists", "currentTrack:" in js)
set_browse = js[js.index("function setBrowseGenre"):js.index("function updateThemeMeta")]
check("genre browsing does not load audio", all(term not in set_browse for term in ["selectTrack(", "audio.src", "audio.pause", "audio.play"]))
check("genre browsing repaints wheel", "renderWheelContents();" in set_browse and "renderMobileRail();" in set_browse)
check("redundant browse playing genre strip removed", 'id="gbr-browse-genre"' not in html and 'id="gbr-playing-genre"' not in html)
check("explicit wheel activation loads browsed cut", "function activateWheelSlot" in js and "primaryTrack(song, state.browseGenre)" in js and "selectTrack(track" in js)

# Catalogue conveyor
check("conveyor has a bounded visible window", "const CONVEYOR_VISIBLE = 20" in js and "phase >= CONVEYOR_VISIBLE" in js)
check("conveyor artwork uses real img elements", 'button.innerHTML = `<img alt="" loading="eager" decoding="async">' in js and "img.src = src" in js)
check("conveyor art falls back to placeholder", 'return `assets/img/sleeves/${base}-${size}.${ext}`' in js and '"gbr-placeholder"' in js)
check("conveyor cards contain artwork only", "gbr-track-tag" not in js[js.index("function buildWheel"):js.index("function normaliseWheelIndex")])
check("genre artwork is preloaded before browsing", "preloadAllWheelArtwork" in js and "preloadGenreArtwork(genre);" in js)
check("load gate removed", "gbr-load-gate" not in html and ".gbr-load-gate" not in css)
check("desktop conveyor path is SVG driven", "gbr-conveyor-track" in js and "getPointAtLength" in js and "getTotalLength" in js)
check("conveyor auto moves while idle", "CONVEYOR_IDLE_SPEED" in js and "animateConveyor(now)" in js and "conveyorIdleUntil" in js)
check("conveyor pauses after interaction", "markConveyorInteraction" in js and "CONVEYOR_RESUME_DELAY" in js)
check("catalogue supports pointer drag", "addEventListener('pointermove'" in js)
check("cover clicks are not swallowed by drag capture", "event.target.closest('.gbr-slot-card')" in js)
check("loaded track syncs into conveyor", "function syncWheelToTrack" in js and "CONVEYOR_FOCUS_SLOT" in js and "syncWheelToTrack(track);" in js[js.index("function selectTrack"):js.index("async function playAudio")])
check("conveyor supports mouse wheel", "addEventListener('wheel'" in js)
check("mobile artwork rail exists", 'id="gbr-mobile-rail"' in html and ".gbr-mobile-rail" in css)
check("catalogue title bar is removed", ".gbr-genre-bank {\n  display:none!important;" in css)

check("magazine title chrome removed", "ROTARY CASSETTE MAGAZINE" not in html and "14 SONG POSITIONS · BROWSE WITHOUT INTERRUPTING PLAYBACK" in html)
check("central wheel artwork is created at runtime", 'id="gbr-wheel-center-artwork"' in js and 'function renderWheelCenter' in js)
check("central wheel title is created at runtime", 'id="gbr-wheel-center-title"' in js and 'gbr-wheel-center-copy' in css)
check("loaded track updates central wheel identity", 'renderWheelCenter(track);' in js)
check("expanded genre button labels", all(label in js for label in ["METAL/ROCK","POP/HIP-HOP","COUNTRY/FOLK","DISCO/ELECTRONIC","ORCHESTRAL/CLASSICAL","SPECIAL"]))
check("display lamp moved to top power bank", 'class="gbr-top-lamp"' in html and html.index('id="gbr-lamp-knob"') < html.index('<main class="gbr-machine"'))
check("display lamp is global illumination rheostat", '--light-meter-brightness' in js and '--light-control-brightness' in js and '--light-led-opacity' in js and '.gbr-spectrum-well canvas' in css)
check("lamp is visible and interactive", 'id="gbr-lamp-knob"' in html and "applyLamp" in js and "knobInteraction(el.lampKnob" in js)
check("desktop conveyor replaces the old lamp ring", ".gbr-conveyor-track-outer" in css and ".gbr-wheel-stage::before," in css)
check("cassette lamp has extended brightness range", "state.lamp * .92" in js and "state.lamp * .64" in js)
check("cassette lamp can pulse from live audio", "function updateLampPulse" in js and "rms(graph.analyser" in js and "updateLampPulse();" in js)

# Loaded release and content
check("large loaded artwork", 'id="gbr-artwork"' in html and ".gbr-release-art-wrap" in css)
check("description moved into playback info", html.index('id="gbr-description"') > html.index('id="gbr-progress"') and 'class="gbr-playback-story"' in html)
check("description uses song story", "function storyText" in js and "el.description.textContent = storyText(track)" in js)
check("track title removed from beneath artwork", 'id="gbr-title"' not in html and 'gbr-variant-line' not in html)
check("inspiration sits under now playing", html.index('id="gbr-inspiration"') > html.index('id="gbr-now-title"'))
check("story sits under inspiration", html.index('id="gbr-description"') > html.index('id="gbr-inspiration"'))
check("album artwork expands into freed release space", "flex:1 1 auto" in css[css.index(".gbr-release-card"):css.index(".gbr-release-card-inner")])
check("technical details live on reverse of artwork", 'id="gbr-release-card"' in html and 'gbr-release-face--back' in html and 'id="gbr-tech-grid"' in html)
check("details button flips artwork", 'toggleReleaseFlip' in js and 'data-flipped' in html and 'rotateY(180deg)' in css)
check("reference button removed from release card", 'id="gbr-reference-button"' not in html and 'id="gbr-reference-drawer"' not in html)
check("YAML link retained", 'id="gbr-yaml-link"' in html)
check("ATR drawer retained", 'id="gbr-atr-drawer"' in html and 'id="gbr-atr-audio"' in html)
check("ATR drawer remains contained", ".gbr-inline-drawer" in css and "position: fixed" not in css[css.index(".gbr-inline-drawer"):css.index(".gbr-reference-entry")])
check("reverse card uses large two-column detail grid", 'grid-template-columns:repeat(2,minmax(0,1fr))' in css[css.index('.gbr-card-backplate dl'):css.index('.gbr-release-actions')])
check("reverse card shows Top K sampler scheduler", all(label in js[js.index('function techRows'):js.index('function renderRelease')] for label in ['Top K','Sampler','Scheduler']))
check("importer captures Top K sampler scheduler", all(token in importer for token in ['"topK": number(raw, "top_k", "topk")','"sampler": str(raw.get("sampler")','"scheduler": str(raw.get("scheduler")']))

# Audio console separation
check("dedicated spectrum visualiser canvas", html.count('id="gbr-spectrum"') == 1 and "drawSpectrum" in js)
check("dedicated VU canvas", html.count('id="gbr-vu"') == 1 and "drawVu" in js)
check("spectrum and VU have separate wells", 'gbr-spectrum-well' in html and 'gbr-vu-well' in html)
check("canvas wells clip drawing", ".gbr-canvas-well { overflow:hidden" in css)
check("spectrum and VU use same console width", '.gbr-spectrum-panel,.gbr-vu-panel,.gbr-volume-panel { width:100%; }' in css)
check("EQ visualiser label retained", "PROGRAM EQ VISUALISER" in html)
check("EQ control sliders removed", 'gbr-eq-bank' not in html and 'gbr-eq-flat' not in html and 'data-eq-frequency' not in html)
check("EQ processing code removed", "EQ_FREQS" not in js and 'gbr:eq' not in js and "applyEq" not in js and "data-eq-frequency" not in js)
check("power switch moved to top right", 'class="gbr-top-power"' in html and 'id="gbr-power"' in html and "setPower" in js and html.index('id="gbr-power"') < html.index('id="gbr-volume-meter"'))
check("power pauses playback and darkens the instrument", 'if (!el.audio.paused) el.audio.pause();' in js and 'POWER OFF' in js and 'data-power="off"' in css)
check("power does not auto-resume playback", 'setPower(state.power, false)' in js and 'el.audio.play()' not in js[js.index('function setPower'):js.index('function wireControls')])
check("song-count status text removed from top right", 'CUTS READY' not in template and '{{SONG_COUNT}} SONGS' not in template)

# Volume styling
check("volume knob exists", 'id="gbr-volume-knob"' in html and ".gbr-knob--volume" in css)
check("segmented volume level exists", 'id="gbr-volume-meter"' in html and "gbr-volume-segment" in js)
check("volume dB readout exists", 'id="gbr-volume-db"' in html and "Math.log10" in js)
check("volume persists", 'recall("gbr:volume")' in js and 'remember("gbr:volume"' in js)
check("native volume remains accessible state", 'id="gbr-volume"' in html)

# Transport / lyrics
check("one main audio element", html.count('id="gbr-audio"') == 1)
check("native playback starts before analyser", js.index('await el.audio.play()') < js.index('ensureGraph().catch'))
check("analyser establishes audible route first", 'source.connect(analyser);' in js and 'analyser.connect(ctx.destination);' in js)
check("analyser failure leaves native playback path", 'native playback remains active' in js)
check("audio load errors are surfaced", 'addEventListener("error"' in js and 'AUDIO ERROR' in js)
check("shuffle retained", 'id="gbr-shuffle"' in html and 'remember("gbr:shuffle"' in js)
check("shuffle spans all genres", "function allPlayableTracks" in js and "GENRES.forEach((genre)" in js and "const list = allPlayableTracks();" in js)
check("shuffle follows the shuffled genre visually", "setBrowseGenre(next.variantSlot);" in js)
check("release artwork fills exact square sleeve without letterboxing", "aspect-ratio:1254 / 1254" in css and ".gbr-release-art" in css and "object-fit:cover" in css)
check("wheel artwork fills square carrier without letterboxing", "object-fit:cover" in css[css.rindex(".gbr-slot-card img {"):])
check("now playing moved under player controls", html.index('id="gbr-now-title"') > html.index('id="gbr-progress"') and 'class="gbr-playback-info"' in html)
console_start = html.index('class="gbr-console-stack"')
console_end = html.index('</aside>', console_start)
check("player controls live under volume module", html.index('id="gbr-shuffle"') > html.index('id="gbr-volume-meter"') and html.index('id="gbr-shuffle"') < console_end)
check("previous play next retained", all(f'id="gbr-{name}"' in html for name in ["prev", "play", "next"]))
check("transport icons are oversized and physical", '#gbr-prev,#gbr-play,#gbr-next' in css and 'min-width:62px' in css)
check("hardware controls make a synthesized clunk", 'function playClunk' in js and 'createBuffer' in js and 'createOscillator' in js and 'playClunk(weight)' in js)
check("clunk has heavier latch and limiter", "createDynamicsCompressor" in js[js.index("function playClunk"):js.index("genre bank")] and "latch" in js[js.index("function playClunk"):js.index("genre bank")])
check("Side A/B retained", 'id="gbr-side-switch"' in html and "selectSide" in js)
check("MP3 FLAC retained", 'data-quality="stream"' in html and 'data-quality="lossless"' in html)
check("styled seek track retained", 'id="gbr-progress"' in html and "--seek-pct" in css and "--seek-pct" in js)
check("lyrics always visible", 'class="gbr-panel gbr-lyrics"' in html and "lyrics toggle" not in html.lower())
check("single full lyric line", html.count('id="gbr-lyric-line"') == 1 and 'id="gbr-lyric-word"' not in html)
check("current lyric word is highlighted inline", 'gbr-lyric-token' in js and 'is-current' in js and '.gbr-lyric-token.is-current' in css)
check("current word persists until next word starts", "next word's start as the boundary" in js)
check("word timing fetched on demand", "fetch(timing.src)" in js)
check("raw lyric fallback exists", "function fallbackLyricLines" in js)
check("media session retained", "MediaMetadata" in js)

# Genre material identities
for genre in slots:
    check(f"{genre} hardware theme exists", f'html[data-browse-genre="{genre}"]' in css)
check("artwork is never genre-filtered", ".gbr-release-art {" in css and "filter:" not in css[css.index(".gbr-release-art {"):css.index(".gbr-art-glass")])


# Hidden reject/easter bank
check("easter directory is reserved from normal importer", 'p.name.lower() != "easter"' in importer and 'is_easter_path' in importer)
check("easter bank scans metadata-free audio directly", 'EASTER_DIR = ROOT / "showcase" / "easter"' in builder and 'def load_easter_tracks' in builder and 'EASTER_AUDIO_EXTS' in builder)
check("easter bank is capped at ten masters", 'groups = groups[:MAX_EASTER_TRACKS]' in builder)
check("easter formats with same stem are paired", 'grouped.setdefault' in builder and '"files": {}' in builder)
check("catalogue carries hidden easter bank", "easter" in cat and isinstance((cat.get("easter") or {}).get("tracks"), list))
check("deployment stages easter audio only when referenced", 'data.get("easter")' in stager)
check("hidden mode is session only", 'easter: false' in js and 'remember("gbr:easter"' not in js and 'recall("gbr:easter"' not in js)
check("three rapid power-off cycles toggle hidden mode", 'powerOffClicks' in js and 'now - time <= 5000' in js and 'state.powerOffClicks.length < 3' in js and 'setEasterMode(!state.easter)' in js)
check("hidden mode auto powers the machine back on", 'setPower(true, false)' in js[js.index('function registerPowerOffForEaster'):js.index('function togglePowerWithEasterSequence')])
check("same power ritual exits hidden mode", 'setEasterMode(!state.easter)' in js)
check("hidden bank replaces normal genre controls", 'gbr-service-bank' in js and 'REJECT MASTERS' in js and 'if (state.easter)' in js[js.index('function renderGenreBank'):js.index('function setBrowseGenre')])
check("hidden wheel uses service labels instead of artwork", 'gbr-reject-label' in js and 'img.hidden = true' in js and 'REJECT ${String(index+1)' in js)
check("hidden masters require no lyrics or artwork", 'LYRIC DATA: NOT FOUND // THANK GOD' in js and 'QUALITY CONTROL FAILURE' in template)
check("hidden masters never expose a track URL", 'if (state.easter || (track && track.easter)) return;' in js[js.index('function updateTrackUrl'):js.index('/* -------------------------------------------------------------- lyrics */')])
check("hidden bank supports playback and shuffle", 'function selectEasterTrack' in js and 'easterTracks.filter' in js and 'selectEasterTrack(pool[' in js)
check("hidden service visual treatment exists", 'html[data-easter="true"]' in css and '.gbr-easter-terminal' in css and '.gbr-service-bank' in css)

check("reverse detail grid explicitly fills card width", all(token in css for token in [".gbr-card-backplate > .gbr-eyebrow", "width:100%", "justify-self:stretch"]))
check("wheel artwork uses square full-bleed carriers", all(token in css for token in [".gbr-slot {", "aspect-ratio:1", ".gbr-slot-card img", "inset:0", "background:transparent"]))
check("desktop gives reclaimed height to lyrics", "grid-template-rows:minmax(560px,calc(100dvh - 320px)) 165px" in css and ".gbr-lyrics {\n  height:165px" in css)
check("short desktop still enlarges lyrics", "grid-template-rows:minmax(0,calc(100dvh - 134px)) 106px" in css)

# Surrounding systems
check("folder drawer retained", "{{FOLDERS}}" in template and "setupFolders" in js and "build_folders" in builder)
check("navigation is embedded in top bar", template.index("{{FOLDERS}}") < template.index("</header>") and ".gbr-folders {" in css and "position:absolute" in css[css.index(".gbr-folders {"):css.index(".gbr-folder-tabs {")])
check("desktop top rail can fit ten tabs", "left:270px;right:92px" in css and "flex:1 1 0" in css[css.index('.gbr-folder-tab {'):css.index('.gbr-folder-tab::before')])
check("workflow viewer retained", "comfy-workflow.js" in html and "comfy-workflow.css" in html)
check("Parameter Lab retained", "gbr-matrix-lab.js" in html and "gbr-matrix-lab.css" in html)
check("catalogue embedded", 'id="gbr-catalogue"' in html)

# v11.13 responsive/browser calibration
check("unified readable panel type scale", all(token in css for token in ["--gbr-type-label", "--gbr-type-control", "--gbr-type-body", "--gbr-type-title"]))
check("ten desktop tabs wrap instead of clipping", "white-space:normal" in css[css.rindex("@media (min-width:1181px)"):])
check("tablet layout uses explicit three rows", 'grid-template-rows:auto auto 150px' in css)
check("mobile covers stay square", ".gbr-mobile-card" in css and "aspect-ratio:1" in css)
check("mobile page forbids horizontal overflow", "html,body,.gbr-app { max-width:100%;overflow-x:hidden; }" in css)
check("rotor images cannot start native browser drags", '-webkit-user-drag:none' in css and 'pointer-events:none' in css[css.rindex(".gbr-slot-card img,"):])

# v11.14 mobile compression
check("mobile selector is the artwork instead of duplicate release art", '.gbr-release-card[data-flipped="false"] { display:none; }' in css)
check("mobile selected artwork is visibly identified", 'card.dataset.active = index === state.wheelIndex' in js and '.gbr-mobile-card[data-active="true"]' in css)
check("mobile folder drawer anchors below complete top bar", 'const topbar = document.querySelector(".gbr-topbar")' in js and 'anchor.getBoundingClientRect().bottom' in js)
check("closed folder drawer cannot peek over mobile header", 'visibility:hidden' in css[css.rindex("/* Closed folder drawers"):])
check("mobile VU label is moved clear of needle arc", 'pad+Math.max(14,fh*.17)' in js and 'fh*.72' in js)

for name, ok in checks:
    print(("  PASS  " if ok else "  FAIL  ") + name)
passed = sum(1 for _, ok in checks if ok)
print(("ALL PASS" if passed == len(checks) else "FAILURES PRESENT") + f" ({passed}/{len(checks)})")
raise SystemExit(0 if passed == len(checks) else 1)

