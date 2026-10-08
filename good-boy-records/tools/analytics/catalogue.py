"""Read publication identity from the existing, unmodified GBR catalogue."""
import json, pathlib
from utils import digest_file

def catalogue_reference(p):
 audio={};yamlhash=set()
 if not p:return audio,yamlhash
 obj=json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
 base=pathlib.Path(p).resolve().parent
 if base.name.lower() == 'data': base=base.parent
 for track in obj.get('tracks',[]):
  for rel in (track.get('audio') or {}).get('sources',{}).values():
   if not isinstance(rel,str) or not rel: continue
   path=base/rel
   if path.is_file():audio[digest_file(path)]=track.get('id')
  yp=track.get('yamlUrl')
  if yp and (base/yp).is_file():yamlhash.add(digest_file(base/yp))
 return audio,yamlhash

