"""Parse GBR audio-analysis v2, retaining full compressed frames in SQLite."""
import gzip
import hashlib
import json
import statistics
from pathlib import Path
from utils import scalar_number


def audio_summary_bytes(raw, source_name='generated:timeline'):
    d = json.loads(raw)
    if not isinstance(d, dict):
        raise ValueError('Audio analysis JSON root must be an object')
    dance = d.get('dance') or {}
    frames = dance.get('frames') or []
    channels = dance.get('channels') or []
    scale = scalar_number(dance.get('scale')) or 1
    stats = {}
    for ch in ('energy', 'bass', 'brightness', 'change'):
        values = []
        if ch in channels:
            idx = channels.index(ch)
            values = [float(row[idx]) / scale for row in frames
                      if isinstance(row, list) and len(row) > idx
                      and isinstance(row[idx], (float, int))]
        stats[ch + '_mean'] = round(statistics.fmean(values), 6) if values else None
        stats[ch + '_std'] = round(statistics.pstdev(values), 6) if values else None
    summary = d.get('summary') or {}
    source = d.get('source') or {}
    out = {
        'analysis_path': source_name,
        'analysis_hash': hashlib.sha256(raw).hexdigest(),
        'audio_source_hash': source.get('audio'),
        'format': d.get('format'),
        'duration': scalar_number(d.get('duration')),
        'bpm': scalar_number(d.get('bpm')),
        'rms_db': scalar_number(summary.get('rms_db')),
        'peak_db': scalar_number(summary.get('peak_db')),
        'onset_density': scalar_number(summary.get('onset_density')),
        'frames': len(frames),
        'beats': len(dance.get('beats') or []),
        'events': len(dance.get('events') or []),
        'frame_hz': scalar_number(dance.get('frame_hz')),
        'raw_json_gz': gzip.compress(raw, compresslevel=6),
    }
    out.update(stats)
    return out


def audio_summary(path):
    return audio_summary_bytes(Path(path).read_bytes(), str(path))
