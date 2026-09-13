#!/usr/bin/env python3
"""Regression checks for the v10.4 GBR Parameter Lab integration."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent

def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

html = text("index.html")
template = text("templates/index.html")
lab_js = text("assets/js/gbr-matrix-lab.js")
lab_css = text("assets/css/gbr-matrix-lab.css")
workflow_js = text("assets/js/comfy-workflow.js")
docs = text("tools/build_docs.py")
workflow_media = text("tools/build_workflow_media.py")
runner = text("tools/matrix_lab/minimax_matrix_runner.py")
runner_cfg = text("tools/matrix_lab/minimax_matrix_runner.cfg")
bat = text("RUN-MATRIX-LAB.bat")
workflow = json.loads(text("assets/workflows/LLMExplanation.json"))

checks: list[tuple[str, bool]] = []
def check(name: str, ok) -> None:
    checks.append((name, bool(ok)))

check("Parameter Lab folder is built", 'data-folder="parameter-lab"' in html and '>Parameter Lab</span>' in html)
check("matrix suite directive renders", 'data-gbr-matrix-suite' in html and '_comparison_manifest.json' in html)
check("matrix CSS is loaded", 'assets/css/gbr-matrix-lab.css' in template and 'assets/css/gbr-matrix-lab.css' in html)
check("matrix ES module is loaded", 'type="module" src="assets/js/gbr-matrix-lab.js"' in html)
check("docs builder owns matrix-suite directive", '[matrix-suite]' in docs and 'data-gbr-matrix-suite' in docs)
check("suite exposes four experiment families", all(x in lab_js for x in ['samp_sched','cfg_steps','dit_textenc','encoder_cfg_topk']))
check("sampler scheduler UI uses sockets and plug", 'gbr-jack-socket' in lab_js and 'gbr-jack-plug' in lab_js)
check("jack click is generated locally", 'createOscillator' in lab_js and 'createBufferSource' in lab_js)
check("matrix switching preserves timestamp", 'currentTime' in lab_js and 'selectCell' in lab_js and 'newAudio.currentTime' in lab_js)
check("matrix switching crossfades", 'crossfade' in lab_js.lower() and 'gain' in lab_js)
check("keyboard matrix movement exists", all(k in lab_js for k in ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown']))
check("main deck and matrix do not play together", '#showcase-audio' in lab_js and 'showcaseAudio?.pause()' in lab_js)
check("missing root manifest has a useful empty state", 'NO MATRIX CUT YET' in lab_js and 'RUN-MATRIX-LAB.bat' in lab_js)
check("scheduler plot is labelled illustrative", 'normalised' in lab_js.lower() and 'illustrative' in lab_js.lower())
check("matrix runner supports explicit source/output overrides", '--tracks-root' in runner and '--output-root' in runner)
check("matrix runner fixes comparison seeds", 'actual_seed = baseline.seed' in runner and 'encoder_seed=seed.encoder_seed' in runner and 'sampler_seed=seed.sampler_seed' in runner)
check("matrix runner writes root manifest", '_comparison_manifest.json' in runner)
check("matrix runner supports all four experiment families", all(x in runner for x in ['samp_sched','cfg_steps','dit_textenc','encoder_cfg_topk']))
check("matrix output defaults to GBR content-source", r'..\..\content-source\otheraudio' in runner_cfg)
check("Windows launcher writes matrices into this repo", 'content-source\\otheraudio' in bat and '--output-root' in bat)
check("workflow audio folder is mirrored to public runtime", 'content-source" / "otheraudio' in workflow_media and 'assets" / "workflow-media' in workflow_media)
check("latest workflow includes GBR comparison explanation", all(any(n.get('title') == title for n in workflow.get('nodes', [])) for title in ['GBR Controlled Comparisons','Sampler × Scheduler','CFG × Steps','DiT × Text Encoder','The Website Patch Bay']))
check("latest workflow optional source media is explicit", len(workflow.get('gbr_optional_media') or []) == 8)
check("optional workflow media is warning-only", 'optional demonstration media' in workflow_media and 'report.warn' in workflow_media)
check("unbundled workflow media gets visible browser fallback", 'Example media is not bundled in this site package.' in workflow_js)
check("matrix UI has responsive rules", '@media' in lab_css and 'gbr-matrix-suite' in lab_css)

for name, ok in checks:
    print(("  PASS  " if ok else "  FAIL  ") + name)
passed = sum(ok for _, ok in checks)
print(("ALL PASS" if passed == len(checks) else "FAILURES PRESENT") + f" ({passed}/{len(checks)})")
sys.exit(0 if passed == len(checks) else 1)
