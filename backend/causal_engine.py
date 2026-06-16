import pandas as pd
import numpy as np
from dowhy import CausalModel
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from econml.dml import LinearDML, CausalForestDML


class CausalInsightEngine:
    def __init__(self, df: pd.DataFrame):
        self.raw_df = df.copy()
        self.df = self._preprocess(df)
        self.model = None
        self.identified = None
        self.estimate = None
        self.refutation_results = {}
        self._encoders = {}

    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        processed = df.copy()
        for col in processed.columns:
            if processed[col].dtype == object or str(processed[col].dtype) == "category":
                le = LabelEncoder()
                processed[col] = le.fit_transform(processed[col].astype(str))
                self._encoders[col] = le
        processed = processed.dropna()
        return processed

    def _is_binary_treatment(self, treatment: str) -> bool:
        values = set(self.df[treatment].dropna().unique())
        return values <= {0, 1} or values <= {0.0, 1.0}

    def build_model(self, treatment: str, outcome: str, confounders: list):
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

    def estimate_ate_propensity(self):
        estimate = self.model.estimate_effect(
            self.identified,
            method_name="backdoor.propensity_score_matching",
        )
        return estimate

    def estimate_ate_doubly_robust(self):
        estimate = self.model.estimate_effect(
            self.identified,
            method_name="backdoor.propensity_score_weighting",
        )
        return estimate

    def estimate_dml(self, treatment: str, outcome: str, confounders: list):
        is_binary = self._is_binary_treatment(treatment)
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
        X = self.df[confounders].values
        T = self.df[treatment].values
        Y = self.df[outcome].values
        dml.fit(Y, T, X=X, W=None)
        ate = dml.ate(X=X)
        interval = dml.ate_interval(X=X)
        ate_lb = interval[0][0] if isinstance(interval[0], (list, tuple, np.ndarray)) else interval[0]
        ate_ub = interval[1][0] if isinstance(interval[1], (list, tuple, np.ndarray)) else interval[1]
        return ate, float(ate_lb), float(ate_ub), dml

    def estimate_causal_forest(self, treatment: str, outcome: str, confounders: list):
        is_binary = self._is_binary_treatment(treatment)
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
        X = self.df[confounders].values
        T = self.df[treatment].values
        Y = self.df[outcome].values
        cf.fit(Y, T, X=X, W=None)
        ate = cf.ate(X=X)
        interval = cf.ate_interval(X=X)
        ate_lb = interval[0][0] if isinstance(interval[0], (list, tuple, np.ndarray)) else interval[0]
        ate_ub = interval[1][0] if isinstance(interval[1], (list, tuple, np.ndarray)) else interval[1]
        cate = cf.effect(X)
        return ate, float(ate_lb), float(ate_ub), cate, cf

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
                    self.identified,
                    self.estimate,
                    method_name=method,
                    num_simulations=num_simulations,
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
                results[name] = {"error": str(e)[:120]}
        self.refutation_results = results
        return results

    def compute_cate_by_feature(self, treatment: str, outcome: str,
                                confounders: list, feature_col: str, n_bins=5):
        """Compute heterogeneous effects binned by a feature using CausalForestDML."""
        is_binary = self._is_binary_treatment(treatment)
        other_confounders = [c for c in confounders if c != feature_col]
        all_features = other_confounders + ([feature_col] if feature_col not in other_confounders else [])

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
        X = self.df[all_features].values
        T = self.df[treatment].values
        Y = self.df[outcome].values
        cf.fit(Y, T, X=X, W=None)
        cate_vals = cf.effect(X)

        try:
            bins = pd.qcut(self.df[feature_col], n_bins, labels=False, duplicates="drop")
        except ValueError:
            bins = pd.cut(self.df[feature_col], n_bins, labels=False, duplicates="drop")

        bin_labels = {}
        for bin_idx in sorted(bins.dropna().unique()):
            mask = bins == bin_idx
            if not mask.any():
                continue
            lo = float(self.df.loc[mask, feature_col].min())
            hi = float(self.df.loc[mask, feature_col].max())
            bin_cate = float(np.mean(cate_vals[mask]))
            bin_labels[str(int(bin_idx))] = {
                "range": [lo, hi],
                "cate": bin_cate,
                "count": int(mask.sum()),
            }
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

    def full_analysis(self, treatment: str, outcome: str, confounders: list):
        if len(self.df) < 10:
            raise ValueError("Not enough complete rows after preprocessing (minimum 10 required)")

        self.build_model(treatment, outcome, confounders)
        self.identify_effect()

        results = {}
        is_binary = self._is_binary_treatment(treatment)

        ate_lr = self.estimate_ate_backdoor()
        results["linear_regression"] = {
            "ate": float(ate_lr.value),
            "method": "Backdoor Linear Regression",
        }

        if is_binary:
            try:
                ate_ps = self.estimate_ate_propensity()
                results["propensity_matching"] = {
                    "ate": float(ate_ps.value),
                    "method": "Propensity Score Matching",
                }
            except Exception as e:
                results["propensity_matching"] = {"error": str(e)[:200], "method": "Propensity Score Matching"}

            try:
                ate_dr = self.estimate_ate_doubly_robust()
                results["doubly_robust"] = {
                    "ate": float(ate_dr.value),
                    "method": "Doubly Robust (IPW)",
                }
            except Exception as e:
                results["doubly_robust"] = {"error": str(e)[:200], "method": "Doubly Robust (IPW)"}
        else:
            msg = "Treatment must be binary (0/1) for propensity methods"
            results["propensity_matching"] = {"error": msg, "method": "Propensity Score Matching"}
            results["doubly_robust"] = {"error": msg, "method": "Doubly Robust (IPW)"}

        try:
            dml_ate, dml_lb, dml_ub, _ = self.estimate_dml(treatment, outcome, confounders)
            results["double_ml"] = {
                "ate": float(dml_ate),
                "ate_interval": [dml_lb, dml_ub],
                "method": "Double Machine Learning (LinearDML)",
            }
        except Exception as e:
            results["double_ml"] = {"error": str(e)[:200], "method": "Double ML"}

        try:
            cf_ate, cf_lb, cf_ub, cate_vals, _ = self.estimate_causal_forest(treatment, outcome, confounders)
            results["causal_forest"] = {
                "ate": float(cf_ate),
                "ate_interval": [cf_lb, cf_ub],
                "method": "Causal Forest (CausalForestDML)",
                "cate_distribution": {
                    "mean": float(np.mean(cate_vals)),
                    "std": float(np.std(cate_vals)),
                    "min": float(np.min(cate_vals)),
                    "max": float(np.max(cate_vals)),
                    "p25": float(np.percentile(cate_vals, 25)),
                    "p50": float(np.percentile(cate_vals, 50)),
                    "p75": float(np.percentile(cate_vals, 75)),
                },
                "cate_samples": [float(v) for v in cate_vals[:500]],
            }
        except Exception as e:
            results["causal_forest"] = {"error": str(e)[:200], "method": "Causal Forest"}

        refutations = self.run_refutation_tests(num_simulations=30)
        results["refutations"] = {}
        for name, res in refutations.items():
            if "error" not in res:
                results["refutations"][name] = {
                    "original_estimate": float(res["original_estimate"]),
                    "new_estimate": float(res["new_estimate"]),
                    "p_value": float(res["p_value"]),
                }
            else:
                results["refutations"][name] = {"error": res["error"]}

        results["summary"] = self.get_summary(treatment, outcome, confounders)
        return results
