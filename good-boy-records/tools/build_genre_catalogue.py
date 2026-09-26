#!/usr/bin/env python3
"""Build a genre-enriched catalogue for the GBR Sonic Landscape.

Tolerates either a top-level list of tracks or a catalogue/manifest dict with a
`tracks` list. Existing track fields are preserved. Genre matching uses the
track variant/version first, then falls back to genre-ish strings already
present on the track.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


def normalize(value: Any) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"(\d+)(?:st|nd|rd|th)\b", r"\1", text)
    return re.sub(r"[^a-z0-9]+", "", text)


def load_taxonomy(path: Path):
    rows = []
    by_key = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            item = {
                "order": int(row.get("order") or idx + 1),
                "cluster": (row.get("cluster") or "unknown").strip(),
                "parent_genre": (row.get("parent_genre") or "Unknown").strip(),
                "child_genre": (row.get("child_genre") or "Unknown").strip(),
                "parent_colour": (row.get("parent_colour") or "#808080").strip(),
                "child_colour": (row.get("child_colour") or "#9a9a9a").strip(),
                "normalised_child": normalize(row.get("normalised_child") or row.get("child_genre")),
            }
            rows.append(item)
            for candidate in (item["normalised_child"], normalize(item["child_genre"]), normalize(item["parent_genre"])):
                if candidate and candidate not in by_key:
                    by_key[candidate] = item
    return rows, by_key


def candidate_labels(track: dict):
    vals = []
    for key in ("variant", "version", "genre", "variantLabel", "variantSlot"):
        v = track.get(key)
        if isinstance(v, str) and v.strip():
            vals.append(v)
        elif isinstance(v, dict):
            for sub in ("child_genre", "parent_genre", "name", "label"):
                if v.get(sub): vals.append(v[sub])
    style = track.get("style") or {}
    if isinstance(style, dict):
        for key in ("genre", "name", "inspiration"):
            if style.get(key): vals.append(style[key])
    return vals


def find_taxonomy(track: dict, by_key: dict):
    for label in candidate_labels(track):
        key = normalize(label)
        if key in by_key:
            return by_key[key]
    # Conservative partial match only for long labels, to avoid bad matches.
    for label in candidate_labels(track):
        key = normalize(label)
        if len(key) < 6:
            continue
        matches = [item for tax_key, item in by_key.items() if len(tax_key) >= 6 and (key in tax_key or tax_key in key)]
        if len(matches) == 1:
            return matches[0]
    return None


def audio_url(track: dict):
    audio = track.get("audio")
    if isinstance(audio, str):
        return audio
    if isinstance(audio, dict):
        sources = audio.get("sources")
        if isinstance(sources, dict):
            for key in ("lossless", "flac", "stream", "mp3", "audio"):
                if sources.get(key): return sources[key]
            for v in sources.values():
                if isinstance(v, str) and v: return v
        for key in ("url", "src", "mp3", "flac"):
            if audio.get(key): return audio[key]
    for key in ("audioUrl", "audio_url", "mp3", "flac", "src"):
        if track.get(key): return track[key]
    return None


def artwork_url(track: dict):
    art = track.get("artwork")
    if isinstance(art, str):
        return art
    if isinstance(art, dict):
        for key in ("url", "src", "webp", "png", "jpg"):
            if art.get(key):
                return art[key]
        # Native GBR catalogue shape: artwork.base -> generated sleeve derivatives.
        base = art.get("base")
        if base:
            return f"assets/img/sleeves/{base}-1280.webp"
    for key in ("artworkUrl", "artwork_url", "cover", "image"):
        if track.get(key):
            return track[key]
    # Last-resort fallback follows the normal sleeve naming convention.
    ident = track.get("id") or track.get("filename") or track.get("title")
    if ident:
        stem = re.sub(r"\.[^.]+$", "", str(ident))
        return f"assets/img/sleeves/{stem}-1280.webp"
    return "assets/img/sleeves/gbr-placeholder-1280.webp"


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: build_genre_catalogue.py <manifest-or-catalogue.json> <taxonomy.csv> [output.json]")
    source_path = Path(sys.argv[1])
    taxonomy_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("_site/catalogue.json")

    source = json.loads(source_path.read_text(encoding="utf-8"))
    tracks = source if isinstance(source, list) else list(source.get("tracks") or [])
    if not tracks:
        raise SystemExit(f"No tracks found in {source_path}")

    tax_rows, by_key = load_taxonomy(taxonomy_path)
    max_order = max((x["order"] for x in tax_rows), default=1)
    parent_first = {}
    cluster_first = {}
    for row in tax_rows:
        parent_first.setdefault(row["parent_genre"], row["order"])
        cluster_first.setdefault(row["cluster"], row["order"])
    ordered_parents = {name: i for i, (name, _) in enumerate(sorted(parent_first.items(), key=lambda kv: kv[1]))}
    ordered_clusters = {name: i for i, (name, _) in enumerate(sorted(cluster_first.items(), key=lambda kv: kv[1]))}
    parent_den = max(1, len(ordered_parents) - 1)
    cluster_den = max(1, len(ordered_clusters) - 1)

    compositions = {}
    for t in tracks:
        comp = t.get("composition") or t.get("title") or t.get("song") or t.get("id") or "unknown"
        compositions.setdefault(str(comp), []).append(t)

    enriched = []
    unmatched = []
    for index, track in enumerate(tracks):
        item = dict(track)
        match = find_taxonomy(item, by_key)
        variant = item.get("variant") or item.get("version") or item.get("genre") or "Unknown"
        if match:
            genre = {
                "parent_genre": match["parent_genre"],
                "child_genre": match["child_genre"],
                "cluster": match["cluster"],
                "parent_colour": match["parent_colour"],
                "child_colour": match["child_colour"],
                "position": (match["order"] - 1) / max(1, max_order - 1),
                "taxonomy_order": match["order"],
                "parent_order": ordered_parents.get(match["parent_genre"], 0),
                "parent_position": ordered_parents.get(match["parent_genre"], 0) / parent_den,
                "cluster_order": ordered_clusters.get(match["cluster"], 0),
                "cluster_position": ordered_clusters.get(match["cluster"], 0) / cluster_den,
                "matched": True,
            }
        else:
            unmatched.append(str(variant))
            genre = {
                "parent_genre": "Unclassified",
                "child_genre": str(variant),
                "cluster": "unclassified",
                "parent_colour": "#657080",
                "child_colour": "#8b98a8",
                "position": 0.5,
                "taxonomy_order": max_order + index + 1,
                "parent_order": len(ordered_parents),
                "parent_position": 1.0,
                "cluster_order": len(ordered_clusters),
                "cluster_position": 1.0,
                "matched": False,
            }
        item["genre"] = genre
        item["audio_url"] = audio_url(item)
        item["artwork_url"] = artwork_url(item)
        comp = str(item.get("composition") or item.get("title") or item.get("song") or item.get("id") or "unknown")
        item["variants"] = [
            {"id": x.get("id"), "variant": x.get("variant") or x.get("version")}
            for x in compositions.get(comp, []) if x.get("id") != item.get("id")
        ]
        enriched.append(item)

    enriched.sort(key=lambda t: (
        t["genre"].get("taxonomy_order", 10**9),
        str(t.get("composition") or t.get("title") or "").casefold(),
        str(t.get("variant") or t.get("version") or "").casefold(),
    ))

    out = {
        "format": "gbr-sonic-landscape-v1",
        "generated": True,
        "tracks": enriched,
        "track_count": len(enriched),
        "composition_count": len(compositions),
        "unmatched_genres": sorted(set(unmatched)),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Genre catalogue built: {len(enriched)} tracks -> {output_path}")
    print(f"Matched: {len(enriched)-len(unmatched)} | Unmatched: {len(unmatched)}")


if __name__ == "__main__":
    main()
