#!/usr/bin/env python3
"""Remove stale deployment output before a normal local showcase build."""
from pathlib import Path
from fs_utils import remove_path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
if OUT.exists():
    remove_path(OUT)
    print("Removed stale _site deployment copy.")
