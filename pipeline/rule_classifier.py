import pandas as pd
import yaml

import os


class RuleClassifier:
    """Stage A: Deterministic keyword and regex classification."""

    def __init__(self, config_path: str = "config.yaml"):
        if os.path.exists(config_path):
            with open(config_path, "r") as file:
                self.config = yaml.safe_load(file) or {}
        else:
            self.config = {}

        self.upi_ids = [str(upi).upper() for upi in self.config.get("own_upi_ids", [])]
        self.account_lasts = [
            str(acc) for acc in self.config.get("own_account_last4", [])
        ]
        self.categories = self.config.get("category_keywords", {})

    def predict_single(self, desc: str) -> tuple:
        """Evaluates a single raw description string for the generator stream."""
        if not desc:
            return None, 0.0, "none"

        desc = str(desc).upper()

        # 1. Highest Priority: Self Transfers
        if any(upi in desc for upi in self.upi_ids) or any(
            acc in desc for acc in self.account_lasts
        ):
            return "Self Transfer", 1.0, "rule"

        # 2. CC Bill Payments
        cc_keywords = ["CC BILL", "CREDIT CARD", "CREDITCARD", "PAYMENT RECEIVED"]
        if any(kw in desc for kw in cc_keywords):
            return "CC Bill Payment", 1.0, "rule"

        # 3. Hardcoded Overrides (Fixed to match your actual config categories)
        if "INDIAN CLEARING CORP" in desc:
            return "Investments & Finance", 1.0, "rule"

        # 4. Config-Driven Keyword Matching
        for category, keywords in self.categories.items():
            if not keywords:
                continue
            for kw in keywords:
                if str(kw).upper() in desc:
                    return category, 1.0, "rule"

        # No rules matched
        return None, 0.0, "none"

    def predict_batch(self, desc_list: list) -> list:
        """Evaluates a batch of descriptions."""
        return [self.predict_single(d) for d in desc_list]

    def _apply_rules(self, row: pd.Series) -> tuple:
        """Legacy wrapper for batch DataFrame processing."""
        if row.get("category") and row["category"] != "Uncategorized":
            return row["category"], row["confidence"], row["classification_method"]

        cat, conf, method = self.predict_single(row.get("description", ""))
        if cat:
            return cat, conf, method

        return "Uncategorized", 0.0, "none"

    def classify(self, df: pd.DataFrame) -> pd.DataFrame:
        """Legacy batch processing entrypoint."""
        if df.empty:
            return df

        results = df.apply(self._apply_rules, axis=1)

        df["category"] = [res[0] for res in results]
        df["confidence"] = [res[1] for res in results]
        df["classification_method"] = [res[2] for res in results]

        return df
