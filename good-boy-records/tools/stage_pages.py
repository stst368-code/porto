#!/usr/bin/env python3
"""Stage deployable runtime files without maintaining a duplicate local audio cache.

Local preview reads curated audio directly from showcase/. For deployment, this
script copies only catalogue-referenced audio into _site/ at the same relative
URL. That leaves one authoritative local copy and one deploy copy only when
_site is deliberately staged.
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

from fs_utils import remove_path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
LIMIT = 1024 ** 3


def copy_item(source: Path) -> None:
    target = OUT / source.relative_to(ROOT)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    elif source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def referenced_audio() -> set[Path]:
    cat_path = ROOT / "data" / "catalogue.json"
    if not cat_path.is_file():
        return set()
    data = json.loads(cat_path.read_text(encoding="utf-8"))
    urls: set[str] = set()
    for track in data.get("tracks") or []:
        for value in ((track.get("audio") or {}).get("sources") or {}).values():
            if value:
                urls.add(str(value))
    for song in data.get("songs") or []:
        for item in song.get("atr") or []:
            if isinstance(item, dict) and item.get("src"):
                urls.add(str(item["src"]))
    for track in ((data.get("easter") or {}).get("tracks") or []):
        for value in ((track.get("audio") or {}).get("sources") or {}).values():
            if value:
                urls.add(str(value))

    out: set[Path] = set()
    for value in urls:
        if value.startswith(("http://", "https://", "//", "data:", "blob:")):
            continue
        rel = Path(value.replace("\\", "/"))
        if rel.is_absolute() or ".." in rel.parts:
            raise SystemExit(f"Unsafe catalogue media path: {value}")
        source = ROOT / rel
        if not source.is_file():
            raise SystemExit(f"Catalogue references missing media: {value}")
        out.add(source)
    return out


def main() -> int:
    if OUT.exists():
        remove_path(OUT)
    OUT.mkdir()
    for name in ["index.html", "assets", "data"]:
        copy_item(ROOT / name)

    media = referenced_audio()
    for source in sorted(media):
        copy_item(source)

    files = [p for p in OUT.rglob("*") if p.is_file()]
    too_large = [p for p in files if p.stat().st_size >= 100 * 1024 * 1024]
    if too_large:
        print("Files at/over GitHub's normal 100 MiB file limit:")
        for path in too_large:
            print("  ", path.relative_to(OUT))
        return 1

    total = sum(p.stat().st_size for p in files)
    print(f"Staged {len(files)} runtime files including {len(media)} referenced audio file(s): {total / (1024**2):.1f} MiB / 1024 MiB")
    if total >= LIMIT:
        print("Published site is at/over 1 GiB; trim audio or other runtime assets before deployment.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
