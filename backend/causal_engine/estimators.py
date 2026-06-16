from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from econml.dml import LinearDML, CausalForestDML
from dowhy import CausalModel


class CausalEstimator(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def requires_binary_treatment(self) -> bool:
        return False

    @abstractmethod
    def estimate(self, engine, treatment: str, outcome: str, confounders: list) -> dict:
        pass


class LinearRegressionEstimator(CausalEstimator):
    def name(self):
        return "Linear Regression"

    def requires_binary_treatment(self):
        return False

    def estimate(self, engine, treatment, outcome, confounders):
        estimate = engine.model.estimate_effect(
            engine.identified,
            method_name="backdoor.linear_regression",
            method_params={"fit_intercept": True},
        )
        engine.estimate = estimate
        return {"ate": float(estimate.value), "method": "Backdoor Linear Regression"}


class PropensityMatchingEstimator(CausalEstimator):
    def name(self):
        return "Propensity Score Matching"

    def requires_binary_treatment(self):
        return True

    def estimate(self, engine, treatment, outcome, confounders):
        estimate = engine.model.estimate_effect(
            engine.identified,
            method_name="backdoor.propensity_score_matching",
        )
        result = {"ate": float(estimate.value), "method": "Propensity Score Matching"}
        bal = engine._run_balance_check(treatment, confounders)
        if bal:
            result["balance"] = bal
        return result


class DoublyRobustEstimator(CausalEstimator):
    def name(self):
        return "Doubly Robust (IPW)"

    def requires_binary_treatment(self):
        return True

    def estimate(self, engine, treatment, outcome, confounders):
        estimate = engine.model.estimate_effect(
            engine.identified,
            method_name="backdoor.propensity_score_weighting",
        )
        return {"ate": float(estimate.value), "method": "Doubly Robust (IPW)"}


class DoubleMLEstimator(CausalEstimator):
    def name(self):
        return "Double ML"

    def requires_binary_treatment(self):
        return False

    def estimate(self, engine, treatment, outcome, confounders):
        is_binary = engine._is_binary_treatment(treatment)
        X = engine.df[confounders].values
        T = engine.df[treatment].values
        Y = engine.df[outcome].values
        X_train, X_test, T_train, T_test, Y_train, Y_test = train_test_split(
            X, T, Y, test_size=0.2, random_state=42
        )
        model_y = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        model_t = (
            RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
            if is_binary
            else RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        )
        dml = LinearDML(
            model_y=model_y,
            model_t=model_t,
            discrete_treatment=is_binary,
            cv=5,
            random_state=42,
        )
        dml.fit(Y_train, T_train, X=X_train, W=None)
        ate = dml.ate(X=X_test)
        interval = dml.ate_interval(X=X_test)
        ate_lb = interval[0][0] if isinstance(interval[0], (list, tuple, np.ndarray)) else interval[0]
        ate_ub = interval[1][0] if isinstance(interval[1], (list, tuple, np.ndarray)) else interval[1]
        return {
            "ate": float(ate),
            "ate_interval": [float(ate_lb), float(ate_ub)],
            "method": "Double Machine Learning (LinearDML)",
        }


class CausalForestEstimator(CausalEstimator):
    def name(self):
        return "Causal Forest"

    def requires_binary_treatment(self):
        return False

    def estimate(self, engine, treatment, outcome, confounders):
        is_binary = engine._is_binary_treatment(treatment)
        X = engine.df[confounders].values
        T = engine.df[treatment].values
        Y = engine.df[outcome].values
        X_train, X_test, T_train, T_test, Y_train, Y_test = train_test_split(
            X, T, Y, test_size=0.2, random_state=42
        )
        model_t = (
            RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
            if is_binary
            else RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        )
        cf = CausalForestDML(
            model_y=RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42),
            model_t=model_t,
            discrete_treatment=is_binary,
            cv=5,
            random_state=42,
        )
        cf.fit(Y_train, T_train, X=X_train, W=None)
        ate = cf.ate(X=X_test)
        interval = cf.ate_interval(X=X_test)
        ate_lb = interval[0][0] if isinstance(interval[0], (list, tuple, np.ndarray)) else interval[0]
        ate_ub = interval[1][0] if isinstance(interval[1], (list, tuple, np.ndarray)) else interval[1]
        cate = cf.effect(X_test)

        return {
            "ate": float(ate),
            "ate_interval": [float(ate_lb), float(ate_ub)],
            "method": "Causal Forest (CausalForestDML)",
            "cate_distribution": {
                "mean": float(np.mean(cate)),
                "std": float(np.std(cate)),
                "min": float(np.min(cate)),
                "max": float(np.max(cate)),
                "p25": float(np.percentile(cate, 25)),
                "p50": float(np.percentile(cate, 50)),
                "p75": float(np.percentile(cate, 75)),
            },
            "cate_samples": [float(v) for v in cate[:500]],
        }


class InstrumentalVariableEstimator(CausalEstimator):
    def name(self):
        return "Instrumental Variable (2SLS)"

    def requires_binary_treatment(self):
        return False

    def estimate(self, engine, treatment, outcome, confounders):
        instruments = engine._instruments if hasattr(engine, '_instruments') and engine._instruments else []
        if not instruments:
            return {"error": "No instruments provided. IV estimation requires at least one instrument variable."}
        try:
            iv_model = CausalModel(
                data=engine.df,
                treatment=treatment,
                outcome=outcome,
                instruments=instruments,
                common_causes=confounders,
            )
            iv_identified = iv_model.identify_effect(proceed_when_unidentifiable=True)
            iv_estimate = iv_model.estimate_effect(
                iv_identified,
                method_name="instrumental_variable.iv_regression",
            )
            return {
                "ate": float(iv_estimate.value),
                "method": "Instrumental Variable (2SLS)",
                "instruments": instruments,
            }
        except Exception as e:
            return {"error": f"IV estimation failed: {str(e)[:200]}", "method": "Instrumental Variable (2SLS)"}


class BootstrapEstimator(CausalEstimator):
    def name(self):
        return "Bootstrap ATE"

    def requires_binary_treatment(self):
        return False

    def estimate(self, engine, treatment, outcome, confounders):
        ate, lb, ub = engine.bootstrap_ate(treatment, outcome, confounders)
        if ate is None:
            return {"error": "Bootstrap failed to converge"}
        return {
            "ate": ate,
            "ate_interval": [lb, ub],
            "method": "Bootstrap (200 resamples)",
        }
