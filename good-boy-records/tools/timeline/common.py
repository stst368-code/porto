#!/usr/bin/env python3
"""Shared discovery/path helpers for GBR timeline tools.

The important rule is: identity comes from the variant DIRECTORY, not from an
audio filename. Lyrics use the human-readable variant directory name while the
other derived sidecars keep fixed names:

    <variant-folder>.lyrics.json
    gbr.audio.json
    gbr.playback.json

The lyric JSON contains content fingerprints rather than absolute source paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:
    yaml = None

AUDIO_EXTS = {".flac", ".wav", ".mp3", ".opus", ".ogg", ".m4a", ".aac"}
AUDIO_RANK = {".flac": 0, ".wav": 1, ".opus": 2, ".ogg": 3, ".mp3": 4, ".m4a": 5, ".aac": 6}

LEGACY_LYRICS_NAME = "gbr.lyrics.json"
AUDIO_NAME = "gbr.audio.json"
PLAYBACK_NAME = "gbr.playback.json"

LYRICS_FORMAT = "gbr-word-lyrics-v2"
AUDIO_FORMAT = "gbr-audio-analysis-v2"
PLAYBACK_FORMAT = "gbr-playback-v2"

DIRECTIVE = re.compile(r"^\s*\[[^\]]+\]\s*$")


@dataclass(frozen=True)
class Variant:
    directory: Path
    yaml_path: Path
    raw: dict[str, Any]
    audio: Path

    @property
    def title(self) -> str:
        return str(self.raw.get("title") or self.yaml_path.stem)

    @property
    def version(self) -> str:
        return str(self.raw.get("version") or "").strip()


def lyrics_name(variant: Variant) -> str:
    """Canonical lyric filename tied to the variant-directory identity."""
    return f"{variant.directory.name}.lyrics.json"


def lyrics_path(variant: Variant) -> Path:
    return variant.directory / lyrics_name(variant)


def legacy_lyrics_path(variant: Variant) -> Path:
    return variant.directory / LEGACY_LYRICS_NAME


def repo_root() -> Path:
    # good-boy-records/tools/timeline/common.py -> good-boy-records
    return Path(__file__).resolve().parents[2]


def default_showcase() -> Path:
    return repo_root() / "showcase"


def resolve_showcase(explicit: str | None) -> Path:
    path = Path(explicit).expanduser().resolve() if explicit else default_showcase().resolve()
    if not path.is_dir():
        raise SystemExit(f"Showcase folder does not exist: {path}")
    return path


def slugify(value: str) -> str:
    value = str(value or "").strip().lower().replace("_", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "track"


def normalised_stem(path: Path) -> str:
    return re.sub(r"^\d+", "", path.stem.lower()).lstrip(" _-")


def is_atr_path(path: Path, showcase: Path) -> bool:
    try:
        rel = path.relative_to(showcase)
    except ValueError:
        rel = path
    return any(part.casefold().endswith("-atr") for part in rel.parts[:-1])


def repair_literal_block_indentation(text: str, keys: tuple[str, ...] = ("lyrics",)) -> tuple[str, list[str]]:
    """Repair the common generated-YAML literal-block indentation error in-memory."""
    lines = text.splitlines()
    repaired: list[str] = []
    changed: list[str] = []
    block_key: str | None = None
    block_indent = 0
    key_re = re.compile(
        r"^(?P<indent>\s*)(?P<key>" + "|".join(re.escape(k) for k in keys) + r")\s*:\s*[|>]\s*[-+]?\s*$",
        re.IGNORECASE,
    )
    yaml_key_re = re.compile(r"^[A-Za-z0-9_.-]+\s*:\s*(?:\S.*)?$")
    for line_no, line in enumerate(lines, start=1):
        match = key_re.match(line)
        if match:
            block_key = match.group("key").lower()
            block_indent = len(match.group("indent"))
            repaired.append(line)
            continue
        if block_key is not None:
            if not line.strip():
                repaired.append(line)
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent <= block_indent:
                stripped = line.strip()
                if indent == 0 and yaml_key_re.match(stripped) and not stripped.startswith("["):
                    block_key = None
                    repaired.append(line)
                    continue
                repaired.append(" " * (block_indent + 2) + line.lstrip())
                changed.append(f"{block_key}: line {line_no}")
                continue
        repaired.append(line)
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(repaired) + suffix, changed


def load_yaml(path: Path) -> dict[str, Any] | None:
    if yaml is None:
        raise SystemExit("PyYAML is required: pip install pyyaml")
    text = path.read_text(encoding="utf-8-sig")
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        repaired, changed = repair_literal_block_indentation(text)
        if not changed:
            return None
        try:
            raw = yaml.safe_load(repaired) or {}
        except Exception:
            return None
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def choose_audio(directory: Path, yaml_path: Path) -> Path | None:
    files = sorted(
        (p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS),
        key=lambda p: (AUDIO_RANK.get(p.suffix.lower(), 99), p.name.casefold()),
    )
    if not files:
        return None

    # Strongest association: audio stem matches YAML stem.
    ystem = normalised_stem(yaml_path)
    exact = [p for p in files if normalised_stem(p) == ystem]
    if exact:
        return exact[0]

    # Normal curated case: FLAC + MP3 represent the same render stem.
    stems = {}
    for p in files:
        stems.setdefault(normalised_stem(p), []).append(p)
    if len(stems) == 1:
        return sorted(next(iter(stems.values())), key=lambda p: (AUDIO_RANK.get(p.suffix.lower(), 99), p.name.casefold()))[0]

    # If one stem begins with the YAML stem, accept that render family.
    prefix_groups = [group for stem, group in stems.items() if stem.startswith(ystem + "_") or stem.startswith(ystem + "-")]
    if len(prefix_groups) == 1:
        return sorted(prefix_groups[0], key=lambda p: (AUDIO_RANK.get(p.suffix.lower(), 99), p.name.casefold()))[0]

    return None


def discover_variants(showcase: Path, filters: Iterable[str] = ()) -> list[Variant]:
    filters = [str(x).casefold() for x in filters if str(x).strip()]
    found: list[Variant] = []
    yaml_paths = sorted(
        [*showcase.rglob("*.yaml"), *showcase.rglob("*.yml")],
        key=lambda p: p.as_posix().casefold(),
    )
    for yaml_path in yaml_paths:
        if is_atr_path(yaml_path, showcase):
            continue
        raw = load_yaml(yaml_path)
        if not raw or not raw.get("lyrics"):
            # Composition YAMLs are not variant jobs.
            continue
        haystack = f"{yaml_path.relative_to(showcase).as_posix()} {raw.get('title','')} {raw.get('version','')}".casefold()
        if filters and not any(f in haystack for f in filters):
            continue
        audio = choose_audio(yaml_path.parent, yaml_path)
        if audio is None:
            print(f"skip {yaml_path.relative_to(showcase)}: no unambiguous audio in this variant folder")
            continue
        found.append(Variant(yaml_path.parent, yaml_path, raw, audio))
    return found


def atomic_json(path: Path, payload: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None



def text_hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def fast_file_fingerprint(path: Path, chunk: int = 1024 * 1024) -> str:
    """Path-independent fingerprint: size + first/middle/last 1 MiB."""
    size = path.stat().st_size
    h = hashlib.sha256()
    h.update(str(size).encode("ascii"))
    with path.open("rb") as f:
        if size <= chunk * 3:
            h.update(f.read())
        else:
            h.update(f.read(chunk))
            f.seek(max(0, size // 2 - chunk // 2)); h.update(f.read(chunk))
            f.seek(max(0, size - chunk)); h.update(f.read(chunk))
    return h.hexdigest()


def source_signature(variant: Variant) -> dict[str, str]:
    return {
        "audio": fast_file_fingerprint(variant.audio),
        "lyrics": text_hash(str(variant.raw.get("lyrics") or "")),
    }


def source_matches(payload: dict[str, Any] | None, signature: dict[str, str]) -> bool | None:
    if not payload:
        return False
    source = payload.get("source")
    if not isinstance(source, dict) or not (source.get("audio") or source.get("lyrics")):
        return None
    if source.get("audio") != signature["audio"] or source.get("lyrics") != signature["lyrics"]:
        return False

    # Optional signature dimensions can be added by individual timeline tools.
    # Language was introduced for lyric alignment in v2.4. Legacy lyric sidecars
    # did not store it and were all produced with the old hard-coded English
    # default, so a missing source language is deliberately treated as ``en``.
    if "language" in signature:
        source_language = str(source.get("language") or "en").strip().lower().replace("_", "-")
        if source_language != signature["language"]:
            return False
    return True


def adopt_signature(path: Path, payload: dict[str, Any], signature: dict[str, str]) -> None:
    updated = dict(payload)
    updated["source"] = signature
    atomic_json(path, updated)


def migrate_old_lyrics(variant: Variant) -> Path | None:
    """Reuse/migrate an existing lyric sidecar without rerunning WhisperX.

    Canonical output is <variant-folder>.lyrics.json. The cleanup-era
    gbr.lyrics.json name is renamed directly when possible, preserving the
    already path-free JSON contents. Older filename-based sidecars are compacted
    into the canonical filename and brittle source path/filename fields dropped.
    """
    target = lyrics_path(variant)
    if target.is_file():
        return target

    legacy = legacy_lyrics_path(variant)
    if legacy.is_file():
        legacy.replace(target)
        print(f"  ~ renamed lyric sidecar: {legacy.name} -> {target.name}")
        return target

    candidates = []
    for p in sorted(variant.directory.glob("*.lyrics.json")):
        if p.name in {target.name, LEGACY_LYRICS_NAME}:
            continue
        data = read_json(p)
        if not data or not isinstance(data.get("lines"), list):
            continue
        stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
        cov = stats.get("coverage")
        coverage = float(cov) if isinstance(cov, (int, float)) else -1.0
        candidates.append((coverage, p.stat().st_mtime_ns, p, data))
    if not candidates:
        return None

    _, _, source, data = max(candidates, key=lambda x: (x[0], x[1]))
    compact = {
        "format": LYRICS_FORMAT,
        "version": 2,
        "title": data.get("title"),
        "song_version": data.get("song_version"),
        "stats": data.get("stats") or {},
        "quality": data.get("quality") or {},
        "lines": data.get("lines") or [],
    }
    for li, line in enumerate(compact["lines"], start=1):
        line["id"] = str(line.get("id") or f"l{li:04d}")
        words = line.get("words") if isinstance(line.get("words"), list) else []
        for wi, word in enumerate(words, start=1):
            word["id"] = str(word.get("id") or f"{line['id']}w{wi:03d}")
    atomic_json(target, compact)
    print(f"  ~ reused old lyric alignment: {source.name} -> {target.name}")
    return target


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--showcase", help="override good-boy-records/showcase")
    parser.add_argument("--track", action="append", default=[], help="only process matching title/path/version text; repeatable")
    parser.add_argument("--force", action="store_true", help="rerun even when current source signatures match")
    parser.add_argument("--list", action="store_true", help="list work only")
