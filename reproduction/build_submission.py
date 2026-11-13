import argparse
import csv
import html
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from pypdf import PdfReader


def numeric(value):
    if 0 < abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.4f}"


def make_chart(summary, output):
    figure, axes = plt.subplots(1, 3, figsize=(10, 3.2))
    for axis, metric, title, unit in zip(
        axes, ("f1", "retrieved", "total_seconds"),
        ("Answer quality", "Retrieved context", "Retrieval + answer latency"),
        ("Mean F1 (0-1)", "Mean memory entries / question", "Mean seconds / question"),
    ):
        for index, seed in enumerate(summary["seeds"]):
            axis.plot([25, 10], [summary["baseline"][metric]["values"][index], summary["modified"][metric]["values"][index]],
                      marker="o", linewidth=1.4, label=f"Seed {seed}")
        axis.set_title(title, fontsize=10)
        axis.set_xlabel("Semantic retrieval top-k")
        axis.set_ylabel(unit)
        axis.set_xticks([10, 25])
        axis.invert_xaxis()
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.2)
    axes[0].legend(fontsize=8)
    figure.suptitle(f"Paired SimpleMem experiment: 20 fixed questions, {len(summary['seeds'])} seeds", fontsize=12)
    figure.tight_layout()
    figure.savefig(output / "paired-results.png", dpi=200)
    figure.savefig(output / "paired-results.pdf")
    plt.close(figure)


def make_table(rows, widths=None, font_size=9):
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--student-id", default="")
    args = parser.parse_args()
    summary = json.loads((args.analysis / "summary.json").read_text())
    trial_count = len(summary["seeds"])
    draft_notice = (
        "DRAFT - INCOMPLETE EXPERIMENT. Only seeds 5660 and 5661 are validated. "
        "Seed 5662 baseline contains API failures and fallback answers; its modified run has no results file. "
        "Both runs for seed 5662 require rerunning. The planned three-trial requirement is not yet met. "
        "All results below use only the two intact pairs, selected by execution validity, not score."
        if not summary["complete"] else ""
    )
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    make_chart(summary, output)
    baseline = summary["baseline"]
    modified = summary["modified"]
    differences = summary["paired_modified_minus_baseline"]
    f1_delta = differences["f1"]["mean"]
    context_delta = differences["retrieved"]["mean"]
    latency_delta = differences["total_seconds"]["mean"]
    outcome = (
        f"Reducing semantic top-k from 25 to 10 changed mean answer F1 from {baseline['f1']['mean']:.4f} "
        f"to {modified['f1']['mean']:.4f} (paired difference {f1_delta:+.4f}, or {f1_delta * 100:+.2f} percentage points). "
        f"Mean retrieved context changed by {context_delta:+.2f} entries per question and retrieval-plus-answer "
        f"latency changed by {latency_delta:+.3f} seconds per question. These are descriptive results for one "
        f"conversation and {trial_count} hosted-model trials, not evidence of a general improvement."
    )
    improved_trials = sum(value > 0 for value in differences["f1"]["values"])
    consistency = (
        f"F1 increased in {improved_trials} of {trial_count} paired trials. "
        f"Per-seed differences range from {min(differences['f1']['values']):+.4f} "
        f"to {max(differences['f1']['values']):+.4f}; the direction is "
        f"{'consistent' if improved_trials in (0, trial_count) else 'not consistent'} across trials. "
        "The observed mean should not be treated as a guaranteed quality gain."
    )
    sections = [
        ("1. Project, target, and measured outcome", [
            "SimpleMem is an agentic memory system that converts conversation windows into structured memory entries, "
            "plans semantic searches, combines semantic, keyword, and metadata retrieval, and reflects on whether "
            "the retrieved evidence is sufficient before answering. This project reproduces the released text pipeline "
            "on a small LoCoMo subset, then isolates a retrieval-depth modification.",
            "The target behavior is answering questions from a complete long conversation using compressed memory. "
            "The reference quantitative target is SimpleMem's LoCoMo F1, with Table 1 and the retrieval-sensitivity "
            "study in Appendix B.3/Table 6 used for context. This is a partial reproduction under a different model, "
            "not an exact replication of the paper's headline number.",
            outcome,
            "The assignment explicitly accepts retrieval-k parameter changes. Our single experimental change is "
            "SEMANTIC_TOP_K=25 to 10. Both conditions retain the same prompts, evaluator, keyword/structured "
            "retrieval settings, planning and reflection. Environment compatibility fixes apply equally to both.",
        ]),
        ("2. Environment and reproducible setup", [
            "Repository: https://github.com/aiming-lab/SimpleMem; starting commit "
            "db80b6a7c591e0ea730a058e9f5fc4eb06572299. Platform: macOS arm64, Python 3.11.16. "
            "The run includes a complete dependency freeze and source snapshot. LanceDB 0.25.3 with pylance "
            "supports the upstream Tantivy index; 0.41.0 had removed that interface.",
            "LLM provider: DeepSeek; base URL https://api.deepseek.com/v1; requested model deepseek-chat. "
            "A preflight response identified deepseek-flash. The upstream client discards response metadata, so "
            "this alias mapping is verified only at preflight, not at every experimental request. Local .env "
            "provides authentication and is ignored by Git. No credentials appear in the submission.",
            "Embedding model: Qwen/Qwen3-Embedding-0.6B, 1024 dimensions. Metric models: all-MiniLM-L6-v2 "
            "and roberta-large through the upstream evaluator. Memory construction and retrieval run sequentially. "
            "Window size is 40, overlap 2, keyword top-k 5, structured top-k 5, and maximum reflection rounds 2.",
            "Actual call-site temperatures: memory construction 0.1; normal answers 0.1; adversarial answers 0.5; "
            "retrieval routines 0.1, 0.2, or 0.3 depending on the prompt. top_p, max_tokens, and provider seed "
            "are omitted and therefore provider-controlled. Streaming and API JSON mode are disabled. "
            "The local thinking flag does not explicitly configure DeepSeek thinking behavior. No prompt templates "
            "were changed and no LLM judge was enabled.",
            "Run from repository root: bash reproduction/start_experiment.sh. It freezes the subset, runs three "
            "paired trials, and saves logs, manifests, predictions, and dependency versions. Reproduction README "
            "contains setup, individual commands, and troubleshooting details.",
        ]),
        ("3. Dataset, control, and metric definitions", [
            "Dataset: snap-research/locomo, data/locomo10.json at commit "
            "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376. Its SHA-256 is "
            "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4. "
            "The pinned upstream file matches the local file byte for byte.",
            "The complete first conversation contains 419 turns. Twenty QA indices were selected using "
            "random.Random(5660).sample before formal outcomes: 1, 9, 23, 24, 28, 48, 52, 54, 65, 74, 78, 91, "
            "99, 114, 132, 139, 149, 153, 157, 176. There are 6 multi-hop, 5 temporal, 6 single-hop, and 3 "
            "adversarial questions, with no open-domain questions. Two pilot questions overlap; selection did "
            "not depend on pilot correctness. This is a case study, not a representative benchmark sample.",
            f"For each analyzed seed ({', '.join(map(str, summary['seeds']))}), baseline memory is built once and then copied for the modified "
            "condition. Directory checksums verify identical initial stored memory. Dataset, seed, and all "
            "settings other than semantic k are checked. The modified evaluation skips clearing and ingestion. "
            "Memory is rebuilt across seeds; local seeding cannot make hosted generation deterministic.",
            "Primary F1 is the upstream scorer: lowercased text, limited punctuation replacement, and sets of "
            "whitespace tokens. F1 is the harmonic mean of token-set precision and recall. Extra explanation "
            "can reduce F1 despite containing the answer. Overall F1 includes adversarial questions, which use "
            "a two-option prompt and no reflection. We separately report F1 on the 17 non-adversarial questions.",
            "Efficiency metrics are unique merged memory count and retrieval/answer seconds per question. "
            "Retrieval includes planning and reflection calls; timings exclude metric evaluation and memory "
            "construction. Semantic k applies to each semantic search, not the final context size. For each "
            "condition compute per-seed aggregates, then mean and sample variance with denominator n-1. "
            f"The {trial_count} paired differences, not individual questions treated as independent trials, measure variability.",
        ]),
        ("4. Modification experiment results", [outcome, consistency,
            f"All values below are computed from retained raw predictions. The variance is across the {trial_count} "
            "per-seed aggregate values, not the upstream summary's across-question variance. Latency includes "
            "hosted-provider load and caching effects; baseline always ran first within a seed.",
            "A smaller context is not itself evidence of lower end-to-end cost or latency. Query planning "
            "and reflection also call the hosted model. Provider load, cache behavior, and generated queries "
            "can therefore affect timing independently of the final number of retrieved entries. No token "
            "or monetary savings can be calculated from memory counts alone.",
        ]),
        ("5. Comparison with reported results", [
            "The downloaded SimpleMem paper (arXiv:2601.02553, accessed 8 November 2026) reports Table 1 "
            "GPT-4.1-mini Average F1=43.24, with multi-hop 43.46, temporal 58.62, open-domain 19.76, and "
            "single-hop 51.12. These four category numbers average to approximately 43.24. Our evaluator "
            "uses a question-weighted mean and includes category 5; the aggregation and category mix differ.",
            "Appendix B.3/Table 6 reports F1 35.20, 42.85, 43.24, 43.45, and 43.40 at k=1,3,5,10,20. "
            "This motivates testing lower retrieval depth, but its retrieved-entry k is not guaranteed to "
            "match our per-semantic-search setting under hybrid query planning. The repository default k=25 "
            "is outside that table's tested range. Our result therefore is a new local sensitivity experiment.",
            "Paper Table 7 specifies window size 20, stride 5, GPT-4.1-mini temperature 0.0, and LanceDB 0.4.5. "
            "Current repository defaults and available dependencies differ. We retain the current pipeline "
            "and document these differences instead of claiming to recreate the exact published configuration.",
            f"Our baseline mean F1 is {baseline['f1']['mean'] * 100:.2f}/100 and modified mean is "
            f"{modified['f1']['mean'] * 100:.2f}/100. These values must not be interpreted as beating or failing "
            "the paper's 43.24 because model, sample, categories, averaging, and implementation differ. "
            "The separate non-adversarial means reduce one mismatch but do not establish comparability.",
            "Paper Table 4 reports 92.6 seconds construction and 388.3 seconds retrieval as per-sample "
            "averages, not per-question timings. Our timing units, workload, concurrency, hardware, and model "
            "differ. The paper's roughly 30-fold token reduction is not tested: upstream disables token counting "
            "and total API usage/cost was not measured.",
        ]),
        ("6. Debug diary and threats to validity", [
            "Initial blockers: sandbox DNS failures, missing dependencies/data, and Hugging Face timeouts. "
            "An authorized network execution and a changed proxy allowed downloads and API calls. Python "
            "3.11 replaced the unsupported system Python 3.9. Model caches and NLTK resources were validated. "
            "NLTK's redundant online checks reject synthetic proxy IPs, but local scoring resources work.",
            "LanceDB 0.41.0 removed Tantivy FTS. Pinning 0.25.3 with pylance restored index creation and "
            "keyword searches; an isolated smoke check verified a matching document is returned. An earlier "
            "pilot with broken FTS was interrupted and excluded. Those attempts incurred unmeasured API usage.",
            "The evaluator still imported a legacy config module in special paths. With only .env present, "
            "category-5 generation could fail and return the correct abstention by default. We changed these "
            "imports to unified runtime settings in both conditions, without changing metric or prompt logic. "
            "A targeted test verifies an actual model invocation without a local config module.",
            "An inherited limitation remains: the local backend initializes its Tantivy index after the "
            "first insertion and does not rebuild after subsequent inserts. A two-row experiment confirmed "
            "that a later unique word is absent from keyword results. Both conditions preserve this behavior, "
            "so the k comparison is controlled but full keyword-retrieval faithfulness is limited. Rebuilding "
            "the index after ingestion should be a separately evaluated future fix.",
            f"Other limits: one conversation, 20 questions, only {trial_count} analyzed seeds, missing category 3, pilot overlap, "
            "non-deterministic hosted model, mutable model alias, fixed condition order, inherited session "
            "ordering and image-evidence handling, and model/dependency drift from the paper. Raw predictions "
            "and failures are preserved. No statistical significance or broad population claim is warranted.",
        ]),
        ("7. Conclusions, artifacts, and references", [
            outcome,
            "What reproduces: the released text system can construct memory from the full selected conversation, "
            "perform planned hybrid retrieval and reflection, produce scored answers, and support a controlled "
            "retrieval-k modification. What is not established: exact published F1, published token savings, "
            "full-benchmark generalization, or a causal latency gain independent of provider effects.",
            "Recommendations: record actual request/response model metadata and token usage; rebuild the keyword "
            "index after ingestion and test it separately; use more conversations, stratified categories, "
            "counterbalanced condition order, and additional seeds. Match paper settings and evaluation "
            "aggregation before attempting a direct numerical replication.",
            "Artifacts: reproduction/README.md (setup/run instructions), PROTOCOL.md (fixed design), "
            "run.py and start_experiment.sh (execution), test_paired_memory.py (six checks), summarize.py "
            "(validated aggregation), trials.csv/questions.csv/categories.csv (measurements), raw results and "
            "manifests, and paired-results.pdf/png (figures). Local memory databases, .env, and full dataset "
            "are excluded from submission evidence. Code, report, slides, and analysis tables are published at "
            "https://github.com/FreshbirdZhao/SimpleMem-Reproducibility; the Zoom recording link "
            "accompanies the submission.",
            "References: (1) SimpleMem: Efficient Lifelong Memory for LLM Agents, arXiv:2601.02553, Table 1, "
            "Table 4, Appendix B.3/Table 6, and Table 7; https://arxiv.org/abs/2601.02553. "
            "(2) aiming-lab/SimpleMem, commit db80b6a7c591e0ea730a058e9f5fc4eb06572299. "
            "(3) snap-research/locomo, pinned commit stated in Section 3. "
            "(4) FTEC5660 Reproducibility Work instructions, Sections 2-7.",
        ]),
    ]
    if draft_notice:
        sections[0][1].insert(0, draft_notice)
    if "recovery" in summary:
        sections[5][1].append(
            "Recovery on 13 November 2026: original seed 5662 baseline contained API connection failures, "
            "fallback answers, and metric errors; its modified run never saved results. Both original runs "
            "were excluded on execution-validity grounds. Seeds 5660 and 5661 retain their original "
            "8 November outputs. The entire third pair was rerun with a fresh baseline memory build, "
            "unchanged execution source, and cached models in Hugging Face offline mode. This prevents "
            "redundant model-download checks; run_cached.py checks installed NLTK resources and skips "
            "their redundant network download check. DeepSeek API calls remain online. recovery.json preserves "
            "the provenance. The later execution date introduces possible provider/model-alias drift "
            "across seeds, even though each pair shares its configuration and stored memory. "
            "recovery-environment.json records rerun package versions and the additional report-dependency "
            "import path; the original dependency freeze is retained separately."
        )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportBody", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=11))
    styles.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=19, leading=24, spaceAfter=18))
    story = []
    markdown = ["# SimpleMem reproduction: retrieval-depth tradeoff", ""]
    for index, (title, paragraphs) in enumerate(sections):
        if index:
            story.append(PageBreak())
        else:
            story.append(Paragraph("SimpleMem reproduction:<br/>retrieval-depth tradeoff", styles["ReportTitle"]))
            identity = " | ".join(value for value in (args.name, args.student_id, "FTEC5660 - 13 November 2026") if value)
            story.append(Paragraph(html.escape(identity), styles["ReportBody"]))
            markdown.extend([identity, ""])
        story.append(Paragraph(title, styles["Heading1"]))
        markdown.extend([f"## {title}", ""])
        for paragraph in paragraphs:
            story.append(Paragraph(html.escape(paragraph), styles["ReportBody"]))
            markdown.extend([paragraph, ""])
        if index == 3:
            rows = [["Metric", "k=25 mean", "Variance", "k=10 mean", "Variance"]]
            labels = {"f1": "F1 (all 20)", "f1_non_adversarial": "F1 (17 non-adv.)", "retrieved": "Memory entries", "retrieval_seconds": "Retrieval (s)", "answer_seconds": "Answer (s)", "total_seconds": "Combined (s)"}
            for metric, label in labels.items():
                rows.append([label, numeric(baseline[metric]["mean"]), numeric(baseline[metric]["sample_variance"]), numeric(modified[metric]["mean"]), numeric(modified[metric]["sample_variance"])])
            story.append(make_table(rows, [120, 82, 75, 82, 75], 8.5))
            story.append(Spacer(1, 12))
            story.append(Image(str(output / "paired-results.png"), width=6.8 * inch, height=2.18 * inch))
            story.append(Paragraph("Source: retained experiment results; each line connects the same seed and initial memory. Units are per-question means.", styles["ReportBody"]))
            for metric, label in labels.items():
                markdown.append(f"- {label}: k=25 mean {numeric(baseline[metric]['mean'])}, sample variance {numeric(baseline[metric]['sample_variance'])}; k=10 mean {numeric(modified[metric]['mean'])}, sample variance {numeric(modified[metric]['sample_variance'])}.")
            markdown.append("")
            story.append(PageBreak())
            story.append(Paragraph("4.1 Paired trials and category breakdown", styles["Heading1"]))
            trial_rows = [["Seed", "k=25 F1", "k=10 F1", "F1 difference"]]
            for seed_index, seed in enumerate(summary["seeds"]):
                trial_rows.append([str(seed), numeric(baseline["f1"]["values"][seed_index]),
                                   numeric(modified["f1"]["values"][seed_index]),
                                   numeric(differences["f1"]["values"][seed_index])])
            story.append(make_table(trial_rows, [80, 110, 110, 130]))
            story.append(Spacer(1, 15))
            difference_rows = [["Paired difference (k=10 minus k=25)", "Mean", "Sample variance"]]
            for metric, label in labels.items():
                difference_rows.append([label, numeric(differences[metric]["mean"]),
                                        numeric(differences[metric]["sample_variance"])])
            story.append(make_table(difference_rows, [250, 90, 100], 8))
            story.append(Spacer(1, 15))
            category_rows = [["Category", "Questions", "k=25 F1", "k=10 F1"]]
            for category, label, count in ((1, "Multi-hop", 6), (2, "Temporal", 5),
                                            (4, "Single-hop", 6), (5, "Adversarial", 3)):
                means = [statistics.mean(row["f1"] for row in summary["categories"]
                                         if row["category"] == category and row["condition"] == condition)
                         for condition in ("baseline", "modified")]
                category_rows.append([label, str(count), *map(numeric, means)])
            story.append(make_table(category_rows, [150, 80, 100, 100]))
            story.append(Spacer(1, 12))
            story.append(Paragraph("Source: validated raw predictions. Category F1 is the mean of per-trial category means. "
                                   "Category 3 has no selected questions. Variances use denominator n-1. "
                                   "Adversarial questions use the upstream two-option protocol and should not be "
                                   "interpreted as ordinary open-ended QA.", styles["ReportBody"]))
            markdown.extend(["## Paired and category details", ""])
            for row in trial_rows[1:] + difference_rows[1:] + category_rows[1:]:
                markdown.append("- " + "; ".join(row))
            markdown.append("")

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        status = "DRAFT - incomplete" if draft_notice else "Completed experiment"
        canvas.drawString(42, 26, f"FTEC5660 | {status} | 13 November 2026")
        canvas.drawRightString(553, 26, str(document.page))

    document = SimpleDocTemplate(str(output / "report.pdf"), pagesize=(595, 842), leftMargin=42, rightMargin=42, topMargin=38, bottomMargin=40)
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    page_count = len(PdfReader(output / "report.pdf").pages)
    if page_count > 10:
        raise ValueError(f"Report exceeds assignment limit: {page_count} pages")
    (output / "report.md").write_text("\n".join(markdown))

    slide_texts = [
        ("SimpleMem: retrieval-depth tradeoff", "Question: can we reduce semantic retrieval depth without sacrificing answer quality?", "0:00-1:00", "Introduce the agentic memory pipeline and the assignment: reproduce a measured behavior, then isolate one modification. Explain that this is a partial reproduction, not a full paper replication."),
        ("What we reproduced", f"Full first LoCoMo conversation: 419 turns. Fixed 20 questions. {trial_count} analyzed seeds. Hosted DeepSeek plus local Qwen embeddings.", "1:00-2:20", "Explain memory construction, planned semantic searches, keyword and structured retrieval, reflection, and answering. State the target F1 behavior and why the subset is feasible."),
        ("One controlled modification", "Semantic top-k 25 to 10. Identical copied memory within each seed. Same prompts, model, evaluator, keyword k=5, structured k=5.", "2:20-3:40", "Show the runner flags and checksum guards. Explain why rebuilding memory separately would confound the comparison. Top-k is per semantic search, not a cap on merged results."),
        ("Measurement design", f"{trial_count * 40} validated predictions in {trial_count * 2} runs. Per-seed means, sample variance across {trial_count} seeds, and paired differences. No provider seed or measured token costs.", "3:40-5:00", "Describe the fixed selection, category counts, pilot overlap, sequential runs, and fixed baseline-first order. Explain unique-token F1 and additional non-adversarial analysis."),
        ("Measured impact", outcome, "5:00-7:00", consistency + " Walk through the paired chart and actual values. Distinguish quality, context count, and latency. Do not claim significance from three trials."),
        ("Comparison with the paper", "Paper Table 1: GPT-4.1-mini F1 43.24/100. Table 6: retrieval sensitivity at k=1,3,5,10,20. Different model, categories, averaging, and code settings.", "7:00-8:20", "Show why a larger local F1 would not prove an improvement over the paper. Mention window/stride differences and that paper timing is per sample. We did not reproduce the 30x token claim."),
        ("Debugging and inherited limitations", "Proxy/model downloads; LanceDB/Tantivy version mismatch; missing legacy config; keyword index covers only the first insertion batch.", "8:20-10:00", "Explain the version pin and category-5 config fix, applied to both conditions. Show that inherited keyword staleness is disclosed rather than silently mixing implementations. Mention the six passing checks."),
        ("Conclusions and next steps", "The pipeline runs and the k modification is measurable. Broader claims need more conversations, category coverage, counterbalanced order, stable models, and usage logging.", "10:00-11:30", "Conclude with actual observed tradeoff, limits, and recommendations. Show the reproducible commands, raw evidence, and the published repository. Keep the recording under 15 minutes."),
    ]
    slide_style = ParagraphStyle(name="SlideBody", fontName="Helvetica", fontSize=19, leading=27, spaceAfter=18)
    slide_title = ParagraphStyle(name="SlideTitle", fontName="Helvetica-Bold", fontSize=28, leading=34, spaceAfter=30)
    slides = []
    notes = ["# Zoom presentation script (target 11.5 minutes)", "", "Record these slides in Zoom with your own narration. Repository: https://github.com/FreshbirdZhao/SimpleMem-Reproducibility", ""]
    for index, (title, body, timing, note) in enumerate(slide_texts):
        if index:
            slides.append(PageBreak())
        slides.append(Paragraph(html.escape(title), slide_title))
        if index == 0:
            body = f"{args.name} | {args.student_id}. " + body
            if draft_notice:
                body += " DRAFT: 2 of 3 planned pairs validated; seed 5662 must be rerun."
        slides.append(Paragraph(html.escape(body), slide_style))
        if index == 4:
            slides.append(Image(str(output / "paired-results.png"), width=9 * inch, height=2.88 * inch))
        notes.extend([f"## Slide {index + 1}: {title} ({timing})", "", body, "", note, ""])
    presentation = SimpleDocTemplate(str(output / "presentation.pdf"), pagesize=(960, 540), leftMargin=45, rightMargin=45, topMargin=35, bottomMargin=30)
    presentation.build(slides)
    slide_count = len(PdfReader(output / "presentation.pdf").pages)
    (output / "presentation-notes.md").write_text("\n".join(notes))
    (output / "artifact-checks.json").write_text(json.dumps({"report_pages": page_count, "presentation_pages": slide_count, "report_page_limit": 10, "source_analysis": str(args.analysis.resolve())}, indent=2))
    print(f"Created report ({page_count} pages), presentation ({slide_count} pages), figures, and narration notes in {output}")


if __name__ == "__main__":
    main()
