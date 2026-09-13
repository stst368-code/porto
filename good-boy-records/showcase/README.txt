GOOD BOY RECORDS — SHOWCASE SOURCE CONTRACT v11

This directory is the single authoritative local copy of curated song media.
Copy your existing showcase tree here before running START-SITE.bat.

showcase\song-name\
    song-name.yaml
    song-name-metal\
        song-name-metal.yaml
        song-name-metal.png
        song-name-metal.mp3
        song-name-metal.flac
        song-name-metal.lyrics.json       optional
    song-name-pop\
    song-name-country\
    song-name-disco\
    song-name-orchestral\
    song-name-special\
    song-name-atr\                        optional unreleased audio only

The composition YAML supports title, inspiration, inspirationyt and story.
Variant directories hold the generation YAML, artwork, MP3/FLAC and optional
word-timing sidecar. Optional Side B remains a sibling treatment directory
ending -b with side: B.

Normal local builds DO NOT mirror audio into assets/audio or _site. Catalogue
URLs point directly into showcase/. BUILD-PAGES.bat creates a deployment _site
copy only when deployment staging is explicitly requested.

The importer scans nothing outside showcase\ and uses no absolute user path.
