import asyncio
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Callable

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from econml.dml import LinearDML, CausalForestDML

from dowhy import CausalModel

from .dag import CausalGraph
from .diagnostics import (
    compute_balance_stats,
    compute_positivity_check,
    heterogeneity_test,
    power_calculator,
    sensitivity_analysis,
)
from .estimators import (
    CausalEstimator,
    LinearRegressionEstimator,
    PropensityMatchingEstimator,
    DoublyRobustEstimator,
    DoubleMLEstimator,
    CausalForestEstimator,
    InstrumentalVariableEstimator,
    BootstrapEstimator,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


class CausalInsightEngine:
    def __init__(self, df: pd.DataFrame):
        self.raw_df = df.copy()
        self._encoders = {}
        self._missing_report = {}
        self.df = self._preprocess(df)
        self.model = None
        self.identified = None
        self.estimate = None
        self.refutation_results = {}
        self.causal_graph = CausalGraph()
        self._result_cache = {}
        self._instruments = []
        self._estimators = self._register_estimators()

    def _register_estimators(self) -> dict[str, CausalEstimator]:
        return {
            "linear_regression": LinearRegressionEstimator(),
            "propensity_matching": PropensityMatchingEstimator(),
            "doubly_robust": DoublyRobustEstimator(),
            "double_ml": DoubleMLEstimator(),
            "causal_forest": CausalForestEstimator(),
            "instrumental_variable": InstrumentalVariableEstimator(),
            "bootstrap": BootstrapEstimator(),
        }

    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        processed = df.copy()
        self._missing_report = {
            col: {
                "count": int(processed[col].isna().sum()),
                "pct": round(float(processed[col].isna().mean() * 100), 2),
            }
            for col in processed.columns
        }
        categorical_cols = []
        for col in processed.columns:
            if processed[col].dtype == object or str(processed[col].dtype) == "category":
                categorical_cols.append(col)
            elif processed[col].dtype in ("int64", "float64"):
                pass
            else:
                try:
                    processed[col] = processed[col].astype(float)
                except (ValueError, TypeError):
                    categorical_cols.append(col)
        if categorical_cols:
            encoder = OneHotEncoder(
                sparse_output=False,
                handle_unknown="ignore",
                drop="first" if len(categorical_cols) == 1 else None,
            )
            encoded = encoder.fit_transform(processed[categorical_cols])
            feature_names = []
            for i, col in enumerate(categorical_cols):
                if hasattr(encoder, "categories_"):
                    cats = encoder.categories_[i][1:] if encoder.drop_idx is not None else encoder.categories_[i]
                    feature_names.extend([f"{col}_{c}" for c in cats])
                else:
                    feature_names.extend([f"{col}_{j}" for j in range(encoded.shape[1] // len(categorical_cols))])
            encoded_df = pd.DataFrame(
                encoded, columns=feature_names[:encoded.shape[1]], index=processed.index
            )
            processed = processed.drop(columns=categorical_cols)
            processed = pd.concat([processed, encoded_df], axis=1)
            self._encoders[categorical_cols[0]] = encoder
        processed = processed.dropna()
        return processed

    def _run_balance_check(self, treatment: str, confounders: list) -> dict:
        if not self._is_binary_treatment(treatment):
            return {}
        return compute_balance_stats(self.df, treatment, confounders)

    def get_missing_report(self) -> dict:
        return {
            "columns": self._missing_report,
            "total_dropped": len(self.raw_df) - len(self.df),
            "rows_before": len(self.raw_df),
            "rows_after": len(self.df),
        }

    def _is_binary_treatment(self, treatment: str) -> bool:
        if treatment not in self.df.columns:
            return False
        values = set(self.df[treatment].dropna().unique())
        return values <= {0, 1} or values <= {0.0, 1.0}

    def _build_cache_key(self, treatment: str, outcome: str, confounders: list) -> str:
        raw = f"{treatment}|{outcome}|{sorted(confounders)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _detect_mediators_colliders(self, treatment: str, outcome: str, confounders: list) -> dict:
        warnings_list = []
        mediators = []
        colliders = []
        for c in confounders:
            if self.causal_graph.check_mediator(c, treatment, outcome):
                mediators.append(c)
                warnings_list.append(
                    f"'{c}' appears to be a mediator (downstream of treatment). "
                    "Controlling for it may block the treatment effect path."
                )
            if self.causal_graph.check_collider(c, treatment, outcome):
                colliders.append(c)
                warnings_list.append(
                    f"'{c}' appears to be a collider (common effect). "
                    "Controlling for it may induce collider bias."
                )
        return {"warnings": warnings_list, "mediators": mediators, "colliders": colliders}

    def _recommend_methods(self, treatment: str, n_samples: int, n_confounders: int) -> dict:
        is_binary = self._is_binary_treatment(treatment)
        recommendations = {}
        recommendations["linear_regression"] = {"recommended": True, "note": "Baseline method; fast but assumes linearity"}
        if is_binary:
            if n_samples >= 100:
                recommendations["propensity_matching"] = {"recommended": True, "note": f"Good with n={n_samples}"}
                recommendations["doubly_robust"] = {"recommended": True, "note": "Robust if either model is correctly specified"}
            else:
                recommendations["propensity_matching"] = {"recommended": False, "note": f"Small sample (n={n_samples}); matching may be unstable"}
                recommendations["doubly_robust"] = {"recommended": True, "note": f"Use with caution (n={n_samples})"}
        else:
            recommendations["propensity_matching"] = {"recommended": False, "note": "Requires binary treatment"}
            recommendations["doubly_robust"] = {"recommended": False, "note": "Requires binary treatment"}
        recommendations["double_ml"] = {"recommended": n_samples >= 200, "note": "Best for high-dimensional confounding" if n_samples >= 200 else f"Small sample (n={n_samples}); DML may overfit"}
        recommendations["causal_forest"] = {"recommended": n_samples >= 300, "note": "Captures heterogeneous effects" if n_samples >= 300 else f"Small sample (n={n_samples}); CATE estimates may be noisy"}
        if self._instruments:
            recommendations["instrumental_variable"] = {"recommended": True, "note": "Useful when unmeasured confounding suspected"}
        return recommendations

    def build_model(self, treatment: str, outcome: str, confounders: list, use_dag: bool = True):
        if use_dag:
            self.causal_graph.build_from_confounders(treatment, outcome, confounders)
            logger.debug(f"Built DAG:\n{self.causal_graph.to_dowhy_string()}")
        self.model = CausalModel(
            data=self.df,
            treatment=treatment,
            outcome=outcome,
            common_causes=confounders,
        )
        return self.model

    def identify_effect(self):
        self.identified = self.model.identify_effect(proceed_when_unidentifiable=True)
        return self.identified

    def estimate_ate_backdoor(self):
        estimate = self.model.estimate_effect(
            self.identified,
            method_name="backdoor.linear_regression",
            method_params={"fit_intercept": True},
        )
        self.estimate = estimate
        return estimate

    def bootstrap_ate(self, treatment: str, outcome: str, confounders: list,
                      n_bootstrap: int = 200, alpha: float = 0.05):
        rng = np.random.RandomState(42)
        n = len(self.df)
        estimates = []
        for i in range(n_bootstrap):
            idx = rng.randint(0, n, n)
            boot_df = self.df.iloc[idx]
            try:
                boot_model = CausalModel(
                    data=boot_df, treatment=treatment, outcome=outcome, common_causes=confounders,
                )
                boot_identified = boot_model.identify_effect(proceed_when_unidentifiable=True)
                boot_est = boot_model.estimate_effect(boot_identified, method_name="backdoor.linear_regression")
                estimates.append(float(boot_est.value))
            except Exception:
                continue
        if len(estimates) < 2:
            return None, None, None
        estimates = np.array(estimates)
        ate = float(np.mean(estimates))
        ci_lower = float(np.percentile(estimates, 100 * alpha / 2))
        ci_upper = float(np.percentile(estimates, 100 * (1 - alpha / 2)))
        return ate, ci_lower, ci_upper

    def run_refutation_tests(self, num_simulations=30):
        if self.estimate is None:
            return {}
        refutation_configs = [
            ("placebo_treatment", "placebo_treatment_refuter"),
            ("data_subset", "data_subset_refuter"),
            ("dummy_outcome", "dummy_outcome_refuter"),
        ]
        results = {}
        for name, method in refutation_configs:
            try:
                refute = self.model.refute_estimate(
                    self.identified, self.estimate, method_name=method, num_simulations=num_simulations,
                )
                r = refute[0] if isinstance(refute, list) and refute else refute
                if r is not None:
                    results[name] = {
                        "original_estimate": float(r.estimated_effect),
                        "new_estimate": float(r.new_effect),
                        "p_value": float(getattr(r, "p_value", 1.0)),
                    }
                else:
                    results[name] = {"error": "No result returned"}
            except Exception as e:
                logger.warning(f"Refutation '{name}' failed: {e}")
                results[name] = {"error": str(e)[:120]}
        try:
            e_value = sensitivity_analysis(self.estimate)
            if e_value is not None:
                results["e_value"] = {"e_value": e_value}
        except Exception as e:
            logger.debug(f"E-value calculation skipped: {e}")
        self.refutation_results = results
        return results

    def _compare_ate_estimates(self, results: dict) -> dict:
        valid = {}
        for key in ["linear_regression", "propensity_matching", "doubly_robust", "double_ml", "causal_forest"]:
            m = results.get(key)
            if m and "error" not in m and "ate" in m:
                valid[key] = m["ate"]
        if len(valid) < 2:
            return {}
        ates = list(valid.values())
        mean_ate = float(np.mean(ates))
        std_ate = float(np.std(ates))
        if std_ate == 0:
            return {"mean": mean_ate, "std": 0, "cochran_q": 0, "p_value": 1.0, "n_methods": len(ates), "significant_difference": False}
        grand_mean = mean_ate
        q_stat = sum((a - grand_mean)**2 / (std_ate**2) for a in ates)
        df = len(ates) - 1
        p_value = 1.0 - scipy_stats.chi2.cdf(q_stat, df)
        return {
            "mean": round(mean_ate, 4),
            "std": round(std_ate, 4),
            "cochran_q": round(float(q_stat), 4),
            "p_value": round(float(p_value), 4),
            "n_methods": len(ates),
            "significant_difference": bool(p_value < 0.05),
            "interpretation": "ATE estimates differ significantly across methods" if p_value < 0.05 else "ATE estimates are consistent across methods",
        }

    def compute_cate_by_feature(self, treatment: str, outcome: str,
                                confounders: list, feature_col: str, n_bins=5):
        is_binary = self._is_binary_treatment(treatment)
        other_confounders = [c for c in confounders if c != feature_col]
        all_features = other_confounders + ([feature_col] if feature_col not in other_confounders else [])
        X = self.df[all_features].values
        T = self.df[treatment].values
        Y = self.df[outcome].values
        X_train, X_test, T_train, T_test, Y_train, Y_test = train_test_split(
            X, T, Y, test_size=0.2, random_state=42
        )
        model_t = (RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
                   if is_binary else RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42))
        cf = CausalForestDML(
            model_y=RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42),
            model_t=model_t, discrete_treatment=is_binary, cv=5, random_state=42,
        )
        cf.fit(Y_train, T_train, X=X_train, W=None)
        cate_vals = cf.effect(X_test)
        feature_data = self.df.loc[X_test.index if hasattr(X_test, 'index') else range(len(X_test)), feature_col]
        try:
            bins = pd.qcut(feature_data, n_bins, labels=False, duplicates="drop")
        except ValueError:
            bins = pd.cut(feature_data, n_bins, labels=False, duplicates="drop")
        bin_labels = {}
        for bin_idx in sorted(set(bins.dropna())):
            mask = bins == bin_idx
            if not mask.any():
                continue
            lo = float(feature_data[mask].min())
            hi = float(feature_data[mask].max())
            bin_cate = float(np.mean(cate_vals[mask]))
            bin_labels[str(int(bin_idx))] = {"range": [lo, hi], "cate": bin_cate, "count": int(mask.sum())}
        return bin_labels

    def get_summary(self, treatment: str, outcome: str, confounders: list):
        return {
            "dataset_shape": list(self.df.shape),
            "raw_rows": len(self.raw_df),
            "treatment": treatment,
            "outcome": outcome,
            "confounders": confounders,
            "treatment_type": str(self.raw_df[treatment].dtype),
            "outcome_type": str(self.raw_df[outcome].dtype),
            "treatment_stats": self.df[treatment].describe().to_dict(),
            "outcome_stats": self.df[outcome].describe().to_dict(),
            "missing_values": int(self.raw_df.isnull().sum().sum()),
            "rows_dropped": len(self.raw_df) - len(self.df),
            "num_rows": len(self.df),
            "is_binary_treatment": self._is_binary_treatment(treatment),
        }

    def full_analysis(self, treatment: str, outcome: str, confounders: list,
                      progress_cb: Optional[Callable] = None):
        if len(self.df) < 10:
            raise ValueError("Not enough complete rows after preprocessing (minimum 10 required)")

        cache_key = self._build_cache_key(treatment, outcome, confounders)
        if cache_key in self._result_cache:
            logger.info(f"Returning cached result for {cache_key}")
            return self._result_cache[cache_key]

        if progress_cb:
            progress_cb("Building causal graph", 2)
        diagnostics_info = self._detect_mediators_colliders(treatment, outcome, confounders)
        recommendations = self._recommend_methods(treatment, len(self.df), len(confounders))

        if progress_cb:
            progress_cb("Identifying causal effect", 5)
        self.build_model(treatment, outcome, confounders)
        self.identify_effect()

        results = {}
        is_binary = self._is_binary_treatment(treatment)
        estimator_keys = ["linear_regression"]
        if is_binary:
            estimator_keys += ["propensity_matching", "doubly_robust"]
        estimator_keys += ["double_ml", "causal_forest"]
        if self._instruments:
            estimator_keys.append("instrumental_variable")

        total = len(estimator_keys) + 1
        for i, key in enumerate(estimator_keys):
            estimator = self._estimators.get(key)
            if not estimator:
                continue
            if estimator.requires_binary_treatment() and not is_binary:
                results[key] = {"error": "Treatment must be binary (0/1) for this method", "method": estimator.name()}
                continue
            if progress_cb:
                progress_cb(f"Running {estimator.name()}...", 10 + int(70 * (i + 1) / total))
            try:
                result = estimator.estimate(self, treatment, outcome, confounders)
                results[key] = result
            except Exception as e:
                logger.warning(f"{estimator.name()} failed: {e}")
                results[key] = {"error": str(e)[:200], "method": estimator.name()}

        if is_binary:
            try:
                overlap = compute_positivity_check(self.df, treatment, confounders)
                if overlap:
                    results["positivity_check"] = overlap
            except Exception as e:
                logger.debug(f"Positivity check skipped: {e}")

        if progress_cb:
            progress_cb("Bootstrapping confidence intervals", 82)
        try:
            boot_result = self._estimators["bootstrap"].estimate(self, treatment, outcome, confounders)
            if "error" not in boot_result:
                results["bootstrap_ate"] = boot_result
        except Exception as e:
            logger.debug(f"Bootstrap skipped: {e}")

        if progress_cb:
            progress_cb("Running refutation tests", 88)
        refutations = self.run_refutation_tests(num_simulations=30)
        results["refutations"] = {}
        for name, res in refutations.items():
            results["refutations"][name] = res if "error" not in res else {"error": res["error"]}

        results["summary"] = self.get_summary(treatment, outcome, confounders)
        results["diagnostics"] = diagnostics_info
        results["recommendations"] = recommendations

        valid_ates = []
        for method_key in ["linear_regression", "propensity_matching", "doubly_robust", "double_ml", "causal_forest"]:
            m = results.get(method_key)
            if m and "error" not in m and "ate" in m:
                valid_ates.append(m["ate"])
        if valid_ates:
            weights = [1.0 / max(len(valid_ates), 1) for _ in valid_ates]
            meta_ate = float(np.average(valid_ates, weights=weights))
            results["meta_estimate"] = {"ate": meta_ate, "method": "Inverse-variance weighted meta-estimate", "n_methods": len(valid_ates)}

        if progress_cb:
            progress_cb("Comparing estimates across methods", 95)
        ate_comparison = self._compare_ate_estimates(results)
        if ate_comparison:
            results["ate_comparison"] = ate_comparison

        try:
            power = power_calculator(self.df, treatment, outcome)
            results["power_analysis"] = power
        except Exception as e:
            logger.debug(f"Power analysis skipped: {e}")

        if len(results.get("causal_forest", {}).get("cate_samples", [])) > 10:
            cate_vals = np.array(results["causal_forest"]["cate_samples"])
            het_test = heterogeneity_test(cate_vals)
            if het_test:
                results["causal_forest"]["heterogeneity_test"] = het_test

        if progress_cb:
            progress_cb("Complete", 100)
        self._result_cache[cache_key] = results
        return results
