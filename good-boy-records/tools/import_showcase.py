#!/usr/bin/env python3
"""Import Good Boy Records' curated showcase tree.

Source contract (v10.5):

    showcase/
      song-name/
        song-name.yaml                 # composition-level metadata
        song-name-metal/
          song-name-metal.yaml         # variant/generation metadata
          song-name-metal.png
          song-name-metal.mp3
          song-name-metal.flac
          song-name-metal.lyrics.json
        song-name-pop/
        song-name-country/
        song-name-disco/
        song-name-orchestral/
        song-name-special/
        song-name-atr/                 # optional song-level unreleased audio only
          any-interesting-file.mp3
          another-cut.flac

The song YAML carries metadata shared by every version, currently title,
inspiration/inspirationyt and story. Variant YAMLs remain self-contained
records for generation settings, prompts, lyrics, and optional variant-specific
inspiration/story fields.

The ATR directory is deliberately *not* a variant. It has no YAML contract and
its audio never enters the normal autoplay/shuffle catalogue. It is exposed as
an opt-in archive drawer for the composition.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from fs_utils import remove_path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required: pip install PyYAML")

ROOT = Path(__file__).resolve().parent.parent
DROP = ROOT / "showcase"
TRACK_OUT = ROOT / "content-source" / "tracks" / "showcase"
SONG_OUT = ROOT / "content-source" / "songs" / "showcase"
MASTERS = ROOT / "masters"
AUDIO_OUT = ROOT / "assets" / "audio" / "tracks"  # legacy cache, removed during import
ATR_AUDIO_OUT = ROOT / "assets" / "audio" / "atr"  # legacy cache, removed during import
LIVE_LYRICS_OUT = ROOT / "data" / "live-lyrics"
RAW_YAML_OUT = ROOT / "data" / "yaml"
MANIFEST = ROOT / "content-source" / "showcase-manifest.json"
LIVE_LYRICS_FORMAT = "gbr-word-lyrics-v1"
AUDIO_EXTS = {".flac", ".mp3"}
ATR_AUDIO_EXTS = {".flac", ".mp3", ".wav", ".m4a", ".ogg", ".opus", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VARIANT_SLOTS = ("metal", "pop", "country", "disco", "orchestral", "special", "one-off")
ONE_OFF_SLOT = "one-off"
ONE_OFF_DIR = DROP / "one-off"


def slugify(value: str) -> str:
    value = str(value or "").strip().lower().replace("_", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "track"


def humanise(value: str) -> str:
    return re.sub(r"[-_]+", " ", str(value or "")).strip().title()


VALID_SIDES = ("A", "B", "C")

def normalise_side(value: Any) -> str:
    side = str(value or "A").strip().upper()
    aliases = {
        "1": "A", "SIDE A": "A", "SIDE-A": "A",
        "2": "B", "SIDE B": "B", "SIDE-B": "B",
        "3": "C", "SIDE C": "C", "SIDE-C": "C",
    }
    side = aliases.get(side, side)
    return side if side in VALID_SIDES else "A"


def choose_file(directory: Path, expected_stem: str, suffixes: set[str]) -> Path | None:
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in suffixes)
    exact = [p for p in files if slugify(p.stem) == slugify(expected_stem)]
    if len(exact) == 1:
        return exact[0]
    if len(files) == 1:
        return files[0]
    return None


def resolve_artwork(source_yaml: Path, raw: dict[str, Any], release_id: str) -> Path | None:
    explicit = raw.get("cover") or raw.get("artwork")
    if explicit:
        candidate = source_yaml.parent / str(explicit)
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_EXTS:
            return candidate
        for ext in IMAGE_EXTS:
            with_ext = source_yaml.parent / (str(explicit) + ext)
            if with_ext.is_file():
                return with_ext
    # Side-aware one-offs are often named song-b.yaml + song-b.png rather
    # than the generated catalogue id song-one-off-b. Honour the YAML stem
    # before falling back to the older release-id/single-file behaviour.
    for expected in (release_id, source_yaml.stem):
        found = choose_file(source_yaml.parent, expected, IMAGE_EXTS)
        if found:
            return found
    return None


def resolve_audio(source_yaml: Path, release_id: str) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for ext, key in ((".mp3", "mp3"), (".flac", "flac")):
        for stem in (release_id, source_yaml.stem):
            exact = source_yaml.parent / f"{stem}{ext}"
            if exact.is_file():
                found[key] = exact
                break
        if key in found:
            continue
        files = sorted(source_yaml.parent.glob(f"*{ext}"))
        if len(files) == 1:
            found[key] = files[0]
    return found


def resolve_lyrics(source_yaml: Path, release_id: str) -> tuple[Path | None, dict[str, Any] | None]:
    candidates = [
        source_yaml.parent / f"{release_id}.lyrics.json",
        source_yaml.parent / f"{release_id}.live-lyrics.json",
        source_yaml.parent / f"{source_yaml.stem}.lyrics.json",
        source_yaml.parent / f"{source_yaml.stem}.live-lyrics.json",
    ]
    candidates.extend(sorted(source_yaml.parent.glob("*.lyrics.json")))
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"warn {path.relative_to(DROP)}: invalid lyric sidecar ({exc})")
            continue
        if not isinstance(data, dict) or data.get("format") != LIVE_LYRICS_FORMAT or not isinstance(data.get("lines"), list):
            print(f"warn {path.relative_to(DROP)}: not a {LIVE_LYRICS_FORMAT} sidecar")
            continue
        return path, data
    return None, None


def number(raw: dict[str, Any], *keys: str) -> int | float | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return float(value) if "." in value else int(value)
            except ValueError:
                pass
    return None


def clean_generated() -> None:
    # Metadata/artwork derivatives are generated. Curated audio is not: the
    # authoritative copy remains inside showcase/. Older builds mirrored it
    # into assets/audio/{tracks,atr}; remove those caches so one local song
    # does not quietly become three byte-for-byte copies.
    for directory in (TRACK_OUT, SONG_OUT, MASTERS, LIVE_LYRICS_OUT, RAW_YAML_OUT):
        directory.mkdir(parents=True, exist_ok=True)
        for path in directory.iterdir():
            if path.name == ".gitkeep":
                continue
            remove_path(path)

    for legacy in (AUDIO_OUT, ATR_AUDIO_OUT):
        if not legacy.exists():
            continue
        for path in list(legacy.iterdir()):
            if path.name == ".gitkeep":
                continue
            remove_path(path)


def load_mapping(path: Path) -> dict[str, Any] | None:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"skip {path.relative_to(DROP)}: invalid YAML ({exc})")
        return None
    if not isinstance(raw, dict):
        print(f"skip {path.relative_to(DROP)}: YAML root is not a mapping")
        return None
    return raw


def is_song_yaml(path: Path) -> bool:
    """A song metadata YAML sits directly inside showcase/<song>/ and matches the folder name."""
    return path.parent.parent == DROP and slugify(path.stem) == slugify(path.parent.name)


def stage_atr(song_dir: Path, song_id: str) -> list[dict[str, Any]]:
    atr_dir = song_dir / f"{song_id}-atr"
    if not atr_dir.is_dir():
        return []

    sources = sorted(p for p in atr_dir.iterdir() if p.is_file() and p.suffix.lower() in ATR_AUDIO_EXTS)
    if not sources:
        return []

    entries: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        source_url = source.relative_to(ROOT).as_posix()
        entries.append({
            "id": f"{song_id}-atr-{index:02d}",
            "label": humanise(source.stem),
            "filename": source.name,
            "format": source.suffix.lower().lstrip("."),
            "src": source_url,
        })
    return entries


def stage_song(song_dir: Path, source_yaml: Path | None, raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    song_id = slugify(raw.get("title") or song_dir.name)
    if slugify(song_dir.name) != song_id:
        print(f"warn {song_dir.relative_to(DROP)}: folder is {song_dir.name!r}; song title resolves to {song_id!r}")

    raw_yaml_url = None
    if source_yaml:
        raw_yaml_target = RAW_YAML_OUT / f"{song_id}.yaml"
        shutil.copy2(source_yaml, raw_yaml_target)
        raw_yaml_url = f"data/yaml/{raw_yaml_target.name}"

    record = {
        "id": song_id,
        "title": song_id,
        "displayTitle": humanise(song_id),
        "story": str(raw.get("story") or "").strip(),
        "style": {
            "inspiration": str(raw.get("inspiration") or "").strip(),
            "inspirationUrl": str(raw.get("inspirationyt") or raw.get("inspiration_url") or "").strip(),
        },
        "yamlUrl": raw_yaml_url,
        "atr": stage_atr(song_dir, song_id),
        "source": {
            "yaml": str(source_yaml.relative_to(DROP)).replace("\\", "/") if source_yaml else None,
            "directory": str(song_dir.relative_to(DROP)).replace("\\", "/"),
        },
    }
    out = SONG_OUT / f"{song_id}.yaml"
    out.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    return record


def stage_variant(source_yaml: Path, raw: dict[str, Any], song_record: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    title = slugify(raw.get("title") or (song_record or {}).get("id") or source_yaml.parent.parent.name)
    variant_raw = str(raw.get("version") or "").strip()
    if not variant_raw:
        prefix = title + "-"
        folder_slug = slugify(source_yaml.parent.name)
        variant_raw = folder_slug[len(prefix):] if folder_slug.startswith(prefix) else folder_slug
        print(f"warn {source_yaml.relative_to(DROP)}: no version field; inferred {variant_raw!r} from directory")

    variant_slug = slugify(variant_raw)
    # Legacy showcase cuts used a trailing "-b" rather than an explicit
    # side field. Preserve those as cassette Side B.
    inferred_side = "B" if variant_slug.endswith("-b") else "A"

    explicit_side = str(raw.get("side") or "").strip().upper()
    side = explicit_side if explicit_side in {"A", "B"} else inferred_side
    # Side may be explicit in YAML, but the curated archive historically also
    # used ``-a`` / ``-b`` release-directory suffixes. Honour explicit YAML
    # first; otherwise infer a cassette side from the version/directory name.
    # When ``version: metal-b`` is used, treat that as the B side of the metal
    # cut rather than inventing a separate SPECIAL genre called "metal b".
    side_value = raw.get("side")
    side_explicit = side_value is not None and str(side_value).strip() != ""
    side_raw = str(side_value).strip() if side_explicit else ""
    side = normalise_side(side_raw or "A")
    supported_side_tokens = {"A", "B", "C", "1", "2", "3", "SIDE A", "SIDE B", "SIDE C", "SIDE-A", "SIDE-B", "SIDE-C"}
    if side_explicit and side_raw.upper() not in supported_side_tokens:
        print(f"warn {source_yaml.relative_to(DROP)}: unsupported side {side_raw!r}; defaulting to Side A")

    if not side_explicit:
        inferred_side = None
        for suffix, candidate_side in (("-c", "C"), ("-b", "B"), ("-a", "A")):
            if variant_slug.endswith(suffix) and variant_slug[:-2] in VARIANT_SLOTS:
                variant_slug = variant_slug[:-2]
                variant_raw = humanise(variant_slug)
                inferred_side = candidate_side
                break
        if inferred_side is None:
            folder_slug = slugify(source_yaml.parent.name)
            stem_slug = slugify(source_yaml.stem)
            for suffix, candidate_side in (("-c", "C"), ("-b", "B"), ("-a", "A")):
                if folder_slug.endswith(suffix) or stem_slug.endswith(suffix):
                    inferred_side = candidate_side
                    break
        if inferred_side:
            side = inferred_side
            print(f"info {source_yaml.relative_to(DROP)}: inferred Side {side} from curated filename/directory")

    slot = variant_slug if variant_slug in VARIANT_SLOTS else "special"
    base_release_id = slugify(f"{title}-{variant_slug}")
    release_id = base_release_id if side == "A" else slugify(f"{base_release_id}-{side.lower()}")
    expected_dir = base_release_id
    accepted_dirs = {expected_dir, release_id}
    if side == "A":
        accepted_dirs.add(slugify(f"{base_release_id}-a"))
    actual_dir = slugify(source_yaml.parent.name)
    if actual_dir not in accepted_dirs:
        expected_note = expected_dir if side == "A" else slugify(f"{base_release_id}-{side.lower()}")
        print(f"warn {source_yaml.relative_to(DROP)}: directory is {source_yaml.parent.name!r}; expected {expected_note!r}")

    artwork = resolve_artwork(source_yaml, raw, release_id)
    audio = resolve_audio(source_yaml, release_id)
    lyric_path, lyric_data = resolve_lyrics(source_yaml, release_id)

    art_base = release_id
    staged_art = None
    if artwork:
        staged_art = MASTERS / f"{art_base}{artwork.suffix.lower()}"
        shutil.copy2(artwork, staged_art)
    else:
        art_base = "gbr-placeholder"
        print(f"warn {source_yaml.relative_to(DROP)}: no album artwork found; using placeholder")

    # Audio remains in showcase/. The catalogue points at the curated source
    # file directly during local preview. Deployment staging copies only those
    # referenced files into _site/ while preserving the same relative URL.
    staged_audio: dict[str, str] = {}
    for fmt, source in audio.items():
        staged_audio[fmt] = source.relative_to(ROOT).as_posix()

    raw_yaml_target = RAW_YAML_OUT / f"{release_id}.yaml"
    shutil.copy2(source_yaml, raw_yaml_target)

    word_timing = None
    staged_lyrics = None
    if lyric_path and lyric_data:
        staged_lyrics = LIVE_LYRICS_OUT / f"{release_id}.json"
        shutil.copy2(lyric_path, staged_lyrics)
        stats = lyric_data.get("stats") if isinstance(lyric_data.get("stats"), dict) else {}
        quality = lyric_data.get("quality") if isinstance(lyric_data.get("quality"), dict) else {}
        coverage = stats.get("coverage")
        inferred_review = isinstance(coverage, (int, float)) and float(coverage) < 0.80
        review_required = bool(quality.get("review_required", inferred_review))
        approved = bool(quality.get("approved", False))
        usable = bool(quality.get("usable_for_live_lyrics", approved or not review_required))
        word_timing = {
            "src": f"data/live-lyrics/{release_id}.json",
            "format": LIVE_LYRICS_FORMAT,
            "coverage": coverage,
            "rating": quality.get("rating"),
            "reviewRequired": review_required,
            "approved": approved,
            "usable": usable,
        }

    special_label = None
    if slot == "special":
        special_label = str(raw.get("special_label") or raw.get("special") or (variant_raw if variant_slug != "special" else "Special")).strip()

    record = {
        "id": release_id,
        "composition": title,
        "title": title,
        "displayTitle": humanise(title),
        "slug": release_id,
        "variant": variant_slug,
        "variantSlot": slot,
        "variantLabel": special_label or humanise(variant_raw),
        "side": side,
        "model": {
            "name": str(raw.get("model") or "").strip(),
            "dit": str(raw.get("dit") or "").strip(),
            "textEncoder": str(raw.get("text_encoder") or raw.get("textenc") or raw.get("text_encoder_model") or "").strip(),
        },
        "generation": {
            "encoderCfg": number(raw, "encoder_cfg"),
            "encoderSeed": number(raw, "encoder_seed"),
            "topK": number(raw, "top_k", "topk"),
            "sampler": str(raw.get("sampler") or "").strip(),
            "scheduler": str(raw.get("scheduler") or "").strip(),
            "samplerCfg": number(raw, "sampler_cfg", "cfg"),
            "samplerSeed": number(raw, "sampler_seed", "seed"),
            "steps": number(raw, "sampler_steps", "steps"),
        },
        "style": {
            "inspiration": str(raw.get("inspiration") or "").strip(),
            "inspirationUrl": str(raw.get("inspirationyt") or raw.get("inspiration_url") or "").strip(),
        },
        "story": str(raw.get("story") or "").strip(),
        "audio": {
            "available": bool(staged_audio),
            "sources": {"mp3": staged_audio.get("mp3"), "flac": staged_audio.get("flac")},
        },
        "artwork": {
            "base": art_base,
            "alt": f"Album artwork for {humanise(title)} — {special_label or humanise(variant_raw)} — Side {side}",
            "placeholder": artwork is None,
        },
        "lyrics": {
            "raw": str(raw.get("lyrics") or "").rstrip(),
            "wordTiming": word_timing,
        },
        "yamlUrl": f"data/yaml/{release_id}.yaml",
        "source": {
            "yaml": str(source_yaml.relative_to(DROP)).replace("\\", "/"),
            "directory": str(source_yaml.parent.relative_to(DROP)).replace("\\", "/"),
        },
    }

    out = TRACK_OUT / f"{release_id}.yaml"
    out.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")

    manifest_entry = {
        "id": release_id,
        "composition": title,
        "variant": variant_slug,
        "slot": slot,
        "side": side,
        "source": record["source"]["directory"],
        "songYaml": (song_record or {}).get("yamlUrl"),
        "yaml": raw_yaml_target.name,
        "artwork": staged_art.name if staged_art else None,
        "audio": staged_audio,
        "lyrics": staged_lyrics.name if staged_lyrics else None,
        "atrCount": len((song_record or {}).get("atr") or []),
    }
    return record, manifest_entry


def stage_one_off(source_yaml: Path, raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stage one public standalone release, optionally as Side A/B/C.

    Multiple YAMLs with the same title are grouped into one ONE-OFF magazine
    position. Side can be declared with ``side: A|B|C`` or inferred from a
    ``-a``/``-b``/``-c`` YAML filename or directory suffix.
    """
    title = slugify(raw.get("title") or source_yaml.parent.name)
    label = str(raw.get("one_off_label") or raw.get("version") or "One-Off").strip() or "One-Off"

    side_value = raw.get("side")
    side_explicit = side_value is not None and str(side_value).strip() != ""
    side_raw = str(side_value).strip() if side_explicit else ""
    side = normalise_side(side_raw or "A")
    supported_side_tokens = {"A", "B", "C", "1", "2", "3", "SIDE A", "SIDE B", "SIDE C", "SIDE-A", "SIDE-B", "SIDE-C"}
    if side_explicit and side_raw.upper() not in supported_side_tokens:
        print(f"warn {source_yaml.relative_to(DROP)}: unsupported side {side_raw!r}; defaulting to Side A")

    if not side_explicit:
        folder_slug = slugify(source_yaml.parent.name)
        stem_slug = slugify(source_yaml.stem)
        for suffix, candidate_side in (("-c", "C"), ("-b", "B"), ("-a", "A")):
            if folder_slug.endswith(suffix) or stem_slug.endswith(suffix):
                side = candidate_side
                print(f"info {source_yaml.relative_to(DROP)}: inferred Side {side} from one-off filename/directory")
                break

    composition_id = slugify(f"{title}-one-off")
    release_id = composition_id if side == "A" else slugify(f"{composition_id}-{side.lower()}")

    artwork = resolve_artwork(source_yaml, raw, release_id)
    audio = resolve_audio(source_yaml, release_id)
    lyric_path, lyric_data = resolve_lyrics(source_yaml, release_id)

    art_base = release_id
    staged_art = None
    if artwork:
        staged_art = MASTERS / f"{art_base}{artwork.suffix.lower()}"
        shutil.copy2(artwork, staged_art)
    else:
        art_base = "gbr-placeholder"
        print(f"warn {source_yaml.relative_to(DROP)}: no album artwork found; using placeholder")

    staged_audio = {fmt: source.relative_to(ROOT).as_posix() for fmt, source in audio.items()}

    raw_yaml_target = RAW_YAML_OUT / f"{release_id}.yaml"
    shutil.copy2(source_yaml, raw_yaml_target)

    word_timing = None
    staged_lyrics = None
    if lyric_path and lyric_data:
        staged_lyrics = LIVE_LYRICS_OUT / f"{release_id}.json"
        shutil.copy2(lyric_path, staged_lyrics)
        stats = lyric_data.get("stats") if isinstance(lyric_data.get("stats"), dict) else {}
        quality = lyric_data.get("quality") if isinstance(lyric_data.get("quality"), dict) else {}
        coverage = stats.get("coverage")
        inferred_review = isinstance(coverage, (int, float)) and float(coverage) < 0.80
        review_required = bool(quality.get("review_required", inferred_review))
        approved = bool(quality.get("approved", False))
        usable = bool(quality.get("usable_for_live_lyrics", approved or not review_required))
        word_timing = {
            "src": f"data/live-lyrics/{release_id}.json",
            "format": LIVE_LYRICS_FORMAT,
            "coverage": coverage,
            "rating": quality.get("rating"),
            "reviewRequired": review_required,
            "approved": approved,
            "usable": usable,
        }

    record = {
        "id": release_id,
        "oneOff": True,
        "composition": composition_id,
        "title": title,
        "displayTitle": humanise(title),
        "slug": release_id,
        "variant": ONE_OFF_SLOT,
        "variantSlot": ONE_OFF_SLOT,
        "variantLabel": label,
        "side": side,
        "model": {
            "name": str(raw.get("model") or "").strip(),
            "dit": str(raw.get("dit") or "").strip(),
            "textEncoder": str(raw.get("text_encoder") or raw.get("textenc") or raw.get("text_encoder_model") or "").strip(),
        },
        "generation": {
            "encoderCfg": number(raw, "encoder_cfg"),
            "encoderSeed": number(raw, "encoder_seed"),
            "topK": number(raw, "top_k", "topk"),
            "sampler": str(raw.get("sampler") or "").strip(),
            "scheduler": str(raw.get("scheduler") or "").strip(),
            "samplerCfg": number(raw, "sampler_cfg", "cfg"),
            "samplerSeed": number(raw, "sampler_seed", "seed"),
            "steps": number(raw, "sampler_steps", "steps"),
        },
        "style": {
            "inspiration": str(raw.get("inspiration") or "").strip(),
            "inspirationUrl": str(raw.get("inspirationyt") or raw.get("inspiration_url") or "").strip(),
        },
        "story": str(raw.get("story") or "").strip(),
        "audio": {
            "available": bool(staged_audio),
            "sources": {"mp3": staged_audio.get("mp3"), "flac": staged_audio.get("flac")},
        },
        "artwork": {
            "base": art_base,
            "alt": f"Album artwork for {humanise(title)} — {label} — Side {side}",
            "placeholder": artwork is None,
        },
        "lyrics": {
            "raw": str(raw.get("lyrics") or "").rstrip(),
            "wordTiming": word_timing,
        },
        "yamlUrl": f"data/yaml/{release_id}.yaml",
        "source": {
            "yaml": str(source_yaml.relative_to(DROP)).replace("\\", "/"),
            "directory": str(source_yaml.parent.relative_to(DROP)).replace("\\", "/"),
        },
    }

    out = TRACK_OUT / f"{release_id}.yaml"
    out.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")

    manifest_entry = {
        "id": release_id,
        "composition": composition_id,
        "variant": ONE_OFF_SLOT,
        "slot": ONE_OFF_SLOT,
        "side": side,
        "oneOff": True,
        "source": record["source"]["directory"],
        "songYaml": None,
        "yaml": raw_yaml_target.name,
        "artwork": staged_art.name if staged_art else None,
        "audio": staged_audio,
        "lyrics": staged_lyrics.name if staged_lyrics else None,
        "atrCount": 0,
    }
    return record, manifest_entry


def main() -> int:
    DROP.mkdir(parents=True, exist_ok=True)
    clean_generated()

    all_yamls = sorted([*DROP.rglob("*.yaml"), *DROP.rglob("*.yml")])
    # Reserved banks are not part of the normal six-cut composition matrix.
    # Easter is hidden and metadata-free; one-off is public and intentionally
    # contains standalone releases that will never need six genre variants.
    def reserved_bank(path: Path) -> str | None:
        try:
            first = path.relative_to(DROP).parts[0].lower()
        except (ValueError, IndexError):
            return None
        return first if first in {"easter", "one-off", "oneoff"} else None

    normal_yamls = [path for path in all_yamls if reserved_bank(path) is None]
    one_off_yamls = [path for path in all_yamls if reserved_bank(path) in {"one-off", "oneoff"}]
    song_yamls = {path.parent: path for path in normal_yamls if is_song_yaml(path)}
    variant_yamls = [path for path in normal_yamls if not is_song_yaml(path)]

    # Build song records for every actual song directory, even if the common
    # YAML is temporarily absent. That preserves backward compatibility while
    # making the new composition metadata contract available immediately.
    song_dirs = sorted(
        p for p in DROP.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name.lower() not in {"easter", "one-off", "oneoff"}
    )
    song_records: dict[str, dict[str, Any]] = {}
    for song_dir in song_dirs:
        source_yaml = song_yamls.get(song_dir)
        raw = load_mapping(source_yaml) if source_yaml else None
        record = stage_song(song_dir, source_yaml, raw)
        song_records[record["id"]] = record
        if source_yaml is None:
            print(f"warn {song_dir.relative_to(DROP)}: no composition YAML; expected {song_dir.name}.yaml")
        atr_count = len(record.get("atr") or [])
        print(f"song {record['id']}: common metadata{' + ' + str(atr_count) + ' ATR' if atr_count else ''}")

    if not variant_yamls and not one_off_yamls:
        print(f"No release YAML files under {DROP}")
        print("Expected showcase/<song>/<song>-<variant>/<song>-<variant>.yaml or showcase/one-off/<song>/<song>.yaml")
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text("[]\n", encoding="utf-8")
        return 0

    manifest: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source_yaml in variant_yamls:
        raw = load_mapping(source_yaml)
        if raw is None:
            continue
        if not raw.get("title"):
            print(f"skip {source_yaml.relative_to(DROP)}: no title")
            continue

        title = slugify(raw.get("title"))
        song_record = song_records.get(title)
        if not song_record:
            # Variant exists under a malformed/mismatched song folder. Build a
            # compatibility record rather than losing the release.
            song_dir = source_yaml.parent.parent
            song_record = stage_song(song_dir, song_yamls.get(song_dir), load_mapping(song_yamls[song_dir]) if song_dir in song_yamls else None)
            song_records[song_record["id"]] = song_record

        record, entry = stage_variant(source_yaml, raw, song_record)
        if record["id"] in seen:
            raise SystemExit(f"Duplicate release id {record['id']!r}; check title/version/side combinations")
        seen.add(record["id"])
        manifest.append(entry)

        sources = record["audio"]["sources"]
        available = [key.upper() for key, value in sources.items() if value]
        timing = record["lyrics"].get("wordTiming") or {}
        timing_note = ""
        if timing:
            cov = timing.get("coverage")
            timing_note = f" | lyrics {float(cov)*100:.1f}%" if isinstance(cov, (int, float)) else " | lyrics staged"
        print(f"{record['id']} [Side {record['side']}]: {' + '.join(available) if available else 'NO AUDIO'}{timing_note}")

    for source_yaml in one_off_yamls:
        raw = load_mapping(source_yaml)
        if raw is None:
            continue
        if not raw.get("title"):
            raw["title"] = source_yaml.parent.name
            print(f"warn {source_yaml.relative_to(DROP)}: no title; inferred {raw['title']!r} from directory")
        record, entry = stage_one_off(source_yaml, raw)
        if record["id"] in seen:
            raise SystemExit(f"Duplicate release id {record['id']!r}; check one-off title/folder names")
        seen.add(record["id"])
        manifest.append(entry)
        sources = record["audio"]["sources"]
        available = [key.upper() for key, value in sources.items() if value]
        timing = record["lyrics"].get("wordTiming") or {}
        timing_note = ""
        if timing:
            cov = timing.get("coverage")
            timing_note = f" | lyrics {float(cov)*100:.1f}%" if isinstance(cov, (int, float)) else " | lyrics staged"
        print(f"{record['id']} [ONE-OFF Side {record['side']}]: {' + '.join(available) if available else 'NO AUDIO'}{timing_note}")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    songs = {item["composition"] for item in manifest}
    one_off_count = sum(1 for item in manifest if item.get("oneOff"))
    print(f"Imported {len(manifest)} recording(s) across {len(songs)} song(s), including {one_off_count} one-off(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
