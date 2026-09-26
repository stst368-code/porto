(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const catalogueNode = $("gbr-catalogue");
  if (!catalogueNode) return;

  let catalogue;
  try { catalogue = JSON.parse(catalogueNode.textContent || "{}"); }
  catch (error) { console.error("GBR catalogue parse failed", error); return; }

  const tracks = Array.isArray(catalogue.tracks) ? catalogue.tracks : [];
  const genres = Array.isArray(catalogue.genres) && catalogue.genres.length
    ? catalogue.genres
    : [...new Set(tracks.map((track) => track.genre || track.variantLabel || track.variantSlot).filter(Boolean))];
  const EASTER_CAPACITY = Math.max(1, Number(catalogue.maxEasterTracks) || 10);
  const easterTracks = Array.isArray(catalogue.easter && catalogue.easter.tracks)
    ? catalogue.easter.tracks.slice(0, EASTER_CAPACITY)
    : [];
  const songs = Array.isArray(catalogue.songs) ? catalogue.songs : [];
  const trackById = Object.fromEntries(tracks.map((track) => [String(track.id), track]));
  const songById = Object.fromEntries(songs.map((song) => [String(song.id), song]));
  const normalWheelCount = Math.max(1, tracks.length);
  const activeTracks = () => state.easter ? easterTracks : tracks;
  const activeCount = () => Math.max(1, activeTracks().length);
  const wheelStep = () => 360 / activeCount();

  const el = {
    app: $("gbr-app"), status: $("gbr-status"), audio: $("gbr-audio"),
    genreBank: $("gbr-genre-bank"), magazineModeLabel: $("gbr-magazine-mode-label"),
    wheelStage: $("gbr-wheel-stage"), wheelDisc: $("gbr-wheel-disc"), wheelSlots: $("gbr-wheel-slots"),
    wheelCenter: $("gbr-wheel-center"), centerArtwork: $("gbr-wheel-center-artwork"), centerTitle: $("gbr-wheel-center-title"), centerVersion: $("gbr-wheel-center-version"),
    mobileRail: $("gbr-mobile-rail"),
    lampKnob: $("gbr-lamp-knob"),
    releaseLabel: $("gbr-release-label"), artwork: $("gbr-artwork"), releaseArtWrap: $("gbr-release-art-wrap"),
    easterTerminal: $("gbr-easter-terminal"), easterReject: $("gbr-easter-reject"), easterFilename: $("gbr-easter-filename"), description: $("gbr-description"),
    inspiration: $("gbr-inspiration"), detailsButton: $("gbr-details-button"), yaml: $("gbr-yaml-link"),
    releaseCard: $("gbr-release-card"), cardBackTitle: $("gbr-card-back-title"),
    atrButton: $("gbr-atr-button"), atrDrawer: $("gbr-atr-drawer"),
    techGrid: $("gbr-tech-grid"), atrList: $("gbr-atr-list"), atrAudio: $("gbr-atr-audio"),
    spectrum: $("gbr-spectrum"), vu: $("gbr-vu"), power: $("gbr-power"),
    volume: $("gbr-volume"), volumeKnob: $("gbr-volume-knob"), volumeDb: $("gbr-volume-db"), volumeMeter: $("gbr-volume-meter"),
    nowTitle: $("gbr-now-title"), nowVersion: $("gbr-now-version"), shuffle: $("gbr-shuffle"), prev: $("gbr-prev"), play: $("gbr-play"), next: $("gbr-next"),
    sideSwitch: $("gbr-side-switch"), progress: $("gbr-progress"), time: $("gbr-time"), total: $("gbr-total"),
    lyricLine: $("gbr-lyric-line"),
  };
  const qualityButtons = [...document.querySelectorAll("[data-quality]")];
  const sideButtons = [...document.querySelectorAll("[data-side]")];

  const state = {
    browseGenre: "all",
    wheelIndex: 0,
    wheelSpin: 0,
    conveyorPhase: 0,
    conveyorLastFrame: 0,
    conveyorIdleUntil: 0,
    wallVisibleSlots: 20,
    wallColumns: 5,
    wallRows: 4,
    currentTrack: null,
    currentSong: null,
    quality: recall("gbr:quality") || "stream",
    shuffle: recall("gbr:shuffle") === "true",
    lamp: numberOr(recall("gbr:lamp"), .62),
    volume: numberOr(recall("gbr:volume"), .9),
    power: recall("gbr:power") !== "false",
    easter: false,
    savedNormalTrack: null,
    savedNormalTime: 0,
    savedBrowseGenre: null,
    powerOffClicks: [],
    lyricLines: [],
    lyricToken: 0,
    lyricLastLine: -1,
    lyricLastWord: -2,
    draggingWheel: null,
  };

  const graph = { ctx: null, source: null, analyser: null, analyserL: null, analyserR: null, freq: null, timeMain: null, timeL: null, timeR: null, ready: false };
  const lyricCache = new Map();
  const artworkPreload = new Map();
  let animationFrame = 0;
  let vuLeft = 0, vuRight = 0;
  let uiAudioContext = null;

  function recall(key) { try { return localStorage.getItem(key); } catch (_) { return null; } }
  function remember(key, value) { try { localStorage.setItem(key, String(value)); } catch (_) {} }
  function numberOr(value, fallback) { const n = Number(value); return Number.isFinite(n) ? n : fallback; }
  function clamp(lo, value, hi) { return Math.max(lo, Math.min(hi, value)); }
  function esc(value) { return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]); }
  function humanise(value) { return String(value || "").replace(/[-_]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }
  function clock(value) { const s = Number(value);
  if (!Number.isFinite(s) || s < 0) return "--:--";
  const whole = Math.floor(s);
  return `${Math.floor(whole/60)}:${String(whole%60).padStart(2,"0")}`;
  }
  function songForTrack(track) { return track ? songById[String(track.composition)] || null : null; }
  function sideIds(song, genre) { return song && song.sideIds && song.sideIds[genre] && typeof song.sideIds[genre] === "object" ? song.sideIds[genre] : {};
  }
  function sidesFor(song, genre) { const ids = sideIds(song, genre);
  const out = {};
  ["A","B"].forEach((side) => { if (ids[side] && trackById[ids[side]]) out[side] = trackById[ids[side]]; });
  if (!out.A && song && song.variantIds && song.variantIds[genre] && trackById[song.variantIds[genre]]) out.A = trackById[song.variantIds[genre]];
  return out;
  }
  function primaryTrack(song, genre) { const sides = sidesFor(song, genre); return sides.A || sides.B || null; }
  function sideOf(track) { return String(track && track.side || "A").toUpperCase() === "B" ? "B" : "A"; }
  function artworkUrl(track, size = 640, ext = "webp") { const base = track && track.artwork && track.artwork.base ? track.artwork.base : "gbr-placeholder";
  return `assets/img/sleeves/${base}-${size}.${ext}`;
  }
  function preloadArtwork(track, size = 640) {
    if (!track) return;
    const src = artworkUrl(track, size, "webp");
    if (artworkPreload.has(src)) return;
    const image = new Image();
    image.decoding = "async";
    image.src = src;
    artworkPreload.set(src, image);
  }
  function preloadGenreArtwork() { tracks.forEach(preloadArtwork); }
  function preloadAllWheelArtwork() { tracks.forEach(preloadArtwork); }
  function sourceFor(track) {
    const sources = track && track.audio && track.audio.sources || {};
    if (state.quality === "lossless") return sources.flac || sources.mp3 || Object.values(sources).find(Boolean) || null;
    return sources.mp3 || sources.flac || Object.values(sources).find(Boolean) || null;
  }
  function availableQuality(track, quality) { const sources = track && track.audio && track.audio.sources || {};
  return quality === "lossless" ? !!sources.flac : !!sources.mp3;
  }

  function setStatus(text, tone = "") { if (!el.status) return; el.status.textContent = text; el.status.dataset.tone = tone; }

  /* --------------------------------------------------------- control sound */
  function getUiAudioContext() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    if (!uiAudioContext) uiAudioContext = new AC();
    if (uiAudioContext.state === "suspended") uiAudioContext.resume().catch(() => {});
    return uiAudioContext;
  }
  function playClunk(weight = 1) {
    const ctx = getUiAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const master = ctx.createGain();
    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -8;
    limiter.knee.value = 3;
    limiter.ratio.value = 10;
    limiter.attack.value = .001;
    limiter.release.value = .06;
    master.gain.value = clamp(.82, 1.06 * weight, 1.34);
    master.connect(limiter).connect(ctx.destination);

    /* A heavier switch body: short metal snap plus a low cabinet thump. */
    const duration = .096;
    const frames = Math.max(1, Math.floor(ctx.sampleRate * duration));
    const buffer = ctx.createBuffer(1, frames, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < frames; i++) {
      const decay = Math.exp(-i / (ctx.sampleRate * .019));
      data[i] = (Math.random() * 2 - 1) * decay;
    }
    const noise = ctx.createBufferSource();
    const filter = ctx.createBiquadFilter();
    const noiseGain = ctx.createGain();
    noise.buffer = buffer;
    filter.type = "bandpass";
    filter.frequency.value = 820;
    filter.Q.value = .82;
    noiseGain.gain.setValueAtTime(.0001, now);
    noiseGain.gain.exponentialRampToValueAtTime(.135, now + .002);
    noiseGain.gain.exponentialRampToValueAtTime(.0001, now + duration);
    noise.connect(filter).connect(noiseGain).connect(master);

    const thump = ctx.createOscillator();
    const thumpGain = ctx.createGain();
    thump.type = "triangle";
    thump.frequency.setValueAtTime(108, now);
    thump.frequency.exponentialRampToValueAtTime(46, now + .09);
    thumpGain.gain.setValueAtTime(.0001, now);
    thumpGain.gain.exponentialRampToValueAtTime(.125, now + .002);
    thumpGain.gain.exponentialRampToValueAtTime(.0001, now + .095);
    thump.connect(thumpGain).connect(master);

    const latch = ctx.createOscillator();
    const latchGain = ctx.createGain();
    latch.type = "square";
    latch.frequency.setValueAtTime(1450, now + .008);
    latch.frequency.exponentialRampToValueAtTime(920, now + .024);
    latchGain.gain.setValueAtTime(.0001, now);
    latchGain.gain.exponentialRampToValueAtTime(.038, now + .009);
    latchGain.gain.exponentialRampToValueAtTime(.0001, now + .032);
    latch.connect(latchGain).connect(master);

    noise.start(now); noise.stop(now + duration + .012);
    thump.start(now); thump.stop(now + .102);
    latch.start(now + .006); latch.stop(now + .038);
  }

  /* ----------------------------------------------------------- genre bank */
  function renderGenreBank() {
    if (!el.genreBank) return;
    el.genreBank.replaceChildren();
    const plate = document.createElement("div");
    plate.className = "gbr-service-bank gbr-all-tracks-bank";
    if (state.easter) {
      plate.innerHTML = `<span>SERVICE BANK</span><strong>REJECT MASTERS</strong><small>${String(easterTracks.length).padStart(2,"0")} FAILED CUTS</small>`;
    } else {
      plate.innerHTML = `<span>CATALOGUE</span><strong>ALL TRACKS</strong><small>${tracks.length} TRACKS · ${genres.length} GENRES</small>`;
    }
    el.genreBank.appendChild(plate);
  }

  function setBrowseGenre() { /* Genres are metadata, never navigation. */ }

  function updateThemeMeta() {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = state.easter ? "#d64a35" : "#c47b21";
  }

  function ensureWheelCenter() {
    if (!el.wheelStage) return;
    let center = $("gbr-wheel-center");
    if (!center) {
      center = document.createElement("section");
      center.id = "gbr-wheel-center";
      center.className = "gbr-wheel-center";
      center.setAttribute("aria-live", "polite");
      center.innerHTML = `
        <img id="gbr-wheel-center-artwork" class="gbr-wheel-center-artwork" alt="">
        <div class="gbr-wheel-center-copy">
          <strong id="gbr-wheel-center-title"></strong>
          <small id="gbr-wheel-center-version"></small>
        </div>`;
      el.wheelStage.appendChild(center);
    }
    el.wheelCenter = center;
    el.centerArtwork = $("gbr-wheel-center-artwork");
    el.centerTitle = $("gbr-wheel-center-title");
    el.centerVersion = $("gbr-wheel-center-version");
  }

  function renderWheelCenter(track) {
    ensureWheelCenter();
    if (!el.wheelCenter || !track) return;

    const title = track.displayTitle || humanise(track.title || track.filename);
    const variant = track.easter
      ? "REJECT MASTER"
      : (track.genre || track.variantLabel || humanise(track.variantSlot || track.variant));

    el.centerTitle.textContent = title;
    el.centerVersion.textContent = variant || "";

    if (track.easter) {
      el.centerArtwork.src = artworkUrl(null, 640, "webp");
      el.centerArtwork.alt = "Good Boy Records reject master";
      el.wheelCenter.dataset.reject = "true";
    } else {
      el.centerArtwork.src = artworkUrl(track, 1280, "webp");
      el.centerArtwork.alt = track.artwork && track.artwork.alt || `Album artwork for ${title}`;
      el.wheelCenter.dataset.reject = "false";
    }
  }

  /* ----------------------------------------------------------- cover wall */
  const CONVEYOR_VISIBLE = 20;
  const CONVEYOR_RESUME_DELAY = 2600;
  const CONVEYOR_FOCUS_SLOT = 12;
  const COVER_WALL_TARGET_TILE = 116;

  function ensureConveyorTrack() {
    if (!el.wheelStage) return null;
    let svg = el.wheelStage.querySelector('.gbr-conveyor-track');
    if (svg) return svg.querySelector('path[data-conveyor-path]');

    svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('gbr-conveyor-track');
    svg.setAttribute('viewBox', '0 0 1000 1000');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-hidden', 'true');
    const d = "M -150 390 L 190 390 C 225 390 242 386 260 366 C 285 338 300 292 336 230 C 414 98 602 70 758 120 C 905 168 975 304 975 485 C 975 682 894 825 742 870 C 585 916 404 888 322 754 C 292 705 279 649 257 622 C 240 600 222 592 190 592 L -150 592";
    svg.innerHTML = `
      <path class="gbr-conveyor-track-outer" d="${d}" />
      <path class="gbr-conveyor-track-bed" d="${d}" />
      <path class="gbr-conveyor-track-seams" data-conveyor-path d="${d}" />`;
    el.wheelStage.insertBefore(svg, el.wheelSlots);
    return svg.querySelector('path[data-conveyor-path]');
  }

  function markConveyorInteraction() {
    state.conveyorIdleUntil = performance.now() + CONVEYOR_RESUME_DELAY;
  }

  function buildWheel() {
    ensureConveyorTrack();
    el.wheelSlots.replaceChildren();
    const list = activeTracks();
    list.forEach((track, index) => {
      const wrap = document.createElement('div');
      wrap.className = 'gbr-slot';
      wrap.dataset.index = String(index);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'gbr-slot-card';
      button.dataset.index = String(index);
      button.innerHTML = `<img alt="" loading="eager" decoding="async"><span class="gbr-reject-label" hidden><b></b><small></small></span>`;
      button.addEventListener('click', () => activateWheelSlot(index));
      wrap.appendChild(button);
      el.wheelSlots.appendChild(wrap);
    });
    state.wheelIndex = Math.min(state.wheelIndex, Math.max(0, list.length - 1));
    state.conveyorPhase = 0;
    renderWheelContents();
    positionWheel();
  }

  function renderWheelContents() {
    const list = activeTracks();
    [...el.wheelSlots.children].forEach((wrap, index) => {
      const button = wrap.querySelector('.gbr-slot-card');
      const img = button.querySelector('img');
      const rejectLabel = button.querySelector('.gbr-reject-label');
      const track = list[index] || null;
      const ready = !!track;

      if (state.easter) {
        img.hidden = true;
        rejectLabel.hidden = false;
        rejectLabel.querySelector('b').textContent = `REJECT ${String(index + 1).padStart(2, '0')}`;
        rejectLabel.querySelector('small').textContent = track ? (track.displayTitle || track.filename || 'FAILED MASTER') : 'EMPTY';
      } else {
        rejectLabel.hidden = true;
        img.hidden = false;
        const title = track ? (track.displayTitle || humanise(track.title || track.id)) : '';
        const src = artworkUrl(track, 640, 'webp');
        if (img.getAttribute('src') !== src) img.src = src;
        img.alt = track ? ((track.artwork && track.artwork.alt) || `Album artwork for ${title}`) : '';
        img.onerror = () => {
          const fallback = artworkUrl(null, 640, 'webp');
          if (!img.src.endsWith(fallback)) img.src = fallback;
        };
      }

      button.dataset.ready = ready ? 'true' : 'false';
      button.disabled = !ready;
      button.dataset.atGate = index === state.wheelIndex ? 'true' : 'false';
      button.dataset.playing = !!(state.currentTrack && track && state.currentTrack.id === track.id) ? 'true' : 'false';
      const title = track ? (track.displayTitle || track.filename || humanise(track.title || track.id)) : 'EMPTY';
      const genre = track && !state.easter ? (track.genre || track.variantLabel || humanise(track.variantSlot || track.variant)) : '';
      button.setAttribute('aria-label', track ? `${title}${genre ? ` — ${genre}` : ''}` : 'Empty');
      button.title = button.getAttribute('aria-label');
    });
    positionWheel();
  }

  function normaliseWheelIndex(index) {
    const count = activeCount();
    return ((Number(index) || 0) % count + count) % count;
  }

  function setWheelIndex(index, immediate = false) {
    const next = normaliseWheelIndex(index);
    state.wheelIndex = next;
    const visiblePhase = conveyorProgressForIndex(next);
    if (immediate && visiblePhase === null) {
      const focus = Math.floor(Math.max(1, state.wallVisibleSlots) / 2);
      state.conveyorPhase = -next + focus;
    }
    renderWheelCenter(activeTracks()[next] || state.currentTrack);
    positionWheel();
  }

  function conveyorProgressForIndex(index) {
    const count = activeCount();
    if (!count) return null;
    const phase = ((index + state.conveyorPhase) % count + count) % count;
    if (phase >= Math.max(1, state.wallVisibleSlots)) return null;
    return phase;
  }

  function fullBleedWallRows(count, stageWidth, stageHeight) {
    let best = null;
    for (let rows = 1; rows <= count; rows += 1) {
      const tile = stageHeight / rows;
      const minPerRow = Math.max(1, Math.ceil(stageWidth / tile));
      const needed = rows * minPerRow;
      if (needed > count) continue;
      const leftover = count - needed;
      const overscan = (count / rows - minPerRow) * tile;
      const score = rows * 1000 - overscan;
      if (!best || score > best.score) {
        best = { rows, tile, minPerRow, leftover, score };
      }
    }
    if (best) return best;

    // Fallback: if the library is tiny, use the tallest near-square layout we can.
    const rows = Math.max(1, Math.round(Math.sqrt(count * stageHeight / Math.max(1, stageWidth))));
    const cols = Math.ceil(count / rows);
    const tile = Math.max(stageWidth / cols, stageHeight / rows);
    return { rows, tile, minPerRow: cols, leftover: 0, score: 0 };
  }

  function positionConveyor() {
    const stageWidth = el.wheelStage.clientWidth;
    const stageHeight = el.wheelStage.clientHeight;
    if (stageWidth < 100 || stageHeight < 100) return;

    const count = activeCount();
    const wall = fullBleedWallRows(count, stageWidth, stageHeight);
    const rows = wall.rows;
    const tileSize = wall.tile;
    const visibleSlots = count;

    const rowCounts = new Array(rows).fill(wall.minPerRow);
    for (let i = 0; i < wall.leftover; i += 1) rowCounts[i % rows] += 1;

    state.wallColumns = Math.max(...rowCounts);
    state.wallRows = rows;
    state.wallVisibleSlots = visibleSlots;

    const offsets = [];
    let cursor = 0;
    for (let row = 0; row < rows; row += 1) {
      offsets.push(cursor);
      cursor += rowCounts[row];
    }

    [...el.wheelSlots.children].forEach((wrap, index) => {
      const slotIndex = conveyorProgressForIndex(index);
      if (slotIndex === null || slotIndex >= visibleSlots) {
        wrap.hidden = true;
        return;
      }

      let row = 0;
      for (; row < rows; row += 1) {
        const start = offsets[row];
        if (slotIndex < start + rowCounts[row]) break;
      }
      const rowStart = offsets[row];
      const colInSequence = slotIndex - rowStart;
      const itemsInRow = rowCounts[row];
      const visualCol = row % 2 === 1 ? (itemsInRow - 1 - colInSequence) : colInSequence;
      const rowWidth = itemsInRow * tileSize;
      const rowXOffset = (stageWidth - rowWidth) / 2;

      const x = rowXOffset + visualCol * tileSize + tileSize / 2;
      const y = row * tileSize + tileSize / 2;
      const selected = index === state.wheelIndex;

      wrap.hidden = false;
      wrap.style.width = `${tileSize + 0.35}px`;
      wrap.style.left = `${x}px`;
      wrap.style.top = `${y}px`;
      wrap.style.transform = 'translate3d(-50%, -50%, 0)';
      wrap.style.zIndex = String(selected ? 30 : 10);
      wrap.style.opacity = '1';

      const button = wrap.querySelector('.gbr-slot-card');
      button.style.setProperty('--card-scale', '1');
      button.style.removeProperty('--card-counter');
      button.dataset.atGate = selected ? 'true' : 'false';

      if (selected && el.wheelCenter) {
        el.wheelCenter.style.left = `${x}px`;
        el.wheelCenter.style.top = `${y}px`;
        el.wheelCenter.style.setProperty('--selected-tile-size', `${tileSize}px`);
      }
    });
  }

  function positionLegacyWheel() {
    const count = activeCount();
    const step = 360 / count;
    const rotorWidth = el.wheelSlots.offsetWidth;
    const rotorHeight = el.wheelSlots.offsetHeight;
    if (rotorWidth < 100 || rotorHeight < 100) return;
    const firstCard = el.wheelSlots.querySelector('.gbr-slot-card');
    const cardWidth = firstCard ? firstCard.offsetWidth : 92;
    const cardHeight = firstCard ? firstCard.offsetHeight : 116;
    const radius = Math.max(150, Math.min(rotorWidth / 2 - cardWidth / 2 - 18, rotorHeight / 2 - cardHeight / 2 - 18));

    el.wheelSlots.style.setProperty('--wheel-spin', `${state.wheelSpin}deg`);
    el.wheelDisc.style.setProperty('--wheel-spin', `${state.wheelSpin}deg`);
    el.wheelSlots.style.setProperty('--slot-radius', `${radius}px`);

    [...el.wheelSlots.children].forEach((wrap, index) => {
      wrap.hidden = false;
      const baseAngle = index * step;
      const displayAngle = baseAngle + state.wheelSpin;
      const radians = displayAngle * Math.PI / 180;
      const depth = (Math.cos(radians) + 1) / 2;
      wrap.style.left = '50%';
      wrap.style.top = '50%';
      wrap.style.transform = '';
      wrap.style.setProperty('--slot-angle', `${baseAngle}deg`);
      wrap.style.zIndex = String(4 + Math.round(depth * 8));
      wrap.style.opacity = String(.62 + depth * .38);
      const button = wrap.querySelector('.gbr-slot-card');
      button.style.setProperty('--card-counter', `${-displayAngle}deg`);
      button.style.setProperty('--card-scale', '1');
      button.dataset.atGate = index === state.wheelIndex ? 'true' : 'false';
    });
  }

  function positionWheel() {
    if (!el.wheelStage || getComputedStyle(el.wheelStage).display === 'none') return;
    if (matchMedia('(min-width: 1181px)').matches && !state.easter) positionConveyor();
    else positionLegacyWheel();
  }

  function rotateWheel(delta) {
    markConveyorInteraction();
    if (matchMedia('(min-width: 1181px)').matches && !state.easter) {
      setWheelIndex(state.wheelIndex + (delta < 0 ? -1 : 1), true);
      return;
    }
    setWheelIndex(state.wheelIndex + (delta < 0 ? -1 : 1));
  }

  function syncWheelToTrack(track) {
    if (!track) return;
    const list = activeTracks();
    const index = list.findIndex((item) => item.id === track.id);
    if (index < 0) return;
    state.wheelIndex = index;
    if (matchMedia('(min-width: 1181px)').matches && !state.easter) {
      state.conveyorPhase = 0;
      positionWheel();
    } else {
      const step = 360 / activeCount();
      state.wheelSpin = -index * step;
      positionWheel();
    }
  }

  function activateWheelSlot(index) {
    markConveyorInteraction();
    state.wheelIndex = normaliseWheelIndex(index);
    const continuePlaying = !!(el.audio && !el.audio.paused && !el.audio.ended);
    const track = activeTracks()[state.wheelIndex] || null;
    if (!track) return;
    if (state.easter) selectEasterTrack(track, continuePlaying);
    else selectTrack(track, continuePlaying);
  }

  function renderMobileRail() {
    el.mobileRail.replaceChildren();
    activeTracks().forEach((track, index) => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'gbr-mobile-card';
      card.dataset.active = index === state.wheelIndex ? 'true' : 'false';
      if (state.easter) {
        card.classList.add('gbr-mobile-card--reject');
        card.innerHTML = `<strong>REJECT ${String(index + 1).padStart(2, '0')}</strong><small>${esc(track.displayTitle || track.filename || 'FAILED MASTER')}</small>`;
      } else {
        const title = track.displayTitle || humanise(track.title || track.id);
        const genre = track.genre || track.variantLabel || humanise(track.variantSlot || track.variant);
        card.innerHTML = `<img src="${artworkUrl(track, 640, 'webp')}" alt="${esc(`Album artwork for ${title}`)}" loading="eager" decoding="async"><span><strong>${esc(title)}</strong><small>${esc(genre)}</small></span>`;
      }
      card.setAttribute('aria-label', track.displayTitle || track.filename || track.id);
      card.addEventListener('click', () => activateWheelSlot(index));
      el.mobileRail.appendChild(card);
    });
  }

  function setupWheelInput() {
    el.wheelStage.addEventListener('wheel', (event) => {
      event.preventDefault();
      rotateWheel(event.deltaY > 0 || event.deltaX > 0 ? 1 : -1);
    }, { passive: false });
    el.wheelStage.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault();
        rotateWheel(-1);
      } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        event.preventDefault();
        rotateWheel(1);
      } else if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        activateWheelSlot(state.wheelIndex);
      }
    });
    el.wheelStage.addEventListener('pointerenter', markConveyorInteraction);
    el.wheelStage.addEventListener('pointerdown', (event) => {
      markConveyorInteraction();
      if (event.target.closest('.gbr-slot-card')) return;
      state.draggingWheel = {
        id: event.pointerId,
        x: event.clientX,
        phase: state.conveyorPhase,
        index: state.wheelIndex,
        spin: state.wheelSpin,
        steps: 0,
      };
      try { el.wheelStage.setPointerCapture(event.pointerId); } catch (_) {}
    });
    el.wheelStage.addEventListener('pointermove', (event) => {
      const drag = state.draggingWheel;
      if (!drag || drag.id !== event.pointerId) return;
      markConveyorInteraction();
      if (matchMedia('(min-width: 1181px)').matches && !state.easter) {
        const steps = Math.trunc((drag.x - event.clientX) / 70);
        if (steps !== drag.steps) {
          drag.steps = steps;
          setWheelIndex(drag.index + steps, true);
        }
        return;
      }
      const steps = Math.trunc((drag.x - event.clientX) / 70);
      if (steps !== drag.steps) {
        drag.steps = steps;
        state.wheelIndex = normaliseWheelIndex(drag.index + steps);
        state.wheelSpin = drag.spin - steps * wheelStep();
        positionWheel();
      }
    });
    const end = (event) => {
      if (state.draggingWheel && state.draggingWheel.id === event.pointerId) state.draggingWheel = null;
      markConveyorInteraction();
    };
    el.wheelStage.addEventListener('pointerup', end);
    el.wheelStage.addEventListener('pointercancel', end);
    new ResizeObserver(positionWheel).observe(el.wheelStage);
  }

  function animateConveyor(now) {
    state.conveyorLastFrame = now;
  }

  /* ---------------------------------------------------------- loaded release */
  function storyText(track) {
    const song = songForTrack(track) || {};
    const common = String(song.story || "").trim();
    const variant = String(track && track.story || "").trim();
    if (common && variant && variant !== common) return `${common}\n\n${variant}`;
    return variant || common || "No song description has been added for this release.";
  }

  function referenceEntries(track) {
    const song = songForTrack(track) || {};
    const entries = [];
    const push = (scope, style) => {
      style = style || {};
      const name = String(style.inspiration || "").trim();
      const url = String(style.inspirationUrl || "").trim();
      if (!name && !url) return;
      if (entries.some((entry) => entry.name === name && entry.url === url)) return;
      entries.push({ scope, name: name || "Reference", url });
    };
    push("TRACK", song.style);
    push("VERSION", track && track.style);
    return entries;
  }

  function techRows(track) {
    const model = track && track.model || {};
    const gen = track && track.generation || {};
    const rows = [
      ["Cassette side", `Side ${sideOf(track)}`],
      ["Model", model.name], ["DIT", model.dit], ["Text encoder", model.textEncoder],
      ["Encoder CFG", gen.encoderCfg], ["Encoder seed", gen.encoderSeed], ["Top K", gen.topK],
      ["Sampler", gen.sampler], ["Scheduler", gen.scheduler], ["Sampler CFG", gen.samplerCfg],
      ["Sampler seed", gen.samplerSeed], ["Steps", gen.steps],
    ];
    return rows.filter(([,value]) => value !== null && value !== undefined && String(value) !== "");
  }

  function renderRelease(track) {
    if (!track) return;
    if (el.easterTerminal) el.easterTerminal.hidden = true;
    if (el.releaseArtWrap) el.releaseArtWrap.hidden = false;
    el.detailsButton.disabled = false;
    const song = songForTrack(track) || {};
    const title = track.displayTitle || song.title || humanise(track.title);
    const variant = track.genre || track.variantLabel || humanise(track.variantSlot || track.variant);
    el.releaseLabel.textContent = `${variant.toUpperCase()} MASTER`;
    if (el.cardBackTitle) el.cardBackTitle.textContent = title;
    if (el.releaseCard) el.releaseCard.dataset.flipped = "false";
    if (el.detailsButton) { el.detailsButton.textContent = "DETAILS"; el.detailsButton.setAttribute("aria-pressed", "false"); }
    el.artwork.src = artworkUrl(track, 1280, "webp");
    el.artwork.alt = track.artwork && track.artwork.alt || `Album artwork for ${title}`;
    renderWheelCenter(track);
    el.description.textContent = storyText(track);

    const refs = referenceEntries(track);
    if (refs.length) {
      const summary = refs.map((entry) => entry.url ? `<a href="${esc(entry.url)}" target="_blank" rel="noopener">${esc(entry.name)} ↗</a>` : esc(entry.name)).join(" · ");
      el.inspiration.innerHTML = `<strong>INSPIRATION</strong> · ${summary}`;
      el.inspiration.hidden = false;
    } else {
      el.inspiration.hidden = true;
      el.inspiration.textContent = "";
    }

    el.techGrid.innerHTML = techRows(track).map(([label,value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join("");
    el.yaml.href = track.yamlUrl || "#";
    el.yaml.setAttribute("aria-disabled", track.yamlUrl ? "false" : "true");


    const atr = Array.isArray(song.atr) ? song.atr : [];
    el.atrButton.disabled = !atr.length;
    el.atrButton.setAttribute("aria-disabled", atr.length ? "false" : "true");
    el.atrList.innerHTML = atr.length
      ? atr.map((item, index) => `<article class="gbr-atr-entry"><small>ARCHIVE ${String(index+1).padStart(2,"0")}</small><strong>${esc(item.label || item.filename || "Unreleased")}</strong><button type="button" data-atr-src="${esc(item.src || "")}">PLAY ARCHIVE</button></article>`).join("")
      : `<article class="gbr-atr-entry"><strong>No unreleased audio has been added for this song.</strong></article>`;
    el.atrList.querySelectorAll("[data-atr-src]").forEach((button) => button.addEventListener("click", () => { el.atrAudio.src = button.dataset.atrSrc; el.atrAudio.play().catch(() => {}); }));
    closeReleaseDrawers();
  }

  function renderEasterRelease(track) {
    if (!track) return;
    const index = Math.max(0, easterTracks.findIndex((item) => item.id === track.id));
    el.releaseLabel.textContent = "QUALITY CONTROL FAILURE";
    renderWheelCenter(track);
    if (el.releaseCard) el.releaseCard.dataset.flipped = "false";
    if (el.releaseArtWrap) el.releaseArtWrap.hidden = true;
    if (el.easterTerminal) el.easterTerminal.hidden = false;
    if (el.easterReject) el.easterReject.textContent = `REJECT ${String(index+1).padStart(2,"0")}`;
    if (el.easterFilename) el.easterFilename.textContent = track.filename || track.displayTitle || "FAILED MASTER";
    el.detailsButton.textContent = "FAILED";
    el.detailsButton.setAttribute("aria-pressed", "false");
    el.detailsButton.disabled = true;
    el.yaml.href = "#";
    el.yaml.setAttribute("aria-disabled", "true");
    el.description.textContent = "Unreleased generation failure recovered from the reject archive. No metadata, no cover, no excuses.";
    el.inspiration.innerHTML = `<strong>SERVICE ARCHIVE</strong> · ${esc(track.filename || track.displayTitle || "UNKNOWN MASTER")}`;
    el.inspiration.hidden = false;
    el.techGrid.innerHTML = "";
    el.atrButton.disabled = true;
    el.atrButton.setAttribute("aria-disabled", "true");
    closeReleaseDrawers();
  }

  function closeReleaseDrawers() {
    if (el.atrDrawer) el.atrDrawer.hidden = true;
    if (el.atrButton) el.atrButton.setAttribute("aria-expanded", "false");
  }
  function toggleReleaseDrawer(name) {
    if (name !== "atr" || !el.atrDrawer || !el.atrButton || el.atrButton.disabled) return;
    const opening = el.atrDrawer.hidden;
    closeReleaseDrawers();
    el.atrDrawer.hidden = !opening;
    el.atrButton.setAttribute("aria-expanded", opening ? "true" : "false");
  }
  function toggleReleaseFlip(force) {
    if (!el.releaseCard || !el.detailsButton) return;
    const current = el.releaseCard.dataset.flipped === "true";
    const flipped = typeof force === "boolean" ? force : !current;
    el.releaseCard.dataset.flipped = flipped ? "true" : "false";
    el.detailsButton.setAttribute("aria-pressed", flipped ? "true" : "false");
    el.detailsButton.textContent = flipped ? "FRONT" : "DETAILS";
  }

  /* --------------------------------------------------------------- audio */
  async function ensureGraph() {
    if (graph.ready) {
      if (graph.ctx && graph.ctx.state === "suspended") await graph.ctx.resume().catch(() => {});
      return true;
    }
    if (location.protocol === "file:") return false;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    try {
      const ctx = new AC();
      const source = ctx.createMediaElementSource(el.audio);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = .34;
      analyser.minDecibels = -88;
      analyser.maxDecibels = -18;

      /* Establish the audible route immediately. If optional metering setup
         fails later, the media element is still connected to the speakers. */
      source.connect(analyser);
      analyser.connect(ctx.destination);

      graph.ctx = ctx;
      graph.source = source;
      graph.analyser = analyser;
      graph.freq = new Uint8Array(analyser.frequencyBinCount);
      graph.timeMain = new Uint8Array(analyser.fftSize);
      graph.ready = true;

      try {
        const splitter = ctx.createChannelSplitter(2);
        const left = ctx.createAnalyser(), right = ctx.createAnalyser();
        left.fftSize = right.fftSize = 1024;
        left.smoothingTimeConstant = right.smoothingTimeConstant = .08;
        analyser.connect(splitter);
        splitter.connect(left,0); splitter.connect(right,1);
        graph.analyserL = left; graph.analyserR = right;
        graph.timeL = new Uint8Array(left.fftSize); graph.timeR = new Uint8Array(right.fftSize);
      } catch (meterError) {
        console.warn("Stereo metering unavailable; using mono meter fallback", meterError);
      }

      if (ctx.state === "suspended") await ctx.resume().catch(() => {});
      return true;
    } catch (error) {
      console.warn("GBR visual analyser unavailable; native playback remains active", error);
      return false;
    }
  }

  function selectEasterTrack(track, autoplay = false) {
    if (!track) return;
    const source = sourceFor(track);
    if (!source) { setStatus("NO AUDIO", "fault"); return; }
    const sameTrack = state.currentTrack && state.currentTrack.id === track.id;
    const oldTime = sameTrack ? el.audio.currentTime : 0;
    state.currentTrack = track;
    state.currentSong = null;
    syncWheelToTrack(track);
    renderEasterRelease(track);
    renderPlaybackIdentity();
    renderWheelContents();
    renderMobileRail();
    state.lyricLines = [];
    state.lyricLastLine = -1;
    state.lyricLastWord = -2;
    el.lyricLine.textContent = "LYRIC DATA: NOT FOUND // THANK GOD";
    paintQuality();
    updateSideSwitch();
    if (!sameTrack || el.audio.getAttribute("src") !== source) {
      el.audio.src = source;
      el.audio.load();
      if (oldTime > 0) el.audio.currentTime = oldTime;
    }
    if (autoplay && state.power) playAudio();
    if (!state.power) setStatus("POWER OFF", "");
    else setStatus(autoplay ? "REJECT PLAYING" : "REJECT LOADED", autoplay ? "live" : "");
  }

  function selectTrack(track, autoplay = false) {
    if (!track) return;
    const source = sourceFor(track);
    if (!source) { setStatus("NO AUDIO", "fault"); return; }
    const sameTrack = state.currentTrack && state.currentTrack.id === track.id;
    const oldTime = sameTrack ? el.audio.currentTime : 0;
    state.currentTrack = track;
    state.currentSong = songForTrack(track);
    syncWheelToTrack(track);
    renderRelease(track);
    renderPlaybackIdentity();
    renderWheelContents();
    renderMobileRail();
    loadLyrics(track);
    paintQuality();
    updateSideSwitch();
    if (!sameTrack || el.audio.getAttribute("src") !== source) {
      el.audio.src = source;
      el.audio.load();
      if (oldTime > 0) el.audio.currentTime = oldTime;
    }
    updateTrackUrl(track);
    if (autoplay && state.power) playAudio();
    if (!state.power) setStatus("POWER OFF", "");
    else setStatus(autoplay ? "PLAYING" : "LOADED", autoplay ? "live" : "");
  }

  async function playAudio() {
    if (!state.power) { setStatus("POWER OFF", ""); return; }
    if (!state.currentTrack) {
      const track = tracks[state.wheelIndex] || tracks[0] || null;
      if (track) selectTrack(track, false);
    }
    if (!state.currentTrack) return;
    try {
      /* Once a MediaElementSource exists, its AudioContext owns the audible
         route. Resume that route before playback after a power cycle. */
      if (graph.ready && graph.ctx && graph.ctx.state === "suspended") await graph.ctx.resume().catch(() => {});
      /* On first playback the media element is still native, so sound starts
         before the analyser is attached. */
      await el.audio.play();
      setStatus("PLAYING", "live");
      ensureGraph().catch(() => {});
    } catch (error) {
      console.warn("Playback failed", error, el.audio.currentSrc || el.audio.src);
      setStatus("PLAYBACK ERROR", "fault");
    }
  }

  function renderPlaybackIdentity() {
    const track = state.currentTrack;
    if (!track) return;
    if (track.easter) {
      const index = Math.max(0, easterTracks.findIndex((item) => item.id === track.id));
      const title = track.displayTitle || humanise(track.title || track.filename);
      el.nowTitle.textContent = title;
      el.nowVersion.textContent = `REJECT ${String(index+1).padStart(2,"0")}`;
      if ("mediaSession" in navigator) {
        try { navigator.mediaSession.metadata = new MediaMetadata({ title, artist: "Good Boy Records", album: "Reject Masters" }); } catch (_) {}
      }
      return;
    }
    const title = track.displayTitle || humanise(track.title);
    const variant = track.genre || track.variantLabel || humanise(track.variantSlot || track.variant);
    const song = songForTrack(track);
    const sides = song ? sidesFor(song, track.variantSlot) : {};
    el.nowTitle.textContent = title;
    el.nowVersion.textContent = `${variant}${sides.B ? ` · SIDE ${sideOf(track)}` : ""}`;
    if ("mediaSession" in navigator) {
      try { navigator.mediaSession.metadata = new MediaMetadata({ title, artist: "Good Boy Records", album: variant, artwork: [{ src: artworkUrl(track,640,"webp"), sizes: "640x640", type: "image/webp" }] });
      } catch (_) {}
    }
  }

  function updateSideSwitch() {
    if (state.easter || (state.currentTrack && state.currentTrack.easter)) {
      el.sideSwitch.hidden = true;
      return;
    }
    const track = state.currentTrack, song = state.currentSong;
    const sides = track && song ? sidesFor(song, track.variantSlot) : {};
    const multi = !!(sides.A && sides.B);
    el.sideSwitch.hidden = !multi;
    sideButtons.forEach((button) => { const side = button.dataset.side; button.disabled = !sides[side]; button.setAttribute("aria-pressed", side === sideOf(track) ? "true" : "false"); });
  }

  function selectSide(side) {
    const track = state.currentTrack, song = state.currentSong;
    if (!track || !song) return;
    const target = sidesFor(song, track.variantSlot)[side];
    if (!target || target.id === track.id) return;
    const continuePlaying = !el.audio.paused && !el.audio.ended;
    selectTrack(target, continuePlaying);
  }

  function allPlayableTracks() {
    return tracks.filter((track)=>sourceFor(track));
  }
  function stepPlayback(delta) {
    if(!state.currentTrack)return;
    const list=state.easter?easterTracks.filter(sourceFor):allPlayableTracks();
    if(!list.length)return;
    let index=list.findIndex((track)=>track.id===state.currentTrack.id);
    index=index<0?0:(index+delta+list.length)%list.length;
    if(state.easter)selectEasterTrack(list[index],!el.audio.paused&&!el.audio.ended);
    else selectTrack(list[index],!el.audio.paused&&!el.audio.ended);
  }
  function nextPlayback() {
    if(!state.currentTrack)return;
    const list=state.easter?easterTracks.filter(sourceFor):allPlayableTracks();
    if(!list.length)return;
    if(state.shuffle){
      const pool=list.filter((track)=>track.id!==state.currentTrack.id);
      if(!pool.length)return;
      const next=pool[Math.floor(Math.random()*pool.length)];
      if(state.easter)selectEasterTrack(next,true); else selectTrack(next,true);
    }else stepPlayback(1);
  }

  function setQuality(quality, userChange = true) {
    state.quality = quality === "lossless" ? "lossless" : "stream";
    remember("gbr:quality", state.quality);
    paintQuality();
    if (!userChange || !state.currentTrack) return;
    const source = sourceFor(state.currentTrack);
    if (!source || el.audio.getAttribute("src") === source) return;
    const t = el.audio.currentTime, wasPlaying = !el.audio.paused && !el.audio.ended;
    el.audio.src = source; el.audio.load();
    el.audio.addEventListener("loadedmetadata", () => { if (Number.isFinite(t)) el.audio.currentTime = Math.min(t, el.audio.duration || t); if (wasPlaying) playAudio(); }, { once: true });
  }
  function paintQuality() {
    qualityButtons.forEach((button) => { const active = button.dataset.quality === state.quality; button.setAttribute("aria-pressed", active ? "true" : "false"); button.disabled = state.currentTrack ? !availableQuality(state.currentTrack, button.dataset.quality) : false; });
  }
  function updateTrackUrl(track) {
    if (state.easter || (track && track.easter)) return;
    try { const url = new URL(location.href); url.searchParams.set("track", track.id); history.replaceState(null,"",url); } catch (_) {}
  }

  /* -------------------------------------------------------------- lyrics */
  async function loadLyrics(track) {
    const token = ++state.lyricToken;
    state.lyricLines = [];
    state.lyricLastLine = -1;
    state.lyricLastWord = -2;
    el.lyricLine.textContent = "…";
    const timing = track && track.lyrics && track.lyrics.wordTiming;
    if (timing && timing.src && timing.usable !== false) {
      try {
        let data = lyricCache.get(timing.src);
        if (!data) { const response = await fetch(timing.src);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        data = await response.json();
        lyricCache.set(timing.src,data);
        }
        if (token !== state.lyricToken) return;
        if (data && Array.isArray(data.lines)) state.lyricLines = data.lines;
      } catch (error) { console.warn("Live lyric timing unavailable", error); }
    }
    if (!state.lyricLines.length) state.lyricLines = fallbackLyricLines(track);
    updateLyrics();
  }

  function fallbackLyricLines(track) {
    const raw = String(track && track.lyrics && track.lyrics.raw || "");
    const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter((line) => line && !/^\[[^\]]+\]$/.test(line));
    if (!lines.length) return [];
    const duration = Number(el.audio.duration) || Number(track.duration) || Math.max(60, lines.length * 5);
    const step = duration / lines.length;
    return lines.map((text, index) => {
      const start = index * step, end = (index + 1) * step;
      const words = text.split(/\s+/).filter(Boolean);
      const wordStep = (end-start) / Math.max(1,words.length);
      return { text, start, end, words: words.map((word, i) => ({ text: word, start: start+i*wordStep, end: start+(i+1)*wordStep })) };
    });
  }

  function renderLyricLine(line, lineIndex, activeWord) {
    el.lyricLine.replaceChildren();
    const words = Array.isArray(line && line.words) ? line.words : [];
    if (!words.length) {
      el.lyricLine.textContent = String(line && line.text || "");
      state.lyricLastLine = lineIndex;
      state.lyricLastWord = -1;
      return;
    }
    const fragment = document.createDocumentFragment();
    words.forEach((item, index) => {
      if (index) fragment.appendChild(document.createTextNode(" "));
      const span = document.createElement("span");
      span.className = "gbr-lyric-token";
      span.dataset.wordIndex = String(index);
      span.textContent = String(item.text || "");
      if (index === activeWord) span.classList.add("is-current");
      fragment.appendChild(span);
    });
    el.lyricLine.appendChild(fragment);
    state.lyricLastLine = lineIndex;
    state.lyricLastWord = activeWord;
  }

  function updateLyrics() {
    if (state.easter) {
      if (el.lyricLine.textContent !== "LYRIC DATA: NOT FOUND // THANK GOD") el.lyricLine.textContent = "LYRIC DATA: NOT FOUND // THANK GOD";
      return;
    }
    const lines = state.lyricLines;
    if (!lines.length) {
      if (el.lyricLine.textContent !== "READY") el.lyricLine.textContent = "READY";
      state.lyricLastLine = -1; state.lyricLastWord = -2;
      return;
    }
    const t = el.audio.currentTime || 0;
    let lineIndex = lines.findIndex((item) => t >= Number(item.start || 0) && t < Number(item.end || Infinity));
    if (lineIndex < 0) {
      for (let i = lines.length - 1; i >= 0; i--) { if (t >= Number(lines[i].start || 0)) { lineIndex = i; break; } }
      if (lineIndex < 0) lineIndex = 0;
    }
    const line = lines[lineIndex];
    const words = Array.isArray(line.words) ? line.words : [];
    let wordIndex = -1;
    /* Deliberately use the next word's start as the boundary. This keeps the
       current word highlighted through timing gaps until its successor begins. */
    for (let i = 0; i < words.length; i++) {
      if (t >= Number(words[i].start || 0)) wordIndex = i;
      else break;
    }
    if (lineIndex !== state.lyricLastLine) { renderLyricLine(line, lineIndex, wordIndex); return; }
    if (wordIndex !== state.lyricLastWord) {
      el.lyricLine.querySelectorAll(".gbr-lyric-token").forEach((span, index) => span.classList.toggle("is-current", index === wordIndex));
      state.lyricLastWord = wordIndex;
    }
  }

  /* ------------------------------------------------------------- EQ/volume */
  function buildVolumeMeter() {
    el.volumeMeter.replaceChildren();
    for (let i=0;i<24;i++) { const segment = document.createElement("span");
    segment.className = "gbr-volume-segment";
    el.volumeMeter.appendChild(segment);
    }
  }
  function applyVolume(save = true) {
    state.volume = clamp(0, Number(el.volume.value), 1);
    if (save) remember("gbr:volume", state.volume);
    /* HTMLMediaElement volume remains authoritative whether or not the
       visual analyser is available. */
    el.audio.volume = state.volume;
    const db = state.volume <= .001 ? -60 : 20 * Math.log10(state.volume);
    el.volumeDb.textContent = `${db.toFixed(1)} dB`;
    const angle = -130 + state.volume * 260;
    el.volumeKnob.style.setProperty("--knob-angle", `${angle}deg`);
    el.volumeKnob.setAttribute("aria-valuenow", String(Math.round(state.volume*100)));
    const count = Math.round(state.volume * 24);
    [...el.volumeMeter.children].forEach((segment, index) => segment.classList.toggle("is-on", index < count));
  }
  function applyLamp(save = true) {
    state.lamp = clamp(0, state.lamp, 1);
    if (save) remember("gbr:lamp", state.lamp);
    const angle = -130 + state.lamp * 260;
    el.lampKnob.style.setProperty("--knob-angle", `${angle}deg`);
    el.lampKnob.setAttribute("aria-valuenow", String(Math.round(state.lamp*100)));
    const powered = state.power ? 1 : 0;
    const effective = state.lamp * powered;

    /* DISPLAY LAMP is now the master illumination rheostat for the console.
       Cabinet/text remain readable, while illuminated meters, pilot lamps,
       active selections and the magazine ring all follow this one control. */
    el.app.style.setProperty("--light-level", effective.toFixed(3));
    el.app.style.setProperty("--light-meter-brightness", (0.10 + effective * 1.10).toFixed(3));
    el.app.style.setProperty("--light-control-brightness", (0.42 + effective * 0.68).toFixed(3));
    el.app.style.setProperty("--light-control-saturation", (0.38 + effective * 0.78).toFixed(3));
    el.app.style.setProperty("--light-led-opacity", (0.16 + effective * 0.84).toFixed(3));

    el.wheelStage.style.setProperty("--lamp-opacity", String(state.lamp * .64 * powered));
    el.wheelStage.style.setProperty("--ring-opacity", String(state.lamp * .92 * powered));
  }
  function updateLampPulse() {
    if (!el.wheelStage) return;
    if (!state.power || state.lamp <= .001) {
      el.wheelStage.style.setProperty("--ring-opacity", "0");
      el.wheelStage.style.setProperty("--ring-pulse", "0");
      return;
    }
    let level = 0;
    if (!el.audio.paused && graph.ready && graph.analyser && graph.timeMain) level = clamp(0, rms(graph.analyser, graph.timeMain) * 3.6, 1);
    const opacity = state.lamp * (.72 + level * .22);
    el.wheelStage.style.setProperty("--ring-opacity", String(opacity));
    el.wheelStage.style.setProperty("--ring-pulse", String(level));
  }
  function knobInteraction(node, getValue, setValue, step = .025) {
    let drag = null;
    node.addEventListener("pointerdown", (event) => { drag = { id:event.pointerId, y:event.clientY, value:getValue() }; try { node.setPointerCapture(event.pointerId); } catch (_) {} });
    node.addEventListener("pointermove", (event) => { if (!drag || drag.id !== event.pointerId) return; setValue(clamp(0, drag.value + (drag.y-event.clientY)*.006, 1)); });
    const end = (event) => { if (drag && drag.id === event.pointerId) drag = null; };
    node.addEventListener("pointerup", end); node.addEventListener("pointercancel", end);
    node.addEventListener("wheel", (event) => { event.preventDefault(); setValue(clamp(0,getValue()+(event.deltaY<0?step:-step),1)); }, { passive:false });
    node.addEventListener("keydown", (event) => { if (!["ArrowUp","ArrowRight","ArrowDown","ArrowLeft","Home","End"].includes(event.key)) return; event.preventDefault(); if (event.key === "Home") setValue(0); else if (event.key === "End") setValue(1); else setValue(clamp(0,getValue()+(["ArrowUp","ArrowRight"].includes(event.key)?step:-step),1)); });
  }

  /* --------------------------------------------------------------- meters */
  function fitCanvas(canvas) {
    const rect = canvas.getBoundingClientRect(); if (rect.width < 2 || rect.height < 2) return null;
    const dpr = Math.min(devicePixelRatio || 1, 2); const w = Math.round(rect.width*dpr), h = Math.round(rect.height*dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width=w; canvas.height=h; }
    const ctx = canvas.getContext("2d"); ctx.setTransform(dpr,0,0,dpr,0,0); return {ctx,w:rect.width,h:rect.height};
  }
  function css(name, fallback) { const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); return value || fallback; }
  function drawSpectrum() {
    const fit = fitCanvas(el.spectrum); if (!fit) return;
    const {ctx,w,h} = fit; ctx.clearRect(0,0,w,h);
    const accent = css("--gbr-accent","#d98925"), hot = css("--gbr-hot","#ffc264");
    const bands = 24, segs = 12, gap = Math.max(2,w*.0025), bandW = (w-gap*(bands+1))/bands;
    let data = null;
    if (graph.ready && state.power) { graph.analyser.getByteFrequencyData(graph.freq); data = graph.freq; }
    for (let i=0;i<bands;i++) {
      let level = 0;
      if (data) {
        const p = i/(bands-1); const bin = Math.min(data.length-1, Math.round(Math.pow(p,1.65)*(data.length-1)));
        level = data[bin]/255;
      }
      const lit = Math.round(level*segs);
      for (let s=0;s<segs;s++) {
        const sh = (h-10)/segs - 2, x = gap+i*(bandW+gap), y = h-5-(s+1)*(sh+2);
        ctx.globalAlpha = s < lit ? 1 : .10;
        ctx.fillStyle = s > segs-3 ? hot : accent;
        ctx.fillRect(x,y,bandW,sh);
      }
    }
    ctx.globalAlpha = 1;
  }
  function rms(analyser, buffer) {
    if (!graph.ready || !state.power || !analyser || !buffer) return 0;
    analyser.getByteTimeDomainData(buffer); let sum=0;
    for (let i=0;i<buffer.length;i++) { const n=(buffer[i]-128)/128; sum += n*n; }
    return Math.sqrt(sum/buffer.length);
  }
  function roundRect(ctx,x,y,w,h,r) { r=Math.min(r,w/2,h/2);
  ctx.beginPath();
  ctx.moveTo(x+r,y);
  ctx.arcTo(x+w,y,x+w,y+h,r);
  ctx.arcTo(x+w,y+h,x,y+h,r);
  ctx.arcTo(x,y+h,x,y,r);
  ctx.arcTo(x,y,x+w,y,r);
  ctx.closePath();
  }
  function drawVu() {
    const fit = fitCanvas(el.vu); if (!fit) return;
    const {ctx,w,h}=fit; ctx.clearRect(0,0,w,h);
    const mono = graph.ready ? clamp(0,rms(graph.analyser,graph.timeMain)*4.6,1) : 0;
    const targetL = graph.analyserL ? clamp(0,rms(graph.analyserL,graph.timeL)*4.6,1) : mono;
    const targetR = graph.analyserR ? clamp(0,rms(graph.analyserR,graph.timeR)*4.6,1) : mono;
    vuLeft += (targetL-vuLeft)*.18; vuRight += (targetR-vuRight)*.18;
    const gap = Math.max(8,w*.025), meterW=(w-gap)/2;
    [vuLeft,vuRight].forEach((level,index) => {
      const x=index*(meterW+gap), pad=9, fw=meterW-pad*2, fh=h-pad*2;
      ctx.save();
      const bezel=ctx.createLinearGradient(0,0,0,h);
      bezel.addColorStop(0,"#2c2925");
      bezel.addColorStop(1,"#050403");
      ctx.fillStyle=bezel;
      roundRect(ctx,x+2,2,meterW-4,h-4,8);
      ctx.fill();
      const face=ctx.createLinearGradient(0,pad,0,pad+fh);
      face.addColorStop(0,state.power?"#ead8b1":"#575147");
      face.addColorStop(.75,state.power?"#d0ac78":"#342f29");
      face.addColorStop(1,state.power?"#a27648":"#201d1a");
      ctx.fillStyle=face;
      roundRect(ctx,x+pad,pad,fw,fh,7);
      ctx.fill();
      const cx=x+meterW/2, cy=pad+fh*.95, radius=Math.min(fw*.46,fh*.72);
      for(let i=0;i<=10;i++){ const frac=i/10, angle=-Math.PI*.82+frac*Math.PI*.64;
      const r1=radius*.78,r2=radius*.92;
      ctx.strokeStyle=i>8?"#a1322d":"#3f3428";
      ctx.lineWidth=i===8?1.5:1;
      ctx.beginPath();
      ctx.moveTo(cx+Math.cos(angle)*r1,cy+Math.sin(angle)*r1);
      ctx.lineTo(cx+Math.cos(angle)*r2,cy+Math.sin(angle)*r2);
      ctx.stroke();
      }
      ctx.fillStyle="#35281d";
      ctx.textAlign="center";
      ctx.textBaseline="middle";
      ctx.font=`700 ${Math.max(8,Math.min(12,meterW*.042))}px ui-monospace,monospace`;
      ctx.fillText(index===0?"LEFT VU":"RIGHT VU",cx,pad+Math.max(14,fh*.17));
      const angle=-Math.PI*.82+clamp(0,level,1)*Math.PI*.64;
      ctx.strokeStyle="#17100b";
      ctx.lineWidth=2;
      ctx.beginPath();
      ctx.moveTo(cx,cy);
      ctx.lineTo(cx+Math.cos(angle)*radius,cy+Math.sin(angle)*radius);
      ctx.stroke();
      ctx.fillStyle="#25180f";
      ctx.beginPath();
      ctx.arc(cx,cy,4,0,Math.PI*2);
      ctx.fill();
      ctx.restore();
    });
  }
  function animate(now) {
    animateConveyor(now);
    drawSpectrum();
    drawVu();
    updateLyrics();
    updateLampPulse();
    animationFrame = requestAnimationFrame(animate);
  }

  /* -------------------------------------------------------------- transport */
  function updateTransport() {
    const duration = Number(el.audio.duration) || 0;
    const current = Number(el.audio.currentTime) || 0;
    el.time.textContent = clock(current);
    el.total.textContent = duration ? clock(duration) : "--:--";
    el.progress.max = duration || 0;
    if (!el.progress.matches(":active")) el.progress.value = Math.min(current,duration || current);
    const pct = duration ? (current/duration)*100 : 0; el.progress.style.setProperty("--seek-pct", `${pct}%`);
    el.play.textContent = el.audio.paused ? "▶" : "❚❚";
  }

  /* ---------------------------------------------------------- folder drawer */
  function setupFolders() {
    const root = $("gbr-folders"); if (!root) return;
    const drawer = $("gbr-folder-drawer"), resizer = $("gbr-folder-resizer");
    const tabs = [...root.querySelectorAll(".gbr-folder-tab")], sheets = [...root.querySelectorAll(".gbr-folder-sheet")];
    const setTop = () => {
      const topbar = document.querySelector(".gbr-topbar");
      const anchor = topbar || root;
      root.style.setProperty("--folder-drawer-top", `${Math.round(anchor.getBoundingClientRect().bottom)}px`);
    };
    const close = () => { root.dataset.open=""; tabs.forEach((tab)=>tab.setAttribute("aria-selected","false")); };
    const open = (id) => { root.dataset.open=id;
    tabs.forEach((tab)=>tab.setAttribute("aria-selected",tab.dataset.folder===id?"true":"false"));
    sheets.forEach((sheet)=>sheet.hidden=sheet.id!==`gbr-folder-${id}`);
    setTop();
    };
    tabs.forEach((tab,index)=>{
      tab.addEventListener("click",()=> root.dataset.open===tab.dataset.folder ? close() : open(tab.dataset.folder));
      tab.addEventListener("keydown",(event)=>{ let next=null; if(event.key==="ArrowLeft")next=(index-1+tabs.length)%tabs.length; else if(event.key==="ArrowRight")next=(index+1)%tabs.length; else if(event.key==="Home")next=0; else if(event.key==="End")next=tabs.length-1; if(next!==null){event.preventDefault();tabs[next].focus();}});
    });
    $("gbr-folder-close")?.addEventListener("click",close); $("gbr-folder-scrim")?.addEventListener("click",close);
    const saved=numberOr(recall("gbr:folder-height"),760);
    const setHeight=(height,save=true)=>{ const top=root.getBoundingClientRect().bottom;
    const max=Math.max(260,innerHeight-top-10);
    const value=clamp(260,height,max);
    root.style.setProperty("--folder-drawer-height",`${Math.round(value)}px`);
    if(save)remember("gbr:folder-height",value);
    };
    setTop(); setHeight(saved,false);
    if(resizer&&drawer){ let drag=null;
    resizer.addEventListener("pointerdown",(e)=>{drag={id:e.pointerId,top:drawer.getBoundingClientRect().top};try{resizer.setPointerCapture(e.pointerId);}catch(_){}});
    resizer.addEventListener("pointermove",(e)=>{if(drag&&drag.id===e.pointerId)setHeight(e.clientY-drag.top,false);});
    const end=(e)=>{if(!drag||drag.id!==e.pointerId)return;
    remember("gbr:folder-height",drawer.getBoundingClientRect().height);
    drag=null;
    };
    resizer.addEventListener("pointerup",end);
    resizer.addEventListener("pointercancel",end);
    }
    addEventListener("resize",()=>{setTop();setHeight(numberOr(recall("gbr:folder-height"),760),false);});
    document.addEventListener("keydown",(event)=>{if(event.key==="Escape"&&root.dataset.open)close();});
  }

  /* --------------------------------------------------------------- setup */
  function renderEmptyEasterBank() {
    state.currentTrack = null;
    state.currentSong = null;
    el.releaseLabel.textContent = "SERVICE BANK EMPTY";
    if (el.releaseArtWrap) el.releaseArtWrap.hidden = true;
    if (el.easterTerminal) el.easterTerminal.hidden = false;
    if (el.easterReject) el.easterReject.textContent = "NO REJECT MASTERS";
    if (el.easterFilename) el.easterFilename.textContent = "DROP AUDIO INTO showcase/easter/";
    el.nowTitle.textContent = "Reject archive empty";
    el.nowVersion.textContent = "SERVICE BANK";
    ensureWheelCenter();
    if (el.centerTitle) el.centerTitle.textContent = "Reject archive empty";
    if (el.centerVersion) el.centerVersion.textContent = "SERVICE BANK";
    if (el.centerArtwork) {
      el.centerArtwork.src = artworkUrl(null, 640, "webp");
      el.centerArtwork.alt = "Good Boy Records";
    }
    el.description.textContent = "Add up to ten audio files to showcase/easter and rebuild the curated showcase.";
    el.inspiration.hidden = true;
    el.detailsButton.disabled = true;
    el.yaml.setAttribute("aria-disabled", "true");
    el.atrButton.disabled = true;
    el.sideSwitch.hidden = true;
    el.lyricLine.textContent = "LYRIC DATA: NOT FOUND // THANK GOD";
  }

  function setEasterMode(on) {
    const next = !!on;
    if (next === state.easter) return;
    if (next) {
      state.savedNormalTrack = state.currentTrack && !state.currentTrack.easter ? state.currentTrack : null;
      state.savedNormalTime = Number(el.audio.currentTime) || 0;
      state.savedBrowseGenre = state.browseGenre;
    }
    state.easter = next;
    el.app.dataset.easter = state.easter ? "true" : "false";
    document.documentElement.dataset.easter = state.easter ? "true" : "false";
    if (el.magazineModeLabel) el.magazineModeLabel.textContent = state.easter ? "SERVICE BANK // REJECT MASTERS" : `${tracks.length} TRACKS · CONVEYOR CATALOGUE · ${genres.length} GENRES`;
    renderGenreBank();
    state.wheelIndex = 0;
    state.wheelSpin = 0;
    buildWheel();
    renderMobileRail();

    if (state.easter) {
      if (easterTracks.length) selectEasterTrack(easterTracks[0], false);
      else renderEmptyEasterBank();
      setStatus("SERVICE BANK", "fault");
    } else {
      const restore = state.savedNormalTrack || initialTrack();
      if (restore) {
        selectTrack(restore, false);
        const restoreTime = state.savedNormalTime;
        if (restoreTime > 0) {
          el.audio.addEventListener("loadedmetadata", () => {
            if (Number.isFinite(el.audio.duration)) el.audio.currentTime = Math.min(restoreTime, el.audio.duration || restoreTime);
          }, { once:true });
        }
      }
      state.savedNormalTrack = null;
      state.savedNormalTime = 0;
      state.savedBrowseGenre = null;
      renderGenreBank();
      renderWheelContents();
      renderMobileRail();
      setStatus(restore ? "PAUSED" : "READY", "");
    }
    updateThemeMeta();
    applyLamp(false);
  }

  function registerPowerOffForEaster() {
    const now = performance.now();
    state.powerOffClicks = state.powerOffClicks.filter((time) => now - time <= 5000);
    state.powerOffClicks.push(now);
    if (state.powerOffClicks.length < 3) return false;
    state.powerOffClicks = [];
    setTimeout(() => {
      setEasterMode(!state.easter);
      setPower(true, false);
      playClunk(1.75);
    }, 260);
    return true;
  }

  function togglePowerWithEasterSequence() {
    const turningOff = state.power;
    setPower(!state.power, true);
    if (turningOff) registerPowerOffForEaster();
  }

  function setPower(on, userAction = false) {
    state.power = !!on; remember("gbr:power", state.power);
    el.app.dataset.power = state.power ? "on" : "off";
    el.power.setAttribute("aria-checked", state.power ? "true" : "false");
    if (!state.power) {
      if (!el.audio.paused) el.audio.pause();
      if (el.atrAudio && !el.atrAudio.paused) el.atrAudio.pause();
      if (graph.ctx && graph.ctx.state === "running") graph.ctx.suspend().catch(() => {});
      setStatus("POWER OFF", "");
    } else if (userAction) {
      setStatus(state.currentTrack ? "PAUSED" : "READY", "");
    }
    applyLamp(false);
    updateTransport();
  }

  function wireControls() {
    el.detailsButton.addEventListener("click",()=>toggleReleaseFlip());
    el.atrButton.addEventListener("click",()=>toggleReleaseDrawer("atr"));
    document.querySelectorAll("[data-close-drawer]").forEach((button)=>button.addEventListener("click",closeReleaseDrawers));
    el.yaml.addEventListener("click",(event)=>{ if(el.yaml.getAttribute("aria-disabled")==="true")event.preventDefault(); });

    el.play.addEventListener("click",()=> el.audio.paused ? playAudio() : el.audio.pause());
    el.prev.addEventListener("click",()=>stepPlayback(-1)); el.next.addEventListener("click",()=>nextPlayback());
    el.shuffle.addEventListener("click",()=>{state.shuffle=!state.shuffle;remember("gbr:shuffle",state.shuffle);el.shuffle.setAttribute("aria-pressed",state.shuffle?"true":"false");});
    sideButtons.forEach((button)=>button.addEventListener("click",()=>selectSide(button.dataset.side)));
    qualityButtons.forEach((button)=>button.addEventListener("click",()=>setQuality(button.dataset.quality,true)));
    el.progress.addEventListener("input",()=>{if(Number.isFinite(el.audio.duration))el.audio.currentTime=Number(el.progress.value)||0;updateTransport();});

    el.audio.addEventListener("play",()=>{syncWheelToTrack(state.currentTrack);el.play.textContent="❚❚";setStatus("PLAYING","live");});
    el.audio.addEventListener("pause",()=>{el.play.textContent="▶";if(!el.audio.ended)setStatus(state.power ? "PAUSED" : "POWER OFF","");});
    el.audio.addEventListener("timeupdate",updateTransport);
    el.audio.addEventListener("loadedmetadata",()=>{updateTransport(); if(!state.lyricLines.length&&state.currentTrack)state.lyricLines=fallbackLyricLines(state.currentTrack);});
    el.audio.addEventListener("ended",nextPlayback);
    el.audio.addEventListener("canplay",()=>{ if (el.audio.paused) setStatus("LOADED",""); });
    el.audio.addEventListener("error",()=>{
      const err = el.audio.error;
      const code = err ? err.code : 0;
      console.error("GBR audio load error", { code, src: el.audio.currentSrc || el.audio.src });
      setStatus(`AUDIO ERROR ${code || ""}`.trim(),"fault");
    });

    el.power.addEventListener("click",togglePowerWithEasterSequence);
    el.app.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button || button.disabled) return;
      const weight = button === el.power ? 1.42 : (button.closest(".gbr-transport-controls") ? 1.24 : (button.classList.contains("gbr-genre-button") ? 1.0 : .92));
      playClunk(weight);
    });
    el.volume.value=String(state.volume); el.volume.addEventListener("input",()=>applyVolume(true));
    knobInteraction(el.volumeKnob,()=>state.volume,(value)=>{el.volume.value=String(value);applyVolume(true);});
    knobInteraction(el.lampKnob,()=>state.lamp,(value)=>{state.lamp=value;applyLamp(true);});

    if("mediaSession" in navigator){ try { navigator.mediaSession.setActionHandler("play",playAudio);
    navigator.mediaSession.setActionHandler("pause",()=>el.audio.pause());
    navigator.mediaSession.setActionHandler("previoustrack",()=>stepPlayback(-1));
    navigator.mediaSession.setActionHandler("nexttrack",nextPlayback);
    } catch(_){} }
  }

  function initialTrack() {
    const requested=new URLSearchParams(location.search).get("track");
    if(requested&&trackById[requested])return trackById[requested];
    return tracks[0]||null;
  }

  function init() {
    el.app.dataset.easter="false";
    document.documentElement.dataset.easter="false";
    renderGenreBank();
    preloadAllWheelArtwork();
    ensureWheelCenter();
    buildWheel();
    renderMobileRail();
    setupWheelInput();
    buildVolumeMeter();
    setupFolders();
    wireControls();
    if(el.magazineModeLabel)el.magazineModeLabel.textContent=`${tracks.length} TRACKS · CONVEYOR CATALOGUE · ${genres.length} GENRES`;
    el.shuffle.setAttribute("aria-pressed",state.shuffle?"true":"false");
    applyVolume(false);
    paintQuality();
    const track=initialTrack();
    if(track){
      const idx=tracks.findIndex((item)=>item.id===track.id);
      if(idx>=0)setWheelIndex(idx,true);
      selectTrack(track,false);
      positionWheel();
    }else setStatus("EMPTY","fault");
    setPower(state.power,false);
    updateTransport();
    updateThemeMeta();
    animationFrame=requestAnimationFrame(animate);
  }

  init();
})();
