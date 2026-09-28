# Good Boy Records — external showcase storage

The local `showcase/` directory remains the authoritative curated source. In production its contents are served from Cloudflare R2; GitHub Pages serves only the player, documents, taxonomy and compact catalogue.

## R2 layout

Upload the local directory as the `showcase/` prefix in the bucket:

```text
bucket root/
└── showcase/
    ├── dogtushya/
    ├── moses-supposes/
    ├── one-off/
    └── easter/
```

This includes all files already curated there: MP3, FLAC, PNG/JPG/WEBP covers, YAML and lyric timing JSON.

## Configure the public URL

Edit `showcase-host.js` and set the URL that corresponds to the remote `showcase/` directory itself:

```js
window.GBR_SHOWCASE_ROOT = "https://media.example.com/showcase/";
```

For an R2 development URL where the bucket contains a `showcase/` prefix, use:

```js
window.GBR_SHOWCASE_ROOT = "https://pub-xxxxxxxx.r2.dev/showcase/";
```

Do not put a track/song path in this setting. The runtime appends the relative path from the catalogue.

## Upload

Configure an rclone remote named `r2`, set the bucket name near the top of `UPLOAD-SHOWCASE-R2.bat`, then run the BAT. It uses `rclone copy`, followed by `rclone check --one-way`, so it does not delete remote files.

## Rebuild catalogue locally

Run `BUILD-SONIC-LANDSCAPE.bat` while your local `showcase/` exists. The patched importer records original `showcase/...` paths for audio, artwork, YAML and live-lyrics sidecars. Commit the refreshed `data/catalogue.json` and other small generated metadata used by your current repo workflow.

## Stop tracking showcase in Git

Only after the R2 upload verifies successfully:

```powershell
.\good-boy-records\UNTRACK-SHOWCASE.ps1
.\good-boy-records\UNTRACK-SHOWCASE.ps1 -Apply
```

The apply mode adds `good-boy-records/showcase/` to the repository `.gitignore` and removes it from Git's index without deleting your local source files.

## R2 CORS

For the current GitHub Pages origin use a bucket CORS policy equivalent to:

```json
[
  {
    "AllowedOrigins": ["https://stst368-code.github.io"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag", "Content-Length", "Content-Range", "Accept-Ranges"],
    "MaxAgeSeconds": 3600
  }
]
```

Use a custom R2 domain for production when available; the `r2.dev` endpoint is intended for development/testing.
