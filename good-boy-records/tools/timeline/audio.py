#!/usr/bin/env python3
"""Pre-analyse tracks for deterministic GBR music-reactive visuals.

Writes compact gbr.audio.json with whole-track QA values, 10 Hz dance frames,
beat timing, and sparse pulsar candidates for sudden intensity lifts.
"""
from __future__ import annotations
import argparse, math
from pathlib import Path
from typing import Any
import numpy as np
from common import AUDIO_FORMAT, add_common_args, atomic_json, discover_variants, read_json, resolve_showcase, source_matches, source_signature, adopt_signature, audio_name, audio_path, legacy_audio_path, migrate_fixed_sidecar

def db(v: float, floor: float=1e-12) -> float: return float(20.0 * math.log10(max(float(v), floor)))
def robust01(v):
    v=np.asarray(v,dtype=float)
    if not v.size: return v
    lo,hi=np.percentile(v,[5,95])
    if not np.isfinite(lo) or not np.isfinite(hi) or hi<=lo: return np.zeros_like(v)
    return np.clip((v-lo)/(hi-lo),0,1)
def moving_mean(v,n):
    n=max(1,int(n)); return np.asarray(v,float) if n==1 else np.convolve(v,np.ones(n)/n,mode='same')
def band_energy(power,freqs,lo,hi):
    m=(freqs>=lo)&(freqs<hi)
    return np.sqrt(np.maximum(0,power[m].mean(axis=0))) if np.any(m) else np.zeros(power.shape[1])
def sample(times,values,out_times):
    return np.interp(out_times,times,values,left=float(values[0]),right=float(values[-1])) if len(values) else np.zeros_like(out_times)

def build_events(times,energy,onset,flux,min_score,min_gap):
    if len(times)<16: return []
    dt=float(np.median(np.diff(times))) if len(times)>1 else .02
    pre=max(1,int(round(.80/max(dt,1e-6)))); post=max(1,int(round(.35/max(dt,1e-6))))
    lift=np.zeros_like(energy)
    for i in range(pre,len(energy)-post):
        lift[i]=max(0.0,float(np.mean(energy[i:i+post])-np.mean(energy[i-pre:i])))
    ln,on,fl=robust01(lift),robust01(onset),robust01(flux)
    score=np.clip(.56*ln+.25*on+.19*fl,0,1)
    picked=[]
    for idx in np.argsort(score)[::-1]:
        if float(score[idx])<min_score: break
        if float(ln[idx])<.30 and float(on[idx])<.72: continue
        t=float(times[idx])
        if any(abs(t-float(times[j]))<min_gap for j in picked): continue
        picked.append(int(idx))
        if len(picked)>=48: break
    events=[]
    for n,idx in enumerate(sorted(picked),1):
        strength=float(score[idx])
        events.append({'id':f'e{n:03d}','time':round(float(times[idx]),3),'type':'pulsar','strength':round(strength,3),'duration':round(.65+1.10*strength,3),'spread':round(.65+.35*strength,3)})
    return events

def analyse(path: Path, signature: dict[str,str], frame_hz: int, event_threshold: float, event_gap: float) -> dict[str,Any]:
    try: import librosa
    except ImportError: raise RuntimeError('librosa is required. Run tools\\launchers\\timeline-setup-audio.bat once.')
    yn,srn=librosa.load(path,sr=None,mono=True)
    if not yn.size: raise RuntimeError('decoded audio is empty')
    sr=22050; y=librosa.resample(yn,orig_sr=srn,target_sr=sr) if srn!=sr else yn
    hop=512; nfft=2048
    rms=librosa.feature.rms(y=y,frame_length=nfft,hop_length=hop,center=True)[0]
    centroid=librosa.feature.spectral_centroid(y=y,sr=sr,n_fft=nfft,hop_length=hop)[0]
    onset=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop)
    stft=librosa.stft(y,n_fft=nfft,hop_length=hop,center=True); mag=np.abs(stft); power=mag**2
    freqs=librosa.fft_frequencies(sr=sr,n_fft=nfft); bass=band_energy(power,freqs,30,180)
    normmag=mag/np.maximum(np.linalg.norm(mag,axis=0,keepdims=True),1e-12)
    flux=np.sqrt(np.maximum(0,np.sum(np.maximum(0,np.diff(normmag,axis=1))**2,axis=0))); flux=np.pad(flux,(1,0))
    times=librosa.frames_to_time(np.arange(len(rms)),sr=sr,hop_length=hop); duration=float(len(yn)/srn)
    energy=robust01(moving_mean(rms,5)); bassn=robust01(moving_mean(bass,5)); bright=robust01(moving_mean(centroid,5))
    delta=np.maximum(0,np.diff(energy,prepend=energy[0])); change=np.clip(.48*robust01(moving_mean(delta,3))+.32*robust01(onset)+.20*robust01(flux),0,1)
    ot=np.arange(0,max(duration,.001),1.0/frame_hz)
    sampled=np.column_stack([sample(times,energy,ot),sample(times,bassn,ot),sample(times,bright,ot),sample(times,change,ot)])
    frames=np.rint(np.clip(sampled,0,1)*255).astype(np.uint8).tolist()
    tempo,bf=librosa.beat.beat_track(y=y,sr=sr,hop_length=hop); tempo=float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
    bt=librosa.frames_to_time(bf,sr=sr,hop_length=hop); on=robust01(onset)
    beats=[[round(float(t),3),int(round(float(on[min(max(int(f),0),len(on)-1)])*255))] for t,f in zip(bt,bf)]
    onsets=librosa.onset.onset_detect(onset_envelope=onset,sr=sr,hop_length=hop,units='frames')
    events=build_events(times,energy,onset,flux,event_threshold,event_gap)
    peak=float(np.max(np.abs(yn))); rmslin=float(np.sqrt(np.mean(np.square(yn,dtype=np.float64))))
    return {'format':AUDIO_FORMAT,'version':2,'source':signature,'duration':round(duration,3),'bpm':round(tempo,3),'summary':{'rms_db':round(db(rmslin),4),'peak_db':round(db(peak),4),'onset_density':round(float(len(onsets)/duration),5) if duration else 0.0},'dance':{'frame_hz':int(frame_hz),'scale':255,'channels':['energy','bass','brightness','change'],'frames':frames,'beats':beats,'events':events}}

def main():
    ap=argparse.ArgumentParser(description=__doc__); add_common_args(ap); ap.add_argument('--frame-hz',type=int,default=10,choices=range(5,21),metavar='5..20'); ap.add_argument('--event-threshold',type=float,default=.64); ap.add_argument('--event-gap',type=float,default=2.0); args=ap.parse_args()
    showcase=resolve_showcase(args.showcase); variants=discover_variants(showcase,args.track); jobs=[]
    print(f'GBR AUDIO / DANCE ANALYSIS\\nShowcase: {showcase}')
    for v in variants:
        target=audio_path(v); migrate_fixed_sidecar(target, legacy_audio_path(v)); sig=source_signature(v); old=read_json(target)
        if old and not args.force:
            matched=source_matches(old,sig)
            if matched is True: print(f'skip {v.directory.relative_to(showcase)}: audio analysis current'); continue
            if matched is None and old.get('format')==AUDIO_FORMAT: adopt_signature(target,old,sig); print(f'skip {v.directory.relative_to(showcase)}: adopted source signature'); continue
        jobs.append((v,sig))
    print(f'Jobs: {len(jobs)}')
    if args.list:
        for v,_ in jobs: print('  ',v.directory.relative_to(showcase),'->',v.audio.name)
        return 0
    failures=0
    for v,sig in jobs:
        print(f'\\n{v.directory.relative_to(showcase)}')
        try:
            payload=analyse(v.audio,sig,args.frame_hz,args.event_threshold,args.event_gap); atomic_json(target,payload)
            print(f"  + {audio_name(v)}: {payload['bpm']:.1f} BPM, {len(payload['dance']['frames'])} dance frames, {len(payload['dance']['events'])} pulsar candidate(s)")
        except Exception as exc: failures+=1; print(f'  ERROR: {exc}')
    print(f'\\nComplete: {len(jobs)-failures} succeeded, {failures} failed.'); return 1 if failures else 0
if __name__=='__main__': raise SystemExit(main())
