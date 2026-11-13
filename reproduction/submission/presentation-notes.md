# Zoom presentation script (target 12 minutes)

Record these slides in Zoom with your own narration. Repository: https://github.com/FreshbirdZhao/SimpleMem-Reproducibility

## Slide 1: SimpleMem: retrieval-depth tradeoff (0:00-1:00)

ZHAO GUODONG | 1155263139. Question: can we reduce semantic retrieval depth without sacrificing answer quality?

Introduce the agentic memory pipeline and the assignment: reproduce a measured behavior, then isolate one modification. Explain that this is a partial reproduction, not a full paper replication.

## Slide 2: What we reproduced (1:00-2:20)

Full first LoCoMo conversation: 419 turns. Fixed 20 questions. 3 analyzed seeds. Hosted DeepSeek plus local Qwen embeddings.

Explain memory construction, planned semantic searches, keyword and structured retrieval, reflection, and answering. State the target F1 behavior and why the subset is feasible.

## Slide 3: One controlled modification (2:20-3:40)

Semantic top-k 25 to 10. Identical copied memory within each seed. Same prompts, model, evaluator, keyword k=5, structured k=5.

Show the runner flags and checksum guards. Explain why rebuilding memory separately would confound the comparison. Top-k is per semantic search, not a cap on merged results.

## Slide 4: Measurement design (3:40-5:00)

120 validated predictions in 6 runs. Per-seed means, sample variance across 3 seeds, and paired differences. No provider seed or measured token costs.

Describe the fixed selection, category counts, pilot overlap, sequential runs, and fixed baseline-first order. Explain unique-token F1 and additional non-adversarial analysis.

## Demo: Evidence check (5:00-5:45)

Before I show the results, let me verify the evidence chain behind them. Every number in this talk comes from six completed runs, three paired trials, and one hundred twenty question predictions.

（操作：提前把终端开在项目根目录，字号调到 20pt 以上，先试跑一次再用 Cmd+K 清屏。讲完上面这句后按 Cmd+Tab 切到终端，回车运行下面这条命令。约 0.3 秒，不调用 API，不产生费用。）

```bash
.venv/bin/python reproduction/validate_evidence.py reproduction/runs/recovered-20261113-060600-75832
```

（操作：输出会停在屏幕上，显示 verified_predictions 120、verified_pairs 3、complete true 和八项检查。用鼠标指一下 JSON 的前三行，再指一下 checks 列表；不要打开 results.json 滚动。）

The script independently recomputes token-level F1, re-sums the retrieval and answer timings, and verifies the dataset hash, the question order, the settings, the logs, the paired memory, and the stored memory digest. One hundred twenty predictions, three pairs, every check passes.

So the numbers on the next slide are not hand-entered; they are computed from these validated files. Now, the measured impact.

（操作：讲完立即 Cmd+Tab 回到 PDF，翻到第 5 页。整段演示控制在 45 秒内；如果终端出错，直接切回 PDF 说一句 “I will show a screenshot instead”，不要现场 debug。）

## Slide 5: Measured impact (5:45-7:20)

Reducing semantic top-k from 25 to 10 changed mean answer F1 from 0.6243 to 0.6494 (paired difference +0.0251, or +2.51 percentage points). Mean retrieved context changed by -21.58 entries per question and retrieval-plus-answer latency changed by +0.467 seconds per question. These are descriptive results for one conversation and 3 hosted-model trials, not evidence of a general improvement.

F1 increased in 2 of 3 paired trials. Per-seed differences range from -0.0166 to +0.0569; the direction is not consistent across trials. The observed mean should not be treated as a guaranteed quality gain. Walk through the paired chart and actual values. Distinguish quality, context count, and latency. Do not claim significance from three trials.

## Slide 6: Comparison with the paper (7:20-8:40)

Paper Table 1: GPT-4.1-mini F1 43.24/100. Table 6: retrieval sensitivity at k=1,3,5,10,20. Different model, categories, averaging, and code settings.

Show why a larger local F1 would not prove an improvement over the paper. Mention window/stride differences and that paper timing is per sample. We did not reproduce the 30x token claim.

## Slide 7: Debugging and inherited limitations (8:40-10:20)

Proxy/model downloads; LanceDB/Tantivy version mismatch; missing legacy config; keyword index covers only the first insertion batch.

Explain the version pin and category-5 config fix, applied to both conditions. Show that inherited keyword staleness is disclosed rather than silently mixing implementations. Mention the six passing checks.

## Slide 8: Conclusions and next steps (10:20-11:50)

The pipeline runs and the k modification is measurable. Broader claims need more conversations, category coverage, counterbalanced order, stable models, and usage logging.

Conclude with actual observed tradeoff, limits, and recommendations. Show the reproducible commands, raw evidence, and the published repository. Keep the recording under 15 minutes.
