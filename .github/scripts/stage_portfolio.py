from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_pages"

RESERVED = {
    ".git",
    ".github",
    "_pages",
    "cv",
    "gbr",
    "good-boy-records",
}

def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    # /cv/
    cv = ROOT / "cv"
    if not (cv / "index.html").exists():
        raise FileNotFoundError("cv/index.html is missing")
    copy_tree(cv, OUT / "cv")

    # /good-boy-records/
    # Preserve the existing GBR build; only change where its staged output is mounted.
    gbr_build = ROOT / "good-boy-records" / "_site"
    if not (gbr_build / "index.html").exists():
        raise FileNotFoundError(
            "good-boy-records/_site/index.html is missing. "
            "Run the existing GBR build/stage steps first."
        )
    copy_tree(gbr_build, OUT / "good-boy-records")

    # Any future root-level folder containing index.html becomes its own route.
    # Example: blabla/index.html -> /blabla/
    for child in ROOT.iterdir():
        if not child.is_dir():
            continue
        if child.name in RESERVED or child.name.startswith("."):
            continue
        if (child / "index.html").exists():
            copy_tree(child, OUT / child.name)
            print(f"Published extra site: /{child.name}/")

    print("Portfolio artifact staged in _pages")

if __name__ == "__main__":
    main()
