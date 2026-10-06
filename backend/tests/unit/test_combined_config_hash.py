"""Combined runtime configuration must agree across API and worker processes."""

import os
import subprocess
import sys

from pydantic import BaseModel

from alon_ai.services.combined_idea import stable_config_hash


class Policy(BaseModel):
    permissions: frozenset[str]
    ordered: tuple[str, ...]


def test_config_hash_preserves_ordered_values():
    first = Policy(permissions=frozenset({"URL", "TEXT"}), ordered=("first", "second"))
    second = Policy(permissions=frozenset({"TEXT", "URL"}), ordered=("first", "second"))
    changed = second.model_copy(update={"ordered": ("second", "first")})
    assert stable_config_hash(first) == stable_config_hash(second)
    assert stable_config_hash(first) != stable_config_hash(changed)


def test_config_hash_agrees_across_process_hash_seeds():
    script = """
from pydantic import BaseModel
from alon_ai.services.combined_idea import stable_config_hash
class Policy(BaseModel):
    permissions: frozenset[str]
    nested: dict[str, frozenset[str]]
print(stable_config_hash(Policy(permissions=frozenset({'URL','TITLE','TEXT'}), nested={'fields':frozenset({'URL','TEXT'})})))
"""
    hashes = {
        subprocess.check_output(
            [sys.executable, "-c", script],
            env={**os.environ, "PYTHONHASHSEED": seed},
            text=True,
        ).strip()
        for seed in ("1", "2", "3", "4")
    }
    assert len(hashes) == 1
