# FTEC5660 SimpleMem reproduction

## Submission links

- Student: **ZHAO GUODONG / 1155263139**.
- [Final report (8 pages)](../report.pdf), within the assignment's 10-page limit. An identical copy is retained at [submission/report.pdf](submission/report.pdf).
- [GitHub repository](https://github.com/FreshbirdZhao/SimpleMem-Reproducibility), with installation/run instructions and incremental commits.
- [Recorded Zoom presentation](https://us06web.zoom.us/clips/share/n_A3LQLlSWecG5G8tEjOLA). The assignment requires a recording of at most 15 minutes; the viewer must be able to open the shared link.

The assignment allows a meaningful subset, a documented model substitution,
and a retrieval-k modification. This study reproduces the released text
pipeline's memory-based question-answering behavior and measures the effect of
changing semantic top-k. It does not claim to reproduce the exact published F1.

## Status

The two-question pilot completed successfully on 2026-11-08. Inspection on
2026-11-13 verified the original pairs for seeds 5660 and 5661 (80 predictions).
The original baseline-5662 manifest says completed but its log contains API
failures and fallback answers; modified-5662 has no results. Neither belongs in
the valid comparison. Preserve the original experiment as failure evidence.
The complete third pair was successfully rerun in
`runs/recovered-20261113-060600-75832`, retaining the first two valid pairs.
All six runs and 120 predictions pass independent evidence validation.
The final report is `../report.pdf`; final statistics are in `analysis/`.
The presentation is supplied through the Zoom link above. Slide files and
document-generation scripts are not included in the current checkout.
Mean F1 changes from 0.624330 to 0.649385; retrieved entries from 45.0333 to
23.4500; combined retrieval/answer seconds from 8.6164 to 9.0839. F1 improves
in two of three trials and falls in the third; no consistent gain is established.
See `PROTOCOL.md` for the fixed design. Completion requires both clean logs and
the aggregation/independent-evidence checks, not merely completed manifests.

Student: **ZHAO GUODONG / 1155263139**. Published at https://github.com/FreshbirdZhao/SimpleMem-Reproducibility; the upstream project is kept as the `upstream` remote, and this study is committed in reviewable steps.

## Recovery and validation (13 November)

The recovery preserves original artifacts and refuses changed execution-source
hashes. It builds fresh memory for seed 5662 and reuses it within that pair.
Hosted-model date drift across seeds must be disclosed. Hugging Face models run
from cache; `run_cached.py` verifies installed NLTK resources before skipping
redundant download checks. API calls remain online and billable.

`recover_experiment.py` is retained as historical recovery source. Its final
step still references the removed `build_submission.py`; it is not a supported
end-to-end command in this checkout. To run a new experiment, use
`start_experiment.sh` as described below.

On the original machine, where all six local memory databases are retained,
the following independent evidence check passes:

```bash
.venv/bin/python reproduction/validate_evidence.py reproduction/runs/recovered-20261113-060600-75832
```

This independently recomputes token-set F1 and timing aggregates and verifies
the current memory files against their saved checksums. A fresh Git clone does
not contain these databases, so use the saved-results aggregation command
below for verification without rerunning the model. The default analysis
requires all three planned seeds; `--seeds 5660 5661` is explicitly a partial
analysis and does not meet the planned trial count.
The initial debug diary below is historical, not current setup status.

Scope: the original text SimpleMem pipeline and its LoCoMo evaluator, not
Omni-SimpleMem or EvolveMem. Starting commit: db80b6a7c591e0ea730a058e9f5fc4eb06572299.

## Evidence in this repository

`reproduction/runs/` is versioned: manifests, `results.json` predictions,
console logs, subset selection, dependency freezes and the execution-source
snapshot for the pilots, the original experiment, both recovery attempts and
the six analysed runs. LanceDB `memory/` directories and derived
`analysis/`/`submission/` copies inside run folders stay local; `.env` and the
downloaded LoCoMo file are never committed.

## Research question

On a fixed LoCoMo question subset, how does reducing semantic retrieval top-k
from 25 to 10 affect the upstream evaluator's answer F1, retrieved memory count,
and retrieval/answer latency? Keyword and structured retrieval remain at their
configured values. Top-k is per semantic search, not a cap on total retrieved
memories: planning, reflection, and other retrieval paths may add more entries.

Both conditions disable parallel memory construction and parallel retrieval to
reduce scheduling variability. Disclose this deviation from upstream defaults.
Each seed builds memory once in the baseline run. The modified run copies that
completed database, verifies its checksum, and skips ingestion and clearing.
Both conditions therefore use identical stored memory within a seed. Use the
same three seeds (5660, 5661, 5662) for both conditions.
Local seeds do not control randomness at the hosted model provider.

## Setup

Run commands from the repository root. Python >=3.10 is required. Example with uv:

```bash
uv venv --python 3.11
uv pip install --python .venv/bin/python -e '.[benchmark]' -r reproduction/requirements.txt
```

This installs upstream's unified package, including multimodal dependencies.
The reproduction requirements pin LanceDB to 0.25.3 with its `pylance` extra:
LanceDB 0.41.0 removed the Tantivy FTS interface used by the upstream local
backend. Without this pin, index creation fails and keyword retrieval is lost.
Network access is also required for model weights and NLTK resources.
Configure OPENAI_API_KEY, OPENAI_BASE_URL, and LLM_MODEL in local environment
variables, or copy config.py.example to the ignored config.py and edit locally.
The reproduction runner automatically loads the repository-root .env before
initializing SimpleMem. Existing process environment variables take priority
over .env, and config.py takes priority over both. Never commit secrets.

For DeepSeek, copy the credential-free template and fill in your own key:

```bash
cp reproduction/deepseek.env.example .env
```

If `.env` already exists, edit it instead of overwriting it. Set OPENAI_API_KEY
to your DeepSeek API key. The variable retains its upstream name because the client
uses an OpenAI-compatible interface; it does not require an OpenAI key.
The initial model selection is deepseek-chat at https://api.deepseek.com/v1;
confirm availability with a pilot before the benchmark. Embeddings use the
local Qwen model, which must be downloaded separately from the LLM service.
The credential-free template is reproduction/deepseek.env.example. Directly
running test_locomo10.py does not load .env; use reproduction/run.py instead.

Obtain the dataset at the revision used in this study:

```bash
curl -fL https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json -o test_ref/locomo10.json
shasum -a 256 test_ref/locomo10.json
```

Expected SHA-256:
`79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.

## Prepare and run

To install dependencies, download the dataset if missing, and run a two-question
pilot from a terminal with network access:

```bash
bash reproduction/start_pilot.sh
```

This makes billable calls using the configured API. It processes the full first
conversation even though it evaluates only two questions. Logs, dependency
versions, the subset, and results are saved under a unique reproduction/runs/
directory. A failed pilot is not a measured benchmark result. Inspect successful
pilot outputs and API expenditure before launching the repeated experiments.

```bash
.venv/bin/python reproduction/run.py prepare --dataset test_ref/locomo10.json --output reproduction/local-subset --questions 20
.venv/bin/python reproduction/run.py run --dataset reproduction/local-subset/subset.json --output reproduction/runs/baseline-5660 --top-k 25 --seed 5660
.venv/bin/python reproduction/run.py run --dataset reproduction/local-subset/subset.json --output reproduction/runs/modified-5660 --top-k 10 --seed 5660 --memory-source reproduction/runs/baseline-5660
```

Start with a separate 2-question subset to check functionality and expenditure.
Even two questions require processing the selected full conversation. Confirm
provider, model, and budget before launching measured API runs. After the pilot,
freeze the question selection before examining final outcomes. The default
selection is 20 randomly selected questions from conversation index 0; it is a
small case study and cannot establish full-benchmark performance.

Repeat both conditions with seeds 5661 and 5662, each using a new output folder.
Each run creates an isolated database, manifest, and original evaluator output.
Existing output folders are refused to prevent overwriting previous evidence.

Run the complete fixed 20-question, three-seed paired experiment with:

```bash
UV_CACHE_DIR=/tmp/simplemem-uv-cache bash reproduction/start_experiment.sh
```

This makes six sequential evaluations (120 question predictions) and three
full-conversation memory builds. Each seed runs baseline before modified; this
fixed order is a limitation for latency comparisons because provider caching
and load can differ. The selection is fixed before results are inspected and
includes the two pilot questions; report that overlap. No question selection is
based on pilot correctness. The sample has categories 1, 2, 4, and 5, but not 3.

The evaluator's optional `--reuse-memory` flag preserves the original default
behavior, and permits only a single conversation with a nonempty database. The
runner also checks source status, seed, dataset hash, settings, and copied file
checksums. The evaluator now uses the unified runtime settings in four legacy
`import config` call sites. This prevents category-5 questions from silently
falling back to the correct abstention answer when only `.env` is configured.
Both conditions use this identical compatibility fix; the metric is unchanged.

## Verify saved results without API calls

From the repository root, aggregate the six retained valid runs with Python
3.10 or newer. This uses only the standard library; API credentials, model
downloads, and local memory databases are not required. Use a new output
directory each time because the summarizer refuses to overwrite existing files:

```bash
verification_root=$(mktemp -d)
python3 reproduction/summarize.py reproduction/runs/recovered-20261113-060600-75832 --output "$verification_root/analysis"
```

This refuses incomplete runs, mismatched settings/subsets/memory pairs, and
known retrieval/evaluation error messages. Memory pairing here is checked
against the recorded manifest hashes, not against absent database files.
It produces per-trial, per-question, and per-category CSVs plus a summary
containing means and sample variances. The committed reference outputs are in
`reproduction/analysis/`. The original `experiment-20261108-153818-44119`
contains the failed third pair and must not be used for the final three-trial
comparison.

For a newly completed experiment, replace the input directory with the one
printed by `start_experiment.sh`. That script retains the logs needed by the
summarizer; the individual `run.py` examples alone do not capture those logs.

After installing the benchmark dependencies, run the six targeted tests with:

```bash
.venv/bin/python -m unittest reproduction.test_paired_memory -v
```

These tests use mocked LLM calls. Importing the evaluator loads the MiniLM
metric model; with its weights already cached, prefix the command with
`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` to avoid model-download checks.

## Interpretation of the final results

Across three paired trials, reducing semantic top-k from 25 to 10 changes:

- Mean F1: 0.624330 to 0.649385 (paired mean difference +0.025055).
- Mean merged memory entries per question: 45.0333 to 23.4500.
- Mean retrieval-plus-answer latency: 8.6164 to 9.0839 seconds per question.

Sample variances across trials are reported in the report and `analysis/summary.json`.
F1 improves in two trials and decreases in one; smaller retrieved context does
not establish lower latency, token usage, or monetary cost. The study covers
one conversation and 20 questions, omits category 3, uses a different hosted
model from the paper, and always runs baseline first. The third pair was rerun
on a later date. An inherited keyword-index refresh limitation affects both
conditions. These constraints limit generalization and direct comparison with
the paper's score; see report Sections 5 and 6 for details.

## Interpretation and deliverables

- Preserve question IDs via selection.json; retain raw predictions and failures.
- For each condition calculate one aggregate metric per trial, then report the
  mean and sample variance across three trials. Per-question variability in the
  upstream summary is not the variance across trials.
- Inspect the actual F1 definition and category handling before comparing with
  the paper. Do not substitute another evaluator silently.
- Record model/provider/base URL (without credentials), actual decoding
  parameters at call sites, embedding model, hardware, dependency versions,
  data version, prompt changes, and all setup changes.
- Verify the specific original paper table and model configuration before
  quoting a reference number. A changed model or subset limits comparability.
- The upstream evaluator disables token counting; do not claim measured token
  savings or dollar costs without collecting provider usage.
- Results JSON is ignored by the upstream .gitignore. Review selected outputs
  for secrets and dataset redistribution constraints before deliberately adding
  appropriate evidence to the submission. Do not commit memory databases.
- Required final package: report <=10 pages, GitHub link with setup/run steps
  and reviewable commits, and a recorded Zoom presentation <=15 minutes.

## Historical debug diary: initial setup

The following entries describe earlier attempts and their resolution, not
missing prerequisites in the completed experiment.

- Repository is now inside the writable workspace.
- System python3 is 3.9.6, below the package's >=3.10 requirement.
- Found uv-managed Python 3.11.16 and created the local .venv successfully.
- Dependency installation failed because pypi.org could not be resolved. When
  uv's default cache is not writable, use UV_CACHE_DIR=/tmp/simplemem-uv-cache.
- Dataset and core dependencies were absent during initial inspection.
- GitHub raw content DNS resolution failed in the execution environment.
- At initial inspection, model credentials, provider, and budget had not yet
  been supplied.

## Pilot attempt (2026-11-08)

- Confirmed Python 3.11.16 and a nonempty, non-placeholder API key in `.env`
  without printing the key. API authentication has not been verified.
- DNS lookup failed for pypi.org, raw.githubusercontent.com, and
  api.deepseek.com in the execution environment.
- Core dependencies (`python-dotenv`, `openai`, `torch`, `transformers`,
  `lancedb`, `numpy`, and `nltk`) and `test_ref/locomo10.json` remain absent.
- Attempted `UV_CACHE_DIR=/tmp/simplemem-uv-cache bash reproduction/start_pilot.sh`.
  It exited with code 2 during dependency installation: fetching
  `setuptools>=40.8.0` from PyPI failed after three retries due to DNS resolution.
- The two-question evaluation did not start. No API calls, predictions, or
  benchmark measurements were produced. Retry the same command from the
  repository root in a terminal with working network access.

## Network retry and compatibility checks (2026-11-08)

- After switching the network proxy, Hugging Face returned HTTP 200 and the
  MiniLM and Qwen3 embedding models loaded successfully.
- A minimal authenticated `deepseek-chat` request returned HTTP 200 with response
  model `deepseek-flash`. The models endpoint lists `deepseek-flash` and
  `deepseek-v4-pro`; `deepseek-chat` still works as an alias. Record this mapping
  when interpreting the experiment; the alias may change over time.
- The local LoCoMo file contains 10 conversations and exactly matches the
  upstream main-branch file downloaded during validation. SHA-256:
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
  The upstream main ref observed via Git was
  `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`; the file fetched from this exact
  commit also matched the local file byte for byte.
- The two-question subset uses sample 0, zero-based QA indices 1 and 91, seed
  5660, and all 419 conversation turns.
- Earlier stalled processes were interrupted before restarting. The attempt in
  `reproduction/runs/pilot-20261108-151805-42530` was interrupted after discovering
  the LanceDB FTS incompatibility; it made API calls but is not a valid result.
- LanceDB 0.25.3 plus `pylance` passed an isolated Tantivy index creation and
  keyword search smoke check. No retrieval implementation was changed.
- NLTK's download check rejected the proxy's synthetic IP, but existing local
  `punkt`, `punkt_tab`, and `wordnet` resources were present and word tokenization
  passed. Preserve any evaluation errors in the pilot log.
- The corrected attempt is
  `reproduction/runs/pilot-20261108-152317-42936`; its manifest, dependency freeze,
  subset selection, and console log are the primary execution records.

## Completed two-question pilot

The corrected attempt exited with code 0 and its manifest status is `completed`.
Raw predictions and evaluator metrics are in
`reproduction/runs/pilot-20261108-152317-42936/baseline/results.json`.
`preflight.json` records the verified dataset revision, provider alias mapping,
hardware platform, and compatibility checks without credentials.

- Configuration: semantic top-k 25, seed 5660, Qwen3-Embedding-0.6B (1024
  dimensions), sequential construction and retrieval, no LLM-as-judge.
- Full conversation memory construction: 266.11 seconds. Keyword retrieval
  returned 5 entries for each question; no FTS failures occurred in this run.
- Question index 1: answer `In 2022`, reference `2022`; F1 0.6667, 35 retrieved
  entries, retrieval 7.272 seconds, answer generation 1.224 seconds.
- Question index 91: answer `Love, faith, and strength; reminds her of her roots
  and family support`, reference `love, faith, and strength`; F1 0.4286, 40
  retrieved entries, retrieval 8.853 seconds, answer generation 1.107 seconds.
- Mean F1: 0.5476; mean ROUGE-L: 0.5833; mean BERTScore F1: 0.9236.
  Mean retrieval latency: 8.062 seconds; mean answer latency: 1.166 seconds.
  These timings exclude metric evaluation and memory construction.

Upstream F1 uses sets of lowercased tokens, replacing only `.`, `,`, `!`, and
`?` before whitespace splitting. Extra words therefore lower F1 even when the
answer contains the reference. The evaluator's reported standard deviation is
across these two questions, not across repeated trials. This pilot validates
execution only; it does not establish benchmark quality or a top-k effect.
Provider usage and total expenditure were not measured. Interrupted attempts
also made API calls. At pilot completion no formal repeated-condition runs had
been launched; the subsequent experiment is tracked in the status section.
