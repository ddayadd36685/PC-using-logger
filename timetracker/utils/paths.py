from __future__ import annotations

import os
import sys
from pathlib import Path


def get_base_path() -> Path:
    if hasattr(sys, "frozen") or hasattr(sys, "importers"):
        return Path(os.path.abspath(sys.argv[0])).parent
    return Path(__file__).resolve().parents[2]


def resource_path(relative: str) -> Path:
    return get_base_path() / relative
