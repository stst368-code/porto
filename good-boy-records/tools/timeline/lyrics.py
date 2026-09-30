#!/usr/bin/env python3
"""Build per-variant <song>-<version>.lyrics.json using Demucs + WhisperX.

Existing canonical lyric files are skipped unless --force is used. Cleanup-era
gbr.lyrics.json files are renamed in place; older filename-based lyric files are
reused when possible. JSON source metadata remains path-independent.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from common import (
    LYRICS_FORMAT, add_common_args, atomic_json, discover_variants,
    migrate_old_lyrics, read_json, resolve_showcase, source_matches, source_signature, adopt_signature,
    lyrics_name, lyrics_path, legacy_lyrics_path,
)

TOOL_ROOT = Path(__file__).resolve().parent
WORK_ROOT = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "GBR-Timeline" / "whisperx-work"
DEFAULT_REVIEW_THRESHOLD = 80.0
DIRECTIVE = re.compile(r"^\s*\[[^\]]+\]\s*$")


@dataclass
class LyricToken:
    line_index: int
    word_index: int
    text: str
    norm: str
    start: float | None = None
    end: float | None = None
    matched: bool = False


@dataclass
class LyricLine:
    text: str
    tokens: list[LyricToken]


def normalize_word(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold().replace("’", "'").replace("‘", "'"))
    return "".join(ch for ch in text if ch.isalnum())


def normalize_language(value: Any, default: str = "en") -> str:
    """Return a WhisperX language code from YAML/CLI metadata.

    GBR uses short ISO-style codes such as en, es, ro and pt. Underscores are
    normalised to hyphens so metadata remains predictable. Invalid/blank values
    fail early with a useful per-track error instead of being silently ignored.
    """
    text = str(value or default).strip().lower().replace("_", "-")
    if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})?", text):
        raise ValueError(f"invalid language code {value!r}; use a code such as en, es, ro or pt")
    return text


def effective_language(raw: dict[str, Any], cli_override: str | None) -> str:
    """CLI override wins; otherwise use YAML language, defaulting to English."""
    return normalize_language(cli_override if cli_override is not None else raw.get("language"), "en")


def lyric_source_signature(variant: Any, language: str) -> dict[str, str]:
    signature = source_signature(variant)
    signature["language"] = language
    return signature


def lyric_lines(raw: str) -> list[LyricLine]:
    result: list[LyricLine] = []
    for raw_line in str(raw or "").splitlines():
        text = raw_line.strip()
        if not text or DIRECTIVE.match(text):
            continue
        tokens: list[LyricToken] = []
        for word in re.findall(r"\S+", text):
            norm = normalize_word(word)
            if norm:
                tokens.append(LyricToken(len(result), len(tokens), word, norm))
        if tokens:
            result.append(LyricLine(text=text, tokens=tokens))
    return result


def choose_runtime(requested: str, compute_requested: str) -> tuple[str, str]:
    try:
        import torch
        cuda = bool(torch.cuda.is_available())
    except Exception:
        cuda = False
    if requested == "cuda" and not cuda:
        raise RuntimeError("CUDA requested but PyTorch reports no CUDA device.")
    device = "cuda" if requested == "cuda" or (requested == "auto" and cuda) else "cpu"
    compute = compute_requested if compute_requested != "auto" else ("float16" if device == "cuda" else "int8")
    return device, compute


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("  $ " + " ".join(f'"{x}"' if " " in x else x for x in cmd))
    completed = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    if completed.returncode:
        raise RuntimeError(f"command failed with exit code {completed.returncode}")


def isolate_vocals(audio: Path, work: Path, model: str, device: str, cpu_fallback: bool) -> tuple[Path, str, bool]:
    out = work / "demucs"

    def attempt(which: str) -> Path:
        if out.exists():
            shutil.rmtree(out, ignore_errors=True)
        run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", model, "-d", which, "--out", str(out), str(audio)])
        matches = sorted(out.rglob("vocals.wav"), key=lambda p: len(p.parts))
        if not matches:
            raise RuntimeError("Demucs completed but vocals.wav was not found")
        return matches[0]

    try:
        return attempt(device), device, False
    except Exception:
        if device != "cuda" or not cpu_fallback:
            raise
        print("  ! Demucs CUDA failed; retrying on CPU.")
        return attempt("cpu"), "cpu", True


def whisperx_executable() -> list[str]:
    sibling = Path(sys.executable).with_name("whisperx.exe" if os.name == "nt" else "whisperx")
    if sibling.exists():
        return [str(sibling)]
    command = shutil.which("whisperx")
    if command:
        return [command]
    return [sys.executable, "-m", "whisperx"]


def transcribe_words(
    audio: Path, work: Path, model: str, language: str, batch_size: int,
    device: str, compute_type: str, cpu_fallback: bool,
) -> tuple[list[dict[str, Any]], str, str, bool]:
    out = work / "whisperx"

    def attempt(dev: str, compute: str, batch: int) -> list[dict[str, Any]]:
        if out.exists():
            shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True, exist_ok=True)
        cmd = whisperx_executable() + [
            str(audio), "--model", model, "--language", language, "--device", dev,
            "--compute_type", compute, "--batch_size", str(batch),
            "--output_format", "json", "--output_dir", str(out),
        ]
        run(cmd)
        files = sorted(out.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            raise RuntimeError("WhisperX produced no JSON")
        import json
        data = json.loads(files[0].read_text(encoding="utf-8"))
        words = []
        for segment in data.get("segments", []):
            for item in segment.get("words") or []:
                text = str(item.get("word") or item.get("text") or "").strip()
                start, end = item.get("start"), item.get("end")
                norm = normalize_word(text)
                if norm and isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    words.append({"text": text, "norm": norm, "start": float(start), "end": float(end)})
        if not words:
            raise RuntimeError("WhisperX JSON contained no aligned words")
        return words

    try:
        return attempt(device, compute_type, batch_size), device, compute_type, False
    except Exception:
        if device != "cuda" or not cpu_fallback:
            raise
        print("  ! WhisperX CUDA failed; retrying on CPU/int8.")
        return attempt("cpu", "int8", min(batch_size, 4)), "cpu", "int8", True


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return -2.0
    if a == b:
        return 3.0
    if len(a) > 2 and len(b) > 2 and (a.startswith(b) or b.startswith(a)):
        return 1.8
    ratio = SequenceMatcher(None, a, b).ratio()
    if ratio >= 0.86:
        return 1.5
    if ratio >= 0.72:
        return 0.7
    return -1.7


def sequence_map(lyrics: list[LyricToken], recognised: list[dict[str, Any]]) -> dict[int, int]:
    n, m = len(lyrics), len(recognised)
    gap = -1.0
    score = [[0.0] * (m + 1) for _ in range(n + 1)]
    trace = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0], trace[i][0] = i * gap, 2
    for j in range(1, m + 1):
        score[0][j], trace[0][j] = j * gap, 3
    for i in range(1, n + 1):
        a, row, prev = lyrics[i - 1].norm, score[i], score[i - 1]
        for j in range(1, m + 1):
            diag = prev[j - 1] + similarity(a, recognised[j - 1]["norm"])
            up, left = prev[j] + gap, row[j - 1] + gap
            if diag >= up and diag >= left:
                row[j], trace[i][j] = diag, 1
            elif up >= left:
                row[j], trace[i][j] = up, 2
            else:
                row[j], trace[i][j] = left, 3
    mapping: dict[int, int] = {}
    i, j = n, m
    while i or j:
        direction = trace[i][j]
        if direction == 1 and i and j:
            if similarity(lyrics[i - 1].norm, recognised[j - 1]["norm"]) > 0:
                mapping[i - 1] = j - 1
            i -= 1; j -= 1
        elif direction == 2 and i:
            i -= 1
        elif j:
            j -= 1
        else:
            break
    return mapping


def fill_unmatched(tokens: list[LyricToken], duration: float | None) -> None:
    anchors = [i for i, t in enumerate(tokens) if t.matched and t.start is not None and t.end is not None]
    if not anchors:
        span = max(float(duration or len(tokens) * 0.4), len(tokens) * 0.18)
        step = span / max(1, len(tokens))
        for i, t in enumerate(tokens):
            t.start, t.end = i * step, (i + 1) * step
        return
    bounds = [-1] + anchors + [len(tokens)]
    for left_anchor, right_anchor in zip(bounds, bounds[1:]):
        first, last = left_anchor + 1, right_anchor - 1
        if first > last:
            continue
        count = last - first + 1
        if left_anchor >= 0:
            left_time = float(tokens[left_anchor].end or tokens[left_anchor].start or 0)
        else:
            right_time = float(tokens[right_anchor].start or 0) if right_anchor < len(tokens) else 0
            left_time = max(0.0, right_time - count * 0.34)
        if right_anchor < len(tokens):
            right_time = float(tokens[right_anchor].start or left_time + count * 0.34)
        else:
            natural = left_time + count * 0.34
            right_time = min(float(duration), natural) if duration else natural
        if right_time <= left_time:
            right_time = left_time + count * 0.12
        step = (right_time - left_time) / count
        for offset, token_index in enumerate(range(first, last + 1)):
            tokens[token_index].start = left_time + offset * step
            tokens[token_index].end = left_time + (offset + 1) * step
    cursor = 0.0
    for token in tokens:
        start = max(cursor, float(token.start or cursor))
        end = float(token.end or (start + 0.18))
        if end <= start:
            end = start + 0.08
        token.start, token.end, cursor = round(start, 3), round(end, 3), round(end, 3)


def quality_bucket(coverage: float) -> str:
    if coverage >= 0.92: return "excellent"
    if coverage >= 0.85: return "good"
    if coverage >= 0.80: return "fair"
    if coverage >= 0.65: return "review"
    return "poor"


def build_payload(
    raw: dict[str, Any], recognised: list[dict[str, Any]], signature: dict[str, str],
    review_threshold: float, language: str,
) -> dict[str, Any]:
    lines = lyric_lines(str(raw.get("lyrics") or ""))
    tokens = [t for line in lines for t in line.tokens]
    if not tokens:
        raise RuntimeError("YAML contains no lyric words")
    mapping = sequence_map(tokens, recognised)
    for li, ri in mapping.items():
        tokens[li].start = recognised[ri]["start"]
        tokens[li].end = recognised[ri]["end"]
        tokens[li].matched = True
    duration = raw.get("duration")
    duration_f = float(duration) if isinstance(duration, (int, float)) and duration > 0 else None
    fill_unmatched(tokens, duration_f)

    output_lines = []
    for line_index, line in enumerate(lines, start=1):
        line_id = f"l{line_index:04d}"
        words = []
        for word_index, token in enumerate(line.tokens, start=1):
            words.append({
                "id": f"{line_id}w{word_index:03d}",
                "text": token.text,
                "start": round(float(token.start or 0), 3),
                "end": round(float(token.end or 0), 3),
                "matched": bool(token.matched),
            })
        output_lines.append({
            "id": line_id,
            "text": line.text,
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "words": words,
        })

    matched = sum(1 for t in tokens if t.matched)
    coverage = matched / len(tokens)
    threshold = max(0.0, min(1.0, review_threshold / 100.0))
    review_required = coverage < threshold
    return {
        "format": LYRICS_FORMAT,
        "version": 2,
        "source": signature,
        "title": str(raw.get("title") or ""),
        "song_version": raw.get("version"),
        "language": language,
        "stats": {
            "lyric_words": len(tokens),
            "recognised_words": len(recognised),
            "matched_words": matched,
            "coverage": round(coverage, 4),
        },
        "quality": {
            "rating": quality_bucket(coverage),
            "review_required": review_required,
            "approved": False,
            "usable": not review_required,
        },
        "lines": output_lines,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    parser.add_argument("--no-demucs", action="store_true")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument(
        "--language", default=None,
        help="override YAML language for every selected track (default: per-track YAML language, then en)",
    )
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--demucs-model", default="htdemucs")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--compute-type", choices=["auto", "float16", "float32", "int8"], default="auto")
    parser.add_argument("--no-cpu-fallback", action="store_true")
    parser.add_argument("--review-threshold", type=float, default=DEFAULT_REVIEW_THRESHOLD)
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args()

    showcase = resolve_showcase(args.showcase)
    variants = discover_variants(showcase, args.track)
    device, compute_type = choose_runtime(args.device, args.compute_type)
    print(f"GBR LYRIC ALIGNMENT\nShowcase: {showcase}\nRuntime: {device}/{compute_type}")

    jobs = []
    for v in variants:
        target = lyrics_path(v)
        try:
            language = effective_language(v.raw, args.language)
        except ValueError as exc:
            print(f"skip {v.directory.relative_to(showcase)}: {exc}")
            continue
        signature = lyric_source_signature(v, language)
        old = read_json(target)
        if old and not args.force:
            matched = source_matches(old, signature)
            if matched is True:
                print(f"skip {v.directory.relative_to(showcase)}: lyrics current")
                continue
            if matched is None:
                if language == "en":
                    adopt_signature(target, old, signature)
                    print(f"skip {v.directory.relative_to(showcase)}: adopted source signature for existing English alignment")
                    continue
                print(
                    f"refresh {v.directory.relative_to(showcase)}: existing lyric alignment has no "
                    f"language signature; regenerating as {language}"
                )
        if not old and not args.force and migrate_old_lyrics(v):
            migrated = read_json(target)
            if migrated and language == "en":
                adopt_signature(target, migrated, signature)
                continue
            if migrated:
                print(
                    f"refresh {v.directory.relative_to(showcase)}: migrated lyric alignment predates "
                    f"language metadata; regenerating as {language}"
                )
        jobs.append((v, signature, language))

    if not jobs:
        print("No lyric alignment work required.")
        return 0
    print(f"Jobs: {len(jobs)}")
    if args.list:
        for v, _, language in jobs:
            print(f"  {v.directory.relative_to(showcase)}  [{language}]")
        return 0

    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    failures = 0
    for v, signature, language in jobs:
        print(f"\n{v.directory.relative_to(showcase)}  [language={language}]")
        work = Path(tempfile.mkdtemp(prefix="gbr-", dir=str(WORK_ROOT)))
        try:
            alignment_audio = v.audio
            if not args.no_demucs:
                print(f"  Isolating vocals: {v.audio.name}")
                alignment_audio, _, _ = isolate_vocals(v.audio, work, args.demucs_model, device, not args.no_cpu_fallback)
            print("  WhisperX word timing...")
            recognised, _, _, _ = transcribe_words(
                alignment_audio, work, args.model, language, args.batch_size,
                device, compute_type, not args.no_cpu_fallback,
            )
            print("  Mapping authored YAML lyrics...")
            payload = build_payload(v.raw, recognised, signature, args.review_threshold, language)
            target = lyrics_path(v)
            atomic_json(target, payload)
            legacy = legacy_lyrics_path(v)
            if legacy.is_file() and legacy != target:
                legacy.unlink()
            print(f"  + {lyrics_name(v)}: {payload['stats']['coverage']*100:.1f}% direct coverage")
        except Exception as exc:
            failures += 1
            print(f"  ERROR: {exc}")
        finally:
            if not args.keep_work:
                shutil.rmtree(work, ignore_errors=True)

    print(f"\nComplete: {len(jobs)-failures} succeeded, {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
