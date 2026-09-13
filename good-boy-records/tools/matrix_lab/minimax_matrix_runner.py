"""
Good Boy Records - MiniMax Music 3 comparison matrix runner.

Purpose
-------
Generate controlled comparison sets for the GBR website. One selected track is
used as the source and only the variables belonging to the selected experiment
are changed. Prompt, lyrics, duration, seeds and all non-axis settings remain
fixed inside each matrix.

Experiments
-----------
  samp_sched       sampler x scheduler
  cfg_steps        sampler CFG x sampler steps
  dit_textenc      DiT x text encoder
  encoder_cfg_topk text-encoder CFG x Top-K (optional)

The selected track's YAML generation metadata is used as the preferred baseline
when present; CFG defaults fill any missing values.

Outputs are MP3 and use a suffix contract designed for the website. The title
or prefix may change; the suffix identifies the matrix cell, e.g.:

  anything-at-all__dpmpp_2m_sde_gpu_karras.mp3
  anything-at-all__cfg-1p70_steps-33.mp3

Usage
-----
  py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg
  py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg --experiment samp_sched
  py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg --experiment all --yes
  py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg --plan

This is intentionally a finite experiment runner, not a continuous generator.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import queue
import re
import threading
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml


# =============================================================================
# CONSTANTS / ALIASES
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CFG = "minimax_matrix_runner.cfg"
T = TypeVar("T")
PRINT_LOCK = threading.Lock()
MANIFEST_LOCK = threading.Lock()

TEXT_ENCODER_ALIASES = {
    "fp8": "minimax_music3_text_encoder_fp8_e4m3fn.safetensors",
    "fp8_e4m3fn": "minimax_music3_text_encoder_fp8_e4m3fn.safetensors",
    "pruned_int8_convrot": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors",
    "int8_convrot": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors",
    "bf16": "minimax_music3_text_encoder_bf16.safetensors",
}

DIT_ALIASES = {
    "int8": "minimax_music3_dit_int8_convrot.safetensors",
    "int8_convrot": "minimax_music3_dit_int8_convrot.safetensors",
    "fp16": "minimax_music3_dit_fp16.safetensors",
    "fp32": "minimax_music3_dit_fp32.safetensors",
}

EXPERIMENT_ORDER = ("samp_sched", "cfg_steps", "dit_textenc", "encoder_cfg_topk")


# =============================================================================
# DATA MODEL
# =============================================================================


@dataclass(frozen=True)
class WorkerConfig:
    name: str
    url: str


@dataclass(frozen=True)
class SeedSet:
    encoder_seed: int
    sampler_seed: int


@dataclass(frozen=True)
class Baseline:
    text_encoder: str
    dit: str
    vae: str
    encoder_cfg: float
    encoder_top_k: int
    sampler_cfg: float
    sampler_steps: int
    sampler_name: str
    scheduler_name: str
    denoise: float
    seed: SeedSet


@dataclass(frozen=True)
class TrackTarget:
    index: int
    title: str
    version: str
    track_name: str
    yaml_path: Path
    yaml_stem: str
    caption: str
    lyrics: str
    duration: float
    raw: dict[str, Any]
    yaml_format: str


@dataclass(frozen=True)
class ExperimentSpec:
    name: str
    enabled: bool
    folder: str
    axis_x: tuple[str, ...]
    axis_y: tuple[str, ...]


@dataclass(frozen=True)
class RunnerConfig:
    cfg_path: Path
    tracks_root: Path
    output_root: Path
    default_duration: float

    baseline_text_encoder: str
    baseline_dit: str
    baseline_vae: str
    baseline_encoder_cfg: float
    baseline_encoder_top_k: int
    baseline_sampler_cfg: float
    baseline_steps: int
    baseline_sampler: str
    baseline_scheduler: str
    denoise: float

    seed_sets: tuple[SeedSet, ...]
    prefer_yaml_baseline: bool
    prefer_yaml_seeds: bool

    mp3_quality: str
    use_tiled_decode: bool
    vae_tile_size: int
    vae_tile_overlap: int

    poll_seconds: float
    request_timeout_seconds: float
    retry_seconds: float
    max_attempts: int
    skip_existing: bool
    strict_worker_capabilities: bool
    shuffle_jobs: bool

    experiments: dict[str, ExperimentSpec]
    workers: tuple[WorkerConfig, ...]


@dataclass(frozen=True)
class CapabilitySet:
    samplers: frozenset[str]
    schedulers: frozenset[str]
    text_encoders: frozenset[str]
    dits: frozenset[str]
    vaes: frozenset[str]
    save_audio_advanced: bool
    save_audio_mp3: bool


@dataclass(frozen=True)
class MatrixJob:
    experiment: str
    folder: str
    axis_x_name: str
    axis_y_name: str
    axis_x_value: str
    axis_y_value: str
    suffix: str
    target: TrackTarget
    baseline: Baseline
    text_encoder: str
    dit: str
    vae: str
    encoder_cfg: float
    encoder_top_k: int
    sampler_cfg: float
    sampler_steps: int
    sampler_name: str
    scheduler_name: str
    encoder_seed: int
    sampler_seed: int
    output_path: Path


# =============================================================================
# HELPERS
# =============================================================================


def banner(title: str) -> None:
    with PRINT_LOCK:
        print()
        print("=" * 92)
        print(title)
        print("=" * 92)


def status(message: str, worker: str | None = None) -> None:
    prefix = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]"
    if worker:
        prefix += f" [{worker}]"
    with PRINT_LOCK:
        print(f"{prefix} {message}", flush=True)


def safe_component(value: Any) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", str(value))
    value = re.sub(r"\s+", "-", value.strip())
    value = re.sub(r"-{2,}", "-", value)
    return value.strip(" .-") or "value"


def suffix_component(value: Any) -> str:
    # Preserve underscores because ComfyUI sampler/scheduler names use them and
    # the website's suffix matcher deliberately compares against known values.
    value = str(value).strip().replace(".safetensors", "")
    value = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return value.strip(".-") or "value"


def number_token(value: float) -> str:
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return text.replace("-", "m").replace(".", "p")


def normalize_url(value: str) -> str:
    value = str(value).strip().rstrip("/")
    if not value:
        raise ValueError("Blank ComfyUI worker URL")
    if "://" not in value:
        host = value.split("/", 1)[0].lower()
        value = ("http://" if host.startswith(("127.", "localhost")) else "https://") + value
    return value.rstrip("/")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.part")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write(path, text.encode("utf-8"))


def natural_key(value: str) -> list[Any]:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", value)]


def parse_csv(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def parse_csv_cast(raw: str | None, cast: type[T], default: Iterable[T]) -> tuple[T, ...]:
    values = parse_csv(raw)
    if not values:
        return tuple(default)
    try:
        return tuple(cast(v) for v in values)
    except Exception as exc:
        raise ValueError(f"Invalid comma-separated value in {raw!r}") from exc


def cfg_bool(section: configparser.SectionProxy, key: str, default: bool) -> bool:
    if key not in section:
        return default
    try:
        return section.getboolean(key)
    except ValueError as exc:
        raise ValueError(f"Invalid boolean {key}={section.get(key)!r}") from exc


def normalize_model_key(value: str) -> str:
    value = value.strip().lower().replace(".safetensors", "")
    value = re.sub(r"^minimax[_-]?music3[_-]?", "", value)
    return value


def resolve_text_encoder(value: str) -> str:
    value = str(value).strip()
    if value.lower().endswith(".safetensors"):
        return value
    key = re.sub(r"^text[_-]?encoder[_-]?", "", normalize_model_key(value))
    if key in TEXT_ENCODER_ALIASES:
        return TEXT_ENCODER_ALIASES[key]
    return value


def resolve_dit(value: str) -> str:
    value = str(value).strip()
    if value.lower().endswith(".safetensors"):
        return value
    key = re.sub(r"^(dit|unet)[_-]?", "", normalize_model_key(value))
    if key in DIT_ALIASES:
        return DIT_ALIASES[key]
    return value


def is_minimax_model(value: Any) -> bool:
    if value is None:
        return False
    normalized = re.sub(r"[^a-z0-9]+", "", str(value).lower())
    return normalized.startswith("minimax")


def first_present(data: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def state_is_active(data: dict[str, Any]) -> bool:
    if "state" not in data or data.get("state") is None:
        return True
    return str(data.get("state", "")).strip().lower() in {"active", "enabled", "true", "1", "yes", "on"}


def parse_selection(text: str, maximum: int) -> list[int]:
    text = text.strip()
    if not text:
        raise ValueError("No selection entered")
    if text.lower() in {"a", "all", "*"}:
        return list(range(1, maximum + 1))
    selected: set[int] = set()
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            lo, hi = sorted((int(a), int(b)))
            selected.update(range(lo, hi + 1))
        else:
            selected.add(int(chunk))
    bad = [i for i in selected if i < 1 or i > maximum]
    if bad:
        raise ValueError(f"Selection outside 1..{maximum}: {bad}")
    return sorted(selected)


def experiment_axes(name: str) -> tuple[str, str]:
    # Axis orientation is chosen for the UI: columns are the second/independent
    # control and rows are the first. Filename suffix order remains human-readable
    # (sampler_scheduler, cfg_steps, dit_textencoder, ecfg_topk).
    return {
        "samp_sched": ("scheduler", "sampler"),
        "cfg_steps": ("steps", "cfg"),
        "dit_textenc": ("text_encoder", "dit"),
        "encoder_cfg_topk": ("top_k", "encoder_cfg"),
    }[name]


# =============================================================================
# CONFIG
# =============================================================================


def locate_cfg(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if not p.exists():
            raise FileNotFoundError(p)
        return p
    p = BASE_DIR / DEFAULT_CFG
    if p.exists():
        return p
    raise FileNotFoundError(f"No CFG supplied and {p} does not exist")


def parse_seed_sets(raw: str | None) -> tuple[SeedSet, ...]:
    if not raw or not raw.strip():
        return (SeedSet(1234567890, 9876543210),)
    result: list[SeedSet] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "/" not in item:
            raise ValueError("seed_sets entries must be encoder_seed/sampler_seed")
        a, b = (part.strip() for part in item.split("/", 1))
        result.append(SeedSet(int(a), int(b)))
    if not result:
        raise ValueError("seed_sets is empty")
    return tuple(result)


def load_config(path: Path) -> RunnerConfig:
    parser = configparser.ConfigParser(interpolation=None)
    if not parser.read(path, encoding="utf-8"):
        raise RuntimeError(f"Could not read {path}")
    if "global" not in parser:
        raise ValueError("CFG requires [global]")
    g = parser["global"]

    base = path.parent.resolve()

    def config_path(raw: str) -> Path:
        # Allow the same CFG to use the requested Windows-style paths when the
        # runner itself happens to execute on Linux (for example on RunPod).
        value = os.path.expandvars(str(raw).strip())
        if os.name != "nt":
            value = value.replace("\\", "/")
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = base / candidate
        return candidate.resolve()

    tracks_root = config_path(g.get("tracks_root", "trackstemp"))
    output_root = config_path(g.get("output_root", r"port\good-boy-records\content-source\otheraudio"))

    experiments: dict[str, ExperimentSpec] = {}
    for name in EXPERIMENT_ORDER:
        section_name = f"experiment:{name}"
        section = parser[section_name] if section_name in parser else None
        enabled = cfg_bool(section, "enabled", name != "encoder_cfg_topk") if section else (name != "encoder_cfg_topk")
        folder = (section.get("folder", name).strip() if section else name) or name

        if name == "samp_sched":
            x = parse_csv(section.get("schedulers", "*") if section else "*")
            y = parse_csv(section.get("samplers", "*") if section else "*")
        elif name == "cfg_steps":
            x = tuple(str(v) for v in parse_csv_cast(section.get("step_values") if section else None, int, (15, 25, 33, 45, 60)))
            y = tuple(str(v) for v in parse_csv_cast(section.get("cfg_values") if section else None, float, (1.2, 1.5, 1.7, 2.0, 2.5, 4.0)))
        elif name == "dit_textenc":
            x = parse_csv(section.get("text_encoders", "*") if section else "*")
            y = parse_csv(section.get("dits", "*") if section else "*")
        else:
            x = tuple(str(v) for v in parse_csv_cast(section.get("top_k_values") if section else None, int, (10, 25, 50, 75, 100)))
            y = tuple(str(v) for v in parse_csv_cast(section.get("encoder_cfg_values") if section else None, float, (1.2, 1.5, 1.7, 2.0)))

        experiments[name] = ExperimentSpec(name, enabled, folder, x, y)

    workers: list[WorkerConfig] = []
    for section_name in parser.sections():
        if not section_name.lower().startswith("worker:"):
            continue
        section = parser[section_name]
        if not cfg_bool(section, "enabled", True):
            continue
        url = section.get("url", "").strip()
        if not url:
            raise ValueError(f"Enabled [{section_name}] has no url")
        workers.append(WorkerConfig(section_name.split(":", 1)[1].strip() or section_name, normalize_url(url)))
    if not workers:
        raise ValueError("No enabled [worker:...] sections")

    mp3_quality = g.get("mp3_quality", "320k").strip()
    if mp3_quality not in {"V0", "128k", "320k"}:
        raise ValueError("mp3_quality must be V0, 128k or 320k")

    return RunnerConfig(
        cfg_path=path,
        tracks_root=tracks_root,
        output_root=output_root,
        default_duration=g.getfloat("default_duration", fallback=300.0),
        baseline_text_encoder=resolve_text_encoder(g.get("baseline_text_encoder", "bf16")),
        baseline_dit=resolve_dit(g.get("baseline_dit", "fp16")),
        baseline_vae=g.get("baseline_vae", "minimax_music3_dav.safetensors").strip(),
        baseline_encoder_cfg=g.getfloat("baseline_encoder_cfg", fallback=1.7),
        baseline_encoder_top_k=g.getint("baseline_encoder_top_k", fallback=50),
        baseline_sampler_cfg=g.getfloat("baseline_sampler_cfg", fallback=1.7),
        baseline_steps=g.getint("baseline_steps", fallback=33),
        baseline_sampler=g.get("baseline_sampler", "euler").strip(),
        baseline_scheduler=g.get("baseline_scheduler", "simple").strip(),
        denoise=g.getfloat("denoise", fallback=1.0),
        seed_sets=parse_seed_sets(g.get("seed_sets")),
        prefer_yaml_baseline=cfg_bool(g, "prefer_yaml_baseline", True),
        prefer_yaml_seeds=cfg_bool(g, "prefer_yaml_seeds", True),
        mp3_quality=mp3_quality,
        use_tiled_decode=cfg_bool(g, "use_tiled_decode", False),
        vae_tile_size=g.getint("vae_tile_size", fallback=512),
        vae_tile_overlap=g.getint("vae_tile_overlap", fallback=64),
        poll_seconds=g.getfloat("poll_seconds", fallback=2.0),
        request_timeout_seconds=g.getfloat("request_timeout_seconds", fallback=120.0),
        retry_seconds=g.getfloat("retry_seconds", fallback=10.0),
        max_attempts=max(1, g.getint("max_attempts", fallback=3)),
        skip_existing=cfg_bool(g, "skip_existing", True),
        strict_worker_capabilities=cfg_bool(g, "strict_worker_capabilities", True),
        shuffle_jobs=cfg_bool(g, "shuffle_jobs", False),
        experiments=experiments,
        workers=tuple(workers),
    )


# =============================================================================
# TRACK DISCOVERY / BASELINE
# =============================================================================


def discover_targets(cfg: RunnerConfig) -> list[TrackTarget]:
    if not cfg.tracks_root.exists():
        raise FileNotFoundError(f"tracks_root does not exist: {cfg.tracks_root}")
    targets: list[TrackTarget] = []
    files = sorted(
        [p for p in cfg.tracks_root.rglob("*") if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}],
        key=lambda p: natural_key(str(p.relative_to(cfg.tracks_root))),
    )
    for path in files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            status(f"Ignoring invalid YAML {path}: {exc}")
            continue
        if not isinstance(data, dict) or not state_is_active(data):
            continue
        model = data.get("model")
        if model is not None and not is_minimax_model(model):
            continue
        if "caption" not in data or "lyrics" not in data:
            continue
        duration = float(first_present(data, "duration", "max_duration") or cfg.default_duration)
        if duration <= 0:
            continue
        runtime_keys = {
            "dit", "text_encoder", "vae", "encoder_cfg", "text_encoder_cfg", "encoder_top_k",
            "text_encoder_top_k", "top_k", "sampler_cfg", "cfg", "sampler_steps", "steps",
            "encoder_seed", "sampler_seed", "seed", "sampler", "sampler_name", "scheduler", "scheduler_name",
        }
        targets.append(
            TrackTarget(
                index=len(targets) + 1,
                title=str(data.get("title") or path.stem),
                version=str(data.get("version", "")),
                track_name=path.parent.name if path.parent != cfg.tracks_root else str(data.get("title") or path.stem),
                yaml_path=path,
                yaml_stem=path.stem,
                caption=str(data["caption"]),
                lyrics=str(data["lyrics"]),
                duration=duration,
                raw=data,
                yaml_format="new" if any(k in data for k in runtime_keys) else "old",
            )
        )
    return targets


def choose_target(targets: list[TrackTarget], select_arg: str | None) -> TrackTarget:
    if not targets:
        raise RuntimeError("No active MiniMax YAMLs found")
    banner("Source track")
    for target in targets:
        rel = target.yaml_path
        print(f"[{target.index:>3}] {target.track_name:<30} {rel.name:<46} [{target.yaml_format}] {target.duration:g}s")

    if select_arg is not None:
        selected = parse_selection(select_arg, len(targets))
    else:
        while True:
            try:
                selected = parse_selection(input("Select exactly one track: "), len(targets))
                break
            except Exception as exc:
                print(f"Invalid selection: {exc}")
    if len(selected) != 1:
        raise ValueError("Comparison runs require exactly one source track")
    return targets[selected[0] - 1]


def baseline_from_target(cfg: RunnerConfig, target: TrackTarget) -> Baseline:
    d = target.raw

    def pick(default: Any, *keys: str) -> Any:
        if not cfg.prefer_yaml_baseline:
            return default
        value = first_present(d, *keys)
        return default if value is None else value

    text_encoder = resolve_text_encoder(str(pick(cfg.baseline_text_encoder, "text_encoder")))
    dit = resolve_dit(str(pick(cfg.baseline_dit, "dit", "unet")))
    vae = str(pick(cfg.baseline_vae, "vae"))
    encoder_cfg = float(pick(cfg.baseline_encoder_cfg, "text_encoder_cfg", "encoder_cfg"))
    encoder_top_k = int(pick(cfg.baseline_encoder_top_k, "text_encoder_top_k", "encoder_top_k", "top_k"))
    sampler_cfg = float(pick(cfg.baseline_sampler_cfg, "sampler_cfg", "cfg"))
    sampler_steps = int(pick(cfg.baseline_steps, "sampler_steps", "steps"))
    sampler_name = str(pick(cfg.baseline_sampler, "sampler_name", "sampler"))
    scheduler_name = str(pick(cfg.baseline_scheduler, "scheduler_name", "scheduler"))

    seed = cfg.seed_sets[0]
    if cfg.prefer_yaml_seeds:
        e_seed = first_present(d, "encoder_seed")
        s_seed = first_present(d, "sampler_seed", "seed")
        if e_seed is not None and s_seed is not None:
            seed = SeedSet(int(e_seed), int(s_seed))

    return Baseline(
        text_encoder=text_encoder,
        dit=dit,
        vae=vae,
        encoder_cfg=encoder_cfg,
        encoder_top_k=encoder_top_k,
        sampler_cfg=sampler_cfg,
        sampler_steps=sampler_steps,
        sampler_name=sampler_name,
        scheduler_name=scheduler_name,
        denoise=cfg.denoise,
        seed=seed,
    )


# =============================================================================
# COMFYUI CLIENT / CAPABILITIES
# =============================================================================


class ComfyClient:
    def __init__(self, worker: WorkerConfig, cfg: RunnerConfig):
        self.worker = worker
        self.base_url = worker.url
        self.cfg = cfg
        self.client_id = str(uuid.uuid4())
        self.api_prefix: str | None = None

    def _candidate_paths(self, path: str) -> list[str]:
        path = "/" + path.lstrip("/")
        if self.api_prefix is not None:
            return [self.api_prefix + path]
        return [path, "/api" + path]

    def _request(self, method: str, path: str, body: Any | None = None, binary: bool = False) -> Any:
        last_error: Exception | None = None
        for candidate in self._candidate_paths(path):
            url = self.base_url + candidate
            data = None if body is None else json.dumps(body).encode("utf-8")
            headers = {"User-Agent": "GBR-Matrix-Runner/1.0"}
            if data is not None:
                headers["Content-Type"] = "application/json"
            req = Request(url, data=data, headers=headers, method=method)
            try:
                with urlopen(req, timeout=self.cfg.request_timeout_seconds) as response:
                    payload = response.read()
                    if self.api_prefix is None:
                        self.api_prefix = "/api" if candidate.startswith("/api/") else ""
                    if binary:
                        return payload
                    return json.loads(payload.decode("utf-8")) if payload else None
            except HTTPError as exc:
                last_error = exc
                if exc.code == 404 and self.api_prefix is None:
                    continue
                try:
                    detail = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    detail = str(exc)
                raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc
            except (URLError, TimeoutError, ConnectionError) as exc:
                last_error = exc
                continue
        raise RuntimeError(f"Could not reach {self.base_url}: {last_error}")

    def get_json(self, path: str) -> Any:
        return self._request("GET", path)

    def post_json(self, path: str, body: Any) -> Any:
        return self._request("POST", path, body=body)

    def test_connection(self) -> None:
        status(f"Connecting to {self.base_url}", self.worker.name)
        self.get_json("/system_stats")
        status("Connection OK", self.worker.name)

    @staticmethod
    def _choices(info: Any, class_type: str, input_name: str) -> list[str] | None:
        if not isinstance(info, dict):
            return None
        node = info.get(class_type, info)
        if not isinstance(node, dict):
            return None
        block = node.get("input", {})
        for section_name in ("required", "optional"):
            section = block.get(section_name, {}) if isinstance(block, dict) else {}
            if not isinstance(section, dict) or input_name not in section:
                continue
            spec = section[input_name]
            if isinstance(spec, (list, tuple)) and spec:
                values = spec[0]
                if isinstance(values, (list, tuple)):
                    return [str(v) for v in values]
            return None
        return None

    def choices(self, class_type: str, input_name: str) -> list[str]:
        info = self.get_json(f"/object_info/{class_type}")
        values = self._choices(info, class_type, input_name)
        if values is None:
            raise RuntimeError(f"Could not read {class_type}.{input_name} choices")
        return values

    def node_exists(self, class_type: str) -> bool:
        try:
            info = self.get_json(f"/object_info/{class_type}")
        except Exception:
            return False
        return isinstance(info, dict) and bool(info)

    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(
            samplers=frozenset(self.choices("KSampler", "sampler_name")),
            schedulers=frozenset(self.choices("KSampler", "scheduler")),
            text_encoders=frozenset(self.choices("CLIPLoader", "clip_name")),
            dits=frozenset(self.choices("UNETLoader", "unet_name")),
            vaes=frozenset(self.choices("VAELoader", "vae_name")),
            save_audio_advanced=self.node_exists("SaveAudioAdvanced"),
            save_audio_mp3=self.node_exists("SaveAudioMP3"),
        )

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        result = self.post_json("/prompt", {"prompt": workflow, "client_id": self.client_id})
        if not isinstance(result, dict) or not result.get("prompt_id"):
            raise RuntimeError(f"ComfyUI rejected prompt: {result}")
        if result.get("node_errors"):
            raise RuntimeError("ComfyUI validation errors:\n" + json.dumps(result["node_errors"], indent=2))
        return str(result["prompt_id"])

    def wait(self, prompt_id: str, stop_event: threading.Event) -> dict[str, Any]:
        while not stop_event.is_set():
            history = self.get_json(f"/history/{prompt_id}")
            if isinstance(history, dict) and prompt_id in history:
                entry = history[prompt_id]
                s = entry.get("status", {}) if isinstance(entry, dict) else {}
                state = str(s.get("status_str", "")).lower()
                if state == "error":
                    raise RuntimeError("ComfyUI workflow failed:\n" + json.dumps(s, indent=2))
                if bool(s.get("completed")) or state in {"success", "completed"}:
                    return entry
            stop_event.wait(self.cfg.poll_seconds)
        raise InterruptedError("Stop requested")

    def fetch_audio(self, history_entry: dict[str, Any], save_node_id: str = "9") -> bytes:
        outputs = history_entry.get("outputs", {})
        node = outputs.get(save_node_id, {}) if isinstance(outputs, dict) else {}
        items = node.get("audio") or node.get("audios") or []
        if not items:
            raise RuntimeError(f"Save node {save_node_id} produced no audio metadata: {node}")
        item = items[0]
        query = urlencode({
            "filename": item["filename"],
            "subfolder": item.get("subfolder", ""),
            "type": item.get("type", "output"),
        })
        return self._request("GET", f"/view?{query}", binary=True)


# =============================================================================
# CAPABILITY RESOLUTION / MATRIX CREATION
# =============================================================================


def common_capabilities(all_caps: dict[str, CapabilitySet], strict: bool) -> CapabilitySet:
    caps = list(all_caps.values())
    if not caps:
        raise RuntimeError("No worker capabilities")

    def relevant(values: frozenset[str], attr: str) -> frozenset[str]:
        # Workers may legitimately have unrelated models installed. For model
        # loaders, strict comparison only concerns MiniMax Music 3 entries; for
        # samplers/schedulers the entire advertised list is relevant.
        if attr == "text_encoders":
            return frozenset(v for v in values if "minimax" in v.lower() and "music3" in v.lower())
        if attr == "dits":
            return frozenset(v for v in values if "minimax" in v.lower() and "music3" in v.lower() and "dit" in v.lower())
        if attr == "vaes":
            return frozenset(v for v in values if "minimax" in v.lower() and "music3" in v.lower())
        return values

    def intersection(attr: str) -> frozenset[str]:
        sets = [getattr(c, attr) for c in caps]
        common = frozenset.intersection(*sets)
        if strict:
            compared = [relevant(s, attr) for s in sets]
            if any(s != compared[0] for s in compared[1:]):
                details = "; ".join(f"{name}={len(relevant(getattr(c, attr), attr))}" for name, c in all_caps.items())
                raise RuntimeError(f"Worker capability mismatch for {attr}: {details}")
        return common

    advanced = all(c.save_audio_advanced for c in caps)
    mp3 = all(c.save_audio_mp3 for c in caps)
    if not advanced and not mp3:
        raise RuntimeError("Workers do not share SaveAudioAdvanced or SaveAudioMP3")

    return CapabilitySet(
        samplers=intersection("samplers"),
        schedulers=intersection("schedulers"),
        text_encoders=intersection("text_encoders"),
        dits=intersection("dits"),
        vaes=intersection("vaes"),
        save_audio_advanced=advanced,
        save_audio_mp3=mp3,
    )


def expand_axis(values: tuple[str, ...], kind: str, caps: CapabilitySet) -> tuple[str, ...]:
    if values == ("*",) or "*" in values:
        if kind == "sampler":
            resolved = sorted(caps.samplers, key=natural_key)
        elif kind == "scheduler":
            resolved = sorted(caps.schedulers, key=natural_key)
        elif kind == "dit":
            resolved = sorted(
                [v for v in caps.dits if "minimax" in v.lower() and "music3" in v.lower() and "dit" in v.lower()],
                key=natural_key,
            )
        elif kind == "text_encoder":
            resolved = sorted(
                [v for v in caps.text_encoders if "minimax" in v.lower() and "music3" in v.lower()],
                key=natural_key,
            )
        else:
            raise ValueError(f"Wildcard not supported for {kind}")
        if not resolved:
            raise RuntimeError(f"Wildcard for {kind} resolved to nothing")
        return tuple(resolved)

    if kind == "dit":
        return tuple(resolve_dit(v) for v in values)
    if kind == "text_encoder":
        return tuple(resolve_text_encoder(v) for v in values)
    return values


def validate_baseline_and_axes(b: Baseline, cfg: RunnerConfig, specs: list[ExperimentSpec], caps: CapabilitySet) -> list[ExperimentSpec]:
    errors: list[str] = []
    for label, value, available in (
        ("baseline text encoder", b.text_encoder, caps.text_encoders),
        ("baseline DiT", b.dit, caps.dits),
        ("baseline VAE", b.vae, caps.vaes),
        ("baseline sampler", b.sampler_name, caps.samplers),
        ("baseline scheduler", b.scheduler_name, caps.schedulers),
    ):
        if value not in available:
            errors.append(f"{label} {value!r} unavailable")

    resolved_specs: list[ExperimentSpec] = []
    for spec in specs:
        x_kind, y_kind = experiment_axes(spec.name)
        x = expand_axis(spec.axis_x, x_kind, caps)
        y = expand_axis(spec.axis_y, y_kind, caps)
        if x_kind == "dit":
            errors.extend(f"DiT {v!r} unavailable" for v in x if v not in caps.dits)
        if y_kind == "text_encoder":
            errors.extend(f"text encoder {v!r} unavailable" for v in y if v not in caps.text_encoders)
        if x_kind == "sampler":
            errors.extend(f"sampler {v!r} unavailable" for v in x if v not in caps.samplers)
        if y_kind == "scheduler":
            errors.extend(f"scheduler {v!r} unavailable" for v in y if v not in caps.schedulers)
        resolved_specs.append(replace(spec, axis_x=x, axis_y=y))

    if errors:
        raise RuntimeError("Configuration is not available on every worker:\n  " + "\n  ".join(sorted(set(errors))))
    return resolved_specs


def output_for(cfg: RunnerConfig, target: TrackTarget, spec: ExperimentSpec, suffix: str, seed_index: int) -> Path:
    folder = cfg.output_root / spec.folder
    if len(cfg.seed_sets) > 1:
        folder = folder / f"seed-{seed_index:02d}"
    filename = f"{safe_component(target.yaml_stem)}__{suffix}.mp3"
    return folder / filename


def make_job(
    cfg: RunnerConfig,
    target: TrackTarget,
    baseline: Baseline,
    spec: ExperimentSpec,
    x: str,
    y: str,
    seed: SeedSet,
    seed_index: int,
) -> MatrixJob:
    params = dict(
        text_encoder=baseline.text_encoder,
        dit=baseline.dit,
        vae=baseline.vae,
        encoder_cfg=baseline.encoder_cfg,
        encoder_top_k=baseline.encoder_top_k,
        sampler_cfg=baseline.sampler_cfg,
        sampler_steps=baseline.sampler_steps,
        sampler_name=baseline.sampler_name,
        scheduler_name=baseline.scheduler_name,
    )

    if spec.name == "samp_sched":
        params["scheduler_name"] = x
        params["sampler_name"] = y
        suffix = f"{suffix_component(y)}_{suffix_component(x)}"
    elif spec.name == "cfg_steps":
        params["sampler_steps"] = int(float(x))
        params["sampler_cfg"] = float(y)
        suffix = f"cfg-{number_token(float(y))}_steps-{int(float(x))}"
    elif spec.name == "dit_textenc":
        params["text_encoder"] = resolve_text_encoder(x)
        params["dit"] = resolve_dit(y)
        suffix = f"{suffix_component(params['dit'])}_{suffix_component(params['text_encoder'])}"
    elif spec.name == "encoder_cfg_topk":
        params["encoder_top_k"] = int(float(x))
        params["encoder_cfg"] = float(y)
        suffix = f"ecfg-{number_token(float(y))}_topk-{int(float(x))}"
    else:
        raise ValueError(spec.name)

    return MatrixJob(
        experiment=spec.name,
        folder=spec.folder,
        axis_x_name=experiment_axes(spec.name)[0],
        axis_y_name=experiment_axes(spec.name)[1],
        axis_x_value=x,
        axis_y_value=y,
        suffix=suffix,
        target=target,
        baseline=baseline,
        text_encoder=str(params["text_encoder"]),
        dit=str(params["dit"]),
        vae=str(params["vae"]),
        encoder_cfg=float(params["encoder_cfg"]),
        encoder_top_k=int(params["encoder_top_k"]),
        sampler_cfg=float(params["sampler_cfg"]),
        sampler_steps=int(params["sampler_steps"]),
        sampler_name=str(params["sampler_name"]),
        scheduler_name=str(params["scheduler_name"]),
        encoder_seed=seed.encoder_seed,
        sampler_seed=seed.sampler_seed,
        output_path=output_for(cfg, target, spec, suffix, seed_index),
    )


def build_jobs(cfg: RunnerConfig, target: TrackTarget, baseline: Baseline, specs: list[ExperimentSpec]) -> list[MatrixJob]:
    jobs: list[MatrixJob] = []
    for spec in specs:
        for seed_index, seed in enumerate(cfg.seed_sets, start=1):
            # If YAML supplied a known-good seed pair and there is only one configured
            # seed set, keep the YAML pair. Multiple configured seed sets are explicit.
            actual_seed = baseline.seed if len(cfg.seed_sets) == 1 else seed
            for x in spec.axis_x:
                for y in spec.axis_y:
                    jobs.append(make_job(cfg, target, baseline, spec, x, y, actual_seed, seed_index))
    return jobs


# =============================================================================
# WORKFLOW / GENERATION
# =============================================================================


def generation_workflow(job: MatrixJob, cfg: RunnerConfig, temp_prefix: str, use_advanced_save: bool) -> dict[str, Any]:
    decode: dict[str, Any] = {
        "class_type": "VAEDecodeAudioTiled" if cfg.use_tiled_decode else "VAEDecodeAudio",
        "inputs": {"samples": ["7", 0], "vae": ["4", 0]},
    }
    if cfg.use_tiled_decode:
        decode["inputs"].update({"tile_size": cfg.vae_tile_size, "overlap": cfg.vae_tile_overlap})

    save: dict[str, Any]
    if use_advanced_save:
        save = {
            "class_type": "SaveAudioAdvanced",
            "inputs": {
                "audio": ["8", 0],
                "filename_prefix": temp_prefix,
                "format": {"format": "mp3", "quality": cfg.mp3_quality},
            },
        }
    else:
        save = {
            "class_type": "SaveAudioMP3",
            "inputs": {
                "audio": ["8", 0],
                "filename_prefix": temp_prefix,
                "quality": cfg.mp3_quality,
            },
        }

    return {
        "1": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": job.text_encoder, "type": "minimax", "device": "default"},
        },
        "2": {
            "class_type": "MiniMaxMusic3TextEncode",
            "inputs": {
                "clip": ["1", 0],
                "caption": job.target.caption,
                "lyrics": job.target.lyrics,
                "seed": job.encoder_seed,
                "max_duration": job.target.duration,
                "cfg_scale": job.encoder_cfg,
                "top_k": job.encoder_top_k,
            },
        },
        "3": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": job.dit, "weight_dtype": "default"},
        },
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": job.vae}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["2", 0]}},
        "6": {"class_type": "EmptyMiniMaxMusic3LatentAudio", "inputs": {"seconds": ["2", 1], "batch_size": 1}},
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["2", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": job.sampler_seed,
                "steps": job.sampler_steps,
                "cfg": job.sampler_cfg,
                "sampler_name": job.sampler_name,
                "scheduler": job.scheduler_name,
                "denoise": job.baseline.denoise,
            },
        },
        "8": decode,
        "9": save,
    }


def describe_job(job: MatrixJob) -> str:
    return (
        f"{job.experiment} {job.axis_x_value} x {job.axis_y_value} | "
        f"TE={Path(job.text_encoder).stem} DIT={Path(job.dit).stem} | "
        f"ECFG={job.encoder_cfg:g} TOPK={job.encoder_top_k} "
        f"CFG={job.sampler_cfg:g} STEPS={job.sampler_steps} | "
        f"{job.sampler_name}/{job.scheduler_name} | "
        f"ESEED={job.encoder_seed} SSEED={job.sampler_seed}"
    )


def run_job(client: ComfyClient, job: MatrixJob, cfg: RunnerConfig, stop_event: threading.Event, use_advanced_save: bool) -> None:
    session = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    temp_prefix = f"gbr-matrix/{safe_component(client.worker.name)}/{session}/{safe_component(job.suffix)}"
    status("GEN " + describe_job(job), client.worker.name)
    prompt_id = client.queue_prompt(generation_workflow(job, cfg, temp_prefix, use_advanced_save))
    history = client.wait(prompt_id, stop_event)
    audio = client.fetch_audio(history, "9")
    atomic_write(job.output_path, audio)
    status(f"SAVED {job.output_path}", client.worker.name)


# =============================================================================
# MANIFEST
# =============================================================================


def baseline_dict(b: Baseline) -> dict[str, Any]:
    return {
        "text_encoder": b.text_encoder,
        "dit": b.dit,
        "vae": b.vae,
        "encoder_cfg": b.encoder_cfg,
        "encoder_top_k": b.encoder_top_k,
        "sampler_cfg": b.sampler_cfg,
        "sampler_steps": b.sampler_steps,
        "sampler_name": b.sampler_name,
        "scheduler_name": b.scheduler_name,
        "denoise": b.denoise,
        "encoder_seed": b.seed.encoder_seed,
        "sampler_seed": b.seed.sampler_seed,
    }


def write_manifests(cfg: RunnerConfig, target: TrackTarget, baseline: Baseline, jobs: list[MatrixJob]) -> None:
    cfg.output_root.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[MatrixJob]] = {}
    for job in jobs:
        grouped.setdefault(job.experiment, []).append(job)

    root_manifest: dict[str, Any] = {
        "schema": "gbr-comparison-matrix-v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": {
            "title": target.title,
            "version": target.version,
            "yaml": str(target.yaml_path),
            "duration": target.duration,
        },
        "baseline": baseline_dict(baseline),
        "suffix_contract": {
            "separator": "__",
            "extension": ".mp3",
            "note": "The website may ignore everything before '__' and match cells by suffix.",
        },
        "experiments": {},
    }

    for name, exp_jobs in grouped.items():
        first = exp_jobs[0]
        x_values: list[str] = []
        y_values: list[str] = []
        for job in exp_jobs:
            if job.axis_x_value not in x_values:
                x_values.append(job.axis_x_value)
            if job.axis_y_value not in y_values:
                y_values.append(job.axis_y_value)
        folder = cfg.output_root / first.folder
        folder.mkdir(parents=True, exist_ok=True)
        cells = [
            {
                "x": job.axis_x_value,
                "y": job.axis_y_value,
                "suffix": job.suffix,
                "file": job.output_path.name,
                "relative_file": str(job.output_path.relative_to(cfg.output_root)).replace("\\", "/"),
                "parameters": {
                    "text_encoder": job.text_encoder,
                    "dit": job.dit,
                    "vae": job.vae,
                    "encoder_cfg": job.encoder_cfg,
                    "encoder_top_k": job.encoder_top_k,
                    "sampler_cfg": job.sampler_cfg,
                    "sampler_steps": job.sampler_steps,
                    "sampler_name": job.sampler_name,
                    "scheduler_name": job.scheduler_name,
                    "encoder_seed": job.encoder_seed,
                    "sampler_seed": job.sampler_seed,
                },
            }
            for job in exp_jobs
        ]
        exp_manifest = {
            "schema": "gbr-comparison-matrix-v1",
            "experiment": name,
            "folder": first.folder,
            "axis_x": {"name": first.axis_x_name, "values": x_values},
            "axis_y": {"name": first.axis_y_name, "values": y_values},
            "baseline": baseline_dict(baseline),
            "cells": cells,
        }
        atomic_write_text(folder / "_matrix.json", json.dumps(exp_manifest, indent=2, ensure_ascii=False) + "\n")
        root_manifest["experiments"][name] = {
            "folder": first.folder,
            "manifest": f"{first.folder}/_matrix.json",
            "axis_x": exp_manifest["axis_x"],
            "axis_y": exp_manifest["axis_y"],
            "count": len(cells),
        }

    atomic_write_text(cfg.output_root / "_comparison_manifest.json", json.dumps(root_manifest, indent=2, ensure_ascii=False) + "\n")


# =============================================================================
# WORKER POOL
# =============================================================================


def worker_loop(
    worker: WorkerConfig,
    cfg: RunnerConfig,
    cap: CapabilitySet,
    job_queue: queue.Queue[MatrixJob],
    stop_event: threading.Event,
    failures: queue.Queue[tuple[MatrixJob, str]],
) -> None:
    client = ComfyClient(worker, cfg)
    try:
        client.test_connection()
    except Exception as exc:
        status(f"Worker unavailable: {exc}", worker.name)
        return

    # Prefer the simple MP3 node when present because its API input contract is
    # unambiguous; newer installs can fall back to SaveAudioAdvanced.
    use_advanced = not cap.save_audio_mp3 and cap.save_audio_advanced
    while not stop_event.is_set():
        try:
            job = job_queue.get_nowait()
        except queue.Empty:
            return
        try:
            if cfg.skip_existing and job.output_path.exists() and job.output_path.stat().st_size > 0:
                status(f"SKIP existing {job.output_path.name}", worker.name)
                continue
            job.output_path.parent.mkdir(parents=True, exist_ok=True)
            last_exc: Exception | None = None
            for attempt in range(1, cfg.max_attempts + 1):
                try:
                    run_job(client, job, cfg, stop_event, use_advanced)
                    last_exc = None
                    break
                except InterruptedError:
                    return
                except Exception as exc:
                    last_exc = exc
                    status(f"ERROR attempt {attempt}/{cfg.max_attempts}: {exc}", worker.name)
                    if attempt < cfg.max_attempts and stop_event.wait(cfg.retry_seconds):
                        return
            if last_exc is not None:
                failures.put((job, str(last_exc)))
        finally:
            job_queue.task_done()


def run_pool(cfg: RunnerConfig, jobs: list[MatrixJob], all_caps: dict[str, CapabilitySet]) -> list[tuple[MatrixJob, str]]:
    q: queue.Queue[MatrixJob] = queue.Queue()
    for job in jobs:
        q.put(job)
    stop_event = threading.Event()
    failures: queue.Queue[tuple[MatrixJob, str]] = queue.Queue()
    threads: list[threading.Thread] = []

    for worker in cfg.workers:
        thread = threading.Thread(
            target=worker_loop,
            args=(worker, cfg, all_caps[worker.name], q, stop_event, failures),
            daemon=True,
            name=f"gbr-matrix-{worker.name}",
        )
        thread.start()
        threads.append(thread)

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopping workers...")
        stop_event.set()
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=max(1.0, cfg.poll_seconds + 0.5))

    result: list[tuple[MatrixJob, str]] = []
    while not failures.empty():
        result.append(failures.get_nowait())
    return result


# =============================================================================
# CLI
# =============================================================================


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Good Boy Records controlled MiniMax comparison matrix runner")
    p.add_argument("--cfg", help=f"CFG path; default: {DEFAULT_CFG} beside the script")
    p.add_argument("--select", help="Select one source YAML by number")
    p.add_argument("--tracks-root", help="Override the CFG source YAML root")
    p.add_argument("--output-root", help="Override the CFG matrix output root")
    p.add_argument(
        "--experiment",
        action="append",
        choices=[*EXPERIMENT_ORDER, "all"],
        help="Experiment to run. Repeat flag for several, or use all.",
    )
    p.add_argument("--list", action="store_true", help="List source YAMLs and exit")
    p.add_argument("--plan", action="store_true", help="Build and print the matrix plan but do not generate")
    p.add_argument("--yes", action="store_true", help="Skip the final confirmation prompt")
    p.add_argument("--overwrite", action="store_true", help="Regenerate files even when the exact output already exists")
    return p.parse_args()


def selected_specs(cfg: RunnerConfig, args: argparse.Namespace) -> list[ExperimentSpec]:
    requested = args.experiment or []
    if "all" in requested:
        names = [name for name in EXPERIMENT_ORDER if cfg.experiments[name].enabled]
    elif requested:
        names = requested
    else:
        names = [name for name in EXPERIMENT_ORDER if cfg.experiments[name].enabled]
    # Preserve canonical order and de-duplicate repeated flags.
    wanted = set(names)
    return [cfg.experiments[name] for name in EXPERIMENT_ORDER if name in wanted]


def print_baseline(b: Baseline) -> None:
    print("Baseline:")
    print(f"  text encoder : {b.text_encoder}")
    print(f"  DiT          : {b.dit}")
    print(f"  VAE          : {b.vae}")
    print(f"  encoder CFG  : {b.encoder_cfg:g}")
    print(f"  Top-K        : {b.encoder_top_k}")
    print(f"  sampler CFG  : {b.sampler_cfg:g}")
    print(f"  steps        : {b.sampler_steps}")
    print(f"  sampler      : {b.sampler_name}")
    print(f"  scheduler    : {b.scheduler_name}")
    print(f"  denoise      : {b.denoise:g}")
    print(f"  encoder seed : {b.seed.encoder_seed}")
    print(f"  sampler seed : {b.seed.sampler_seed}")


def main() -> None:
    args = parse_args()
    cfg_path = locate_cfg(args.cfg)
    cfg = load_config(cfg_path)

    def cli_path(value: str) -> Path:
        raw = os.path.expandvars(str(value).strip())
        if os.name != "nt":
            raw = raw.replace("\\", "/")
        return Path(raw).expanduser().resolve()

    if args.tracks_root:
        cfg = replace(cfg, tracks_root=cli_path(args.tracks_root))
    if args.output_root:
        cfg = replace(cfg, output_root=cli_path(args.output_root))
    if args.overwrite:
        cfg = replace(cfg, skip_existing=False)

    banner("Good Boy Records - Comparison Matrix Runner")
    print(f"CFG         : {cfg.cfg_path}")
    print(f"Tracks root : {cfg.tracks_root}")
    print(f"Output root : {cfg.output_root}")
    print(f"Workers     : {', '.join(w.name for w in cfg.workers)}")

    targets = discover_targets(cfg)
    if args.list:
        choose_target(targets, args.select or "1")
        return
    target = choose_target(targets, args.select)
    baseline = baseline_from_target(cfg, target)
    print()
    print(f"Selected source: {target.yaml_path}")
    print_baseline(baseline)

    specs = selected_specs(cfg, args)
    if not specs:
        raise RuntimeError("No experiments selected/enabled")

    banner("Checking worker capabilities")
    clients = {worker.name: ComfyClient(worker, cfg) for worker in cfg.workers}
    all_caps: dict[str, CapabilitySet] = {}
    for worker in cfg.workers:
        client = clients[worker.name]
        client.test_connection()
        cap = client.capabilities()
        all_caps[worker.name] = cap
        status(
            f"samplers={len(cap.samplers)} schedulers={len(cap.schedulers)} "
            f"text_encoders={len(cap.text_encoders)} dits={len(cap.dits)}",
            worker.name,
        )

    common = common_capabilities(all_caps, cfg.strict_worker_capabilities)
    specs = validate_baseline_and_axes(baseline, cfg, specs, common)
    jobs = build_jobs(cfg, target, baseline, specs)

    banner("Matrix plan")
    total = 0
    for spec in specs:
        count = len(spec.axis_x) * len(spec.axis_y) * len(cfg.seed_sets)
        total += count
        print(f"{spec.name:<18} {len(spec.axis_x):>3} x {len(spec.axis_y):<3} = {count:>4} generation(s) -> {cfg.output_root / spec.folder}")
        print(f"  X {experiment_axes(spec.name)[0]}: {', '.join(spec.axis_x)}")
        print(f"  Y {experiment_axes(spec.name)[1]}: {', '.join(spec.axis_y)}")
    existing = sum(1 for job in jobs if job.output_path.exists() and job.output_path.stat().st_size > 0)
    print(f"\nPlanned: {total} | already present: {existing} | to generate: {total - existing if cfg.skip_existing else total}")
    print("The seed pair, prompt, lyrics and duration stay fixed within the run.")

    write_manifests(cfg, target, baseline, jobs)
    print(f"Manifest: {cfg.output_root / '_comparison_manifest.json'}")

    if args.plan:
        return
    if not args.yes:
        answer = input("\nGenerate this matrix? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled.")
            return

    if cfg.shuffle_jobs:
        import random
        random.SystemRandom().shuffle(jobs)

    banner("Generating")
    failures = run_pool(cfg, jobs, all_caps)
    write_manifests(cfg, target, baseline, jobs)

    if failures:
        print(f"\nCompleted with {len(failures)} failed cell(s):")
        for job, error in failures:
            print(f"  {job.experiment} {job.suffix}: {error}")
        raise RuntimeError(f"{len(failures)} matrix cell(s) failed")

    print("\nAll requested matrix cells complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by Ctrl+C.")
    except Exception as exc:
        print(f"\nFATAL: {exc}\n")
        raise
