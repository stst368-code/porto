"""Add a small analytics link to generated player HTML without editing its source template."""
from pathlib import Path
import sys

LINK = ('<a id="gbr-analytics-link" href="analytics/" '
        'style="position:fixed;top:8px;right:8px;z-index:10000;'
        'padding:7px 10px;border:1px solid #6c5942;border-radius:4px;'
        'background:#111d;color:#edddc8;font:700 11px Arial,sans-serif;'
        'text-decoration:none" title="Generation research and ratings">Analytics</a>')
for filename in sys.argv[1:]:
    path = Path(filename)
    text = path.read_text(encoding='utf-8')
    if 'id="gbr-analytics-link"' in text:
        continue
    if '</body>' not in text:
        raise SystemExit(f'Missing body closing tag in {path}')
    path.write_text(text.replace('</body>', LINK + '\n</body>', 1), encoding='utf-8')
    print('Analytics navigation added to', path)
