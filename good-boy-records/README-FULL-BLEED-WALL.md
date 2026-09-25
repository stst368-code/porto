# GBR Full-Bleed Wall Fix

This patch makes the sleeve wall fill the entire scene by scaling sleeves for full-height coverage and allowing rows to overfill horizontally so the panel crops cleanly at the edges.

## Changes
- no bottom voids: rows are chosen so the wall always fills the full browser height
- rows overfill horizontally when needed, then crop at the panel edges
- all tracks remain visible at once
- selected sleeve still expands with a local ripple push
- genre ordering from the YAML-derived sort is retained

## Apply
Extract over the dense genre-wall build (or the wall fill fix) and replace the matching files.
