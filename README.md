# Markdown-driven portfolio

Place this entire folder at `porto/cv/`.

## Edit content
Edit the Markdown files in `content/`.

Images can be embedded directly:

```md
![Diagram](images/my-diagram.png)
```

Put the image at:

```text
content/images/my-diagram.png
```

## Add a new page
Create a `.md` file and add it to `content/manifest.json`.

```json
{
  "file": "11-new-project.md",
  "x": 1200,
  "y": 2600,
  "w": 650,
  "rotate": -0.6,
  "z": 70
}
```

Width is configured; page height is automatic from the Markdown content.

## Desktop
- Drag empty spreadsheet: pan camera
- Wheel: zoom around cursor
- Drag any page/certificate/GBR object: reposition it
- RESET VIEW: camera only
- RESET LAYOUT: objects only
- LinkedIn stays fixed to the viewport

## Mobile
At 900px or below, the 3D canvas is replaced by a conventional single-column layout using the same Markdown content. This is intentional: the content remains readable and touch-friendly rather than forcing desktop pan/zoom interactions onto mobile.

## Certificates
Expected:
- `certs/CSCP.pdf`
- `certs/IBMDA.pdf`
- `certs/GoogleDA.pdf`
- `certs/CMILT.pdf`

`CMILT.pdf` is optional until added.

## Existing examples
The supplied Markdown files are pre-segmented from the current CV and are intended as editable starting points.

## v2
- Certificate frames now drag from anywhere on the certificate image.
- Click without dragging still opens the PDF.
- Markdown pages now use stronger technical-document styling and section-specific accents.
