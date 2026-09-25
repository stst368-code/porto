# Single-wheel catalogue notes

This patch removes genre-slot navigation from the player.

## New catalogue rule

Every curated track YAML may contain any genre string:

```yaml
title: california-rear-view
version: creepy-pop
genre: creepy theatrical alt-pop
```

`genre` is display/filter metadata only. It does not have to match a predefined
list and does not create a tab/bank.

For backwards compatibility, if `genre:` is missing the importer uses the
existing `version:` text as the genre label.

## Wheel

Every normal track appears once on one wheel.

There is no:
- six-genre matrix
- 24-song cap
- requirement that a genre be shared by multiple tracks
- special handling for one-off as a UI category

Your existing showcase folder layout is retained.

`showcase/easter/` remains the hidden power-toggle service bank and is not mixed
into the public wheel.

## Desktop layout

The wheel is deliberately large and shifted left so its centre sits partly
outside the viewport, restoring the older visual composition.

## Files to replace

Copy these into `good-boy-records/`:

```text
assets/js/studio.js
assets/css/studio.css
tools/import_showcase.py
tools/build_catalogue.py
tools/test_player.py
```

Then rebuild using your normal Good Boy Records build command.

## Existing YAML

Existing YAMLs continue to work because `version:` is the fallback genre.
You can migrate them gradually by adding explicit `genre:` values.
