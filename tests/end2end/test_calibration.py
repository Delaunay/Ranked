import pytest

from ranked.calibration import ERROR, optimize
from ranked.models.noskill import NoSkill


@pytest.mark.skipif(ERROR is not None, reason="Does not support Orion")
def test_synthetic_callibration():
    optimize(NoSkill, max_trials=1)
