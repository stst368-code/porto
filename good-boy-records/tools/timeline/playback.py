#!/usr/bin/env python3
"""Combine gbr.lyrics.json + gbr.audio.json into runtime gbr.playback.json.
Manual word/line overrides and manual free-standing events survive recompilation.
"""
from __future__ import annotations
import argparse
from typing import Any
from common import AUDIO_FORMAT,AUDIO_NAME,LYRICS_NAME,PLAYBACK_FORMAT,PLAYBACK_NAME,add_common_args,atomic_json,discover_variants,read_json,resolve_showcase

def f01(v): return round(max(0.0,min(1.0,float(v))),3)
def old_manual(old):
    lm,wm,me={},{},[]
    if not old:return lm,wm,me
    for line in old.get('lines') or []:
        if not isinstance(line,dict):continue
        lid=str(line.get('id') or ''); r=line.get('reaction') if isinstance(line.get('reaction'),dict) else {}
        if lid and 'manual' in r:lm[lid]=r.get('manual')
        for word in line.get('words') or []:
            if not isinstance(word,dict):continue
            wid=str(word.get('id') or ''); wr=word.get('reaction') if isinstance(word.get('reaction'),dict) else {}
            if wid and 'manual' in wr:wm[wid]=wr.get('manual')
    me=[x for x in (old.get('manual_events') or []) if isinstance(x,dict)]
    return lm,wm,me

def frame_slice(d,start,end):
    hz=int(d.get('frame_hz') or 10); frames=d.get('frames') if isinstance(d.get('frames'),list) else []
    if not frames:return []
    a=max(0,int(start*hz)); b=min(len(frames),max(a+1,int(end*hz)+1)); return [x for x in frames[a:b] if isinstance(x,list) and len(x)>=4]
def auto_reaction(d,start,end):
    frames=frame_slice(d,start,end)
    if not frames:return {'intensity':0.0,'accent':0.0,'pulsar':0.0}
    scale=float(d.get('scale') or 255); intensity=sum(float(x[0]) for x in frames)/len(frames)/scale; accent=max(float(x[3]) for x in frames)/scale; pulsar=0.0
    lo,hi=start-.12,end+.12
    for e in d.get('events') or []:
        if isinstance(e,dict) and isinstance(e.get('time'),(int,float)) and isinstance(e.get('strength'),(int,float)) and lo<=float(e['time'])<=hi:pulsar=max(pulsar,float(e['strength']))
    return {'intensity':f01(intensity),'accent':f01(accent),'pulsar':f01(pulsar)}
def nearest_word(lines,t):
    best=None
    for line in lines:
        if not isinstance(line,dict):continue
        ls,le=line.get('start'),line.get('end')
        if not isinstance(ls,(int,float)) or not isinstance(le,(int,float)) or not(float(ls)-.15<=t<=float(le)+.15):continue
        lid=str(line.get('id') or '') or None
        for word in line.get('words') or []:
            if not isinstance(word,dict):continue
            ws,we=word.get('start'),word.get('end')
            if not isinstance(ws,(int,float)) or not isinstance(we,(int,float)):continue
            ws,we=float(ws),float(we); dist=0.0 if ws<=t<=we else min(abs(t-ws),abs(t-we))
            if best is None or dist<best[0]:best=(dist,lid,str(word.get('id') or '') or None)
        if best is None:best=(0.0,lid,None)
    return (best[1],best[2]) if best else (None,None)
def compile_playback(lyrics,audio,old):
    lm,wm,manual_events=old_manual(old); d=audio.get('dance') if isinstance(audio.get('dance'),dict) else {}; lines=[]
    for line in lyrics.get('lines') or []:
        if not isinstance(line,dict):continue
        lid=str(line.get('id') or ''); start=float(line.get('start') or 0); end=float(line.get('end') or 0); words=[]
        for word in line.get('words') or []:
            if not isinstance(word,dict):continue
            wid=str(word.get('id') or ''); ws=float(word.get('start') or 0); we=float(word.get('end') or 0)
            words.append({'id':wid,'text':word.get('text'),'start':round(ws,3),'end':round(we,3),'matched':bool(word.get('matched',False)),'reaction':{'auto':auto_reaction(d,ws,we),'manual':wm.get(wid)}})
        lines.append({'id':lid,'text':line.get('text'),'start':round(start,3),'end':round(end,3),'reaction':{'auto':auto_reaction(d,start,end),'manual':lm.get(lid)},'words':words})
    events=[]
    for e in d.get('events') or []:
        if not isinstance(e,dict):continue
        t=float(e.get('time') or 0); lid,wid=nearest_word(lines,t)
        events.append({'id':e.get('id'),'time':round(t,3),'type':e.get('type') or 'pulsar','strength':f01(e.get('strength') or 0),'duration':round(float(e.get('duration') or 1.0),3),'spread':f01(e.get('spread') or 1.0),'line_id':lid,'word_id':wid})
    dance={'frame_hz':d.get('frame_hz',10),'scale':d.get('scale',255),'channels':d.get('channels') or ['energy','bass','brightness','change'],'frames':d.get('frames') or [],'beats':d.get('beats') or [],'events':events}
    return {'format':PLAYBACK_FORMAT,'version':2,'duration':audio.get('duration'),'bpm':audio.get('bpm'),'dance':dance,'lines':lines,'manual_events':manual_events}
def main():
    ap=argparse.ArgumentParser(description=__doc__); add_common_args(ap); args=ap.parse_args(); showcase=resolve_showcase(args.showcase); variants=discover_variants(showcase,args.track); made=missing=0
    print(f'GBR PLAYBACK COMPILER\\nShowcase: {showcase}')
    for v in variants:
        lp=v.directory/LYRICS_NAME; apath=v.directory/AUDIO_NAME; out=v.directory/PLAYBACK_NAME; lyrics=read_json(lp); audio=read_json(apath)
        if not lyrics or not isinstance(lyrics.get('lines'),list):print(f'skip {v.directory.relative_to(showcase)}: missing {LYRICS_NAME}');missing+=1;continue
        if not audio or audio.get('format')!=AUDIO_FORMAT:print(f'skip {v.directory.relative_to(showcase)}: missing/current-version {AUDIO_NAME}');missing+=1;continue
        if args.list:print('  ',v.directory.relative_to(showcase),'->',PLAYBACK_NAME);continue
        payload=compile_playback(lyrics,audio,read_json(out)); atomic_json(out,payload); print(f"  + {v.directory.relative_to(showcase)}/{PLAYBACK_NAME}: {len(payload['dance']['events'])} automatic pulsar(s)"); made+=1
    if args.list:return 0
    print(f'\\nComplete: {made} playback file(s) written; {missing} waiting for an input sidecar.');return 0
if __name__=='__main__': raise SystemExit(main())
