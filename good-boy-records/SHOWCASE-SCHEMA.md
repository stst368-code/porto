# Good Boy Records showcase schema v10.5

The showcase source is always relative to the `good-boy-records` project root. No absolute Windows or GitHub path is stored in catalogue data.

```text
showcase/
└── song-name/
    ├── song-name.yaml
    ├── song-name-metal/
    │   ├── song-name-metal.yaml
    │   ├── song-name-metal.png
    │   ├── song-name-metal.mp3
    │   ├── song-name-metal.flac
    │   └── song-name-metal.lyrics.json
    ├── song-name-pop/
    ├── song-name-country/
    ├── song-name-disco/
    ├── song-name-orchestral/
    ├── song-name-special/
    └── song-name-atr/
        └── arbitrary-audio-files.*
```

For a local checkout such as:

```text
C:\Users\Simon\OneDrive\porto\good-boy-records\
```

the Gimmie composition directory is:

```text
C:\Users\Simon\OneDrive\porto\good-boy-records\showcase\gimmie-gimmie-ball\
```

GitHub Actions uses the same relative structure under `$GITHUB_WORKSPACE/good-boy-records`.

## Composition YAML

The YAML directly under the song directory describes the composition rather than one render.

```yaml
title: gimmie-gimmie-ball
inspiration: Abba - Gimmie Gimmie
inspirationyt: https://www.youtube.com/watch?v=XEjLoHdbVeE
story: Poor lonely BamBam, he sits at night longing for a ball...
```

| Field | Meaning | Required |
| --- | --- | --- |
| `title` | Composition slug | recommended |
| `inspiration` | Shared human-readable reference | optional |
| `inspirationyt` | One shared YouTube/reference URL | optional |
| `story` | Shared background/story copy | optional |

The composition YAML is copied unchanged to `data/yaml/<song>.yaml`.

## Variant YAML

A version directory remains one generated release.

```yaml
title: gimmie-gimmie-ball
version: disco
model: minimax music3
dit: fp16
text_encoder: pruned_int8_convrot
encoder_cfg: 1.7
encoder_seed: 1009198332718831
top_k: 50
sampler: seeds_2
scheduler: ddim_uniform
sampler_cfg: 1.7
sampler_seed: 1103018069344295
sampler_steps: 30
inspiration:
inspirationyt:
story:
caption: |
  ...
lyrics: |
  ...
```

| Field | Meaning | Required |
| --- | --- | --- |
| `title` | Composition slug | yes |
| `version` | `metal`, `pop`, `country`, `disco`, `orchestral`, `special`, or a unique special style | yes |
| `side` | Optional cassette side `A` or `B`; missing means A | optional |
| `model` | Base model / family | recommended |
| `dit` | Diffusion transformer variant | recommended |
| `text_encoder` | Text encoder variant | recommended |
| `encoder_cfg` | Encoder CFG | optional |
| `encoder_seed` | Encoder seed | optional |
| `top_k` | Top-K sampling value | optional |
| `sampler` | Sampler implementation/name | optional |
| `scheduler` | Scheduler implementation/name | optional |
| `sampler_cfg` | Sampler CFG | optional |
| `sampler_seed` | Sampler seed | optional |
| `sampler_steps` | Sampling steps | optional |
| `inspiration` | Version-specific reference text | optional |
| `inspirationyt` | One version-specific YouTube/reference URL | optional |
| `story` | Version-specific story/addendum | optional |
| `caption` | Full generation prompt | optional |
| `lyrics` | Lyrics/fallback transcript | recommended |
| `special_label` | Visible name for `version: special` | optional |

Blank version-level `inspiration`, `inspirationyt` or `story` values do not replace the composition-level values. The browser keeps both layers separate. A selected release can therefore expose at most two reference videos: one from the composition YAML and one from the selected variant YAML.

## Release identity

For:

```yaml
title: gimmie-gimmie-ball
version: disco
```

Side A remains:

```text
gimmie-gimmie-ball-disco
```

with source directory:

```text
showcase/gimmie-gimmie-ball/gimmie-gimmie-ball-disco/
```

Side B uses a sibling directory such as:

```text
showcase/gimmie-gimmie-ball/gimmie-gimmie-ball-disco-b/
```

and `side: B`. It publishes as `gimmie-gimmie-ball-disco-b` while sharing the same physical Disco cassette slot.

## Artwork

The importer tries:

1. explicit `cover:` / `artwork:`;
2. an image matching the release ID;
3. the only image in the version directory.

The composition YAML does not define the active cover. Artwork remains version-specific.

## Audio

Public releases use MP3 and/or FLAC in their variant directory. MP3 is the normal streaming choice; FLAC is the optional lossless choice.

## Lyrics

An approved `gbr-word-lyrics-v1` `.lyrics.json` can sit beside the variant audio. If unavailable, the variant YAML `lyrics:` block remains the fallback transcript.

## Unreleased / ATR

A composition may contain exactly one song-level archive folder:

```text
showcase/<song>/<song>-atr/
```

It has **no YAML requirement**. Put arbitrary audio files directly inside it. Supported staged extensions are:

```text
.mp3 .flac .wav .m4a .ogg .opus .webm
```

The build copies these files to:

```text
assets/audio/atr/<song>/
```

and lists them only under the composition's `atr` catalogue field. ATR audio is never added to:

- the 60 cassette positions;
- `orderedTracks()`;
- genre-lock candidate lists;
- sequential autoplay;
- shuffle.

The visitor must deliberately open the **UNRELEASED** binder tab and choose a cut.

## Album reverse and reference drawer

The square sleeve remains a fixed physical size. The reverse does not scale text down to fit. Instead it contains fixed-size scrollable panels:

- `GENERATION`: model/generation values and reference text;
- `STORY`: shared composition story plus optional version story.

The sleeve edge has binder-style tabs:

- `REFERENCE`: composition and version references. YouTube embeds are created only when this drawer is opened, using `youtube-nocookie.com`.
- `UNRELEASED`: song-level ATR audio and its independent mini-player.

## Rotary magazine

The magazine is unchanged: six genre banks × ten song positions = 60 physical cassettes. Side B and ATR do not add positions.

```text
01-10  Metal
11-20  Pop
21-30  Country
31-40  Disco
41-50  Orchestral
51-60  Special
```

## Hidden reject bank

`showcase/easter/` is reserved for the optional Easter-egg reject archive and is not treated as a normal song directory. Put up to ten audio masters directly in that one folder. No YAML, lyrics or artwork are required. Files sharing the same stem are treated as format variants of one secret track. Supported formats are MP3, FLAC, WAV, M4A, OGG, OPUS and WEBM.
