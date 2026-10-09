"""Independent, conservative pipeline telemetry import.

Never guesses a generation link based on song, precision, pod, or parameter settings.
No changes to the operational analytics.sqlite database.
"""
import argparse
import csv
import json
import pathlib
import re
from collections import defaultdict
from datetime import datetime, timezone


def clean(s):
    return str(s or '').strip()


def norm(s):
    return re.sub(r'[^a-z0-9]+', '_', str(s).lower()).strip('_')


def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        rd = csv.DictReader(f)
        for r in rd:
            yield {norm(k): clean(v) for k, v in r.items() if k}


def val(row, *names):
    for name in names:
        v = row.get(norm(name), '')
        if v != '':
            return v
    return None


def num(value):
    if value is None:
        return None
    try:
        x = float(value.replace('$', '').replace(',', ''))
        return x if abs(x) < 1e15 else None
    except (ValueError, AttributeError):
        return None


def stem(path):
    # Windows paths can be present even when this script runs on another OS.
    name = str(path or '').replace('\\', '/').split('/')[-1]
    return re.sub(r'\.(flac|wav|mp3|yaml|yml)$', '', name, flags=re.I).lower()


def main():
    ap = argparse.ArgumentParser(description='GBR cost-performance bridge (non-destructive)')
    ap.add_argument('--timings', required=True)
    ap.add_argument('--summary')
    ap.add_argument('--generations', default='data/analytics/generations.json')
    ap.add_argument('--output', default='data/analytics/cost-analysis.json')
    args = ap.parse_args()
    dataset = json.loads(pathlib.Path(args.generations).read_text(encoding='utf-8-sig'))
    generations = dataset['generations']
    by_id = {str(g.get('id')): g for g in generations}
    by_hash = {str(g.get('audio_hash')): g for g in generations if g.get('audio_hash')}
    by_file = defaultdict(list)
    for g in generations:
        if g.get('audio_file'):
            by_file[stem(g['audio_file'])].append(g)
    raw = list(read_csv(args.timings))
    if not raw:
        raise SystemExit('Timings CSV has no records. Keeping existing cost analysis unchanged.')
    supported = set().union(*(r.keys() for r in raw))
    # Stage-level telemetry: billable total-stage rows, not substage totals.
    stage_fields = ('stage', 'phase', 'event', 'operation', 'timing_stage')
    stages_present = bool(set(stage_fields) & supported)
    costs_present = bool(set(['estimated_cost_usd','estimated_cost','cost_usd','cost','billable_cost_usd','stage_cost_usd']) & supported)
    if not costs_present and not (('cost_per_hour' in supported or 'hourly_rate' in supported) and ('seconds' in supported or 'elapsed_seconds' in supported or 'duration_seconds' in supported)):
        raise SystemExit('No identifiable cost or hourly-rate/seconds fields. Refusing to invent prices; inspect CSV headers.')
    ledger = defaultdict(lambda: {'cost_usd':0.,'seconds':0.,'rows':0,'stages':set(),'gpu':set(),'ids':set()})
    matched = defaultdict(lambda: {'cost_usd':0.,'seconds':0.,'stages':set(),'workers':set()})
    unjoined=[]; skipped=[]; ambiguous=[]
    for rownum,r in enumerate(raw,2):
        stage=clean(val(r,*stage_fields) or '').lower()
        # Job-total records can overlap stage costs; never add them to billable totals.
        if stage in {'job_total','conditioning_compute','conditioning_download','sampling_compute','audio_download','conditioning_queue_wait','sampling_queue_wait','conditioning_upload'}:
            skipped.append({'row':rownum,'reason':'overlap_or_nonbillable_substage','stage':stage});continue
        if stages_present and stage and stage not in {'conditioning_total','sampling_total'}:
            skipped.append({'row':rownum,'reason':'unrecognized_stage','stage':stage});continue
        # If we have no stage identity, require an explicit billable flag or an unambiguous per-generation total cost.
        if not stages_present and val(r,'billable') and val(r,'billable').lower() in {'0','false','no'}:
            continue
        c=num(val(r,'estimated_cost_usd','estimated_cost','cost_usd','billable_cost_usd','stage_cost_usd','cost'))
        seconds=num(val(r,'seconds','elapsed_seconds','duration_seconds','worker_seconds','total_seconds'))
        rate=num(val(r,'cost_per_hour','hourly_rate','gpu_hourly_cost'))
        if c is None and seconds is not None and rate is not None:
            c=seconds*rate/3600
        if c is None or c<0:
            skipped.append({'row':rownum,'reason':'no_valid_cost','stage':stage});continue
        worker=val(r,'worker','worker_name','worker_id','pod','pod_name','compute_id') or 'Unknown worker'
        gpu=val(r,'gpu_name','gpu','gpu_model') or 'Unknown GPU'
        run=val(r,'job_id','generation_id','run_id','task_id','job')
        output=val(r,'audio_path','output_path','output_file','audio_file','filename','flac_path','output_audio')
        key=(worker,gpu)
        rec=ledger[key]
        rec['cost_usd']+=c
        rec['seconds']+=max(0,seconds or 0)
        rec['rows']+=1
        rec['stages'].add(stage or 'total')
        if run:rec['ids'].add(run)
        found=None
        # Only stable export ID/audio hash OR unique exact output file stem.
        for candidate in [val(r,'audio_hash','sha256','content_hash'), val(r,'generation_id','job_id')]:
            if candidate and candidate in by_hash:found=by_hash[candidate];break
            if candidate and candidate in by_id:found=by_id[candidate];break
        if found is None and output:
            hits=by_file[stem(output)]
            if len(hits)==1:found=hits[0]
            elif len(hits)>1:ambiguous.append({'row':rownum,'file':stem(output),'candidates':len(hits)})
        if found is None:
            unjoined.append({'row':rownum,'worker':worker,'stage':stage,'file':stem(output) if output else None,'job_id':run})
            continue
        item=matched[found['id']]
        item['cost_usd']+=c
        item['seconds']+=max(0,seconds or 0)
        item['stages'].add(stage or 'total')
        item['workers'].add(worker)
    # Multiple stage records for one generation are legitimate; costs assigned once per stage.
    attached=[]
    for gid,x in matched.items():
        g=by_id[gid]
        attached.append({'generation_id':gid,'audio_file':g.get('audio_file'),'quality_score':g.get('quality_score'), 'text_encoder':g.get('text_encoder'),'dit':g.get('dit'),'sampler_steps':g.get('sampler_steps'),'sampler':g.get('sampler'),'scheduler':g.get('scheduler'),'cost_usd':round(x['cost_usd'],8),'seconds':round(x['seconds'],3),'workers':sorted(x['workers']),'stages':sorted(x['stages'])})
    workers=[]
    for (worker,gpu),x in ledger.items():
        workers.append({'worker':worker,'gpu':gpu,'cost_usd':round(x['cost_usd'],6),'worker_seconds':round(x['seconds'],3),'billable_rows':x['rows'],'distinct_jobs_seen':len(x['ids']),'stages':sorted(x['stages'])})
    result={'format':'gbr-compute-cost-v1','generated_at':datetime.now(timezone.utc).isoformat(),'source_rows':len(raw),'billable_rows':sum(v['billable_rows'] for v in workers),'currency':'USD','cost_basis':'pipeline-estimated-stage-costs','workers':sorted(workers,key=lambda v:-v['cost_usd']),'matched_generations':attached,'matched_count':len(attached),'unmatched_rows':len(unjoined),'ambiguous_rows':len(ambiguous),'skipped_rows':len(skipped),'audit':{'unmatched_examples':unjoined[:40],'ambiguous_examples':ambiguous[:40],'skipped_examples':skipped[:40],'headers':sorted(supported)},'warning':'Costs are pipeline telemetry estimates, not validated invoice charges. Unmatched costs are NOT allocated to rated records.'}
    if args.summary and pathlib.Path(args.summary).exists():
        sr=list(read_csv(args.summary))
        result['pipeline_summary']={'rows':sr[:250],'headers':sorted(set().union(*(x.keys() for x in sr))) if sr else []}
    out=pathlib.Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'[GBR cost] {len(raw)} timing rows, {len(attached)} matched reviewed generations, {len(unjoined)} unmatched billable rows; wrote {out}')
    if len(attached)==0:print('[GBR cost] WARNING: no verified cost/quality joins. Pod telemetry is available but cost-per-accepted is disabled.')

if __name__=='__main__':main()
