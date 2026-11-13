import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from run import ROOT, write_json
from summarize import summarize


def main():
    parser = argparse.ArgumentParser(description="Preserve valid pairs and rerun the failed third pair")
    parser.add_argument("source", type=Path)
    parser.add_argument("--name", default="ZHAO GUODONG")
    parser.add_argument("--student-id", default="1155263139")
    args = parser.parse_args()
    source = args.source.resolve()
    summarize(source, (5660, 5661))
    provenance = json.loads((source / "provenance.json").read_text())
    for filename in ("reproduction/run.py", "test_locomo10.py"):
        actual = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
        if actual != provenance["source_sha256"][filename]:
            raise ValueError(f"Execution source changed: {filename}")
    socket.getaddrinfo("api.deepseek.com", 443)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destination = ROOT / "reproduction/runs" / f"recovered-{timestamp}-{os.getpid()}"
    destination.mkdir()
    shutil.copytree(source / "subset", destination / "subset")
    for seed in (5660, 5661):
        for condition in ("baseline", "modified"):
            name = f"{condition}-{seed}"
            shutil.copytree(source / name, destination / name)
            shutil.copy2(source / f"{name}.log", destination / f"{name}.log")
    write_json(destination / "recovery.json", {
        "source": str(source), "utc_started": timestamp,
        "retained_seeds": [5660, 5661], "rerun_seed": 5662,
        "reason": "Original third pair contains API failures and missing modified results",
        "limitation": "Third pair rerun on a later date; provider alias, load and caching may drift",
    })
    source_files = ["reproduction/run_cached.py", "reproduction/recover_experiment.py", "reproduction/validate_evidence.py"]
    packages = ["torch", "transformers", "sentence-transformers", "lancedb", "openai", "nltk", "numpy", "pillow"]
    write_json(destination / "recovery-environment.json", {
        "python": sys.version, "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name) for name in packages},
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files},
        "extra_import_path": os.environ.get("PYTHONPATH", ""),
        "note": "Original dependencies.txt describes November 8; this file describes the rerun environment",
    })
    for filename in ("dependencies.txt", "provenance.json", "execution-source.tar.gz"):
        shutil.copy2(source / filename, destination / filename)
    environment = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONUNBUFFERED="1")
    print(f"Recovery directory: {destination}", flush=True)
    for condition, top_k in (("baseline", 25), ("modified", 10)):
        command = [sys.executable, str(ROOT / "reproduction/run_cached.py"), "run",
                   "--dataset", str(destination / "subset/subset.json"),
                   "--output", str(destination / f"{condition}-5662"),
                   "--top-k", str(top_k), "--seed", "5662"]
        if condition == "modified":
            command.extend(["--memory-source", str(destination / "baseline-5662")])
        with (destination / f"{condition}-5662.log").open("w") as log:
            subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run([sys.executable, str(ROOT / "reproduction/summarize.py"), str(destination),
                    "--output", str(destination / "analysis")], check=True)
    subprocess.run([sys.executable, str(ROOT / "reproduction/validate_evidence.py"), str(destination)], check=True)
    subprocess.run([sys.executable, str(ROOT / "reproduction/build_submission.py"), str(destination / "analysis"),
                    "--output", str(destination / "submission"), "--name", args.name,
                    "--student-id", args.student_id], check=True)
    print(f"Validated report and presentation: {destination / 'submission'}")


if __name__ == "__main__":
    main()
