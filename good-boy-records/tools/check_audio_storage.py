#!/usr/bin/env python3
"""Verify curated showcase audio is not mirrored into generated local asset caches."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".webm"}


def media_files(path: Path):
    return [p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS] if path.exists() else []


def main() -> int:
    catalogue_path = ROOT / "data" / "catalogue.json"
    if not catalogue_path.is_file():
        print("FAIL  data/catalogue.json is missing")
        return 1
    catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))

    refs: list[str] = []
    for track in catalogue.get("tracks") or []:
        refs.extend(str(v) for v in ((track.get("audio") or {}).get("sources") or {}).values() if v)
    for song in catalogue.get("songs") or []:
        refs.extend(str(item.get("src")) for item in song.get("atr") or [] if isinstance(item, dict) and item.get("src"))
    for track in ((catalogue.get("easter") or {}).get("tracks") or []):
        refs.extend(str(v) for v in ((track.get("audio") or {}).get("sources") or {}).values() if v)

    bad_refs = [ref for ref in refs if not ref.startswith("showcase/")]
    missing = [ref for ref in refs if not (ROOT / ref).is_file()]
    cache_files = media_files(ROOT / "assets" / "audio" / "tracks") + media_files(ROOT / "assets" / "audio" / "atr")

    for ref in bad_refs:
        print(f"FAIL  catalogue audio is not source-relative: {ref}")
    for ref in missing:
        print(f"FAIL  catalogue audio is missing: {ref}")
    for path in cache_files:
        print(f"FAIL  duplicate generated audio remains: {path.relative_to(ROOT)}")

    if bad_refs or missing or cache_files:
        return 1

    source_files = media_files(ROOT / "showcase")
    print(f"PASS  {len(refs)} catalogue audio reference(s) point directly into showcase/")
    print(f"PASS  assets/audio/tracks and assets/audio/atr contain no mirrored song audio")
    print(f"INFO  curated showcase currently contains {len(source_files)} audio file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
