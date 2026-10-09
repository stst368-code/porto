"""Export public, path-safe JSON for GitHub Pages."""
import gzip, json, pathlib, sqlite3, statistics
from utils import now

def export(args):
 db=sqlite3.connect(args.db);db.row_factory=sqlite3.Row
 rows=db.execute('''SELECT g.*,a.duration,a.bpm,a.rms_db,a.peak_db,a.onset_density,a.frames,a.beats,a.events,
 a.energy_mean,a.energy_std,a.bass_mean,a.bass_std,a.brightness_mean,a.brightness_std,a.change_mean,a.change_std
 FROM generations g LEFT JOIN audio_metrics a ON a.generation_id=g.id ORDER BY g.title,g.cluster,g.version,g.id''').fetchall()
 out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=True)
 public=[]
 for r in rows:
  d=dict(r)
  # Do not publish workstation absolute paths. Instead surface relative filenames and IDs.
  d['audio_file']=pathlib.Path(d.pop('audio_path')).name if d.get('audio_path') else None
  d['yaml_file']=pathlib.Path(d.pop('yaml_path')).name if d.get('yaml_path') else None
  d.pop('source_root',None);d.pop('scan_time',None)
  d['section_counts']=json.loads(d['section_counts'] or '{}')
  public.append(d)
 data={'format':'gbr-generation-analytics-v1','generated_at':now(),'count':len(public),'generations':public}
 (out/'generations.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 (out/'generations.json.gz').write_bytes(gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),compresslevel=9))
 buckets={str(i):0 for i in range(0,6)}
 for r in public:buckets[str(r['quality_score'])]+=1
 summary={'format':'gbr-generation-summary-v1','generated_at':data['generated_at'],'total':len(public),'ratings':buckets,
          'mean_rating':round(statistics.fmean(r['quality_score'] for r in public),3) if public else None,
          'audio_analysed':sum(x.get('duration') is not None for x in public),
          'published':sum(x.get('published') for x in public)}
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 print('Exported',len(public),'records to',out)
 db.close()

