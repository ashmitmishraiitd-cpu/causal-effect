import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.linear_model import LogisticRegression


def compute_balance_stats(
    df: pd.DataFrame, treatment: str, confounders: list
) -> dict:
    treated = df[df[treatment] == 1]
    control = df[df[treatment] == 0]
    if len(treated) < 5 or len(control) < 5:
        return {}
    balance = {}
    for col in confounders:
        if col == treatment:
            continue
        t_mean = treated[col].mean()
        c_mean = control[col].mean()
        t_var = treated[col].var()
        c_var = control[col].var()
        pooled_std = np.sqrt((t_var + c_var) / 2) if (t_var + c_var) > 0 else 1.0
        smd = (t_mean - c_mean) / pooled_std
        balance[col] = {
            "treated_mean": round(float(t_mean), 4),
            "control_mean": round(float(c_mean), 4),
            "smd": round(float(smd), 4),
            "imbalanced": bool(abs(smd) > 0.25),
        }
    return {
        "variables": balance,
        "severe_imbalance": bool(any(v["imbalanced"] for v in balance.values())),
    }


def compute_positivity_check(
    df: pd.DataFrame, treatment: str, confounders: list, threshold: float = 0.05
) -> dict:
    X = df[confounders].values
    y = df[treatment].values
    try:
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X, y)
        probs = model.predict_proba(X)[:, 1]
        violations = {
            "extreme_low": int((probs < threshold).sum()),
            "extreme_high": int((probs > 1 - threshold).sum()),
            "total_flagged": int(((probs < threshold) | (probs > 1 - threshold)).sum()),
            "propensity_range": [round(float(probs.min()), 4), round(float(probs.max()), 4)],
        }
        return violations
    except Exception:
        return {}


def heterogeneity_test(cate_values: np.ndarray, n_sim: int = 1000) -> dict:
    if len(cate_values) < 10:
        return {}
    observed_var = float(np.var(cate_values))
    null_vars = []
    grand_mean = np.mean(cate_values)
    for _ in range(n_sim):
        shuffled = np.random.permutation(cate_values)
        null_vars.append(np.var(shuffled))
    null_vars = np.array(null_vars)
    p_value = float(np.mean(null_vars >= observed_var))
    return {
        "observed_variance": round(observed_var, 6),
        "null_mean_variance": round(float(np.mean(null_vars)), 6),
        "p_value": round(p_value, 4),
        "significant_heterogeneity": bool(p_value < 0.05),
    }


def power_calculator(df: pd.DataFrame, treatment: str, outcome: str,
                     alpha: float = 0.05, power: float = 0.8) -> dict:
    if treatment not in df.columns or outcome not in df.columns:
        return {}
    n = len(df)
    outcome_std = float(df[outcome].std())
    if outcome_std == 0:
        return {}
    effect_size = outcome_std * 0.5
    n_per_group = n / 2
    se = outcome_std * np.sqrt(2 / n_per_group) if n_per_group > 0 else float("inf")
    z_alpha = scipy_stats.norm.ppf(1 - alpha / 2)
    z_beta = scipy_stats.norm.ppf(power)
    mde = (z_alpha + z_beta) * se
    return {
        "sample_size": n,
        "outcome_std": round(outcome_std, 4),
        "minimum_detectable_effect": round(float(mde), 4),
        "power": power,
        "alpha": alpha,
        "note": f"With n={n}, the smallest effect detectable at {int(power*100)}% power is {round(float(mde), 4)}",
    }


def sensitivity_analysis(estimate, r2_max: float = 0.3) -> float:
    try:
        ate = float(estimate.value)
        se = float(getattr(estimate, "standard_error", ate * 0.1))
        if se == 0:
            return None
        t_stat = abs(ate / se)
        e_value = t_stat + np.sqrt(t_stat**2 + 1)
        return round(float(e_value), 4)
    except Exception:
        return None
