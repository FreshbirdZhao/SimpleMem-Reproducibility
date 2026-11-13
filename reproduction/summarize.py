import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path


SEEDS = (5660, 5661, 5662)
METRICS = ("f1", "f1_non_adversarial", "retrieved", "retrieval_seconds", "answer_seconds", "total_seconds")


def distribution(values):
    return {
        "mean": statistics.mean(values),
        "sample_variance": statistics.variance(values),
        "sample_std": statistics.stdev(values),
        "values": values,
    }


def summarize(root, seeds=SEEDS):
    if len(seeds) < 2 or len(set(seeds)) != len(seeds) or not set(seeds) <= set(SEEDS):
        raise ValueError("Select at least two distinct planned seeds")
    dataset_bytes = (root / "subset/subset.json").read_bytes()
    dataset = json.loads(dataset_bytes)[0]
    selection = json.loads((root / "subset/selection.json").read_text())
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()
    trials = []
    questions = []
    category_trials = []
    for seed in seeds:
        baseline_manifest = json.loads((root / f"baseline-{seed}/manifest.json").read_text())
        for condition, top_k in (("baseline", 25), ("modified", 10)):
            folder = root / f"{condition}-{seed}"
            manifest = json.loads((folder / "manifest.json").read_text())
            if manifest["status"] != "completed" or manifest["seed"] != seed:
                raise ValueError(f"Incomplete or mismatched run: {folder}")
            result = json.loads((folder / "results.json").read_text())
            if manifest["dataset_sha256"] != dataset_hash:
                raise ValueError(f"Dataset mismatch: {folder}")
            if manifest["settings"]["SEMANTIC_TOP_K"] != top_k:
                raise ValueError(f"Wrong retrieval condition: {folder}")
            if condition == "modified":
                if manifest["initial_memory_sha256"] != baseline_manifest["memory_sha256"]:
                    raise ValueError(f"Memory pairing failed: {folder}")
                if manifest["memory_sha256"] != manifest["initial_memory_sha256"]:
                    raise ValueError(f"Memory changed during paired evaluation: {folder}")
                for setting, value in baseline_manifest["settings"].items():
                    if setting != "SEMANTIC_TOP_K" and manifest["settings"][setting] != value:
                        raise ValueError(f"Confounded setting: {setting}")
            rows = result["detailed_results"]
            if len(rows) != 20 or result["summary"]["num_questions"] != 20:
                raise ValueError(f"Expected 20 completed questions: {folder}")
            for index, row in enumerate(rows):
                if row["question"] != dataset["qa"][index]["question"]:
                    raise ValueError(f"Question alignment failed: {folder}")
                if row["category"] != dataset["qa"][index]["category"]:
                    raise ValueError(f"Question category mismatch: {folder}")
                expected_reference = "Not mentioned in the conversation" if row["category"] == 5 else dataset["qa"][index]["answer"]
                if str(row["reference"]).strip() != str(expected_reference).strip():
                    raise ValueError(f"Reference answer mismatch: {folder}")
                values = [row["metrics"]["f1"], row["retrieval_time"], row["answer_time"]]
                if not all(math.isfinite(value) and value >= 0 for value in values):
                    raise ValueError(f"Invalid measurement: {folder}")
                questions.append({
                    "condition": condition, "seed": seed,
                    "source_question_index": selection["question_indices"][index],
                    "category": row["category"], "f1": row["metrics"]["f1"],
                    "retrieved": row["num_retrieved"],
                    "retrieval_seconds": row["retrieval_time"],
                    "answer_seconds": row["answer_time"],
                })
            log = (root / f"{condition}-{seed}.log").read_text()
            errors = [line for line in log.splitlines() if any(term in line for term in (
                "Error during", "Error calculating", "failed after", "Failed to generate",
                "FTS index creation skipped", "Traceback (most recent call last)",
            ))]
            if errors:
                raise ValueError(f"Run has unresolved errors; inspect {condition}-{seed}.log")
            memory_time = re.search(r"Memory building time: ([0-9.]+)s", log)
            trial = {
                "condition": condition, "seed": seed, "semantic_top_k": top_k,
                "f1": statistics.mean(row["metrics"]["f1"] for row in rows),
                "f1_non_adversarial": statistics.mean(row["metrics"]["f1"] for row in rows if row["category"] != 5),
                "retrieved": statistics.mean(row["num_retrieved"] for row in rows),
                "retrieval_seconds": result["summary"]["avg_retrieval_time"],
                "answer_seconds": result["summary"]["avg_answer_time"],
                "total_seconds": result["summary"]["avg_total_time"],
                "construction_seconds": float(memory_time.group(1)) if condition == "baseline" else None,
                "memory_entries": sum(int(value) for value in re.findall(r"Added (\d+) memory entries", log)) if condition == "baseline" else None,
            }
            trials.append(trial)
            for category in sorted({row["category"] for row in rows}):
                category_rows = [row for row in rows if row["category"] == category]
                category_trials.append({
                    "condition": condition, "seed": seed, "category": category,
                    "question_count": len(category_rows),
                    "f1": statistics.mean(row["metrics"]["f1"] for row in category_rows),
                })
    summary = {
        "experiment_directory": str(root.resolve()), "trials": trials, "categories": category_trials,
        "seeds": list(seeds), "planned_seeds": list(SEEDS),
        "complete": set(seeds) == set(SEEDS),
    }
    if (root / "recovery.json").exists():
        summary["recovery"] = json.loads((root / "recovery.json").read_text())
    for condition in ("baseline", "modified"):
        summary[condition] = {
            metric: distribution([row[metric] for row in trials if row["condition"] == condition])
            for metric in METRICS
        }
    summary["paired_modified_minus_baseline"] = {
        metric: distribution([
            summary["modified"][metric]["values"][index] - summary["baseline"][metric]["values"][index]
            for index in range(len(seeds))
        ]) for metric in METRICS
    }
    return summary, questions


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    args = parser.parse_args()
    summary, questions = summarize(args.experiment, args.seeds)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    write_csv(args.output / "trials.csv", summary["trials"])
    write_csv(args.output / "questions.csv", questions)
    write_csv(args.output / "categories.csv", summary["categories"])
    print(json.dumps({condition: summary[condition] for condition in ("baseline", "modified", "paired_modified_minus_baseline")}, indent=2))


if __name__ == "__main__":
    main()
