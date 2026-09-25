# Good Boy Records — conveyor catalogue layout

This patch replaces the dense desktop catalogue ring with a baggage-carousel style conveyor path.

## Behaviour

- The conveyor enters from the left, wraps around the central loaded artwork, and exits back to the left.
- Only 16 catalogue covers are visible on the conveyor at once.
- Conveyor covers are artwork-only; titles and genre/version labels are removed from the small cards.
- The loaded album artwork, song name and version/genre remain fixed in the centre.
- The conveyor moves continuously at a slow idle speed.
- Pointer hover, mouse-wheel use, dragging, clicking and keyboard interaction temporarily pause the idle movement.
- Clicking a conveyor cover loads that track normally.
- The selected/playing cover remains visually identified while it is on the visible conveyor.
- The redundant catalogue title/count bar is hidden to reclaim vertical space.
- The existing equipment column and lyrics area remain in place.
- Existing tablet/mobile behaviour is retained rather than forcing the desktop conveyor into narrow layouts.

## Install

Extract this ZIP over the root of the cleaned Good Boy Records project, replacing the matching files. Then run `APPLY-CONVEYOR-LAYOUT.bat` to execute the project's regression checks.
