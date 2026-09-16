#!/usr/bin/env python3
"""Regression checks for the clean Good Boy Records v11 studio rebuild."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")
template = (ROOT / "templates/index.html").read_text(encoding="utf-8")
css = (ROOT / "assets/css/studio-v11.css").read_text(encoding="utf-8")
js = (ROOT / "assets/js/studio-v11.js").read_text(encoding="utf-8")
importer = (ROOT / "tools/import_showcase.py").read_text(encoding="utf-8")
builder = (ROOT / "tools/build_catalogue.py").read_text(encoding="utf-8")
stager = (ROOT / "tools/stage_pages.py").read_text(encoding="utf-8")
build_bat = (ROOT / "BUILD-SHOWCASE.bat").read_text(encoding="utf-8")
cat = json.loads((ROOT / "data/catalogue.json").read_text(encoding="utf-8"))

checks = []
def check(name, ok): checks.append((name, bool(ok)))
slots = ["metal", "pop", "country", "disco", "orchestral", "special"]

# Catalogue and curated-source contract
check("catalogue format retained", cat.get("format") == "gbr-showcase-v10.5")
check("fixed six genre slots", cat.get("variantSlots") == slots)
check("maximum ten songs explicit", "MAX_SONGS = 10" in builder)
check("nested showcase directories scanned", 'DROP.rglob("*.yaml")' in importer)
check("MP3 and FLAC first-class", '".mp3"' in importer and '".flac"' in importer)
check("Side A/B/C support retained", "sideIds" in builder and 'VALID_SIDES = ("A", "B", "C")' in builder)
check("legacy side suffixes infer A/B/C", '("-c", "C")' in importer and '("-b", "B")' in importer and '("-a", "A")' in importer)
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
check("single v11 player stylesheet loaded", 'assets/css/studio-v11.css' in template and 'assets/css/studio-v11.css' in html)
check("single v11 player controller loaded", 'assets/js/studio-v11.js' in template and 'assets/js/studio-v11.js' in html)
check("v10 player styles not loaded", all(name not in template for name in ["base-v10.css", "showcase-v10.css", "hardware-v102.css", "classic-v9.css"]))
check("v10 player scripts not loaded", all(name not in template for name in ["showcase-v10.js", "hardware-v102.js", "v7.js"]))
check("legacy player CSS removed from clean tree", all(not (ROOT / "assets" / "css" / name).exists() for name in ["base-v10.css", "showcase-v10.css", "hardware-v102.css", "classic-v9.css"]))
check("legacy player JS removed from clean tree", all(not (ROOT / "assets" / "js" / name).exists() for name in ["showcase-v10.js", "hardware-v102.js", "v7.js"]))
check("layout contract documented", "Layout contract" in css and "Short viewports scroll vertically" in css)

# Old visual hierarchy, new implementation
check("three-column desktop instrument layout", 'grid-template-columns:minmax(400px,.96fr) minmax(470px,1.14fr) minmax(340px,.80fr)' in css)
check("brown brass baseline", all(token in css for token in ["--gbr-bg", "--gbr-line", "--gbr-accent", "--gbr-hot", "--gbr-meter-face"]))
check("magazine is independent panel", 'class="gbr11-magazine gbr11-panel"' in html)
check("loaded release starts in top row", 'grid-area:release' in css and 'class="gbr11-panel gbr11-release"' in html)
check("console starts in top row", 'grid-area:console' in css and 'class="gbr11-console-stack"' in html)
check("magazine release console share top row", '"magazine release console"' in css)
check("standalone transport row removed", 'grid-area:transport' not in css and 'class="gbr11-panel gbr11-transport"' not in html)
check("lyrics span full machine width", '"lyrics lyrics lyrics"' in css)
check("lyrics sit below all player controls", html.index('id="gbr11-lyric-line"') > html.index('id="gbr11-progress"'))
check("desktop main UI is two rows", '"magazine release console"' in css and '"lyrics lyrics lyrics"' in css)

# Browse/playback separation
check("browse state exists", "browseGenre:" in js)
check("playback state exists", "currentTrack:" in js)
set_browse = js[js.index("function setBrowseGenre"):js.index("function updateThemeMeta")]
check("genre browsing does not load audio", all(term not in set_browse for term in ["selectTrack(", "audio.src", "audio.pause", "audio.play"]))
check("genre browsing repaints wheel", "renderWheelContents();" in set_browse and "renderMobileRail();" in set_browse)
check("redundant browse playing genre strip removed", 'id="gbr11-browse-genre"' not in html and 'id="gbr11-playing-genre"' not in html)
check("explicit wheel activation loads browsed cut", "function activateWheelSlot" in js and "primaryTrack(song, state.browseGenre)" in js and "selectTrack(track" in js)

# Magazine
check("exact ten wheel positions built", "for (let index = 0; index < 10; index++)" in js)
check("wheel artwork uses real img elements", 'button.innerHTML = `<img alt="" loading="eager" decoding="async">' in js and "img.src = src" in js)
check("wheel art falls back to placeholder", 'return `assets/img/sleeves/${base}-${size}.${ext}`' in js and '"gbr-placeholder"' in js)
check("wheel cards contain artwork only", "gbr11-slot-copy" not in html and "gbr11-slot-title" not in html and "gbr11-slot-state" not in html and "gbr11-slot-copy" not in js)
check("genre artwork is preloaded before browsing", "preloadAllWheelArtwork" in js and "preloadGenreArtwork(genre);" in js)
check("load gate removed", "gbr11-load-gate" not in html and ".gbr11-load-gate" not in css)
check("wheel geometry is measured from unrotated rotor", "el.wheelSlots.offsetWidth" in js and "el.wheelSlots.offsetHeight" in js and "const radius =" in js)
check("wheel uses one rotating rotor instead of chord interpolation", "state.wheelSpin" in js and "--wheel-spin" in css and "--slot-angle" in css and "setWheelIndex" in js)
check("cassette cards counter-rotate to remain upright", "--card-counter" in css and 'button.style.setProperty("--card-counter"' in js)
check("wheel supports pointer drag", 'addEventListener("pointermove"' in js)
check("cassette clicks are not swallowed by wheel drag capture", 'event.target.closest(".gbr11-slot-card")' in js and 'return;' in js[js.index('event.target.closest(".gbr11-slot-card")'):js.index('event.target.closest(".gbr11-slot-card")')+120])
check("loaded track rotates to active right-hand wheel position", "function syncWheelToTrack" in js and "setWheelIndex(index);" in js[js.index("function syncWheelToTrack"):js.index("function activateWheelSlot")] and "syncWheelToTrack(track);" in js[js.index("function selectTrack"):js.index("async function playAudio")])
check("wheel supports mouse wheel", 'addEventListener("wheel"' in js)
check("mobile artwork rail exists", 'id="gbr11-mobile-rail"' in html and ".gbr11-mobile-rail" in css)
check("six-cut matrix plus one-off browse target generated", "BROWSE_GENRES.forEach" in js and "ONE_OFF_GENRE" in js and "gbr11-genre-button" in js)

check("magazine title chrome removed", "ROTARY CASSETTE MAGAZINE" not in html and "10 SONG POSITIONS · BROWSE WITHOUT INTERRUPTING PLAYBACK" in html)
check("expanded genre button labels", all(label in js for label in ["METAL/ROCK","POP/HIP-HOP","COUNTRY/FOLK","DISCO/ELECTRONIC","ORCHESTRAL/CLASSICAL","SPECIAL","ONE-OFF"]))
check("display lamp moved to top power bank", 'class="gbr11-top-lamp"' in html and html.index('id="gbr11-lamp-knob"') < html.index('<main class="gbr11-machine"'))
check("display lamp is global illumination rheostat", '--light-meter-brightness' in js and '--light-control-brightness' in js and '--light-led-opacity' in js and '.gbr11-spectrum-well canvas' in css)
check("lamp is visible and interactive", 'id="gbr11-lamp-knob"' in html and "applyLamp" in js and "knobInteraction(el.lampKnob" in js)
check("cassette wheel has a full lamp ring", ".gbr11-wheel-stage::before" in css and "--ring-opacity" in css and "--ring-pulse" in css)
check("cassette lamp has extended brightness range", "state.lamp * .92" in js and "state.lamp * .64" in js)
check("cassette lamp can pulse from live audio", "function updateLampPulse" in js and "rms(graph.analyser" in js and "updateLampPulse();" in js)

# Loaded release and content
check("large loaded artwork", 'id="gbr11-artwork"' in html and ".gbr11-release-art-wrap" in css)
check("description moved into playback info", html.index('id="gbr11-description"') > html.index('id="gbr11-progress"') and 'class="gbr11-playback-story"' in html)
check("description uses song story", "function storyText" in js and "el.description.textContent = storyText(track)" in js)
check("track title removed from beneath artwork", 'id="gbr11-title"' not in html and 'gbr11-variant-line' not in html)
check("inspiration sits under now playing", html.index('id="gbr11-inspiration"') > html.index('id="gbr11-now-title"'))
check("story sits under inspiration", html.index('id="gbr11-description"') > html.index('id="gbr11-inspiration"'))
check("album artwork expands into freed release space", "flex:1 1 auto" in css[css.index(".gbr11-release-card"):css.index(".gbr11-release-card-inner")])
check("technical details live on reverse of artwork", 'id="gbr11-release-card"' in html and 'gbr11-release-face--back' in html and 'id="gbr11-tech-grid"' in html)
check("details button flips artwork", 'toggleReleaseFlip' in js and 'data-flipped' in html and 'rotateY(180deg)' in css)
check("reference button removed from release card", 'id="gbr11-reference-button"' not in html and 'id="gbr11-reference-drawer"' not in html)
check("YAML link retained", 'id="gbr11-yaml-link"' in html)
check("ATR drawer retained", 'id="gbr11-atr-drawer"' in html and 'id="gbr11-atr-audio"' in html)
check("ATR drawer remains contained", ".gbr11-inline-drawer" in css and "position: fixed" not in css[css.index(".gbr11-inline-drawer"):css.index(".gbr11-reference-entry")])
check("reverse card uses large two-column detail grid", 'grid-template-columns:repeat(2,minmax(0,1fr))' in css[css.index('.gbr11-card-backplate dl'):css.index('.gbr11-release-actions')])
check("reverse card shows Top K sampler scheduler", all(label in js[js.index('function techRows'):js.index('function renderRelease')] for label in ['Top K','Sampler','Scheduler']))
check("importer captures Top K sampler scheduler", all(token in importer for token in ['"topK": number(raw, "top_k", "topk")','"sampler": str(raw.get("sampler")','"scheduler": str(raw.get("scheduler")']))

# Audio console separation
check("dedicated spectrum visualiser canvas", html.count('id="gbr11-spectrum"') == 1 and "drawSpectrum" in js)
check("dedicated VU canvas", html.count('id="gbr11-vu"') == 1 and "drawVu" in js)
check("spectrum and VU have separate wells", 'gbr11-spectrum-well' in html and 'gbr11-vu-well' in html)
check("canvas wells clip drawing", ".gbr11-canvas-well { overflow:hidden" in css)
check("spectrum and VU use same console width", '.gbr11-spectrum-panel,.gbr11-vu-panel,.gbr11-volume-panel { width:100%; }' in css)
check("EQ visualiser label retained", "PROGRAM EQ VISUALISER" in html)
check("EQ control sliders removed", 'gbr11-eq-bank' not in html and 'gbr11-eq-flat' not in html and 'data-eq-frequency' not in html)
check("EQ processing code removed", "EQ_FREQS" not in js and 'gbr11:eq' not in js and "applyEq" not in js and "data-eq-frequency" not in js)
check("power switch moved to top right", 'class="gbr11-top-power"' in html and 'id="gbr11-power"' in html and "setPower" in js and html.index('id="gbr11-power"') < html.index('id="gbr11-volume-meter"'))
check("power pauses playback and darkens the instrument", 'if (!el.audio.paused) el.audio.pause();' in js and 'POWER OFF' in js and 'data-power="off"' in css)
check("power does not auto-resume playback", 'setPower(state.power, false)' in js and 'el.audio.play()' not in js[js.index('function setPower'):js.index('function wireControls')])
check("song-count status text removed from top right", 'CUTS READY' not in template and '{{SONG_COUNT}} SONGS' not in template)

# Volume styling
check("volume knob exists", 'id="gbr11-volume-knob"' in html and ".gbr11-knob--volume" in css)
check("segmented volume level exists", 'id="gbr11-volume-meter"' in html and "gbr11-volume-segment" in js)
check("volume dB readout exists", 'id="gbr11-volume-db"' in html and "Math.log10" in js)
check("volume persists", 'recall("gbr11:volume")' in js and 'remember("gbr11:volume"' in js)
check("first visit volume defaults to fifty percent", 'volume: numberOr(recall("gbr11:volume"), .5)' in js)
check("first visit lamp defaults to fifty percent", 'lamp: numberOr(recall("gbr11:lamp"), .5)' in js)
check("native volume remains accessible state", 'id="gbr11-volume"' in html)

# Transport / lyrics
check("one main audio element", html.count('id="gbr11-audio"') == 1)
check("native playback starts before analyser", js.index('await el.audio.play()') < js.index('ensureGraph().catch'))
check("analyser establishes audible route first", 'source.connect(analyser);' in js and 'analyser.connect(ctx.destination);' in js)
check("analyser failure leaves native playback path", 'native playback remains active' in js)
check("audio load errors are surfaced", 'addEventListener("error"' in js and 'AUDIO ERROR' in js)
check("shuffle retained", 'id="gbr11-shuffle"' in html and 'remember("gbr11:shuffle"' in js)
check("shuffle spans matrix and one-off bank", "function allPlayableTracks" in js and "BROWSE_GENRES.forEach((genre)" in js and "const list = allPlayableTracks();" in js)
check("shuffle follows the shuffled genre visually", "setBrowseGenre(next.variantSlot);" in js)
check("non-shuffle end advances within current genre", "function stepPlayback(delta, autoplay = null)" in js and "const list = tracksForGenre(state.currentTrack.variantSlot);" in js)
check("non-shuffle end autoplays next genre track", 'el.audio.addEventListener("ended",()=>nextPlayback(true));' in js and "stepPlayback(1, autoplay);" in js)
check("release artwork fills exact square sleeve without letterboxing", "aspect-ratio:1254 / 1254" in css and ".gbr11-release-art" in css and "object-fit:cover" in css)
check("wheel artwork fills square carrier without letterboxing", "object-fit:cover" in css[css.rindex(".gbr11-slot-card img {"):])
check("now playing moved under player controls", html.index('id="gbr11-now-title"') > html.index('id="gbr11-progress"') and 'class="gbr11-playback-info"' in html)
console_start = html.index('class="gbr11-console-stack"')
console_end = html.index('</aside>', console_start)
check("player controls live under volume module", html.index('id="gbr11-shuffle"') > html.index('id="gbr11-volume-meter"') and html.index('id="gbr11-shuffle"') < console_end)
check("previous play next retained", all(f'id="gbr11-{name}"' in html for name in ["prev", "play", "next"]))
check("transport icons are oversized and physical", '#gbr11-prev,#gbr11-play,#gbr11-next' in css and 'min-width:62px' in css)
check("hardware controls make a synthesized clunk", 'function playClunk' in js and 'createBuffer' in js and 'createOscillator' in js and 'playClunk(weight)' in js)
check("clunk has heavier latch and limiter", "createDynamicsCompressor" in js[js.index("function playClunk"):js.index("genre bank")] and "latch" in js[js.index("function playClunk"):js.index("genre bank")])
check("Side A/B/C retained", 'id="gbr11-side-switch"' in html and 'data-side="C"' in html and "selectSide" in js)
check("MP3 FLAC retained", 'data-quality="stream"' in html and 'data-quality="lossless"' in html)
check("styled seek track retained", 'id="gbr11-progress"' in html and "--seek-pct" in css and "--seek-pct" in js)
check("lyrics always visible", 'class="gbr11-panel gbr11-lyrics"' in html and "lyrics toggle" not in html.lower())
check("single full lyric line", html.count('id="gbr11-lyric-line"') == 1 and 'id="gbr11-lyric-word"' not in html)
check("current lyric word is highlighted inline", 'gbr11-lyric-token' in js and 'is-current' in js and '.gbr11-lyric-token.is-current' in css)
check("current word persists until next word starts", "next word's start as the boundary" in js)
check("word timing fetched on demand", "fetch(timing.src)" in js)
check("raw lyric fallback exists", "function fallbackLyricLines" in js)
check("media session retained", "MediaMetadata" in js)

# Genre material identities
for genre in slots:
    check(f"{genre} hardware theme exists", f'html[data-browse-genre="{genre}"]' in css)
check("artwork is never genre-filtered", ".gbr11-release-art {" in css and "filter:" not in css[css.index(".gbr11-release-art {"):css.index(".gbr11-art-glass")])


# Public standalone / one-off bank
check("one-off directory is reserved from six-cut importer", 'reserved_bank' in importer and '"one-off"' in importer and 'one_off_yamls' in importer)
check("one-off importer creates standalone slot", 'def stage_one_off' in importer and '"oneOff": True' in importer and '"variantSlot": ONE_OFF_SLOT' in importer)
check("one-off importer groups A/B/C as one song", 'composition_id = slugify(f"{title}-one-off")' in importer and 'release_id = composition_id if side == "A" else' in importer)
check("one-off C side can be inferred", '("-c", "C")' in importer and 'inferred Side {side} from one-off filename/directory' in importer)
check("runtime iterates A/B/C sides", 'const SIDE_ORDER = ["A", "B", "C"]' in js and "sideKeys(sides)" in js)
check("one-off songs do not consume matrix positions", 'normal_tracks = [track for track in tracks' in builder and 'one_off_tracks = [track for track in tracks' in builder)
check("one-off bank is unlimited and paged", 'if len(one_off_songs) > MAX_SONGS' not in builder and "ONE_OFF_PAGE_SIZE = 10" in js and "oneOffPageCount" in js and "gbr11-oneoff-pager" in js)
check("catalogue carries one-off bank", "oneOff" in cat and isinstance((cat.get("oneOff") or {}).get("songs"), list))
check("runtime exposes seventh one-off browse target", 'const ONE_OFF_GENRE = "one-off"' in js and 'const BROWSE_GENRES = [...GENRES, ONE_OFF_GENRE]' in js)
check("one-off uses independent song bank", 'function songsForGenre(genre)' in js and 'genre === ONE_OFF_GENRE ? oneOffSongs : songs' in js)
check("one-off browser pages unlimited songs through ten-position wheel", 'visibleSongsForGenre(state.browseGenre)[index]' in js and 'for (let index = 0; index < 10; index++)' in js and "setOneOffPage" in js)
check("one-off control spans existing grid instead of squeezing it", '.gbr11-genre-button[data-genre="one-off"]' in css and 'grid-column:1 / -1' in css)
check("one-off pager is compact and full-width", ".gbr11-oneoff-pager" in css and "grid-template-columns:34px minmax(0,1fr) 34px" in css)
check("one-off hardware theme exists", 'html[data-browse-genre="one-off"]' in css)

# Hidden reject/easter bank
check("easter directory is reserved from normal importer", 'reserved_bank' in importer and '"easter"' in importer)
check("easter bank scans metadata-free audio directly", 'EASTER_DIR = ROOT / "showcase" / "easter"' in builder and 'def load_easter_tracks' in builder and 'EASTER_AUDIO_EXTS' in builder)
check("easter bank is capped at ten masters", 'groups = groups[:MAX_SONGS]' in builder)
check("easter formats with same stem are paired", 'grouped.setdefault' in builder and '"files": {}' in builder)
check("catalogue carries hidden easter bank", "easter" in cat and isinstance((cat.get("easter") or {}).get("tracks"), list))
check("deployment stages easter audio only when referenced", 'data.get("easter")' in stager)
check("hidden mode is session only", 'easter: false' in js and 'remember("gbr11:easter"' not in js and 'recall("gbr11:easter"' not in js)
check("three rapid power-off cycles toggle hidden mode", 'powerOffClicks' in js and 'now - time <= 5000' in js and 'state.powerOffClicks.length < 3' in js and 'setEasterMode(!state.easter)' in js)
check("hidden mode auto powers the machine back on", 'setPower(true, false)' in js[js.index('function registerPowerOffForEaster'):js.index('function togglePowerWithEasterSequence')])
check("same power ritual exits hidden mode", 'setEasterMode(!state.easter)' in js)
check("hidden bank replaces normal genre controls", 'gbr11-service-bank' in js and 'REJECT MASTERS' in js and 'if (state.easter)' in js[js.index('function renderGenreBank'):js.index('function setBrowseGenre')])
check("hidden wheel uses service labels instead of artwork", 'gbr11-reject-label' in js and 'img.hidden = true' in js and 'REJECT ${String(index+1)' in js)
check("hidden masters require no lyrics or artwork", 'LYRIC DATA: NOT FOUND // THANK GOD' in js and 'QUALITY CONTROL FAILURE' in template)
check("hidden masters never expose a track URL", 'if (state.easter || (track && track.easter)) return;' in js[js.index('function updateTrackUrl'):js.index('/* -------------------------------------------------------------- lyrics */')])
check("hidden bank supports playback and shuffle", 'function selectEasterTrack' in js and 'easterTracks.filter' in js and 'selectEasterTrack(pool[' in js)
check("hidden service visual treatment exists", 'html[data-easter="true"]' in css and '.gbr11-easter-terminal' in css and '.gbr11-service-bank' in css)

check("reverse detail grid explicitly fills card width", all(token in css for token in [".gbr11-card-backplate > .gbr11-eyebrow", "width:100%", "justify-self:stretch"]))
check("wheel artwork uses square full-bleed carriers", all(token in css for token in [".gbr11-slot {", "aspect-ratio:1", ".gbr11-slot-card img", "inset:0", "background:transparent"]))
check("desktop gives reclaimed height to lyrics", "grid-template-rows:minmax(560px,calc(100dvh - 320px)) 165px" in css and ".gbr11-lyrics {\n  height:165px" in css)
check("short desktop still enlarges lyrics", "grid-template-rows:minmax(500px,calc(100dvh - 250px)) 112px" in css)

# Surrounding systems
check("folder drawer retained", "{{FOLDERS}}" in template and "setupFolders" in js and "build_folders" in builder)
check("navigation is embedded in top bar", template.index("{{FOLDERS}}") < template.index("</header>") and ".gbr-folders {" in css and "position:absolute" in css[css.index(".gbr-folders {"):css.index(".gbr-folder-tabs {")])
check("desktop top rail can fit ten tabs", "left:270px;right:92px" in css and "flex:1 1 0" in css[css.index('.gbr-folder-tab {'):css.index('.gbr-folder-tab::before')])
check("workflow viewer retained", "comfy-workflow.js" in html and "comfy-workflow.css" in html)
check("Parameter Lab retained", "gbr-matrix-lab.js" in html and "gbr-matrix-lab.css" in html)
check("catalogue embedded", 'id="gbr-catalogue"' in html)

# v11.13 responsive/browser calibration
check("unified readable panel type scale", all(token in css for token in ["--gbr11-type-label", "--gbr11-type-control", "--gbr11-type-body", "--gbr11-type-title"]))
check("ten desktop tabs wrap instead of clipping", "white-space:normal" in css[css.rindex("@media (min-width:1181px)"):])
check("tablet layout uses explicit three rows", 'grid-template-rows:auto auto 150px' in css)
check("mobile covers stay square", ".gbr11-mobile-card" in css and "aspect-ratio:1" in css)
check("mobile page forbids horizontal overflow", "html,body,.gbr11-app { max-width:100%;overflow-x:hidden; }" in css)
check("rotor images cannot start native browser drags", '-webkit-user-drag:none' in css and 'pointer-events:none' in css[css.rindex(".gbr11-slot-card img,"):])

# v11.14 mobile compression
check("mobile selector is the artwork instead of duplicate release art", '.gbr11-release-card[data-flipped="false"] { display:none; }' in css)
check("mobile selected artwork is visibly identified", 'card.dataset.active = index === state.wheelIndex' in js and '.gbr11-mobile-card[data-active="true"]' in css)
check("mobile folder drawer anchors below complete top bar", 'const topbar = document.querySelector(".gbr11-topbar")' in js and 'anchor.getBoundingClientRect().bottom' in js)
check("closed folder drawer cannot peek over mobile header", 'visibility:hidden' in css[css.rindex("/* Closed folder drawers"):])
check("mobile VU label is moved clear of needle arc", 'pad+Math.max(14,fh*.17)' in js and 'fh*.72' in js)
check("mobile double tap starts selected album", 'mobileLastTap' in js and '<= 360' in js and 'if (doubleTap)' in js and 'playAudio();' in js[js.index('if (doubleTap)'):js.index('el.mobileRail.appendChild(card)')])
check("mobile double tap avoids browser zoom gesture", 'touch-action:manipulation' in css[css.rindex(".gbr11-mobile-card {"):])

for name, ok in checks:
    print(("  PASS  " if ok else "  FAIL  ") + name)
passed = sum(1 for _, ok in checks if ok)
print(("ALL PASS" if passed == len(checks) else "FAILURES PRESENT") + f" ({passed}/{len(checks)})")
raise SystemExit(0 if passed == len(checks) else 1)

