#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
experiment_directory="reproduction/runs/experiment-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$experiment_directory"
uv pip freeze --python .venv/bin/python > "$experiment_directory/dependencies.txt"
.venv/bin/python reproduction/run.py prepare \
    --dataset test_ref/locomo10.json --output "$experiment_directory/subset" \
    --questions 20 --seed 5660
echo "Experiment directory: $experiment_directory"
for seed in 5660 5661 5662; do
    PYTHONUNBUFFERED=1 .venv/bin/python reproduction/run.py run \
        --dataset "$experiment_directory/subset/subset.json" \
        --output "$experiment_directory/baseline-$seed" --top-k 25 --seed "$seed" \
        2>&1 | tee "$experiment_directory/baseline-$seed.log"
    PYTHONUNBUFFERED=1 .venv/bin/python reproduction/run.py run \
        --dataset "$experiment_directory/subset/subset.json" \
        --output "$experiment_directory/modified-$seed" --top-k 10 --seed "$seed" \
        --memory-source "$experiment_directory/baseline-$seed" \
        2>&1 | tee "$experiment_directory/modified-$seed.log"
done
echo "Experiment completed: $experiment_directory"
