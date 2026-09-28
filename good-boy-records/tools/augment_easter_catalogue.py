from __future__ import annotations
import json, sys
from pathlib import Path

AUDIO_EXTS={'.mp3','.flac','.wav','.m4a','.ogg','.opus'}

def titleize(stem:str)->str:
    return stem.replace('_',' ').replace('-',' ').strip().title()

def rel(p:Path, root:Path)->str:
    return p.relative_to(root).as_posix()

def main():
    catalogue=Path(sys.argv[1] if len(sys.argv)>1 else '_site/catalogue.json')
    project=Path(sys.argv[2] if len(sys.argv)>2 else '.').resolve()
    easter_root=project/'showcase'/'easter'
    if not catalogue.exists():
        raise SystemExit(f'Missing catalogue: {catalogue}')
    data=json.loads(catalogue.read_text(encoding='utf-8'))
    if isinstance(data,list):
        data={'tracks':data}
    hidden=[]
    if easter_root.exists():
        for audio in sorted(p for p in easter_root.rglob('*') if p.is_file() and p.suffix.lower() in AUDIO_EXTS):
            stem=audio.stem
            folder=audio.parent
            candidates=[folder/f'{stem}.png',folder/f'{stem}.webp',folder/'cover.png',folder/'cover.webp']
            art=next((p for p in candidates if p.exists()),None)
            lyric_candidates=[folder/f'{stem}.lyrics.json',folder/f'{stem}.json']
            lyrics=next((p for p in lyric_candidates if p.exists()),None)
            entry={
                'id':f'easter-{stem}',
                'title':titleize(stem),
                'displayTitle':titleize(stem),
                'composition':'Easter Universe',
                'variant':'hidden',
                'audio_url':rel(audio, project),
                'genre':{
                    'cluster':'easter universe',
                    'parent_genre':'Easter Universe',
                    'child_genre':'Hidden Track',
                    'parent_colour':'#7656C7',
                    'child_colour':'#9A7DE1',
                    'taxonomy_order':999999,
                }
            }
            if art: entry['artwork_url']=rel(art, project)
            if lyrics: entry['lyrics_url']=rel(lyrics, project)
            hidden.append(entry)
    if not hidden:
        existing=data.get('easter_tracks') or ((data.get('easter') or {}).get('tracks') if isinstance(data.get('easter'),dict) else None) or []
        for raw in existing:
            if not isinstance(raw,dict):
                continue
            entry=dict(raw)
            entry.setdefault('composition','Easter Universe')
            entry.setdefault('variant','hidden')
            entry.setdefault('genre',{
                'cluster':'easter universe',
                'parent_genre':'Easter Universe',
                'child_genre':'Hidden Track',
                'parent_colour':'#7656C7',
                'child_colour':'#9A7DE1',
                'taxonomy_order':999999,
            })
            hidden.append(entry)
    data['easter_tracks']=hidden
    catalogue.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    origin=str(easter_root) if easter_root.exists() else 'prebuilt catalogue (external showcase)'
    print(f'Easter catalogue: {len(hidden)} playable tracks from {origin}')

if __name__=='__main__': main()
