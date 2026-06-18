"""Golden regression: the new policy engine must reproduce the legacy resolver.

``tests/golden/policy_resolution.json`` was frozen from the deleted
``resolve_group_config`` across the shared scenario matrix. This proves the
registry-driven ``resolve_policies`` is behaviour-preserving - the gate that
licensed deleting the old path.
"""

import json
import os

import pytest

from duoptimum_hub_services.policy import resolve_policies
from tests._policy_scenarios import scenarios

_GOLDEN = os.path.join(os.path.dirname(__file__), 'golden', 'policy_resolution.json')

with open(_GOLDEN) as f:
    GOLDEN = json.load(f)


@pytest.mark.parametrize('name,kwargs', scenarios(), ids=[n for n, _ in scenarios()])
def test_engine_matches_golden(name, kwargs):
    got = resolve_policies(**kwargs)
    assert got == GOLDEN[name], f"scenario {name} diverged from frozen golden"


def test_all_scenarios_covered():
    names = {n for n, _ in scenarios()}
    assert names == set(GOLDEN), "scenario matrix and golden snapshot are out of sync"
