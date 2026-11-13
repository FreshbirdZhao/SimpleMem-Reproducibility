# Preregistered retrieval-depth experiment

Protocol frozen on 8 November 2026 before inspecting the formal outcomes.
The experiment is `runs/experiment-20261108-153818-44119`.

## Target and modification

Reproduce the released SimpleMem text pipeline's ability to answer questions
from long conversational memory with hybrid retrieval and reflection. Assess
the quality/latency tradeoff when semantic retrieval depth is reduced.

The baseline is the checked-out repository's semantic top-k 25; the modified
condition uses top-k 10. Both retain keyword top-k 5, structured top-k 5,
planning, and at most two reflection rounds. This is a repository-default
baseline, not an exact replication of the paper's Table 1 configuration.
No prompts or scoring rules differ between conditions.

## Dataset and randomization

LoCoMo repository: https://github.com/snap-research/locomo

Verified commit: `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

File: `data/locomo10.json`; SHA-256:
`79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.

Sample index 0; preserve all 419 dialogue turns. Use Python's
`random.Random(5660).sample` to select 20 QA indices before formal runs:
1, 9, 23, 24, 28, 48, 52, 54, 65, 74, 78, 91, 99, 114, 132, 139, 149, 153, 157, 176.

Category counts: multi-hop (1): 6; temporal (2): 5; open-domain (3): 0;
single-hop (4): 6; adversarial (5): 3. Pilot indices 1 and 91 overlap with this
predefined selection. No questions were selected according to pilot outcomes.

Run seeds 5660, 5661, and 5662. For each seed, build memory once, evaluate the
baseline, then copy the completed database and evaluate the modified condition.
Check byte-level directory digests before evaluation. Neither question-answering
condition intentionally writes new conversational memories. Rebuilding between
seeds captures memory-generation variability; identical memory within each pair
controls that variability in the paired comparison. Provider randomness and
load remain uncontrolled. Baseline-first order is fixed, not counterbalanced.

## Model and execution

The same `.env` configuration is used in every condition; secrets are never
part of the experiment evidence. Provider: DeepSeek; base URL:
`https://api.deepseek.com/v1`; requested model: `deepseek-chat`. A preflight call
returned model identifier `deepseek-flash`; mapping is not observed per request
because the upstream client returns only message content. Alias stability is
therefore a limitation. Embeddings: `Qwen/Qwen3-Embedding-0.6B`, 1024 dimensions.

macOS arm64, Python 3.11.16; all resolved versions are in `dependencies.txt`.
LanceDB is pinned to 0.25.3 with `pylance` support for upstream Tantivy FTS.
Memory construction and retrieval are sequential, unlike upstream parallel
defaults. WINDOW_SIZE=40 and OVERLAP_SIZE=2 are unchanged repository defaults.

Actual call-site temperatures: memory extraction/synthesis 0.1; normal answers
0.1; adversarial answers 0.5; retrieval routines use 0.1, 0.2, or 0.3 depending
on the prompt. The client default is 0.2. `top_p`, `max_tokens`, and provider
seed are not sent, so provider defaults apply; settings named MAX_TOKENS and
TEMPERATURE must not be reported as if sent to the API. Streaming and API JSON
response mode are off. Prompts still request JSON. ENABLE_THINKING=False does
not send an explicit DeepSeek thinking parameter; provider behavior is not
independently controlled. No LLM judge is enabled.

## Metrics and aggregation

Primary quality outcome: original evaluator mean F1 over all 20 questions.
The scorer lowercases, replaces period/comma/exclamation/question mark with
spaces, splits on whitespace, and takes sets of tokens. It computes the
harmonic mean of precision and recall on these sets. Repetition has no weight;
extra explanatory words can lower F1.

Primary efficiency outcomes: mean unique retrieved memory count, mean retrieval
seconds, and mean answer-generation seconds. Retrieval includes planning and
reflection API calls. Timing excludes memory construction and metric scoring.
Top-k is per semantic search, not a bound on final merged context count.

Secondary quality outcome: mean F1 excluding the three adversarial questions,
reported alongside the original overall metric, not substituted for it.
Adversarial questions use the upstream two-option prompt with the supplied
distractor and abstention answer; reflection is disabled for this category.
Report categories separately, with no estimate for the absent category 3.

Compute one aggregate per seed and condition, then the mean and sample variance
(denominator n-1) across three seeds. Also compute modified-minus-baseline
paired differences for each seed. Do not treat the 60 responses per condition
as 60 independent experiments. No significance or generalization claim from
three seeds on one conversation. Do not infer token savings or monetary costs.

## Paper reference and comparison limits

Source: https://arxiv.org/pdf/2601.02553, downloaded 8 November 2026.
PDF SHA-256: `8752aa223e004ca286995bc1e8cbde8e89e67ad3aeb9ba0266f3ccab3cc11078`.

Table 1 reports SimpleMem GPT-4.1-mini Average F1 43.24 (0.4324 scale),
with category values 43.46, 58.62, 19.76, and 51.12. Appendix B.3/Table 6
reports F1 35.20, 42.85, 43.24, 43.45, and 43.40 for k=1,3,5,10,20.
This motivates examining retrieval sensitivity, but our per-semantic-search
parameter under hybrid planning is not guaranteed to match that table's k.
Table 7 specifies window 20, stride 5, and temperature 0.0; these differ from
the current code. The paper's Table 1 excludes an adversarial column, whereas
the current evaluator's overall mean includes category 5. Its four category
values average to the reported 43.24; our mean is question-weighted with
different category frequencies. Model, sample, category composition, averaging,
retrieval semantics, dependency versions, and concurrency differ. Report
reference numbers as context, never as a directly comparable superiority test.

## Discovered limitations retained for reproducibility

The upstream local backend builds a Tantivy index after the first insertion and
then skips subsequent index creation. A separate two-row smoke check confirmed
that appending a new row does not make its unique word searchable. Thus the
keyword index can cover only the first memory batch. This inherited behavior
is preserved identically in both conditions; it limits full hybrid retrieval
faithfulness. Future work should rebuild the index after finalization and rerun
both conditions as a separate experiment. This experiment does not silently
mix corrected and uncorrected retrieval paths.

The evaluator retains its dialogue/session ordering and image-evidence handling.
This is the text pipeline, not a multimodal replication. NLTK's redundant online
resource checks are rejected by the proxy's synthetic IP, but installed punkt,
punkt_tab, and wordnet resources work. Metric failures, failed API fallbacks,
and missing predictions must be inspected before interpreting results.

## Compatibility changes and checks

The evaluator's legacy `import config` paths now read unified runtime settings.
Without this fix, category 5 silently abstains after missing-config failures,
artificially improving its score. Both conditions receive this fix. No metric
formula changes. Optional memory reuse defaults to off and rejects empty memory
or multiple conversations. Six focused checks cover copy digests, ingestion
skip, preserved defaults, rejection guards, and category-5 model invocation.

The run directory retains dependency versions, exact subset, source snapshot,
all six logs, manifests, and raw predictions. Databases and dataset are local
evidence, not publication artifacts. Scan publication files for secrets.
