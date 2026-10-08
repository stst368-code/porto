"""Profile non-showcase audio using GBR's existing timeline/audio.py DSP engine.

No audio sidecars are written alongside source files. Only the result is stored
in the research SQLite database. Requires the timeline audio dependencies.
"""
import importlib.util
import json
from pathlib import Path
import sys


def profile_audio(path, audio_hash, frame_hz=10):
    timeline_dir = Path(__file__).resolve().parents[1] / 'timeline'
    script = timeline_dir / 'audio.py'
    if not script.exists():
        raise RuntimeError(f'Existing GBR timeline audio analyser not found: {script}')
    old = list(sys.path)
    try:
        sys.path.insert(0, str(timeline_dir))
        spec = importlib.util.spec_from_file_location('gbr_timeline_profile_engine', script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        payload = mod.analyse(Path(path), {'audio': audio_hash}, frame_hz, .64, 2.0)
        return json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    finally:
        sys.path[:] = old
