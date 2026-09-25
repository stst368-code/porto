#!/usr/bin/env python3
"""Normalize Good Boy Records runtime source names without changing behaviour."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent

REPLACEMENTS = (
    ("studio-v11.css", "studio.css"),
    ("studio-v11.js", "studio.js"),
    ("gbr11-", "gbr-"),
    ("gbr11:", "gbr:"),
)

TARGETS = [
    ROOT / "index.html",
    ROOT / "templates" / "index.html",
    ROOT / "assets" / "css" / "studio.css",
    ROOT / "assets" / "js" / "studio.js",
    ROOT / "tools" / "test_player.py",
]

def rewrite(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    original = text
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}")

def remove_old(path: Path) -> None:
    if path.exists():
        path.unlink()
        print(f"removed {path.relative_to(ROOT)}")

for path in TARGETS:
    rewrite(path)

remove_old(ROOT / "assets" / "css" / "studio-v11.css")
remove_old(ROOT / "assets" / "js" / "studio-v11.js")

for cache in ROOT.rglob("__pycache__"):
    if cache.is_dir():
        shutil.rmtree(cache, ignore_errors=True)
        print(f"removed {cache.relative_to(ROOT)}")

print("GBR source naming cleanup complete.")
