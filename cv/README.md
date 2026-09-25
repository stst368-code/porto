# Grouped Markdown CV

The site is now driven by ordered subdirectories.

## Source structure

```text
content/
├── 1-profile/
│   └── 01-profile.md
├── 2-skills/
│   └── 01-skills.md
├── 3-work-experience/
│   ├── 01-global-inventory.md
│   ├── 02-site-management.md
│   └── 03-early-career.md
├── 4-project-examples/
│   ├── 01-mrp.md
│   ├── 02-automation.md
│   ├── 03-iso9001.md
│   └── images/
├── 5-certifications/
│   └── 01-certifications.md
└── 6-independent/
    └── 01-independent.md
```

## Ordering

Folder order controls group order:

```text
1-profile
2-skills
3-work-experience
4-project-examples
...
```

File order inside a folder controls item order:

```text
01-first.md
02-second.md
03-third.md
```

## Build manifest

GitHub Pages cannot enumerate directories at runtime.

Run:

```powershell
py tools/build_content_manifest.py
```

This scans the folders and writes:

```text
content/content-manifest.json
```

You only need to rerun it when you add/remove/rename/reorder folders or Markdown
files. Editing the text inside an existing `.md` file does not require a manifest
change.

Add this script to the GitHub Action before the Pages staging step:

```yaml
- name: Build CV content manifest
  run: python cv/tools/build_content_manifest.py
```

## Images

Images can live inside the same group:

```text
content/
└── 4-project-examples/
    ├── 01-mrp.md
    └── images/
        └── mrp-flow.svg
```

Markdown:

```md
![MRP flow](images/mrp-flow.svg)
```

Relative image paths are resolved from the Markdown file's own subdirectory.

## Layout

Each subdirectory becomes one minimal outer group frame.

All items inside that subdirectory are laid out together inside the frame.

Groups are independent and rendered from top to bottom. There are no manual x/y
positions for content pages anymore.

Desktop retains camera pan/zoom for the whole portfolio surface.

Mobile renders the same hierarchy as normal top-to-bottom grouped content.

The LinkedIn button remains fixed to the browser viewport.
