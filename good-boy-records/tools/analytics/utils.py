"""Shared filesystem, numeric and time helpers."""
import datetime as dt
import hashlib

def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def digest_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''): h.update(b)
 return h.hexdigest()
def scalar_number(v):
 try: return float(v) if v is not None and str(v).strip() else None
 except (TypeError,ValueError):return None
def scalar_int(v):
 try:return int(v) if v is not None and str(v).strip() else None
 except (TypeError,ValueError):return None
def string(v):return str(v) if v is not None else None

