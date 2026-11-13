import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import nltk


def verify_resource(package, *args, **kwargs):
    resources = {
        "punkt": ("tokenizers/punkt",),
        "punkt_tab": ("tokenizers/punkt_tab",),
        "wordnet": ("corpora/wordnet", "corpora/wordnet.zip"),
    }
    for resource in resources[package]:
        try:
            nltk.data.find(resource)
            return True
        except LookupError:
            continue
    raise RuntimeError(f"Required NLTK resource is missing: {package}")


if __name__ == "__main__":
    for package in ("punkt", "punkt_tab", "wordnet"):
        verify_resource(package)
    runner = Path(__file__).with_name("run.py")
    sys.argv[0] = str(runner)
    with patch.object(nltk, "download", side_effect=verify_resource):
        runpy.run_path(str(runner), run_name="__main__")
