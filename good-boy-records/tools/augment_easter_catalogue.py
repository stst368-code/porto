#!/usr/bin/env python3
"""Refresh the Easter catalogue from the actual R2 objects via rclone.

Audio is sufficient. A same-stem YAML and same-stem artwork are optional.
The YAML uses the normal GBR schema; its existing `story` field is surfaced.
"""
from __future__ import annotations

import json, os, re, subprocess, sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required: python -m pip install PyYAML")

AUDIO_EXTS = {".flac", ".mp3", ".wav", ".m4a", ".ogg", ".opus", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def slugify(value: Any) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "track"


def humanise(value: Any) -> str:
    return re.sub(r"[-_]+", " ", str(value or "")).strip().title()


def run(*args: str) -> str:
    p = subprocess.run(["rclone", *args], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or f"rclone exited {p.returncode}")
    return p.stdout


def remote_root() -> str:
    remote = os.environ.get("R2_REMOTE", "r2").rstrip(":")
    bucket = os.environ.get("R2_BUCKET", "good-boy-records").strip("/")
    return f"{remote}:{bucket}/showcase/easter"


def public_path(name: str) -> str:
    return "showcase/easter/" + name.replace("\\", "/")


def load_remote_yaml(root: str, name: str) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(run("cat", f"{root}/{name}")) or {}
        return raw if isinstance(raw, dict) else {}
    except Exception as exc:
        print(f"warn Easter YAML {name}: {exc}")
        return {}


def first_text(raw: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def build_tracks(root: str) -> list[dict[str, Any]]:
    names = [x.strip().replace("\\", "/") for x in run("lsf", root, "--files-only", "-R").splitlines() if x.strip()]
    # Easter is intentionally flat for track ownership. Ignore nested objects rather than pairing ambiguously.
    names = [n for n in names if "/" not in n]
    by_stem: dict[str, list[str]] = {}
    for name in names:
        by_stem.setdefault(Path(name).stem.casefold(), []).append(name)

    audio_stems = sorted(
        (stem for stem, members in by_stem.items() if any(Path(n).suffix.lower() in AUDIO_EXTS for n in members)),
        key=str.casefold,
    )
    tracks: list[dict[str, Any]] = []
    for index, stem_key in enumerate(audio_stems, 1):
        members = by_stem[stem_key]
        audio = [n for n in members if Path(n).suffix.lower() in AUDIO_EXTS]
        label = Path(sorted(audio, key=str.casefold)[0]).stem
        yaml_names = [n for n in members if Path(n).suffix.lower() in {".yaml", ".yml"}]
        image_names = [n for n in members if Path(n).suffix.lower() in IMAGE_EXTS]
        raw = load_remote_yaml(root, sorted(yaml_names, key=str.casefold)[0]) if yaml_names else {}

        sources: dict[str, str] = {}
        for name in sorted(audio, key=str.casefold):
            fmt = Path(name).suffix.lower().lstrip(".")
            sources.setdefault(fmt, public_path(name))

        title = first_text(raw, "title", "song_title", "track_title") or label
        version = first_text(raw, "version", "genre", "song_genre") or "Hidden Track"
        story = first_text(raw, "story")
        track: dict[str, Any] = {
            "id": f"easter-{index:02d}-{slugify(label)}",
            "title": title,
            "displayTitle": title if title != label else humanise(label),
            "variant": version,
            "genre": {
                "cluster": "easter",
                "parent_genre": "Easter Universe",
                "child_genre": version,
                "parent_colour": "#D0802F",
                "child_colour": "#D9A65E",
                "taxonomy_order": index,
                "parent_order": 0,
            },
            "audio": {"sources": sources},
        }
        if yaml_names:
            track["yamlUrl"] = public_path(sorted(yaml_names, key=str.casefold)[0])
        if story:
            track["story"] = story
        if image_names:
            track["artwork_url"] = public_path(sorted(image_names, key=str.casefold)[0])
        tracks.append(track)
    return tracks


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: augment_easter_catalogue.py <catalogue.json> [repo-root]")
    catalogue_path = Path(sys.argv[1])
    data = json.loads(catalogue_path.read_text(encoding="utf-8"))
    root = remote_root()
    try:
        tracks = build_tracks(root)
    except (FileNotFoundError, RuntimeError) as exc:
        # Do not destroy a valid locally-built Easter catalogue merely because rclone/R2 is unavailable.
        print(f"warn Easter R2 refresh skipped: {exc}")
        return 0
    data["easter"] = {"enabled": bool(tracks), "count": len(tracks), "tracks": tracks}
    # Support either catalogue shape consumed by the player.
    data.pop("easter_tracks", None)
    catalogue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Easter R2 refresh: {len(tracks)} track(s) from {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
