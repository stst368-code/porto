/**
 * Good Boy Records comparison matrix player.
 *
 * Vanilla JS, no dependencies. It consumes the _matrix.json files produced by
 * minimax_matrix_runner_v1.py. Everything before the "__" filename separator is
 * deliberately irrelevant; cells are resolved by suffix.
 *
 * Example:
 *   import { mountGBRMatrixLab } from './gbr-matrix-lab.js';
 *   mountGBRMatrixLab(document.querySelector('#matrix-lab'), {
 *     manifestUrl: '/content-source/otheraudio/samp_sched/_matrix.json',
 *     baseUrl: '/content-source/otheraudio/samp_sched/'
 *   });
 */

export async function mountGBRMatrixLab(root, options = {}) {
  if (!(root instanceof HTMLElement)) throw new TypeError('root must be an HTMLElement');

  const manifest = options.manifest || await loadManifest(options.manifestUrl);
  const baseUrl = normaliseBase(options.baseUrl || './');
  const crossfadeMs = clamp(Number(options.crossfadeMs ?? 90), 20, 500);
  const externalFiles = Array.isArray(options.files) ? options.files : null;

  const state = {
    manifest,
    xIndex: 0,
    yIndex: 0,
    activeSlot: 0,
    playing: false,
    switching: false,
    raf: 0,
    lastSelection: null,
  };

  root.classList.add('gbr-matrix-lab');
  root.tabIndex = root.tabIndex >= 0 ? root.tabIndex : 0;
  root.innerHTML = `
    <div class="gbr-lab-head">
      <div>
        <div class="gbr-lab-kicker">Controlled comparison</div>
        <h3 class="gbr-lab-title"></h3>
        <div class="gbr-lab-subtitle"></div>
      </div>
      <div class="gbr-lab-readout" aria-live="polite"></div>
    </div>

    <div class="gbr-matrix-scroll">
      <div class="gbr-matrix" role="grid" aria-label="Audio comparison matrix"></div>
    </div>

    <div class="gbr-transport">
      <button type="button" class="gbr-play" aria-label="Play">▶</button>
      <span class="gbr-time">0:00</span>
      <input class="gbr-seek" type="range" min="0" max="1000" step="1" value="0" aria-label="Track position">
      <span class="gbr-duration">0:00</span>
    </div>

    <div class="gbr-graph-card">
      <div class="gbr-graph-head">
        <strong class="gbr-graph-title">Parameter view</strong>
        <span class="gbr-graph-note"></span>
      </div>
      <svg class="gbr-graph" viewBox="0 0 760 270" role="img" aria-label="Selected generation parameters"></svg>
    </div>

    <div class="gbr-fixed"></div>

    <audio class="gbr-audio-a" preload="auto"></audio>
    <audio class="gbr-audio-b" preload="auto"></audio>
  `;

  const els = {
    title: root.querySelector('.gbr-lab-title'),
    subtitle: root.querySelector('.gbr-lab-subtitle'),
    readout: root.querySelector('.gbr-lab-readout'),
    matrix: root.querySelector('.gbr-matrix'),
    play: root.querySelector('.gbr-play'),
    time: root.querySelector('.gbr-time'),
    seek: root.querySelector('.gbr-seek'),
    duration: root.querySelector('.gbr-duration'),
    graph: root.querySelector('.gbr-graph'),
    graphTitle: root.querySelector('.gbr-graph-title'),
    graphNote: root.querySelector('.gbr-graph-note'),
    fixed: root.querySelector('.gbr-fixed'),
    audio: [root.querySelector('.gbr-audio-a'), root.querySelector('.gbr-audio-b')],
  };

  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const gains = [audioCtx.createGain(), audioCtx.createGain()];
  const sources = els.audio.map((audio, i) => {
    const src = audioCtx.createMediaElementSource(audio);
    src.connect(gains[i]);
    gains[i].connect(audioCtx.destination);
    gains[i].gain.value = i === 0 ? 1 : 0;
    return src;
  });
  void sources;

  // The showcase deck and the lab share the room. Do not let them both play
  // at once merely because the browser is technically capable of it.
  const showcaseAudio = document.querySelector('#showcase-audio');
  const stopForShowcase = () => { if (state.playing) pause(); };
  showcaseAudio?.addEventListener('play', stopForShowcase);
  document.addEventListener('gbr:auxplay', stopForShowcase);

  const x = manifest.axis_x?.values || [];
  const y = manifest.axis_y?.values || [];
  if (!x.length || !y.length) throw new Error('Matrix manifest has empty axes');

  els.title.textContent = displayExperiment(manifest.experiment);
  els.subtitle.textContent = `${prettyName(manifest.axis_y.name)} × ${prettyName(manifest.axis_x.name)} · ${x.length * y.length} controlled generations`;
  renderFixed(els.fixed, manifest.baseline || {});
  renderMatrix();

  await selectCell(0, 0, false);

  els.play.addEventListener('click', async () => {
    await audioCtx.resume();
    if (state.playing) pause(); else await play();
  });

  els.seek.addEventListener('input', () => {
    const active = els.audio[state.activeSlot];
    if (!Number.isFinite(active.duration) || active.duration <= 0) return;
    const t = (Number(els.seek.value) / 1000) * active.duration;
    els.audio.forEach(a => { if (Number.isFinite(a.duration)) a.currentTime = Math.min(t, a.duration || t); });
    updateTransport();
  });

  root.addEventListener('keydown', async (event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return;
    let nx = state.xIndex;
    let ny = state.yIndex;
    if (event.key === 'ArrowLeft') nx--;
    else if (event.key === 'ArrowRight') nx++;
    else if (event.key === 'ArrowUp') ny--;
    else if (event.key === 'ArrowDown') ny++;
    else if (event.key === ' ') {
      event.preventDefault();
      await audioCtx.resume();
      if (state.playing) pause(); else await play();
      return;
    } else return;
    event.preventDefault();
    nx = clamp(nx, 0, x.length - 1);
    ny = clamp(ny, 0, y.length - 1);
    await selectCell(nx, ny, true);
  });

  els.audio.forEach(audio => {
    audio.addEventListener('ended', () => {
      if (audio === els.audio[state.activeSlot]) {
        state.playing = false;
        els.play.textContent = '▶';
        cancelAnimationFrame(state.raf);
        updateTransport();
      }
    });
    audio.addEventListener('loadedmetadata', updateTransport);
  });

  function renderMatrix() {
    els.matrix.style.setProperty('--gbr-cols', String(x.length));
    els.matrix.innerHTML = '';

    const corner = document.createElement('div');
    corner.className = 'gbr-axis-corner';
    corner.textContent = prettyName(manifest.axis_y.name);
    els.matrix.appendChild(corner);

    x.forEach(value => {
      const h = document.createElement('div');
      h.className = 'gbr-col-label';
      h.textContent = shortLabel(value);
      h.title = value;
      els.matrix.appendChild(h);
    });

    y.forEach((yv, yi) => {
      const row = document.createElement('div');
      row.className = 'gbr-row-label';
      row.textContent = shortLabel(yv);
      row.title = yv;
      els.matrix.appendChild(row);

      x.forEach((xv, xi) => {
        const cell = lookupCell(xv, yv);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'gbr-jack-cell';
        button.dataset.x = String(xi);
        button.dataset.y = String(yi);
        button.setAttribute('role', 'gridcell');
        button.setAttribute('aria-label', `${prettyName(manifest.axis_x.name)} ${xv}, ${prettyName(manifest.axis_y.name)} ${yv}`);
        button.disabled = !cell;
        button.innerHTML = `
          <span class="gbr-jack-socket" aria-hidden="true"><i></i></span>
          <span class="gbr-jack-plug" aria-hidden="true"><b></b><i></i></span>
        `;
        button.addEventListener('click', async () => {
          await audioCtx.resume();
          await selectCell(xi, yi, true);
        });
        els.matrix.appendChild(button);
      });
    });
  }

  async function selectCell(xi, yi, makeClick) {
    if (state.switching) return;
    const xv = x[xi];
    const yv = y[yi];
    const cell = lookupCell(xv, yv);
    if (!cell) return;

    state.switching = true;
    try {
      if (makeClick) playJackClick(audioCtx);
      const oldButton = els.matrix.querySelector('.gbr-jack-cell.is-selected');
      if (oldButton) oldButton.classList.remove('is-selected');
      const newButton = els.matrix.querySelector(`.gbr-jack-cell[data-x="${xi}"][data-y="${yi}"]`);
      if (newButton) newButton.classList.add('is-selected');

      const wasPlaying = state.playing;
      const oldSlot = state.activeSlot;
      const newSlot = oldSlot === 0 ? 1 : 0;
      const oldAudio = els.audio[oldSlot];
      const newAudio = els.audio[newSlot];
      const currentTime = Number.isFinite(oldAudio.currentTime) ? oldAudio.currentTime : 0;
      const src = resolveAudioUrl(cell);

      if (!state.lastSelection) {
        oldAudio.src = src;
        oldAudio.load();
        state.activeSlot = oldSlot;
      } else if (src !== oldAudio.src) {
        newAudio.pause();
        newAudio.src = src;
        newAudio.load();
        await waitForMedia(newAudio);
        newAudio.currentTime = clamp(currentTime, 0, Math.max(0, (newAudio.duration || currentTime) - 0.02));

        if (wasPlaying) {
          await newAudio.play();
          const now = audioCtx.currentTime;
          gains[oldSlot].gain.cancelScheduledValues(now);
          gains[newSlot].gain.cancelScheduledValues(now);
          gains[oldSlot].gain.setValueAtTime(gains[oldSlot].gain.value, now);
          gains[newSlot].gain.setValueAtTime(0, now);
          gains[oldSlot].gain.linearRampToValueAtTime(0, now + crossfadeMs / 1000);
          gains[newSlot].gain.linearRampToValueAtTime(1, now + crossfadeMs / 1000);
          window.setTimeout(() => oldAudio.pause(), crossfadeMs + 25);
        } else {
          gains[oldSlot].gain.value = 0;
          gains[newSlot].gain.value = 1;
        }
        state.activeSlot = newSlot;
      }

      state.xIndex = xi;
      state.yIndex = yi;
      state.lastSelection = cell;
      updateReadout(cell);
      renderGraph(cell);
      updateTransport();
      if (wasPlaying) tick();
    } finally {
      state.switching = false;
    }
  }

  async function play() {
    const active = els.audio[state.activeSlot];
    if (!active.src) return;
    showcaseAudio?.pause();
    document.dispatchEvent(new CustomEvent('gbr:labplay'));
    await waitForMedia(active);
    await active.play();
    state.playing = true;
    els.play.textContent = '❚❚';
    els.play.setAttribute('aria-label', 'Pause');
    tick();
  }

  function pause() {
    els.audio.forEach(a => a.pause());
    state.playing = false;
    els.play.textContent = '▶';
    els.play.setAttribute('aria-label', 'Play');
    cancelAnimationFrame(state.raf);
    updateTransport();
  }

  function tick() {
    cancelAnimationFrame(state.raf);
    updateTransport();
    if (state.playing) state.raf = requestAnimationFrame(tick);
  }

  function updateTransport() {
    const active = els.audio[state.activeSlot];
    const t = Number.isFinite(active.currentTime) ? active.currentTime : 0;
    const d = Number.isFinite(active.duration) ? active.duration : 0;
    els.time.textContent = formatTime(t);
    els.duration.textContent = formatTime(d);
    els.seek.value = d > 0 ? String(Math.round((t / d) * 1000)) : '0';
    const cursor = els.graph.querySelector('.gbr-progress-line');
    if (cursor) {
      const px = 70 + (d > 0 ? clamp(t / d, 0, 1) : 0) * 630;
      cursor.setAttribute('x1', String(px));
      cursor.setAttribute('x2', String(px));
    }
  }

  function updateReadout(cell) {
    els.readout.innerHTML = '';
    const a = document.createElement('strong');
    a.textContent = shortLabel(cell.y);
    const sep = document.createElement('span');
    sep.textContent = ' × ';
    const b = document.createElement('strong');
    b.textContent = shortLabel(cell.x);
    els.readout.append(a, sep, b);
  }

  function lookupCell(xv, yv) {
    return (manifest.cells || []).find(cell => String(cell.x) === String(xv) && String(cell.y) === String(yv)) || null;
  }

  function resolveAudioUrl(cell) {
    const suffix = `__${cell.suffix}.mp3`;
    if (externalFiles) {
      const match = externalFiles.find(file => String(file).toLowerCase().endsWith(suffix.toLowerCase()));
      if (!match) throw new Error(`No supplied audio file matches suffix ${suffix}`);
      return match;
    }
    // Ignore the title/prefix contract on purpose. The manifest provides the
    // generated filename, while suffix remains the stable identity.
    return new URL(cell.file, new URL(baseUrl, window.location.href)).href;
  }

  function renderGraph(cell) {
    const exp = manifest.experiment;
    if (exp === 'samp_sched') renderSamplerSchedulerGraph(els.graph, els.graphTitle, els.graphNote, cell);
    else if (exp === 'cfg_steps') renderNumericMatrixGraph(els.graph, els.graphTitle, els.graphNote, manifest, cell, 'steps', 'cfg');
    else if (exp === 'encoder_cfg_topk') renderNumericMatrixGraph(els.graph, els.graphTitle, els.graphNote, manifest, cell, 'top_k', 'encoder_cfg');
    else renderCategoricalGraph(els.graph, els.graphTitle, els.graphNote, manifest, cell);
  }

  return {
    manifest,
    select: (xi, yi) => selectCell(xi, yi, true),
    play,
    pause,
    destroy() {
      pause();
      showcaseAudio?.removeEventListener('play', stopForShowcase);
      document.removeEventListener('gbr:auxplay', stopForShowcase);
      sources.forEach(s => s.disconnect());
      gains.forEach(g => g.disconnect());
      audioCtx.close();
      root.innerHTML = '';
      root.classList.remove('gbr-matrix-lab');
    },
  };
}

export async function mountGBRMatrixSuite(root, options = {}) {
  if (!(root instanceof HTMLElement)) throw new TypeError('root must be an HTMLElement');

  const manifestUrl = options.manifestUrl || root.dataset.manifestUrl;
  root.classList.add('gbr-matrix-suite');
  root.innerHTML = `
    <div class="gbr-matrix-suite__toolbar">
      <div>
        <div class="gbr-lab-kicker">Good Boy Records / Parameter Lab</div>
        <strong class="gbr-matrix-suite__title">Controlled generation patch bay</strong>
      </div>
      <div class="gbr-matrix-suite__tabs" role="tablist" aria-label="Comparison experiment"></div>
    </div>
    <div class="gbr-matrix-suite__status" role="status">Reading comparison manifest…</div>
    <div class="gbr-matrix-suite__stage"></div>
  `;

  const tabs = root.querySelector('.gbr-matrix-suite__tabs');
  const status = root.querySelector('.gbr-matrix-suite__status');
  const stage = root.querySelector('.gbr-matrix-suite__stage');
  let active = null;
  let activeName = '';
  let rootManifest;

  const labels = {
    samp_sched: 'SAMPLER / SCHED',
    cfg_steps: 'CFG / STEPS',
    dit_textenc: 'DIT / TEXT ENC',
    encoder_cfg_topk: 'ENC CFG / TOP-K',
  };
  const order = Object.keys(labels);

  try {
    rootManifest = await loadManifest(manifestUrl);
  } catch (error) {
    status.classList.add('is-empty');
    status.innerHTML = `
      <strong>NO MATRIX CUT YET</strong>
      <span>The lab is installed, but <code>_comparison_manifest.json</code> has not been generated. Run <code>RUN-MATRIX-LAB.bat</code>, then rebuild the site.</span>
    `;
    stage.innerHTML = `<div class="gbr-matrix-empty"><span>PATCH BAY</span><strong>AWAITING SOURCE AUDIO</strong></div>`;
    return { destroy() {} };
  }

  const experiments = rootManifest.experiments || {};
  status.textContent = sourceSummary(rootManifest);

  order.forEach(name => {
    const info = experiments[name];
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.experiment = name;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-selected', 'false');
    button.className = 'gbr-matrix-suite__tab';
    if (!info) button.classList.add('is-unavailable');
    button.innerHTML = `<span>${labels[name]}</span><small>${info ? `${info.count} CUTS` : 'NOT CUT'}</small>`;
    button.addEventListener('click', () => selectExperiment(name));
    tabs.appendChild(button);
  });

  async function selectExperiment(name) {
    const info = experiments[name];
    tabs.querySelectorAll('button').forEach(button => {
      const selected = button.dataset.experiment === name;
      button.setAttribute('aria-selected', selected ? 'true' : 'false');
    });
    if (!info) {
      active?.destroy();
      active = null;
      activeName = name;
      status.textContent = `${labels[name]} has not been generated yet.`;
      stage.innerHTML = `<div class="gbr-matrix-empty"><span>${labels[name]}</span><strong>NOT CUT</strong><small>Enable this experiment in the matrix CFG and run the generator.</small></div>`;
      return;
    }
    if (activeName === name && active) return;
    active?.destroy();
    active = null;
    activeName = name;
    stage.innerHTML = '<div class="gbr-matrix-loading">Loading matrix…</div>';
    status.textContent = `${sourceSummary(rootManifest)} · ${info.count} controlled generation${info.count === 1 ? '' : 's'}`;
    try {
      const experimentManifestUrl = new URL(info.manifest, new URL(manifestUrl, window.location.href)).href;
      const baseUrl = new URL(`${info.folder}/`, new URL(manifestUrl, window.location.href)).href;
      stage.innerHTML = '<div class="gbr-matrix-suite__mount"></div>';
      active = await mountGBRMatrixLab(stage.firstElementChild, {
        manifestUrl: experimentManifestUrl,
        baseUrl,
        crossfadeMs: options.crossfadeMs ?? 90,
      });
    } catch (error) {
      stage.innerHTML = `<div class="gbr-matrix-error"><strong>MATRIX LOAD FAULT</strong><span>${escapeHtml(error?.message || String(error))}</span></div>`;
    }
  }

  const firstReady = order.find(name => experiments[name]) || order[0];
  await selectExperiment(firstReady);

  return {
    manifest: rootManifest,
    selectExperiment,
    destroy() {
      active?.destroy();
      root.innerHTML = '';
      root.classList.remove('gbr-matrix-suite');
    },
  };
}

function sourceSummary(manifest) {
  const src = manifest?.source || {};
  const title = src.title || 'comparison source';
  const version = src.version ? ` / ${src.version}` : '';
  return `${title}${version}`;
}

async function autoMountGBRMatrixSuites() {
  const hosts = [...document.querySelectorAll('[data-gbr-matrix-suite]')];
  for (const host of hosts) {
    if (host.dataset.gbrMatrixMounted === 'true') continue;
    host.dataset.gbrMatrixMounted = 'true';
    try {
      await mountGBRMatrixSuite(host, { manifestUrl: host.dataset.manifestUrl });
    } catch (error) {
      host.innerHTML = `<div class="gbr-matrix-error"><strong>PARAMETER LAB FAULT</strong><span>${escapeHtml(error?.message || String(error))}</span></div>`;
    }
  }
}

async function loadManifest(url) {
  if (!url) throw new Error('manifestUrl or manifest is required');
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Could not load matrix manifest: ${response.status} ${response.statusText}`);
  return response.json();
}

function renderFixed(el, baseline) {
  const items = [
    ['Encoder seed', baseline.encoder_seed],
    ['Sampler seed', baseline.sampler_seed],
    ['DiT', baseline.dit && shortLabel(baseline.dit)],
    ['Text encoder', baseline.text_encoder && shortLabel(baseline.text_encoder)],
    ['Sampler CFG', baseline.sampler_cfg],
    ['Steps', baseline.sampler_steps],
  ].filter(([, value]) => value !== undefined && value !== null && value !== '');
  el.innerHTML = `<span class="gbr-fixed-label">Held constant</span>${items.map(([k,v]) => `<span><b>${escapeHtml(k)}</b> ${escapeHtml(String(v))}</span>`).join('')}`;
}

function renderSamplerSchedulerGraph(svg, title, note, cell) {
  title.textContent = `${shortLabel(cell.x)} schedule · ${shortLabel(cell.y)} sampler`;
  note.textContent = 'Normalised scheduler shape, illustrative rather than extracted model sigmas';
  const pts = [];
  for (let i = 0; i <= 80; i++) {
    const t = i / 80;
    const n = schedulerProfile(String(cell.x), t);
    const px = 70 + t * 630;
    const py = 220 - n * 165;
    pts.push(`${px.toFixed(1)},${py.toFixed(1)}`);
  }
  svg.innerHTML = `
    ${graphFrame('Denoising step', 'relative noise')}
    <polyline class="gbr-curve" points="${pts.join(' ')}" fill="none" />
    <line class="gbr-progress-line" x1="70" y1="55" x2="70" y2="220" />
    <text class="gbr-graph-label" x="385" y="254" text-anchor="middle">${escapeHtml(shortLabel(cell.x))}</text>
    <text class="gbr-graph-value" x="690" y="78" text-anchor="end">${escapeHtml(shortLabel(cell.y))}</text>
  `;
}

function renderNumericMatrixGraph(svg, title, note, manifest, cell, xParam, yParam) {
  const cells = manifest.cells || [];
  const xVals = cells.map(c => Number(c.parameters?.[xParam])).filter(Number.isFinite);
  const yVals = cells.map(c => Number(c.parameters?.[yParam])).filter(Number.isFinite);
  const xv = Number(cell.parameters?.[xParam]);
  const yv = Number(cell.parameters?.[yParam]);
  const xmin = Math.min(...xVals), xmax = Math.max(...xVals);
  const ymin = Math.min(...yVals), ymax = Math.max(...yVals);
  const sx = v => 70 + ((v - xmin) / Math.max(1e-9, xmax - xmin)) * 630;
  const sy = v => 220 - ((v - ymin) / Math.max(1e-9, ymax - ymin)) * 165;
  const dots = cells.map(c => {
    const xx = Number(c.parameters?.[xParam]);
    const yy = Number(c.parameters?.[yParam]);
    if (!Number.isFinite(xx) || !Number.isFinite(yy)) return '';
    return `<circle class="gbr-matrix-dot" cx="${sx(xx)}" cy="${sy(yy)}" r="3.5"/>`;
  }).join('');
  title.textContent = `${prettyName(yParam)} ${formatNumber(yv)} · ${prettyName(xParam)} ${formatNumber(xv)}`;
  note.textContent = 'Every faint point is another generated cell in this matrix';
  svg.innerHTML = `
    ${graphFrame(prettyName(xParam), prettyName(yParam))}
    ${dots}
    <line class="gbr-crosshair" x1="${sx(xv)}" y1="55" x2="${sx(xv)}" y2="220" />
    <line class="gbr-crosshair" x1="70" y1="${sy(yv)}" x2="700" y2="${sy(yv)}" />
    <circle class="gbr-selected-dot" cx="${sx(xv)}" cy="${sy(yv)}" r="7"/>
    <text class="gbr-graph-value" x="690" y="78" text-anchor="end">${escapeHtml(`${formatNumber(yv)} / ${formatNumber(xv)}`)}</text>
  `;
}

function renderCategoricalGraph(svg, title, note, manifest, cell) {
  const xs = manifest.axis_x?.values || [];
  const ys = manifest.axis_y?.values || [];
  const xi = Math.max(0, xs.indexOf(cell.x));
  const yi = Math.max(0, ys.indexOf(cell.y));
  const sx = xs.length <= 1 ? 385 : 70 + (xi / (xs.length - 1)) * 630;
  const sy = ys.length <= 1 ? 137 : 220 - (yi / (ys.length - 1)) * 165;
  title.textContent = `${shortLabel(cell.y)} × ${shortLabel(cell.x)}`;
  note.textContent = 'Model precision/quantisation comparison; all other generation settings are held constant';
  svg.innerHTML = `
    ${graphFrame(prettyName(manifest.axis_x.name), prettyName(manifest.axis_y.name))}
    <line class="gbr-crosshair" x1="${sx}" y1="55" x2="${sx}" y2="220" />
    <line class="gbr-crosshair" x1="70" y1="${sy}" x2="700" y2="${sy}" />
    <circle class="gbr-selected-dot" cx="${sx}" cy="${sy}" r="8" />
    <text class="gbr-graph-value" x="690" y="78" text-anchor="end">${escapeHtml(shortLabel(cell.x))}</text>
    <text class="gbr-graph-label" x="690" y="98" text-anchor="end">${escapeHtml(shortLabel(cell.y))}</text>
  `;
}

function graphFrame(xLabel, yLabel) {
  return `
    <line class="gbr-axis" x1="70" y1="220" x2="700" y2="220" />
    <line class="gbr-axis" x1="70" y1="55" x2="70" y2="220" />
    <line class="gbr-gridline" x1="70" y1="165" x2="700" y2="165" />
    <line class="gbr-gridline" x1="70" y1="110" x2="700" y2="110" />
    <text class="gbr-axis-text" x="385" y="248" text-anchor="middle">${escapeHtml(xLabel)}</text>
    <text class="gbr-axis-text" x="22" y="138" text-anchor="middle" transform="rotate(-90 22 138)">${escapeHtml(yLabel)}</text>
  `;
}

function schedulerProfile(name, t) {
  const n = name.toLowerCase();
  if (n.includes('karras')) return Math.pow(1 - t, 2.7);
  if (n.includes('exponential')) {
    const e = Math.exp(-4 * t), end = Math.exp(-4);
    return (e - end) / (1 - end);
  }
  if (n.includes('sgm')) return Math.pow(Math.cos(t * Math.PI / 2), 1.35);
  if (n.includes('ddim')) return 1 - t;
  if (n.includes('beta')) return 1 - (t * t * (3 - 2 * t));
  if (n.includes('simple')) return Math.sqrt(Math.max(0, 1 - t));
  if (n.includes('normal')) return Math.pow(1 - t, 1.4);
  return 1 - t;
}

function playJackClick(ctx) {
  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'triangle';
  osc.frequency.setValueAtTime(1450, now);
  osc.frequency.exponentialRampToValueAtTime(420, now + 0.032);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.13, now + 0.002);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.042);
  osc.connect(gain).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.05);

  const length = Math.max(1, Math.floor(ctx.sampleRate * 0.018));
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, 4);
  const noise = ctx.createBufferSource();
  const ng = ctx.createGain();
  noise.buffer = buffer;
  ng.gain.value = 0.055;
  noise.connect(ng).connect(ctx.destination);
  noise.start(now);
}

function waitForMedia(audio) {
  if (audio.readyState >= 2) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const ok = () => { cleanup(); resolve(); };
    const bad = () => { cleanup(); reject(new Error(`Could not load audio: ${audio.currentSrc || audio.src}`)); };
    const cleanup = () => {
      audio.removeEventListener('canplay', ok);
      audio.removeEventListener('error', bad);
    };
    audio.addEventListener('canplay', ok, { once: true });
    audio.addEventListener('error', bad, { once: true });
  });
}

function displayExperiment(name) {
  return ({
    samp_sched: 'Sampler / Scheduler Patch Bay',
    cfg_steps: 'CFG / Steps Patch Bay',
    dit_textenc: 'DiT / Text Encoder Patch Bay',
    encoder_cfg_topk: 'Encoder CFG / Top-K Patch Bay',
  })[name] || prettyName(name);
}

function shortLabel(value) {
  return String(value)
    .replace(/\.safetensors$/i, '')
    .replace(/^minimax_music3_/i, '')
    .replace(/^text_encoder_/i, 'TE ')
    .replace(/^dit_/i, 'DiT ');
}

function prettyName(value) {
  return String(value || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${Math.floor(seconds / 60)}:${s}`;
}

function formatNumber(v) {
  return Number.isInteger(v) ? String(v) : Number(v).toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
}

function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
function normaliseBase(url) { return String(url).endsWith('/') ? String(url) : `${url}/`; }
function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}


if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', autoMountGBRMatrixSuites, { once: true });
} else {
  autoMountGBRMatrixSuites();
}
