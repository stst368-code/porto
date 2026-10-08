"""YAML generation settings and non-semantic text statistics."""
import re, collections, json
import yaml
from utils import scalar_number,scalar_int,string

def words(t): return re.findall(r"[^\W_]+(?:['’\-][^\W_]+)*",t,flags=re.UNICODE)
def text_stats(t,lyrics=False):
 all_lines=[ln.strip() for ln in t.splitlines() if ln.strip()]
 sections=[re.match(r'^\[([^\]]+)\]$', ln) for ln in all_lines]
 tags=[m.group(1).strip().lower() for m in sections if m]
 lines=[ln for ln,m in zip(all_lines,sections) if not (lyrics and m)]
 ws=words('\n'.join(lines))
 return {'chars':len(t),'words':len(ws),'lines':len(lines),
         'avg_word_length':round(sum(len(w) for w in ws)/len(ws),4) if ws else None,
         'avg_line_words':round(sum(len(words(x)) for x in lines)/len(lines),4) if lines else None,
         'section_count':len(tags),'section_counts':dict(collections.Counter(tags))}
def parse_yaml(p):
 d=yaml.safe_load(p.read_text(encoding='utf-8-sig')) or {}
 if not isinstance(d,dict):raise ValueError('YAML root must be object')
 cap=text_stats(str(d.get('caption') or ''))
 lyr=text_stats(str(d.get('lyrics') or ''),True)
 v={k:d.get(k) for k in ['title','cluster','version','model','dit','text_encoder','sampler','scheduler']}
 for k in ['encoder_cfg','sampler_cfg']:v[k]=scalar_number(d.get(k))
 for k in ['top_k','sampler_steps']:v[k]=scalar_int(d.get(k))
 for k in ['encoder_seed','sampler_seed']:v[k]=string(d.get(k))
 v.update({'caption_'+k:cap[k] for k in ('chars','words','lines')})
 v['caption_avg_word_length']=cap['avg_word_length']
 v.update({'lyrics_'+k:lyr[k] for k in ('chars','words','lines')})
 v['lyrics_avg_word_length']=lyr['avg_word_length']
 v['avg_lyric_line_words']=lyr['avg_line_words']
 v['lyric_sections']=lyr['section_count'];v['section_counts']=json.dumps(lyr['section_counts'],ensure_ascii=False)
 return v

