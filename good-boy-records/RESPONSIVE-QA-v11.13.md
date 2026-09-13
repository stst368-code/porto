# Good Boy Records v11.13 — responsive/browser QA

## What changed

v11.13 is a calibration pass, not a visual redesign. It standardises the player typography and explicitly defines geometry for large desktop, ordinary desktop, short laptops, tablet landscape, tablet/phone portrait and narrow phones.

The console no longer uses fixed spectrum/VU/volume heights that can exceed the desktop top row. The first two console modules scale against the available top-row height and the volume/player module receives the remainder. On 720–820px-tall desktops the output controls are compacted without reducing labels below the readable instrument scale.

Mobile explicitly resets the desktop grid rows. The magazine, square release card, console and lyrics therefore participate in normal document flow rather than overlapping each other. Mobile cassette and loaded-master artwork remain square because all curated covers are 1254×1254.

## Rendered viewport matrix

Automated Chromium layout + interaction checks were run at:

- 2560×1440
- 1920×1080
- 1680×1050
- 1536×864
- 1440×900
- 1366×768
- 1280×720
- 1024×768
- 820×1180
- 768×1024
- 430×932
- 390×844
- 360×800

All 13 passed the following checks:

- no horizontal document overflow
- no overlap between magazine / loaded master / console on desktop
- no desktop vertical page scroll at widths >=1181px
- loaded-master card remains square
- module labels >= 8.5px on short desktop and >= 9.6px on normal desktop/mobile
- description/body copy >= 12px on short desktop and >= 13.7px normal desktop / 15px mobile
- hardware labels >= 8.8px short desktop and >= 9.2px normal desktop / 10.2px mobile
- lyric line remains >= 18.8px at the narrowest tested phone
- Details flips the release card
- genre browse buttons change browse state without requiring a track load
- Power toggles the instrument state correctly
- a synthetic ten-tab desktop rail does not clip its labels

## Browser compatibility

The implementation uses standards supported by current Chromium/Edge, Firefox and Safari: CSS Grid/Flexbox, aspect-ratio, Pointer Events, ResizeObserver, Web Audio, CSS custom properties and dynamic viewport units. Critical interactions use guarded APIs where appropriate (`AudioContext || webkitAudioContext`, protected pointer capture, guarded Media Session calls).

The available execution image provided Chromium for live rendering. Firefox/WebKit binaries were not available locally and network installation was unavailable, so Firefox/Safari were compatibility-audited rather than falsely reported as live-rendered. No Chromium-only layout dependency was introduced; container-unit sizing retains the earlier percentage/px wheel sizing as its fallback.

## Typography scale

The player now has one shared hierarchy:

- micro readouts: approximately 8.3–9.6px desktop, 8.3px minimum
- panel/section labels: approximately 9–11px
- hardware/button labels: approximately 9–11px
- metadata values: approximately 10.5–12px
- description/body copy: approximately 12.5–15.7px desktop, 15px mobile
- now-playing title: approximately 16–23px depending on viewport
- lyrics: approximately 19–34px depending on viewport

The point is relative balance rather than every panel independently choosing a microscopic font size, a surprisingly radical concept for this project.
