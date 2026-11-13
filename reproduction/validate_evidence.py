import argparse
import json
import math
from pathlib import Path

from run import memory_digest
from summarize import summarize


def token_set(value):
    text = str(value).strip().lower()
    for punctuation in ".,!?":
        text = text.replace(punctuation, " ")
    return set(text.split())


def main():
    parser = argparse.ArgumentParser(description="Independently verify saved F1, timing and memory evidence")
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--seeds", type=int, nargs="+", default=[5660, 5661, 5662])
    args = parser.parse_args()
    summary, questions = summarize(args.experiment, args.seeds)
    for trial in summary["trials"]:
        folder = args.experiment / f"{trial['condition']}-{trial['seed']}"
        manifest = json.loads((folder / "manifest.json").read_text())
        if memory_digest(folder / "memory") != manifest["memory_sha256"]:
            raise ValueError(f"Stored memory checksum changed: {folder}")
        result = json.loads((folder / "results.json").read_text())
        for row in result["detailed_results"]:
            predicted = token_set(row["answer"])
            reference = token_set(row["reference"])
            expected = 2 * len(predicted & reference) / (len(predicted) + len(reference)) if predicted and reference else 0
            if not math.isclose(expected, row["metrics"]["f1"], abs_tol=1e-12):
                raise ValueError(f"F1 mismatch: {folder}")
            if not math.isclose(row["total_time"], row["retrieval_time"] + row["answer_time"], abs_tol=1e-9):
                raise ValueError(f"Timing mismatch: {folder}")
        for row_key, summary_key in (("retrieval_time", "avg_retrieval_time"), ("answer_time", "avg_answer_time"), ("total_time", "avg_total_time")):
            mean = sum(row[row_key] for row in result["detailed_results"]) / 20
            if not math.isclose(mean, result["summary"][summary_key], abs_tol=1e-9):
                raise ValueError(f"Timing summary mismatch: {folder}")
    print(json.dumps({"verified_predictions": len(questions), "verified_pairs": len(args.seeds),
                      "complete": summary["complete"], "checks": ["dataset hash", "question order", "settings", "logs",
                      "paired memory", "stored memory digest", "independent F1", "timing sums and means"]}, indent=2))


if __name__ == "__main__":
    main()
