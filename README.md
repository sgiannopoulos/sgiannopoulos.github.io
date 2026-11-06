# Sparks of Binary-Space Programming

A short blog post on whether an LLM can read and write executables byte by byte, modeled on
[Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/).

## Tech

The reference post lives in [RikiyaT.github.io](https://github.com/RikiyaT/RikiyaT.github.io), an academicpages site
(Jekyll, forked from minimal-mistakes) on GitHub Pages. The post itself bypasses the site's theme: it is a hand-written
`index.html` with `layout: null`, laid out by the [Distill template](https://distill.pub/template.v2.js), with its own CSS
and small JavaScript files. Jekyll only adds its masthead, citation block and metadata tags.

This repo uses the same post stack: hand-written HTML, the Distill template, Source Sans 3 and JetBrains Mono, served by
GitHub Pages. It leaves out Jekyll because there is only one page, and `.nojekyll` makes Pages serve the files as they are.

## Layout

| Path | What it is |
|---|---|
| `blog/machine-code-programming/index.html` | The post |
| `blog/machine-code-programming/css/style.css` | Styles over the Distill template |
| `blog/machine-code-programming/assets/wc391.bin` | The model's 391-byte `wc`, copied from the Exp 3 run |
| `blog/machine-code-programming/assets/wc391.js` | Figure 2's data, generated from that file |
| `blog/machine-code-programming/js/showcase.js` | The Understand / Extend / Create showcase at the top |
| `blog/machine-code-programming/js/hero.js` | Fills the title band with the 391 bytes |
| `blog/machine-code-programming/js/demos.js` | Figure 1, the before/after terminal GIFs |
| `blog/machine-code-programming/js/toc.js` | The contents list in the left margin, built from each `h2` that has an `id` |
| `blog/machine-code-programming/js/citation.js` | The copy buttons in the Citation section |
| `blog/machine-code-programming/assets/wordcount-*` | The original binary, Sol's Exp 1 report and Exp 2 patch, from the `d2a0e1f` runs |
| `blog/machine-code-programming/assets/showcase.js` | The showcase's data, generated from those files |
| `blog/machine-code-programming/js/runs.js` | The run viewers: each experiment's prompts, replies, bytes and tests |
| `blog/machine-code-programming/assets/runs/` | The viewers' data, copied from the logs repo and from Experiment 5's OpenCode session |
| `scripts/make_runs.py` | Regenerates `assets/runs/`, checking each prompt, patch, file and quoted number against the logs. `WITHHOLD_SAMPLE` controls the sample's hex dump and address |
| `scripts/make_showcase.py` | Regenerates `showcase.js`, checking every quote and highlighted byte against the sources |
| `blog/machine-code-programming/js/creations.js` | Figure 3: the three files Sol wrote, in the showcase's card, with a byte readout |
| `blog/machine-code-programming/assets/aes4144.bin`, `ledger3584.bin` | The other two files Sol wrote in Exp 3, from the `d2a0e1f` runs |
| `blog/machine-code-programming/assets/programmaps.js` | Their maps' data, generated from those files |
| `scripts/make_programmaps.py` | Regenerates `programmaps.js` with GNU objdump (run it in Docker), checking the disassembly and the AES tables |
| `scripts/make_bytemap.py` | Regenerates `wc391.js` by disassembling the binary. It never runs it |
| `index.html` | Redirects the site root to the post |

## Preview

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000/>.

## Publish

Push this repo to GitHub, then choose Settings > Pages > Deploy from a branch > `main`, folder `/ (root)`.

## Before publishing

The post is marked as a draft.

- [ ] Confirm the author's name, and add co-authors and affiliations.
- [ ] Decide how `prog4` is released. The logs contain the sample's address, which this post withholds.
- [ ] Confirm the `ministat` finding on real FreeBSD and file the report, then link it from footnote 1.
- [ ] Add a failing case, repeat attempts and an x86-64 run, then update the numbers and the caveats.
- [ ] Add names to the acknowledgements.
- [ ] Add an Open Graph image and canonical URL once the final address is known.

## Where the numbers come from

| Claim | Source |
|---|---|
| Tokens and times | `turns/t001/events.jsonl` and `run.json` in each run of the logs repo |
| Bytes changed | Each Exp 2 `patch.json` compared with `binaries/<prog>/original.bin` |
| Test scores | `results/exp{2,3}_prog{1,2,3}.json` in the local verification repo |
| Exp 1 key-fact counts | `ARTICLE_PLAN.md` in the logs repo. They are informal |
| GCC build sizes | `levels/<L>/private/after` in the verification repo |
| Context limits | `README.md` and `harness/model_catalog.json` in the logs repo. Tokens per byte come from the run logs |
| 13/13 API hashes | Recomputed from the function and module names, without running the sample |
