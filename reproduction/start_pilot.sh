#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if [[ ! -f .env ]]; then
    echo 'Missing .env: fill your DeepSeek configuration first.' >&2
    exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
    uv venv --python 3.11 .venv
fi

uv pip install --python .venv/bin/python -e '.[benchmark]' -r reproduction/requirements.txt

if [[ ! -s test_ref/locomo10.json ]]; then
    dataset_download="$(mktemp test_ref/locomo10.download.XXXXXX)"
    trap 'rm -f "$dataset_download"' EXIT
    curl -fL --retry 3 --connect-timeout 20 \
        https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json \
        -o "$dataset_download"
    .venv/bin/python -m json.tool "$dataset_download" > /dev/null
    mv "$dataset_download" test_ref/locomo10.json
    trap - EXIT
fi

pilot_directory="reproduction/runs/pilot-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$pilot_directory"
.venv/bin/python -m pip freeze > "$pilot_directory/dependencies.txt" 2>/dev/null || \
    uv pip freeze --python .venv/bin/python > "$pilot_directory/dependencies.txt"

.venv/bin/python reproduction/run.py prepare \
    --dataset test_ref/locomo10.json \
    --output "$pilot_directory/subset" --questions 2 --seed 5660

echo 'Starting a 2-question pilot. The full selected conversation is processed.'
echo 'This makes billable DeepSeek calls and may download embedding/evaluation models.'
PYTHONUNBUFFERED=1 .venv/bin/python reproduction/run.py run \
    --dataset "$pilot_directory/subset/subset.json" \
    --output "$pilot_directory/baseline" --top-k 25 --seed 5660 \
    2>&1 | tee "$pilot_directory/console.log"

echo "Pilot completed. Results: $project_root/$pilot_directory/baseline/results.json"
