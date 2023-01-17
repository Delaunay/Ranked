from ranked.calibration import optimize, ERROR
from ranked.models.noskill import NoSkill

import pytest

@pytest.mark.skipif(ERROR is not None, reason="Does not support Orion")
def test_synthetic_callibration():
    optimize(NoSkill, max_trials=1)
