import argparse
import copy
import hashlib
import json
import random
import runpy
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def memory_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(directory).as_posix().encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def prepare(args):
    source = args.dataset.read_bytes()
    samples = json.loads(source)
    if not 0 <= args.sample < len(samples):
        raise ValueError("Sample index is outside the dataset")
    sample = copy.deepcopy(samples[args.sample])
    if not 1 <= args.questions <= len(sample["qa"]):
        raise ValueError("Question count must be between 1 and the sample QA count")
    indices = sorted(random.Random(args.seed).sample(range(len(sample["qa"])), args.questions))
    sample["qa"] = [sample["qa"][index] for index in indices]
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "subset.json", [sample])
    write_json(args.output / "selection.json", {
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "sample_index": args.sample,
        "question_indices": indices,
        "selection_seed": args.seed,
        "conversation_preserved_in_full": True,
    })
    print(f"Prepared {args.questions} questions with the full conversation in {args.output}")


def execute(args):
    if sys.version_info < (3, 10):
        raise RuntimeError("SimpleMem requires Python 3.10 or newer")
    dataset = args.dataset.resolve()
    if not dataset.is_file():
        raise FileNotFoundError(dataset)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Use a new output directory: {output}")
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    sys.path.insert(0, str(ROOT))
    from simplemem.core.settings import settings

    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-api-key-here":
        raise RuntimeError("Configure OPENAI_API_KEY locally before running")
    settings.SEMANTIC_TOP_K = args.top_k
    settings.LANCEDB_PATH = str(output / "memory")
    settings.ENABLE_PARALLEL_PROCESSING = False
    settings.ENABLE_PARALLEL_RETRIEVAL = False
    random.seed(args.seed)
    import numpy
    import torch

    numpy.random.seed(args.seed)
    torch.manual_seed(args.seed)
    output.mkdir(parents=True)
    fields = [
        "LLM_MODEL", "EMBEDDING_MODEL", "EMBEDDING_DIMENSION",
        "WINDOW_SIZE", "OVERLAP_SIZE", "SEMANTIC_TOP_K", "KEYWORD_TOP_K",
        "STRUCTURED_TOP_K", "ENABLE_PLANNING", "ENABLE_REFLECTION",
        "MAX_REFLECTION_ROUNDS", "USE_STREAMING", "USE_JSON_FORMAT",
        "ENABLE_THINKING", "ENABLE_PARALLEL_PROCESSING", "ENABLE_PARALLEL_RETRIEVAL",
    ]
    manifest = {
        "status": "started",
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "seed": args.seed,
        "memory_source": str(args.memory_source.resolve()) if args.memory_source else None,
        "python": sys.version,
        "settings": {field: getattr(settings, field) for field in fields},
        "limitations": [
            "Local seeds do not guarantee deterministic hosted LLM responses.",
            "Memory is rebuilt per seed and can be copied unchanged for the paired condition.",
            "Original evaluator metrics are retained; no API cost or token counts are inferred.",
            "Record provider and sanitized base URL separately; API keys are never logged here.",
            "Generation parameters are defined at LLM call sites, not inferred from config defaults.",
        ],
    }
    write_json(output / "manifest.json", manifest)
    sys.argv = [str(ROOT / "test_locomo10.py"), "--dataset", str(dataset),
                "--result-file", str(output / "results.json")]
    try:
        if args.memory_source:
            source = args.memory_source.resolve()
            source_manifest = json.loads((source / "manifest.json").read_text())
            if source_manifest["status"] != "completed":
                raise ValueError("Memory source must be a completed run")
            for field in ("dataset_sha256", "seed"):
                if source_manifest[field] != manifest[field]:
                    raise ValueError(f"Memory source mismatch: {field}")
            for field in fields:
                if field != "SEMANTIC_TOP_K" and source_manifest["settings"][field] != manifest["settings"][field]:
                    raise ValueError(f"Memory source setting mismatch: {field}")
            source_digest = memory_digest(source / "memory")
            if source_digest != source_manifest.get("memory_sha256"):
                raise ValueError("Memory source checksum mismatch")
            shutil.copytree(source / "memory", output / "memory")
            if memory_digest(output / "memory") != source_digest:
                raise ValueError("Copied memory checksum mismatch")
            manifest["initial_memory_sha256"] = source_digest
            write_json(output / "manifest.json", manifest)
            sys.argv.append("--reuse-memory")
        runpy.run_path(str(ROOT / "test_locomo10.py"), run_name="__main__")
    except BaseException:
        manifest["status"] = "failed"
        write_json(output / "manifest.json", manifest)
        raise
    manifest["status"] = "completed"
    manifest["memory_sha256"] = memory_digest(output / "memory")
    write_json(output / "manifest.json", manifest)


def main():
    parser = argparse.ArgumentParser(description="Small, isolated SimpleMem reproduction runs")
    commands = parser.add_subparsers(dest="command", required=True)
    subset = commands.add_parser("prepare")
    subset.add_argument("--dataset", type=Path, required=True)
    subset.add_argument("--output", type=Path, required=True)
    subset.add_argument("--sample", type=int, default=0)
    subset.add_argument("--questions", type=int, default=20)
    subset.add_argument("--seed", type=int, default=5660)
    subset.set_defaults(handler=prepare)
    experiment = commands.add_parser("run")
    experiment.add_argument("--dataset", type=Path, required=True)
    experiment.add_argument("--output", type=Path, required=True)
    experiment.add_argument("--top-k", type=int, choices=[25, 10], required=True)
    experiment.add_argument("--seed", type=int, default=5660)
    experiment.add_argument("--memory-source", type=Path)
    experiment.set_defaults(handler=execute)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
