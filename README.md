# CV portfolio — isometric v6

Certificate display changed to match the intended design.

## Certificate files

```text
cv/certs/CSCP.pdf
cv/certs/GoogleDA.pdf
cv/certs/IBMDA.pdf
cv/certs/CMILT.pdf
```

All four are treated as landscape documents.

The package includes the three supplied examples. `CMILT.pdf` remains optional until added.

## Certificate behaviour

- No certificate panel or grouped wall.
- Each PDF is an independent physical frame on the spreadsheet world.
- The first page of the PDF fills its own frame.
- Frame proportions are derived from the actual PDF page dimensions.
- No portrait forcing or fixed thumbnail ratio.
- Each frame has separate 3D/isometric depth and rotation.
- Each frame can be dragged independently.
- Clicking a frame without dragging opens the original certificate PDF.
- RESET LAYOUT returns all frames and other movable objects to their starting positions.

## Existing controls

- Drag empty spreadsheet: pan camera.
- Mouse wheel: zoom around cursor.
- Spreadsheet surface pans/zooms with the world.
- LIGHT/DARK follows browser preference initially.
- RESET VIEW resets camera.
- RESET LAYOUT resets movable objects.
- GBR links to `good-boy-records/`.
