"""Read external quality folders and update the research database."""
import collections, hashlib, json, pathlib, sys
from schema import connect
from utils import now,digest_file
from metrics import parse_yaml
from audio import audio_summary, audio_summary_bytes
from profiler import profile_audio
from catalogue import catalogue_reference

AUDIO_EXT={'.flac','.mp3','.wav','.ogg','.m4a','.opus'}
SCORES={'good':5,'above-average':4,'average':3,'below-average':2,'bad':1,'unlistenable':0}


def normalized_name(path):
 name=path.stem.lower()
 if name.endswith('.audio'):name=name[:-6]
 return name

def scan_root(root, quality, db, cat_audio, cat_yaml, errors, profile_missing=False):
 root=pathlib.Path(root).expanduser().resolve()
 if not root.is_dir(): errors.append((str(root),'Folder does not exist'));return
 audio_files=sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in AUDIO_EXT)
 # FLAC/MP3 representations of the same generation are one record; prefer FLAC.
 grouped=collections.defaultdict(list)
 for a in audio_files: grouped[(a.parent, a.stem.lower())].append(a)
 jobs=[]
 for (parent,stem),assets in grouped.items():
  audio=sorted(assets,key=lambda p: (p.suffix.lower()!='.flac',str(p)))[0]
  y=next((p for p in assets[0].parent.iterdir() if p.suffix.lower() in ('.yaml','.yml') and p.stem.lower()==stem),None)
  jobs.append((audio,y))
 # Include unmatched YAMLs without audio, but not if attached to an audio above.
 matched={str(y.resolve()) for _,y in jobs if y}
 for y in sorted(root.rglob('*')):
  if y.is_file() and y.suffix.lower() in ('.yaml','.yml') and str(y.resolve()) not in matched:
   jobs.append((None,y))
 for audio,y in jobs:
  file_path=audio or y
  try:
   a_hash=digest_file(audio) if audio else None
   # Audio hash is stable identity, but YAML-only entries must remain separable.
   genid=a_hash if a_hash else 'yaml:'+hashlib.sha256(str(y.resolve()).encode()).hexdigest()
   vals=parse_yaml(y) if y else {}
   vals.update({'id':genid,'audio_hash':a_hash,'audio_path':str(audio) if audio else None,
                'yaml_path':str(y) if y else None,'source_root':str(root),'quality_score':quality,
                'quality_folder':root.name,'scan_time':now(),'missing_audio':int(audio is None),'missing_yaml':int(y is None)})
   vals['published']=int(bool(a_hash and a_hash in cat_audio) or bool(y and digest_file(y) in cat_yaml))
   vals['catalogue_id']=cat_audio.get(a_hash) if a_hash else None
   cols=','.join(vals);qs=','.join('?' for _ in vals)
   updates=','.join(f'{k}=excluded.{k}' for k in vals if k!='id')
   old=db.execute('SELECT quality_score,quality_folder FROM generations WHERE id=?',(genid,)).fetchone()
   db.execute(f'INSERT INTO generations ({cols}) VALUES ({qs}) ON CONFLICT(id) DO UPDATE SET {updates}',list(vals.values()))
   if old is None or tuple(old)!=(quality,root.name):
    db.execute('INSERT INTO ratings_history(generation_id,score,folder,observed_at) VALUES(?,?,?,?)',(genid,quality,root.name,now()))
   # Accept common sibling conventions and single gbr.audio.json in the generation directory.
   candidates=[]
   if audio:
    candidates=[audio.with_name(audio.stem+'.audio.json'),audio.with_name('gbr.audio.json')]
   if y: candidates += [y.with_name(y.stem+'.audio.json'),y.with_name('gbr.audio.json')]
   found_profile = False
   for ap in dict.fromkeys(candidates):
    if ap.exists():
     try:
      met=audio_summary(ap);met['generation_id']=genid
      keys=','.join(met);marks=','.join('?' for _ in met)
      ups=','.join(f'{k}=excluded.{k}' for k in met if k!='generation_id')
      db.execute(f'INSERT INTO audio_metrics({keys}) VALUES({marks}) ON CONFLICT(generation_id) DO UPDATE SET {ups}',list(met.values()))
     except Exception as e: errors.append((str(ap),str(e)))
     found_profile = True
     break
   if profile_missing and audio and not found_profile:
    existing=db.execute('SELECT audio_source_hash FROM audio_metrics WHERE generation_id=?',(genid,)).fetchone()
    if existing is None or existing[0]!=a_hash:
     raw=profile_audio(audio,a_hash)
     met=audio_summary_bytes(raw);met['generation_id']=genid
     keys=','.join(met);marks=','.join('?' for _ in met)
     ups=','.join(f'{k}=excluded.{k}' for k in met if k!='generation_id')
     db.execute(f'INSERT INTO audio_metrics({keys}) VALUES({marks}) ON CONFLICT(generation_id) DO UPDATE SET {ups}',list(met.values()))
  except Exception as e:errors.append((str(file_path),str(e)))

def scan(args):
 db=connect(args.db)
 errors=[];cat_audio,cat_yaml=catalogue_reference(args.catalogue)
 for rating,folder in [('good',args.good),('above-average',args.above_average),('average',args.average),('below-average',args.below_average),('bad',args.bad),('unlistenable',args.unlistenable)]:
  if folder:scan_root(folder,SCORES[rating],db,cat_audio,cat_yaml,errors,getattr(args,"profile_missing",False))
 for path,msg in errors:db.execute('INSERT INTO scan_errors(file_path,message,observed_at) VALUES(?,?,?)',(path,msg,now()))
 n=db.execute('SELECT COUNT(*) FROM generations').fetchone()[0]
 db.execute('INSERT INTO analysis_runs(ran_at,generation_count,config_json) VALUES(?,?,?)',(now(),n,json.dumps({k:v for k,v in vars(args).items() if k!="func"})))
 # Retain unresolved historical errors only: successfully profiled files can be recognised by path.
 db.execute("DELETE FROM scan_errors WHERE message LIKE '%librosa%' AND EXISTS (SELECT 1 FROM generations g JOIN audio_metrics a ON a.generation_id=g.id WHERE g.audio_path=scan_errors.file_path OR g.audio_path=REPLACE(scan_errors.file_path,'.audio.json','.flac'))")
 db.commit();db.close();print('Scanned. Database records:',n,'Errors:',len(errors))
 for p,msg in errors[:10]:print('ERROR',p,msg,file=sys.stderr)

