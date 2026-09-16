#!/usr/bin/env python3
"""Build the Good Boy Records v10 song/variant showcase.

The public catalogue is intentionally compact. Full prompts and generation
notes stay in the original YAML files published under data/yaml/, while the
browser receives only the metadata needed to render and play the showcase.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required: pip install PyYAML")

import build_folders
import build_workflow_media
from fs_utils import remove_path

ROOT = Path(__file__).resolve().parent.parent
TRACK_DIR = ROOT / "content-source" / "tracks" / "showcase"
SONG_DIR = ROOT / "content-source" / "songs" / "showcase"
TEMPLATE = ROOT / "templates" / "index.html"
DATA_DIR = ROOT / "data"
SLEEVE_DIR = ROOT / "assets" / "img" / "sleeves"
AUDIO_DIR = ROOT / "assets" / "audio" / "tracks"  # legacy only
ATR_AUDIO_DIR = ROOT / "assets" / "audio" / "atr"
LEGACY_MUSIC_DIR = ROOT / "music"
VARIANT_SLOTS = ("metal", "pop", "country", "disco", "orchestral", "special")
ONE_OFF_SLOT = "one-off"
VALID_SIDES = ("A", "B", "C")
MAX_SONGS = 10
EASTER_DIR = ROOT / "showcase" / "easter"
EASTER_AUDIO_EXTS = (".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".webm")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")

    def summarise(self, strict: bool) -> int:
        for warning in self.warnings:
            print(f"  warn   {warning}")
        for error in self.errors:
            print(f"  ERROR  {error}")
        if self.errors:
            print(f"Build failed: {len(self.errors)} error(s).")
            return 1
        if strict and self.warnings:
            print(f"Build failed: {len(self.warnings)} warning(s) under --strict.")
            return 1
        return 0




def slugify(value: str) -> str:
    value = str(value or "").strip().lower().replace("_", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "reject"


def humanise(value: str) -> str:
    return re.sub(r"[-_]+", " ", str(value or "")).strip().title()


def load_easter_tracks(report: Report) -> list[dict[str, Any]]:
    """Load up to ten metadata-free secret masters from showcase/easter/.

    Files with the same stem are treated as format variants of one reject
    master, e.g. horrible-take.mp3 + horrible-take.flac is one slot. The
    directory is intentionally absent from the public song matrix.
    """
    if not EASTER_DIR.is_dir():
        return []

    grouped: dict[str, dict[str, Any]] = {}
    for path in sorted(EASTER_DIR.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file() or path.suffix.lower() not in EASTER_AUDIO_EXTS:
            continue
        stem = path.stem
        key = stem.casefold()
        group = grouped.setdefault(key, {"stem": stem, "files": {}})
        fmt = path.suffix.lower().lstrip(".")
        if fmt in group["files"]:
            report.warn("easter", f"duplicate {fmt.upper()} for {stem!r}; using {group['files'][fmt].name!r}")
            continue
        group["files"][fmt] = path

    groups = sorted(grouped.values(), key=lambda item: str(item["stem"]).casefold())
    if len(groups) > MAX_SONGS:
        report.warn("easter", f"contains {len(groups)} reject masters; only the first {MAX_SONGS} are exposed")
        groups = groups[:MAX_SONGS]

    tracks: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        files: dict[str, Path] = group["files"]
        stem = str(group["stem"])
        sources = {fmt: path.relative_to(ROOT).as_posix() for fmt, path in sorted(files.items())}
        preferred_name = next(iter(sorted(files.values(), key=lambda item: item.suffix.casefold()))).name
        tracks.append({
            "id": f"easter-{index:02d}-{slugify(stem)}",
            "easter": True,
            "index": index,
            "title": stem,
            "displayTitle": humanise(stem),
            "filename": preferred_name,
            "audio": {"available": True, "sources": sources},
            "source": {"directory": "showcase/easter"},
        })
    return tracks

def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render(template: str, values: dict[str, str]) -> str:
    output = template
    for key, value in values.items():
        output = output.replace("{{" + key + "}}", value)
    leftovers = re.findall(r"\{\{([A-Z_]+)\}\}", output)
    if leftovers:
        raise SystemExit(f"Template still contains unfilled tokens: {sorted(set(leftovers))}")
    return output


def artwork_url(track: dict[str, Any], width: int = 640, ext: str = "webp") -> str:
    base = (track.get("artwork") or {}).get("base") or "gbr-placeholder"
    return f"assets/img/sleeves/{base}-{width}.{ext}"


def validate_track(track: dict[str, Any], where: str, report: Report) -> None:
    required = ("id", "composition", "title", "variant", "variantSlot", "yamlUrl")
    for key in required:
        if not track.get(key):
            report.error(where, f"missing {key}")

    slot = track.get("variantSlot")
    allowed_slots = (*VARIANT_SLOTS, ONE_OFF_SLOT)
    if slot not in allowed_slots:
        report.error(where, f"variantSlot {slot!r} is not one of {', '.join(allowed_slots)}")

    side = str(track.get("side") or "A").upper()
    if side not in VALID_SIDES:
        report.error(where, f"side {side!r} must be one of {', '.join(VALID_SIDES)}")

    art = track.get("artwork") or {}
    base = art.get("base") or "gbr-placeholder"
    for width in (640, 1280):
        for ext in ("webp", "jpg"):
            if not (SLEEVE_DIR / f"{base}-{width}.{ext}").is_file():
                report.error(where, f"missing artwork derivative assets/img/sleeves/{base}-{width}.{ext}")

    sources = (track.get("audio") or {}).get("sources") or {}
    if not any(sources.values()):
        report.warn(where, "has no MP3 or FLAC yet")
    for fmt in ("mp3", "flac"):
        name = sources.get(fmt)
        if not name:
            continue
        rel = Path(str(name))
        # v10.11+ stores source-relative URLs (normally showcase/...). Keep
        # compatibility with old catalogues whose value was only a basename.
        candidate = ROOT / rel if len(rel.parts) > 1 else AUDIO_DIR / rel
        if not candidate.is_file():
            report.error(where, f"missing audio {str(name)}")

    yaml_url = ROOT / str(track.get("yamlUrl"))
    if not yaml_url.is_file():
        report.error(where, f"published YAML {track.get('yamlUrl')} does not exist")

    timing = (track.get("lyrics") or {}).get("wordTiming")
    if isinstance(timing, dict) and timing.get("src"):
        if not (ROOT / str(timing["src"])).is_file():
            report.error(where, f"word timing {timing['src']} does not exist")



def validate_song_meta(song: dict[str, Any], where: str, report: Report) -> None:
    song_id = str(song.get("id") or "")
    if not song_id:
        report.error(where, "missing id")
    yaml_url = song.get("yamlUrl")
    if yaml_url and not (ROOT / str(yaml_url)).is_file():
        report.error(where, f"published composition YAML {yaml_url} does not exist")
    for item in song.get("atr") or []:
        src = item.get("src") if isinstance(item, dict) else None
        if not src:
            report.error(where, "ATR entry missing src")
            continue
        if not (ROOT / str(src)).is_file():
            report.error(where, f"missing unreleased audio {src}")


def load_song_meta(report: Report) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not SONG_DIR.exists():
        return records
    for path in sorted(SONG_DIR.glob("*.yaml")):
        try:
            song = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            report.error(path.name, f"invalid composition YAML ({exc})")
            continue
        if not isinstance(song, dict):
            report.error(path.name, "composition root must be a mapping")
            continue
        song_id = str(song.get("id") or "")
        if song_id in records:
            report.error(path.name, f"duplicate composition id {song_id!r}")
            continue
        validate_song_meta(song, path.name, report)
        records[song_id] = song
    return records

def load_tracks(report: Report) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_slots: set[tuple[str, str, str]] = set()

    for path in sorted(TRACK_DIR.glob("*.yaml")):
        try:
            track = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            report.error(path.name, f"invalid YAML ({exc})")
            continue
        if not isinstance(track, dict):
            report.error(path.name, "root must be a mapping")
            continue

        # Old generated records did not know about cassette sides. Treat them
        # as Side A so v10 catalogues remain forward-compatible.
        track["side"] = str(track.get("side") or "A").upper()

        track_id = str(track.get("id") or "")
        if track_id in seen_ids:
            report.error(path.name, f"duplicate id {track_id!r}")
            continue
        seen_ids.add(track_id)

        key = (
            str(track.get("composition") or ""),
            str(track.get("variantSlot") or ""),
            str(track.get("side") or "A"),
        )
        if key in seen_slots:
            report.error(path.name, f"song {key[0]!r} has more than one {key[1]!r} Side {key[2]}")
            continue
        seen_slots.add(key)

        validate_track(track, path.name, report)
        tracks.append(track)

    slot_rank = {name: index for index, name in enumerate((*VARIANT_SLOTS, ONE_OFF_SLOT))}
    side_rank = {side: index for index, side in enumerate(VALID_SIDES)}
    tracks.sort(key=lambda t: (
        str(t.get("displayTitle") or t.get("title") or t.get("composition") or "").casefold(),
        slot_rank.get(str(t.get("variantSlot")), 99),
        side_rank.get(str(t.get("side") or "A"), 99),
        str(t.get("variantLabel") or "").casefold(),
    ))
    return tracks

def picture(track: dict[str, Any], lazy: bool = True) -> str:
    alt = esc((track.get("artwork") or {}).get("alt") or track.get("displayTitle") or track.get("title") or "Album artwork")
    loading = ' loading="lazy" decoding="async"' if lazy else ' decoding="async"'
    return (
        '<picture>'
        f'<source type="image/webp" srcset="{artwork_url(track, 640, "webp")} 640w, {artwork_url(track, 1280, "webp")} 1280w">'
        f'<img src="{artwork_url(track, 640, "jpg")}" srcset="{artwork_url(track, 640, "jpg")} 640w, {artwork_url(track, 1280, "jpg")} 1280w" '
        f'width="640" height="640" alt="{alt}"{loading}>'
        '</picture>'
    )


def group_songs(tracks: list[dict[str, Any]], song_meta: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    song_meta = song_meta or {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for track in tracks:
        grouped.setdefault(str(track.get("composition") or track["id"]), []).append(track)

    songs = []
    for composition, releases in grouped.items():
        sides_by_slot: dict[str, dict[str, dict[str, Any]]] = {}
        for track in releases:
            slot = str(track.get("variantSlot"))
            side = str(track.get("side") or "A").upper()
            sides_by_slot.setdefault(slot, {})[side] = track

        # ``variants`` remains the primary physical cassette for wheel
        # rendering: Side A where present, otherwise the first available side.
        # ``sides`` carries A/B/C without creating another magazine position.
        variants_by_slot = {
            slot: next((side_map.get(side) for side in VALID_SIDES if side_map.get(side)), None)
            for slot, side_map in sides_by_slot.items()
        }
        variants_by_slot = {slot: track for slot, track in variants_by_slot.items() if track}
        lead = variants_by_slot.get("disco") or next(
            (variants_by_slot.get(slot) for slot in VARIANT_SLOTS if variants_by_slot.get(slot)),
            releases[0],
        )
        meta = song_meta.get(composition) or {}
        songs.append({
            "id": composition,
            "title": meta.get("displayTitle") or lead.get("displayTitle") or lead.get("title") or composition,
            "lead": lead,
            "variants": variants_by_slot,
            "sides": sides_by_slot,
            "story": str(meta.get("story") or ""),
            "style": meta.get("style") or {},
            "yamlUrl": meta.get("yamlUrl"),
            "atr": meta.get("atr") or [],
        })
    songs.sort(key=lambda song: str(song["title"]).casefold())
    return songs

def render_wheel_library(songs: list[dict[str, Any]]) -> str:
    """Render ten physical song positions.

    The genre is selected independently by the six bank buttons. Runtime JS
    swaps the track id, artwork, ready state and label for the chosen genre,
    so the wheel remains ten songs rather than sixty duplicated positions.
    Optional Side B remains attached to the same song/genre position.
    """
    cells: list[str] = []
    song_slots = list(songs[:MAX_SONGS])
    while len(song_slots) < MAX_SONGS:
        song_slots.append(None)

    for song_index, song in enumerate(song_slots):
        angle = song_index * (360 / MAX_SONGS)
        if song is None:
            title = f"Empty {song_index + 1:02d}"
            song_id = ""
            label = f"SLOT {song_index + 1:02d}"
        else:
            title = str(song["title"])
            song_id = str(song["id"])
            label = title

        aria = f"{title} — select a genre cut"
        cells.append(
            f'<div class="showcase-wheel-slot" data-wheel-index="{song_index}" data-song="{esc(song_id)}" '
            f'data-song-index="{song_index}" data-has-side-b="false" '
            f'style="--base-angle:{angle:.3f}deg;--display-angle:{angle:.3f}deg">'
            f'<button class="showcase-wheel-cassette" type="button" data-track="" '
            f'data-song="{esc(song_id)}" data-slot="" data-ready="false" '
            f'style="--cassette-art:url(\'assets/img/sleeves/gbr-placeholder-640.webp\')" '
            f'aria-label="{esc(aria)}" title="{esc(aria)}" disabled>'
            f'<span class="showcase-wheel-cassette__index">{song_index + 1:02d}</span>'
            f'<span class="showcase-wheel-cassette__label">{esc(label)}</span>'
            f'<span class="showcase-wheel-cassette__state">SELECT GENRE</span>'
            '</button></div>'
        )
    return "".join(cells)

def render_mobile_library(songs: list[dict[str, Any]]) -> str:
    groups: list[str] = []
    for genre in VARIANT_SLOTS:
        cards: list[str] = []
        for index in range(MAX_SONGS):
            song = songs[index] if index < len(songs) else None
            track = song["variants"].get(genre) if song else None
            side_map = song.get("sides", {}).get(genre, {}) if song else {}
            title = str(song["title"]) if song else f"Empty {index + 1:02d}"
            ready = track is not None
            track_id = str(track["id"]) if ready else ""
            song_id = str(song["id"]) if song else ""
            available_sides = [side for side in VALID_SIDES if side_map.get(side)]
            has_extra_sides = len(available_sides) > 1
            disabled = "" if ready else " disabled"
            state = (track.get("variantLabel") if track else None) or ("READY" if ready else "NOT CUT")
            if ready and has_extra_sides:
                state = f"{state} · {'/'.join(available_sides)}"
            cards.append(
                f'<button class="showcase-mobile-cassette" type="button" data-track="{esc(track_id)}" '
                f'data-song="{esc(song_id)}" data-slot="{genre}" data-has-side-b="{"true" if has_extra_sides else "false"}" '
                f'data-ready="{"true" if ready else "false"}"{disabled}>'
                f'<span>{index + 1:02d}</span><strong>{esc(title)}</strong>'
                f'<small>{esc(state)}</small>'
                '</button>'
            )
        groups.append(
            f'<section class="showcase-mobile-genre" data-mobile-genre="{genre}">'
            f'<h2>{esc(genre.title())}</h2><div class="showcase-mobile-genre__rail">{"".join(cards)}</div></section>'
        )
    return "".join(groups)

def build(strict: bool) -> int:
    if LEGACY_MUSIC_DIR.exists():
        remove_path(LEGACY_MUSIC_DIR)

    report = Report()
    build_workflow_media.sync(report)
    if report.errors:
        return report.summarise(strict)

    tracks = load_tracks(report)
    song_meta = load_song_meta(report)
    if report.errors:
        return report.summarise(strict)

    # Keep the six-cut matrix and the public one-off bank independent. A
    # standalone song therefore never consumes one of the ten normal song
    # positions and never needs empty metal/pop/etc. placeholder variants.
    normal_tracks = [track for track in tracks if str(track.get("variantSlot")) != ONE_OFF_SLOT and not track.get("oneOff")]
    one_off_tracks = [track for track in tracks if str(track.get("variantSlot")) == ONE_OFF_SLOT or track.get("oneOff")]
    songs = group_songs(normal_tracks, song_meta)
    one_off_songs = group_songs(one_off_tracks, {})
    easter_tracks = load_easter_tracks(report)
    if len(songs) > MAX_SONGS:
        report.error("showcase", f"contains {len(songs)} matrix songs; rotary magazine supports a maximum of {MAX_SONGS}")
    # ONE-OFF is not limited to one physical magazine. Runtime pages the
    # independent bank in groups of ten while playback/navigation sees all.
    if report.errors:
        return report.summarise(strict)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    catalogue = {
        "format": "gbr-showcase-v10.5",
        "variantSlots": list(VARIANT_SLOTS),
        "songCount": len(songs),
        "oneOffCount": len(one_off_songs),
        "variantCount": len(tracks),
        "songs": [
            {
                "id": song["id"],
                "title": song["title"],
                "story": song.get("story") or "",
                "style": song.get("style") or {},
                "yamlUrl": song.get("yamlUrl"),
                "atr": song.get("atr") or [],
                "variantIds": {slot: song["variants"][slot]["id"] for slot in VARIANT_SLOTS if slot in song["variants"]},
                "sideIds": {
                    slot: {side: side_map[side]["id"] for side in VALID_SIDES if side in side_map}
                    for slot, side_map in song.get("sides", {}).items()
                },
            }
            for song in songs
        ],
        "oneOff": {
            "enabled": bool(one_off_songs),
            "slot": ONE_OFF_SLOT,
            "count": len(one_off_songs),
            "songs": [
                {
                    "id": song["id"],
                    "title": song["title"],
                    "story": song.get("story") or song["lead"].get("story") or "",
                    "style": song.get("style") or song["lead"].get("style") or {},
                    "yamlUrl": song.get("yamlUrl") or song["lead"].get("yamlUrl"),
                    "atr": [],
                    "variantIds": {ONE_OFF_SLOT: song["variants"][ONE_OFF_SLOT]["id"]} if ONE_OFF_SLOT in song["variants"] else {},
                    "sideIds": {
                        ONE_OFF_SLOT: {
                            side: side_map[side]["id"]
                            for side in VALID_SIDES if side in side_map
                        }
                        for slot, side_map in song.get("sides", {}).items()
                        if slot == ONE_OFF_SLOT
                    },
                }
                for song in one_off_songs
            ],
        },
        "tracks": tracks,
        "easter": {
            "enabled": bool(easter_tracks),
            "count": len(easter_tracks),
            "tracks": easter_tracks,
        },
    }
    (DATA_DIR / "catalogue.json").write_text(json.dumps(catalogue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    template = TEMPLATE.read_text(encoding="utf-8")
    output = render(template, {
        "ROOT": "",
        "FOLDERS": build_folders.build(report.warn),
        "WHEEL_LIBRARY": render_wheel_library(songs),
        "MOBILE_LIBRARY": render_mobile_library(songs),
        "CATALOGUE_JSON": json.dumps(catalogue, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"),
        "SONG_COUNT": str(len(songs)),
        "VARIANT_COUNT": str(len(tracks)),
        "YEAR": str(date.today().year),
    })
    (ROOT / "index.html").write_text(output, encoding="utf-8")

    print(f"Built {len(songs)} matrix song(s), {len(one_off_songs)} one-off(s), {len(tracks)} recording(s)")
    print(f"  one-off bank    {len(one_off_songs)} standalone song(s), paged 10 per magazine")
    print(f"  easter bank     {len(easter_tracks)} hidden reject master(s)")
    print(f"  target matrix   {MAX_SONGS} song positions × {len(VARIANT_SLOTS)} selectable genre cuts (+ optional A/B/C sides)")
    print(f"  catalogue.json  {(DATA_DIR / 'catalogue.json').stat().st_size / 1024:.1f} KB")
    print(f"  index.html      {(ROOT / 'index.html').stat().st_size / 1024:.1f} KB")
    return report.summarise(strict)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    return build(args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
