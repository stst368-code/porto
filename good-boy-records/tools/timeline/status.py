#!/usr/bin/env python3
from __future__ import annotations
import argparse
from collections import Counter
from common import discover_variants,resolve_showcase,lyrics_path,legacy_lyrics_path,audio_path,legacy_audio_path,playback_path,legacy_playback_path
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--showcase');ap.add_argument('--track',action='append',default=[]);args=ap.parse_args();showcase=resolve_showcase(args.showcase);vs=discover_variants(showcase,args.track);c=Counter()
    for v in vs:
        l=lyrics_path(v).is_file() or legacy_lyrics_path(v).is_file();a=audio_path(v).is_file() or legacy_audio_path(v).is_file();p=playback_path(v).is_file() or legacy_playback_path(v).is_file();c['lyrics']+=l;c['audio']+=a;c['playback']+=p
        if not(l and a and p):print(f"{v.directory.relative_to(showcase)}  lyrics={'Y' if l else '-'} audio={'Y' if a else '-'} playback={'Y' if p else '-'}")
    print(f"\\nVariants: {len(vs)}\\nLyrics:   {c['lyrics']}\\nAudio:    {c['audio']}\\nPlayback: {c['playback']}");return 0
if __name__=='__main__':raise SystemExit(main())
