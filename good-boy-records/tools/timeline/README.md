# GBR Music / Dance Timeline v2

Overlay this `good-boy-records` folder onto the cleaned repo. No files go in the GBR root.

Run everything:

    tools\launchers\timeline-all.bat

Or separately:

    tools\launchers\timeline-lyrics.bat
    tools\launchers\timeline-audio.bat
    tools\launchers\timeline-playback.bat
    tools\launchers\timeline-status.bat

Audio dependencies once:

    tools\launchers\timeline-setup-audio.bat

Per variant the tools write fixed filenames:

    gbr.lyrics.json
    gbr.audio.json
    gbr.playback.json

The variant folder is the durable identity. Audio/YAML filenames and paths are not stored as identity. A fast content fingerprint is stored instead, so renaming a file does not cause expensive work to rerun, while replacing the audio or changing authored lyrics does.

Existing `gbr.lyrics.json` files produced by the cleanup have no content signature. On the first v2 run they are simply adopted/stamped; WhisperX does **not** rerun all of them.

## Deterministic dance data

`gbr.audio.json` stores a compact 10 Hz timeline. Each frame is four 0..255 integers:

    [energy, bass, brightness, change]

Time is implicit: `frame_index / frame_hz`.

It also stores beat `[time, strength]` pairs and sparse `pulsar` events. Pulsars are based primarily on sudden local energy lift plus onset/spectral novelty, so a continuously loud section does not repeatedly fire major blasts.

`gbr.playback.json` is the combined website-facing file: lyric timings + dance timeline + beats + pulsars + line/word reaction values.

Line/word reactions look like:

    "reaction": {
      "auto": {"intensity": 0.72, "accent": 0.81, "pulsar": 0.91},
      "manual": null
    }

A later editor can set, for example:

    "manual": {"pulsar": 1.0}

or suppress it with:

    "manual": {"pulsar": 0.0}

Manual values and `manual_events` survive playback recompilation.

`dance_runtime.js` is the browser-side helper for the Sonic UI integration. It synchronises from `audio.currentTime`, emits continuous frames, beats and events, and resets event cursors after seeking so it cannot fire a backlog. It does not move/open/centralise graph nodes.

Intended visual mapping:
- energy -> cluster/node/line luminosity
- bass -> centre artwork thump
- brightness -> star bloom
- change -> line charge/motion
- pulsar -> centre artwork flash followed by travelling light along cluster edges to outward nodes

The next step is only the actual hook-up to the existing `landscape.html` renderer.


## Lyric environment setup

The old lyric virtual environment does **not** need to be copied into GBR.
Windows virtual environments are path-sensitive, so moving/copying a venv is
less reliable than either reusing it in place or rebuilding it.

Recommended permanent setup:

    tools\launchers\timeline-setup-lyrics.bat

This creates:

    good-boy-records\.venv-whisperx\

and installs GPU PyTorch/torchaudio, WhisperX, Demucs and PyYAML.

Check it with:

    tools\launchers\timeline-check-lyrics-env.bat

If the old environment still works where it currently lives, you can reuse it
without moving it:

    set "GBR_WHISPERX_PYTHON=C:\path\to\old\venv\Scripts\python.exe"
    tools\launchers\timeline-lyrics.bat --track moses

For future command windows:

    setx GBR_WHISPERX_PYTHON "C:\path\to\old\venv\Scripts\python.exe"

The lyric launcher no longer silently falls back to the system Python. That
avoids accidentally picking up a CPU-only Torch installation.

Model caches are normally stored outside the venv in user-level caches, so a
rebuild usually does not mean copying all model weights into the GBR repo.
