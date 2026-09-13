#!/usr/bin/env python3
"""Preflight the Good Boy Records repository for GitHub + GitHub Pages."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOWCASE = ROOT / "showcase"
CATALOGUE = ROOT / "data" / "catalogue.json"
MIB = 1024 * 1024
GIB = 1024 * MIB
GIT_BLOCK = 100 * MIB
GIT_WARN = 50 * MIB
PAGES_MAX = 1 * GIB
AUDIO_EXTS = {".flac", ".mp3", ".wav", ".m4a", ".ogg", ".opus", ".webm"}


def fmt(n: int) -> str:
    return f"{n / MIB:,.1f} MiB"


def catalogue_audio() -> set[Path]:
    if not CATALOGUE.is_file():
        return set()
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    urls: set[str] = set()
    for track in data.get("tracks") or []:
        urls.update(str(v) for v in ((track.get("audio") or {}).get("sources") or {}).values() if v)
    for song in data.get("songs") or []:
        for item in song.get("atr") or []:
            if isinstance(item, dict) and item.get("src"):
                urls.add(str(item["src"]))
    for track in ((data.get("easter") or {}).get("tracks") or []):
        urls.update(str(v) for v in ((track.get("audio") or {}).get("sources") or {}).values() if v)
    result: set[Path] = set()
    for value in urls:
        if value.startswith(("http://", "https://", "//", "data:", "blob:")):
            continue
        p = ROOT / Path(value.replace("\\", "/"))
        if p.is_file():
            result.add(p)
    return result


def main() -> int:
    errors = 0
    warnings = 0
    files = [p for p in SHOWCASE.rglob("*") if p.is_file()] if SHOWCASE.is_dir() else []
    if not files:
        print("ERROR: good-boy-records/showcase contains no files.")
        return 1

    oversized = [p for p in files if p.stat().st_size >= GIT_BLOCK]
    large = [p for p in files if GIT_WARN <= p.stat().st_size < GIT_BLOCK]
    if oversized:
        errors += 1
        print("ERROR: GitHub blocks normal Git files at/over 100 MiB:")
        for p in oversized:
            print(f"  {fmt(p.stat().st_size):>12}  {p.relative_to(ROOT)}")
    if large:
        warnings += 1
        print("WARN: GitHub warns on files at/over 50 MiB:")
        for p in large:
            print(f"  {fmt(p.stat().st_size):>12}  {p.relative_to(ROOT)}")

    all_audio = [p for p in files if p.suffix.lower() in AUDIO_EXTS]
    all_audio_size = sum(p.stat().st_size for p in all_audio)
    print(f"Showcase audio on disk: {len(all_audio)} file(s), {fmt(all_audio_size)}")

    referenced = catalogue_audio()
    if referenced:
        referenced_size = sum(p.stat().st_size for p in referenced)
        print(f"Catalogue-referenced deploy audio: {len(referenced)} file(s), {fmt(referenced_size)}")
        if referenced_size >= PAGES_MAX:
            errors += 1
            print("ERROR: referenced audio alone is already at/over GitHub Pages' 1 GiB published-site limit.")
        elif referenced_size >= int(PAGES_MAX * 0.85):
            warnings += 1
            print("WARN: referenced audio is above 85% of the 1 GiB Pages limit before HTML/images/assets are added.")
    else:
        print("INFO: no built catalogue found; the GitHub workflow will perform the exact deployment-size check after building.")

    print(f"GitHub preflight: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
