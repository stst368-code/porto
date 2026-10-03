#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, mimetypes, os, shutil, sys, threading, time, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

AUDIO_EXTS = {".flac", ".wav", ".mp3", ".opus", ".ogg", ".m4a", ".aac"}
AUDIO_RANK = {".flac":0, ".wav":1, ".opus":2, ".ogg":3, ".mp3":4, ".m4a":5, ".aac":6}

def norm_stem(p: Path) -> str:
    import re
    return re.sub(r"^\d+", "", p.stem.lower()).lstrip(" _-")

def choose_audio(directory: Path, lyric_path: Path) -> Path|None:
    files = sorted((p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS),
                   key=lambda p:(AUDIO_RANK.get(p.suffix.lower(),99), p.name.casefold()))
    if not files: return None
    # lyric canonical stem is the variant directory name; prefer that family.
    wanted = directory.name.casefold()
    exact = [p for p in files if p.stem.casefold() == wanted]
    if exact: return exact[0]
    groups = {}
    for p in files: groups.setdefault(norm_stem(p), []).append(p)
    if len(groups)==1: return sorted(next(iter(groups.values())), key=lambda p:AUDIO_RANK.get(p.suffix.lower(),99))[0]
    pref = [g for s,g in groups.items() if s == wanted or s.startswith(wanted+"-") or s.startswith(wanted+"_")]
    if len(pref)==1: return sorted(pref[0], key=lambda p:AUDIO_RANK.get(p.suffix.lower(),99))[0]
    return None

def read_json(path: Path):
    try:
        v=json.loads(path.read_text(encoding="utf-8"))
        return v if isinstance(v,dict) else None
    except Exception: return None

def flatten(data):
    out=[]
    for li,line in enumerate(data.get("lines") or []):
        for wi,w in enumerate(line.get("words") or []):
            if isinstance(w,dict):
                out.append((li,wi,w))
    return out

def coverage(data):
    ws=flatten(data)
    return (sum(bool(w.get("matched")) for _,_,w in ws)/len(ws)) if ws else 0.0

def discover(showcase: Path):
    tracks=[]
    for p in sorted(showcase.rglob("*.lyrics.json"), key=lambda x:x.as_posix().casefold()):
        # Ignore known fixed legacy name when canonical exists.
        if p.name=="gbr.lyrics.json" and (p.parent/f"{p.parent.name}.lyrics.json").is_file():
            continue
        d=read_json(p)
        if not d or not isinstance(d.get("lines"),list): continue
        audio=choose_audio(p.parent,p)
        if not audio: continue
        ws=flatten(d); bad=sum(not bool(w.get("matched")) for _,_,w in ws)
        cov=coverage(d)
        tracks.append({
            "id": str(p.relative_to(showcase)).replace("\\","/"),
            "title": d.get("title") or p.parent.name,
            "version": d.get("song_version"),
            "coverage": round(cov,4),
            "total": len(ws), "unresolved": bad,
            "audio_name": audio.name,
            "lyric_name": p.name,
            "dir": str(p.parent.relative_to(showcase)).replace("\\","/"),
        })
    tracks.sort(key=lambda x:(x["unresolved"]==0, -x["unresolved"], x["title"].casefold(), x["dir"].casefold()))
    return tracks

def safe_track(showcase:Path, rel:str):
    p=(showcase/rel).resolve()
    try: p.relative_to(showcase.resolve())
    except ValueError: raise ValueError("outside showcase")
    if not p.is_file() or not p.name.endswith(".lyrics.json"): raise ValueError("invalid lyric file")
    return p

def validate_and_recompute(data):
    lines=data.get("lines")
    if not isinstance(lines,list): raise ValueError("missing lines")
    allw=[]
    last=0.0
    for li,line in enumerate(lines):
        words=line.get("words")
        if not isinstance(words,list) or not words: continue
        for wi,w in enumerate(words):
            try: s=round(float(w.get("start")),3); e=round(float(w.get("end")),3)
            except Exception: raise ValueError(f"invalid timing at line {li+1}, word {wi+1}")
            if s<0 or e<=s: raise ValueError(f"invalid timing at line {li+1}, word {wi+1}: {s}-{e}")
            # Overlap is allowed for vocals, but time must not run backwards grossly.
            if s + 0.5 < last:
                raise ValueError(f"timing runs backwards at line {li+1}, word {wi+1}")
            w["start"],w["end"]=s,e
            w["matched"]=bool(w.get("matched"))
            allw.append(w); last=max(last,e)
        line["start"]=round(float(words[0]["start"]),3)
        line["end"]=round(float(words[-1]["end"]),3)
    total=len(allw); matched=sum(bool(w.get("matched")) for w in allw)
    cov=matched/total if total else 0.0
    stats=data.setdefault("stats",{})
    stats["lyric_words"]=total
    stats["matched_words"]=matched
    stats["coverage"]=round(cov,4)
    quality=data.setdefault("quality",{})
    quality["rating"]="excellent" if cov>=.92 else "good" if cov>=.85 else "fair" if cov>=.80 else "review" if cov>=.65 else "poor"
    quality["review_required"]=cov<1.0
    quality["usable"]=cov>=1.0
    quality["approved"]=cov>=1.0
    data["manual_review"]={
        "completed": cov>=1.0,
        "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": "gbr-lyric-review-v1"
    }
    return data

class App:
    def __init__(self, showcase, webroot):
        self.showcase=showcase.resolve(); self.webroot=webroot.resolve()

    def handler(self):
        app=self
        class H(BaseHTTPRequestHandler):
            def log_message(self, fmt,*args): pass
            def send_json(self,obj,status=200):
                raw=json.dumps(obj,ensure_ascii=False).encode()
                self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
                self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def do_GET(self):
                u=urlparse(self.path)
                try:
                    if u.path=="/api/tracks": return self.send_json({"tracks":discover(app.showcase)})
                    if u.path=="/api/track":
                        rel=parse_qs(u.query).get("id",[""])[0]; p=safe_track(app.showcase,rel); d=read_json(p)
                        audio=choose_audio(p.parent,p)
                        if not d or not audio: raise ValueError("track unavailable")
                        return self.send_json({"lyrics":d,"audio":"/media/"+str(audio.relative_to(app.showcase)).replace("\\","/")})
                    if u.path.startswith("/media/"):
                        rel=unquote(u.path[len("/media/"):]); p=(app.showcase/rel).resolve(); p.relative_to(app.showcase)
                        if not p.is_file() or p.suffix.lower() not in AUDIO_EXTS: raise ValueError("media unavailable")
                        size=p.stat().st_size; rng=self.headers.get("Range")
                        start,end=0,size-1
                        if rng and rng.startswith("bytes="):
                            a,b=rng[6:].split("-",1); start=int(a or 0); end=min(int(b) if b else size-1,size-1)
                            status=206
                        else: status=200
                        self.send_response(status); self.send_header("Content-Type",mimetypes.guess_type(p.name)[0] or "application/octet-stream")
                        self.send_header("Accept-Ranges","bytes"); self.send_header("Content-Length",str(end-start+1))
                        if status==206:self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
                        self.end_headers()
                        with p.open("rb") as f:
                            f.seek(start); remaining=end-start+1
                            while remaining:
                                chunk=f.read(min(1024*256,remaining))
                                if not chunk:break
                                self.wfile.write(chunk); remaining-=len(chunk)
                        return
                    name="index.html" if u.path in ("/","") else u.path.lstrip("/")
                    p=(app.webroot/name).resolve(); p.relative_to(app.webroot)
                    if not p.is_file(): self.send_error(404); return
                    raw=p.read_bytes(); self.send_response(200); self.send_header("Content-Type",mimetypes.guess_type(p.name)[0] or "text/plain")
                    self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
                except Exception as e: self.send_json({"error":str(e)},400)
            def do_POST(self):
                u=urlparse(self.path)
                if u.path!="/api/save": return self.send_json({"error":"not found"},404)
                try:
                    n=int(self.headers.get("Content-Length","0")); body=json.loads(self.rfile.read(n))
                    p=safe_track(app.showcase,str(body.get("id",""))); data=body.get("lyrics")
                    if not isinstance(data,dict): raise ValueError("invalid lyrics payload")
                    data=validate_and_recompute(data)
                    backup=p.with_suffix(p.suffix+".review-backup")
                    if not backup.exists(): shutil.copy2(p,backup)
                    tmp=p.with_suffix(p.suffix+".tmp")
                    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); os.replace(tmp,p)
                    return self.send_json({"ok":True,"coverage":data["stats"]["coverage"],"matched":data["stats"]["matched_words"],"total":data["stats"]["lyric_words"]})
                except Exception as e: return self.send_json({"error":str(e)},400)
        return H

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--showcase")
    ap.add_argument("--port",type=int,default=8765)
    ap.add_argument("--no-browser",action="store_true")
    a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2]
    showcase=Path(a.showcase).expanduser().resolve() if a.showcase else (repo/"showcase").resolve()
    if not showcase.is_dir(): raise SystemExit(f"Showcase not found: {showcase}")
    webroot=Path(__file__).resolve().parent
    app=App(showcase,webroot); srv=ThreadingHTTPServer(("127.0.0.1",a.port),app.handler())
    url=f"http://127.0.0.1:{a.port}/"
    print(f"GBR Lyric Review\nShowcase: {showcase}\nOpen: {url}\nCtrl+C to stop.")
    if not a.no_browser: threading.Timer(.6,lambda:webbrowser.open(url)).start()
    try:srv.serve_forever()
    except KeyboardInterrupt: pass
    finally:srv.server_close()
if __name__=="__main__": main()
