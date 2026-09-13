# Good Boy Records comparison matrix lab

This pack separates the problem into two parts:

1. `minimax_matrix_runner_v1.py` generates controlled MP3 comparison matrices from one selected MiniMax track YAML.
2. `gbr-matrix-lab.js` + `gbr-matrix-lab.css` render those matrices as an interactive browser patch bay.

`LLMExplanation_GBR_matrix_v1.json` is the supplied ComfyUI demonstration workflow with a new comparison-matrix explanation section. The normal workflow graph is left intact; the runner drives the equivalent API workflow externally.

## Output folders

The supplied CFG uses:

```text
port\good-boy-records\content-source\otheraudio
```

and produces:

```text
otheraudio/
  _comparison_manifest.json
  samp_sched/
    _matrix.json
    <anything>__euler_simple.mp3
    <anything>__dpmpp_2m_karras.mp3
    ...
  cfg_steps/
    _matrix.json
    <anything>__cfg-1p70_steps-33.mp3
    ...
  dit_textenc/
    _matrix.json
    <anything>__minimax_music3_dit_fp16_minimax_music3_text_encoder_bf16.mp3
    ...
  encoder_cfg_topk/
    _matrix.json
    ...
```

Everything before `__` is intentionally non-semantic for the website. The stable matrix identity is the suffix.

## Why the specialised runner exists

The normal multi-worker runner is intended for discovery and variation. It generates fresh seeds. That is exactly what a controlled comparison must *not* do.

The matrix runner instead:

- selects exactly one source track;
- prefers that YAML's recorded generation settings and seed pair when present;
- keeps prompt, lyrics, duration and seeds fixed;
- changes only the active experiment axes;
- creates a finite central job queue, so multiple RunPods share the matrix instead of duplicating it;
- skips already-generated output files on restart;
- validates worker capabilities before generation;
- writes manifests before generation so the website contract is known up front;
- exports MP3 at 320 kbps by default.

## Running

From the folder containing the runner and CFG:

```powershell
py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg
```

Select one source YAML when prompted. The runner prints the full matrix size before doing anything expensive and asks for confirmation.

Useful forms:

```powershell
# Show a plan only
py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg --experiment samp_sched --plan

# Run only sampler/scheduler, no confirmation
py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg --experiment samp_sched --yes

# Run the enabled matrices
py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg --experiment all --yes

# Force exact outputs to regenerate
py minimax_matrix_runner_v1.py --cfg minimax_matrix_runner.cfg --experiment cfg_steps --overwrite --yes
```

For sampler/scheduler, `*` means every choice advertised by ComfyUI's `KSampler` object info. For the DiT/text-encoder matrix, `*` is deliberately filtered to MiniMax Music 3 files rather than every unrelated model installed on the pod.

## Website integration

Include the stylesheet and module in the GBR page, add a mount element, then point the component at one generated `_matrix.json`.

```html
<link rel="stylesheet" href="/path/to/gbr-matrix-lab.css">
<div id="sampler-scheduler-lab"></div>
<script type="module">
  import { mountGBRMatrixLab } from '/path/to/gbr-matrix-lab.js';

  mountGBRMatrixLab(document.querySelector('#sampler-scheduler-lab'), {
    manifestUrl: '/content-source/otheraudio/samp_sched/_matrix.json',
    baseUrl: '/content-source/otheraudio/samp_sched/'
  });
</script>
```

If GBR's build process already enumerates the folder, pass a `files: [...]` array instead. The component resolves each cell with `endsWith('__' + suffix + '.mp3')`, so the rest of the song filename is ignored.

### Interaction

- Click a socket to insert the 2.5 mm-style jack.
- Arrow keys move through neighbouring cells.
- Space toggles playback while the matrix has focus.
- Moving to another cell while playing loads the new generation at the same timestamp and uses a short Web Audio gain crossfade.
- The jack movement synthesises a short mechanical/electrical click with Web Audio, so there is no separate sound asset to maintain.
- The graph updates with the selected cell. For sampler/scheduler it shows a deliberately labelled *normalised illustrative scheduler shape*, not a fake claim that the website has extracted MiniMax's internal sigma array.
- The vertical line on the sampler/scheduler graph follows current playback position.

## Exact scheduler curves

The current browser graph is explanatory. If you later want the literal sigma values used by ComfyUI, the generation workflow needs additional instrumentation to expose the calculated sigma tensor from the scheduler path. The existing `KSampler` API node does not return that tensor in prompt history, so pretending otherwise would make the educational demo worse, not better.
