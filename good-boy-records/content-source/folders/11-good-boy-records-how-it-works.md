---
title: Good Boy Records — How It Works
order: 11
---
# Good Boy Records — How It Works

> Write a song → describe how it should sound → encode the words → generate the music → listen → keep the good ones → analyse and prepare them → publish them to Good Boy Records.

## The three layers

The system makes more sense when three things stay separate.

### Core generation

The minimum story: caption + lyrics → text encoder → conditioning → sampler/music model → audio.

### Generation harness

YAML jobs, Python scheduling, local/cloud workers and conditioning caching make generation easier to automate and distribute. They are conveniences around the core workflow, not prerequisites for understanding it.

### Good Boy Records

Accepted recordings are analysed, prepared, catalogued and published into the player. Each recording stands independently; similar song names are a human-recognisable relationship rather than a parent/child database relationship.

## Multimedia examples

Knowledge articles support embedded media. This is where controlled listening tests can live later.

Example syntax for an audio comparison:

```text
:::audio
src: showcase:path/to/example.mp3
label: 20 sampling steps
caption: Same source, seed and settings; only the step count changes.
:::
```

Images can use normal Markdown image syntax or the richer `:::image` block. The intention is simple: show it, explain it briefly, let people hear or see it, then offer the technical detail.

## Publishing architecture

`showcase/` is the curated content source. The catalogue builder produces `data/catalogue.json`. Media is hosted from Cloudflare R2. GitHub Pages serves the Good Boy Records application.
