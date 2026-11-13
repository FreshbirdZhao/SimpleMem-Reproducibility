# SimpleMem reproduction: retrieval-depth tradeoff

ZHAO GUODONG | 1155263139 | FTEC5660 - 13 November 2026

## 1. Project, target, and measured outcome

SimpleMem is an agentic memory system that converts conversation windows into structured memory entries, plans semantic searches, combines semantic, keyword, and metadata retrieval, and reflects on whether the retrieved evidence is sufficient before answering. This project reproduces the released text pipeline on a small LoCoMo subset, then isolates a retrieval-depth modification.

The target behavior is answering questions from a complete long conversation using compressed memory. The reference quantitative target is SimpleMem's LoCoMo F1, with Table 1 and the retrieval-sensitivity study in Appendix B.3/Table 6 used for context. This is a partial reproduction under a different model, not an exact replication of the paper's headline number.

Reducing semantic top-k from 25 to 10 changed mean answer F1 from 0.6243 to 0.6494 (paired difference +0.0251, or +2.51 percentage points). Mean retrieved context changed by -21.58 entries per question and retrieval-plus-answer latency changed by +0.467 seconds per question. These are descriptive results for one conversation and 3 hosted-model trials, not evidence of a general improvement.

The assignment explicitly accepts retrieval-k parameter changes. Our single experimental change is SEMANTIC_TOP_K=25 to 10. Both conditions retain the same prompts, evaluator, keyword/structured retrieval settings, planning and reflection. Environment compatibility fixes apply equally to both.

## 2. Environment and reproducible setup

Repository: https://github.com/aiming-lab/SimpleMem; starting commit db80b6a7c591e0ea730a058e9f5fc4eb06572299. Platform: macOS arm64, Python 3.11.16. The run includes a complete dependency freeze and source snapshot. LanceDB 0.25.3 with pylance supports the upstream Tantivy index; 0.41.0 had removed that interface.

LLM provider: DeepSeek; base URL https://api.deepseek.com/v1; requested model deepseek-chat. A preflight response identified deepseek-flash. The upstream client discards response metadata, so this alias mapping is verified only at preflight, not at every experimental request. Local .env provides authentication and is ignored by Git. No credentials appear in the submission.

Embedding model: Qwen/Qwen3-Embedding-0.6B, 1024 dimensions. Metric models: all-MiniLM-L6-v2 and roberta-large through the upstream evaluator. Memory construction and retrieval run sequentially. Window size is 40, overlap 2, keyword top-k 5, structured top-k 5, and maximum reflection rounds 2.

Actual call-site temperatures: memory construction 0.1; normal answers 0.1; adversarial answers 0.5; retrieval routines 0.1, 0.2, or 0.3 depending on the prompt. top_p, max_tokens, and provider seed are omitted and therefore provider-controlled. Streaming and API JSON mode are disabled. The local thinking flag does not explicitly configure DeepSeek thinking behavior. No prompt templates were changed and no LLM judge was enabled.

Run from repository root: bash reproduction/start_experiment.sh. It freezes the subset, runs three paired trials, and saves logs, manifests, predictions, and dependency versions. Reproduction README contains setup, individual commands, and troubleshooting details.

## 3. Dataset, control, and metric definitions

Dataset: snap-research/locomo, data/locomo10.json at commit 3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376. Its SHA-256 is 79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4. The pinned upstream file matches the local file byte for byte.

The complete first conversation contains 419 turns. Twenty QA indices were selected using random.Random(5660).sample before formal outcomes: 1, 9, 23, 24, 28, 48, 52, 54, 65, 74, 78, 91, 99, 114, 132, 139, 149, 153, 157, 176. There are 6 multi-hop, 5 temporal, 6 single-hop, and 3 adversarial questions, with no open-domain questions. Two pilot questions overlap; selection did not depend on pilot correctness. This is a case study, not a representative benchmark sample.

For each analyzed seed (5660, 5661, 5662), baseline memory is built once and then copied for the modified condition. Directory checksums verify identical initial stored memory. Dataset, seed, and all settings other than semantic k are checked. The modified evaluation skips clearing and ingestion. Memory is rebuilt across seeds; local seeding cannot make hosted generation deterministic.

Primary F1 is the upstream scorer: lowercased text, limited punctuation replacement, and sets of whitespace tokens. F1 is the harmonic mean of token-set precision and recall. Extra explanation can reduce F1 despite containing the answer. Overall F1 includes adversarial questions, which use a two-option prompt and no reflection. We separately report F1 on the 17 non-adversarial questions.

Efficiency metrics are unique merged memory count and retrieval/answer seconds per question. Retrieval includes planning and reflection calls; timings exclude metric evaluation and memory construction. Semantic k applies to each semantic search, not the final context size. For each condition compute per-seed aggregates, then mean and sample variance with denominator n-1. The 3 paired differences, not individual questions treated as independent trials, measure variability.

## 4. Modification experiment results

Reducing semantic top-k from 25 to 10 changed mean answer F1 from 0.6243 to 0.6494 (paired difference +0.0251, or +2.51 percentage points). Mean retrieved context changed by -21.58 entries per question and retrieval-plus-answer latency changed by +0.467 seconds per question. These are descriptive results for one conversation and 3 hosted-model trials, not evidence of a general improvement.

F1 increased in 2 of 3 paired trials. Per-seed differences range from -0.0166 to +0.0569; the direction is not consistent across trials. The observed mean should not be treated as a guaranteed quality gain.

All values below are computed from retained raw predictions. The variance is across the 3 per-seed aggregate values, not the upstream summary's across-question variance. Latency includes hosted-provider load and caching effects; baseline always ran first within a seed.

A smaller context is not itself evidence of lower end-to-end cost or latency. Query planning and reflection also call the hosted model. Provider load, cache behavior, and generated queries can therefore affect timing independently of the final number of retrieved entries. No token or monetary savings can be calculated from memory counts alone.

- F1 (all 20): k=25 mean 0.6243, sample variance 2.104e-06; k=10 mean 0.6494, sample variance 0.0014.
- F1 (17 non-adv.): k=25 mean 0.5580, sample variance 2.912e-06; k=10 mean 0.5875, sample variance 0.0020.
- Memory entries: k=25 mean 45.0333, sample variance 3.2433; k=10 mean 23.4500, sample variance 0.7275.
- Retrieval (s): k=25 mean 7.4300, sample variance 0.1834; k=10 mean 7.9531, sample variance 1.3491.
- Answer (s): k=25 mean 1.1864, sample variance 0.0032; k=10 mean 1.1308, sample variance 0.0010.
- Combined (s): k=25 mean 8.6164, sample variance 0.2336; k=10 mean 9.0839, sample variance 1.3765.

## Paired and category details

- 5660; 0.6259; 0.6608; 0.0349
- 5661; 0.6231; 0.6799; 0.0569
- 5662; 0.6240; 0.6074; -0.0166
- F1 (all 20); 0.0251; 0.0014
- F1 (17 non-adv.); 0.0295; 0.0020
- Memory entries; -21.5833; 1.8808
- Retrieval (s); 0.5231; 0.6639
- Answer (s); -0.0556; 0.0022
- Combined (s); 0.4675; 0.5904
- Multi-hop; 6; 0.3259; 0.3474
- Temporal; 5; 0.6686; 0.7300
- Single-hop; 6; 0.6980; 0.7089
- Adversarial; 3; 1.0000; 1.0000

## 5. Comparison with reported results

The downloaded SimpleMem paper (arXiv:2601.02553, accessed 8 November 2026) reports Table 1 GPT-4.1-mini Average F1=43.24, with multi-hop 43.46, temporal 58.62, open-domain 19.76, and single-hop 51.12. These four category numbers average to approximately 43.24. Our evaluator uses a question-weighted mean and includes category 5; the aggregation and category mix differ.

Appendix B.3/Table 6 reports F1 35.20, 42.85, 43.24, 43.45, and 43.40 at k=1,3,5,10,20. This motivates testing lower retrieval depth, but its retrieved-entry k is not guaranteed to match our per-semantic-search setting under hybrid query planning. The repository default k=25 is outside that table's tested range. Our result therefore is a new local sensitivity experiment.

Paper Table 7 specifies window size 20, stride 5, GPT-4.1-mini temperature 0.0, and LanceDB 0.4.5. Current repository defaults and available dependencies differ. We retain the current pipeline and document these differences instead of claiming to recreate the exact published configuration.

Our baseline mean F1 is 62.43/100 and modified mean is 64.94/100. These values must not be interpreted as beating or failing the paper's 43.24 because model, sample, categories, averaging, and implementation differ. The separate non-adversarial means reduce one mismatch but do not establish comparability.

Paper Table 4 reports 92.6 seconds construction and 388.3 seconds retrieval as per-sample averages, not per-question timings. Our timing units, workload, concurrency, hardware, and model differ. The paper's roughly 30-fold token reduction is not tested: upstream disables token counting and total API usage/cost was not measured.

## 6. Debug diary and threats to validity

Initial blockers: sandbox DNS failures, missing dependencies/data, and Hugging Face timeouts. An authorized network execution and a changed proxy allowed downloads and API calls. Python 3.11 replaced the unsupported system Python 3.9. Model caches and NLTK resources were validated. NLTK's redundant online checks reject synthetic proxy IPs, but local scoring resources work.

LanceDB 0.41.0 removed Tantivy FTS. Pinning 0.25.3 with pylance restored index creation and keyword searches; an isolated smoke check verified a matching document is returned. An earlier pilot with broken FTS was interrupted and excluded. Those attempts incurred unmeasured API usage.

The evaluator still imported a legacy config module in special paths. With only .env present, category-5 generation could fail and return the correct abstention by default. We changed these imports to unified runtime settings in both conditions, without changing metric or prompt logic. A targeted test verifies an actual model invocation without a local config module.

An inherited limitation remains: the local backend initializes its Tantivy index after the first insertion and does not rebuild after subsequent inserts. A two-row experiment confirmed that a later unique word is absent from keyword results. Both conditions preserve this behavior, so the k comparison is controlled but full keyword-retrieval faithfulness is limited. Rebuilding the index after ingestion should be a separately evaluated future fix.

Other limits: one conversation, 20 questions, only 3 analyzed seeds, missing category 3, pilot overlap, non-deterministic hosted model, mutable model alias, fixed condition order, inherited session ordering and image-evidence handling, and model/dependency drift from the paper. Raw predictions and failures are preserved. No statistical significance or broad population claim is warranted.

Recovery on 13 November 2026: original seed 5662 baseline contained API connection failures, fallback answers, and metric errors; its modified run never saved results. Both original runs were excluded on execution-validity grounds. Seeds 5660 and 5661 retain their original 8 November outputs. The entire third pair was rerun with a fresh baseline memory build, unchanged execution source, and cached models in Hugging Face offline mode. This prevents redundant model-download checks; run_cached.py checks installed NLTK resources and skips their redundant network download check. DeepSeek API calls remain online. recovery.json preserves the provenance. The later execution date introduces possible provider/model-alias drift across seeds, even though each pair shares its configuration and stored memory. recovery-environment.json records rerun package versions and the additional report-dependency import path; the original dependency freeze is retained separately.

## 7. Conclusions, artifacts, and references

Reducing semantic top-k from 25 to 10 changed mean answer F1 from 0.6243 to 0.6494 (paired difference +0.0251, or +2.51 percentage points). Mean retrieved context changed by -21.58 entries per question and retrieval-plus-answer latency changed by +0.467 seconds per question. These are descriptive results for one conversation and 3 hosted-model trials, not evidence of a general improvement.

What reproduces: the released text system can construct memory from the full selected conversation, perform planned hybrid retrieval and reflection, produce scored answers, and support a controlled retrieval-k modification. What is not established: exact published F1, published token savings, full-benchmark generalization, or a causal latency gain independent of provider effects.

Recommendations: record actual request/response model metadata and token usage; rebuild the keyword index after ingestion and test it separately; use more conversations, stratified categories, counterbalanced condition order, and additional seeds. Match paper settings and evaluation aggregation before attempting a direct numerical replication.

Artifacts: reproduction/README.md (setup/run instructions), PROTOCOL.md (fixed design), run.py and start_experiment.sh (execution), test_paired_memory.py (six checks), summarize.py (validated aggregation), trials.csv/questions.csv/categories.csv (measurements), raw results and manifests, and paired-results.pdf/png (figures). Local memory databases, .env, and full dataset are excluded from submission evidence. Code, report, slides, and analysis tables are published at https://github.com/FreshbirdZhao/SimpleMem-Reproducibility; the Zoom recording link accompanies the submission.

References: (1) SimpleMem: Efficient Lifelong Memory for LLM Agents, arXiv:2601.02553, Table 1, Table 4, Appendix B.3/Table 6, and Table 7; https://arxiv.org/abs/2601.02553. (2) aiming-lab/SimpleMem, commit db80b6a7c591e0ea730a058e9f5fc4eb06572299. (3) snap-research/locomo, pinned commit stated in Section 3. (4) FTEC5660 Reproducibility Work instructions, Sections 2-7.
