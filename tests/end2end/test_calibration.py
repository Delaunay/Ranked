from ranked.calibration import optimize
from ranked.models.noskill import NoSkill


def test_synthetic_callibration():
    optimize(NoSkill, max_trials=1)
