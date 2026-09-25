from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUTPUT = CONTENT / "content-manifest.json"

def natural_key(value: str):
    return [int(x) if x.isdigit() else x.casefold() for x in re.split(r"(\d+)", value)]

def label_from_folder(name: str) -> str:
    name = re.sub(r"^\d+[-_ ]*", "", name)
    return name.replace("-", " ").replace("_", " ").strip().title()

def main():
    groups = []

    folders = sorted(
        [p for p in CONTENT.iterdir() if p.is_dir() and not p.name.startswith(".")],
        key=lambda p: natural_key(p.name),
    )

    for folder in folders:
        entries = []
        files = sorted(
            [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".md", ".markdown"}],
            key=lambda p: natural_key(p.name),
        )

        for file in files:
            entries.append({
                "file": f"{folder.name}/{file.name}",
                "id": re.sub(r"[^a-z0-9]+", "-", file.stem.casefold()).strip("-"),
            })

        if entries:
            groups.append({
                "folder": folder.name,
                "label": label_from_folder(folder.name),
                "entries": entries,
            })

    payload = {
        "title": "Simon Taylor",
        "subtitle": "Supply Chain · Data · Automation",
        "linkedin": "https://linkedin.com/in/simon-taylor-18202b231/",
        "groups": groups,
        "certificates": [
            {"id":"cscp","file":"certs/CSCP.pdf"},
            {"id":"ibm","file":"certs/IBMDA.pdf"},
            {"id":"google","file":"certs/GoogleDA.pdf"},
            {"id":"cmilt","file":"certs/CMILT.pdf","optional":True}
        ],
        "objects": [
            {
                "type":"polaroid",
                "id":"gbr",
                "title":"GOOD BOY RECORDS",
                "subtitle":"Independent technical experiment",
                "body":"Generative AI · controlled testing · automation · output analysis",
                "href":"../good-boy-records/",
                "systemHref":"../good-boy-records/#how-it-works"
            }
        ],
    }

    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    for group in groups:
        print(f"  {group['folder']}: {len(group['entries'])} item(s)")

if __name__ == "__main__":
    main()
