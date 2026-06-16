import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from causal_engine import CausalInsightEngine


@pytest.fixture
def sample_data():
    rng = np.random.RandomState(42)
    n = 1000
    age = rng.uniform(20, 70, n)
    income = rng.normal(50000, 15000, n)
    education = rng.choice([0, 1, 2], n, p=[0.3, 0.4, 0.3])
    treatment_prob = 1 / (1 + np.exp(-(-2 + 0.03 * age + 0.3 * education)))
    treatment = rng.binomial(1, treatment_prob)
    true_effect = 4.5
    outcome = (
        10
        + true_effect * treatment
        + 0.5 * age
        + 0.0001 * income
        + 1.2 * education
        + rng.normal(0, 5, n)
    )
    return pd.DataFrame({
        "age": age,
        "income": income,
        "education": education,
        "treatment": treatment,
        "outcome_score": outcome,
    })


def test_engine_initialization(sample_data):
    engine = CausalInsightEngine(sample_data)
    assert engine.df is not None
    assert len(engine.df) > 0


def test_missing_report(sample_data):
    engine = CausalInsightEngine(sample_data)
    report = engine.get_missing_report()
    assert "columns" in report
    assert "total_dropped" in report


def test_binary_treatment_detection(sample_data):
    engine = CausalInsightEngine(sample_data)
    assert engine._is_binary_treatment("treatment") is True
    assert engine._is_binary_treatment("age") is False


def test_linear_regression_ate(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    engine.build_model("treatment", "outcome_score", confounders)
    engine.identify_effect()
    ate = engine.estimate_ate_backdoor()
    assert ate is not None
    assert 3.0 <= ate.value <= 6.0


def test_propensity_matching_ate(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    engine.build_model("treatment", "outcome_score", confounders)
    engine.identify_effect()
    ate = engine.estimate_ate_propensity()
    assert ate is not None


def test_doubly_robust_ate(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    engine.build_model("treatment", "outcome_score", confounders)
    engine.identify_effect()
    ate = engine.estimate_ate_doubly_robust()
    assert ate is not None


def test_dml_estimator(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    ate, lb, ub, dml = engine.estimate_dml("treatment", "outcome_score", confounders)
    assert ate is not None
    assert 3.0 <= ate <= 6.0
    assert lb <= ub


def test_causal_forest(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    ate, lb, ub, cate, cf = engine.estimate_causal_forest("treatment", "outcome_score", confounders)
    assert ate is not None
    assert cate is not None
    assert len(cate) > 0


def test_full_analysis_recovers_true_effect(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    results = engine.full_analysis("treatment", "outcome_score", confounders)
    assert "linear_regression" in results
    assert "double_ml" in results
    assert "causal_forest" in results
    lr = results["linear_regression"]
    assert "ate" in lr
    assert 3.0 <= lr["ate"] <= 6.0
    assert "summary" in results
    assert results["summary"]["treatment"] == "treatment"


def test_refutation_tests(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    engine.build_model("treatment", "outcome_score", confounders)
    engine.identify_effect()
    engine.estimate_ate_backdoor()
    refutations = engine.run_refutation_tests(num_simulations=10)
    assert len(refutations) >= 2


def test_recommendations(sample_data):
    engine = CausalInsightEngine(sample_data)
    recs = engine._recommend_methods("treatment", 1000, 3)
    assert "linear_regression" in recs
    assert "propensity_matching" in recs
    assert "double_ml" in recs
    assert "causal_forest" in recs


def test_mediator_collider_detection(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    engine.causal_graph.build_from_confounders("treatment", "outcome_score", confounders)
    diag = engine._detect_mediators_colliders("treatment", "outcome_score", confounders)
    assert "warnings" in diag
    assert "mediators" in diag
    assert "colliders" in diag


def test_bootstrap_ate(sample_data):
    engine = CausalInsightEngine(sample_data)
    confounders = ["age", "income", "education"]
    ate, lb, ub = engine.bootstrap_ate("treatment", "outcome_score", confounders, n_bootstrap=50)
    assert ate is not None
    assert lb <= ub


def test_heterogeneity(sample_data):
    from causal_engine.diagnostics import heterogeneity_test
    cate = np.random.RandomState(42).normal(4, 2, 500)
    result = heterogeneity_test(cate)
    assert "observed_variance" in result
    assert "p_value" in result


def test_power_calculator(sample_data):
    from causal_engine.diagnostics import power_calculator
    result = power_calculator(sample_data, "treatment", "outcome_score")
    assert "minimum_detectable_effect" in result
    assert "sample_size" in result


def test_positivity_check(sample_data):
    from causal_engine.diagnostics import compute_positivity_check
    result = compute_positivity_check(sample_data, "treatment", ["age", "income", "education"])
    assert "propensity_range" in result


def test_balance_stats(sample_data):
    from causal_engine.diagnostics import compute_balance_stats
    result = compute_balance_stats(sample_data, "treatment", ["age", "income", "education"])
    assert "variables" in result


def test_invalid_treatment_raises():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    engine = CausalInsightEngine(df)
    with pytest.raises(ValueError, match="Not enough complete rows"):
        engine.full_analysis("x", "y", ["x"])
