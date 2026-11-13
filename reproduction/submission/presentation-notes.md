# Zoom presentation script (target 12 minutes)

Nine-slide deck: `presentation.pptx`. Numbers match `analysis/summary.json` and the 8-page report.
Repository: https://github.com/FreshbirdZhao/SimpleMem-Reproducibility

## Slide 1: SimpleMem: the retrieval-depth tradeoff

Open with the question and the scope. This is a partial reproduction of SimpleMem's text memory pipeline on LoCoMo, not a full paper replication. State the one modification up front: semantic top-k 25 to 10. Point at the three numbers: 120 validated predictions, 3 paired trials, one 419-turn conversation. Mention the repository.

## Slide 2: What we reproduced

Walk the four stages left to right: compression into memory units, plan, hybrid retrieval, reflection before answering. Then the four facts. Say explicitly that the target is the behavior plus the upstream F1, and that the paper number is context. Mention the question mix and why one full conversation is a feasible case study.

## Slide 3: The one modification

This is the whole experimental change. Baseline is the repository default 25; modified is 10. Everything else is identical: prompts, evaluator, keyword and structured k, planning and reflection. Within a seed the modified run copies the baseline memory database and verifies its checksum, so memory generation cannot confound the comparison. The amber note is important: top-k is per semantic search, not a cap on the final context, which is why the retrieved count falls but does not fall to 10.

## Slide 4: Measurement design

Four numbers: F1, retrieved entries, retrieval seconds, answer seconds. Six runs and 120 predictions. Explain the aggregation: one aggregate per seed, then mean and sample variance across the three seeds; the three paired differences, not 20 questions, measure variability. The dark panel lists what is deliberately missing: no provider seed, no token cost, no counterbalanced order, no significance claim.

## Slide 5: Live check: does the evidence chain hold?

Before I show the results, let me verify the evidence chain behind them. Every number in this talk comes from six completed runs, three paired trials, and one hundred twenty question predictions.

（操作：提前把终端开在项目根目录，字号调到 20pt 以上，先试跑一次再用 Cmd+K 清屏。讲完这句后按 Cmd+Tab 切到终端，回车运行下面这条命令，约 0.3 秒，不调用 API。）

.venv/bin/python reproduction/validate_evidence.py reproduction/runs/recovered-20261113-060600-75832

（操作：输出显示 verified_predictions 120、verified_pairs 3、complete true 和八项检查。用鼠标指一下前三行，再指一下 checks 列表；不要打开 results.json 滚动。）

The script independently recomputes token-level F1, re-sums the retrieval and answer timings, and verifies the dataset hash, the question order, the settings, the logs, the paired memory, and the stored memory digest. One hundred twenty predictions, three pairs, every check passes.

So the numbers on the next slide are not hand-entered; they are computed from these validated files. Now, the measured impact.

（操作：讲完立即 Cmd+Tab 回到 PowerPoint，进入下一页。整段演示控制在 45 秒内；如果终端出错，直接切回这一页说一句 “I will show the screenshot instead”，不要现场 debug。）

## Slide 6: Measured impact

Read the three cards: mean F1 0.6243 to 0.6494, plus 2.51 percentage points; retrieved entries 45.03 to 23.45, minus 21.58; combined latency 8.62 to 9.08 seconds, so no speedup. Then the chart: two of three seeds improve, seed 5662 falls by 0.0166. Say the mean is descriptive and the direction is not consistent. Do not claim statistical significance. A smaller context is not automatically a cost or latency win because planning and reflection also call the hosted model.

## Slide 7: Comparison with the paper

Be explicit: our F1 is higher than the paper's, and that proves nothing because model, data, retrieval range, windowing, category mix and aggregation all differ. The paper's Table 6 is the motivation: performance saturates as k grows, 42.85 at k=3 and 43.45 at k=10, so testing a lower depth is a reasonable local experiment. The dark panel lists what we did not establish, including the 30x token claim, because token accounting is disabled upstream.

## Slide 8: Debugging and inherited limits

Three blockers. LanceDB 0.41 removed the Tantivy full-text interface, so keyword retrieval silently disappeared; pinning 0.25.3 with pylance fixed it and a smoke test confirmed a matching document is returned. The evaluator still imported a legacy config module in category-5 paths, which could fall back to the correct abstention answer; both conditions now use unified settings. The inherited limitation: the keyword index is not rebuilt after the first insertion batch, so keywords are incomplete; it is identical in both conditions and disclosed rather than hidden. Then the recovery and the validity threats.

## Slide 9: Conclusions

Close on three points. The pipeline is reproducible end to end. The modification is measurable: less context, a small and inconsistent F1 move, no speedup. Anything broader needs more data, more categories, counterbalanced order and provider usage logging. Point to the repository for code, report, analysis tables and raw evidence instructions. Invite questions.
