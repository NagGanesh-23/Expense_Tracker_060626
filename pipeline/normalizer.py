import pandas as pd
import re


class Normalizer:
    """Standardizes data types and cleans text for classification."""

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        # 1. Clean the descriptions (remove extra spaces, special chars)
        # We keep alphanumeric and spaces, convert to uppercase for easier rule matching
        df["description"] = df["description_raw"].apply(
            lambda x: re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9\s]", " ", str(x)))
            .strip()
            .upper()
        )

        # 2. Ensure data types are strict
        df["amount"] = df["amount"].astype(float)
        df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.strftime(
            "%Y-%m-%d"
        )

        # 3. Add placeholder columns for the classification stages
        if "category" not in df.columns:
            df["category"] = "Uncategorized"
            df["confidence"] = 0.0
            df["classification_method"] = "none"

        # 4. Add placeholders for manual review
        if "review_status" not in df.columns:
            df["review_status"] = "pending"
            df["reviewed_category"] = ""
            df["reviewed_at"] = ""
            df["reviewer_notes"] = ""

        return df

    def normalize_single(self, txn: dict) -> dict:
        """Cleans and standardizes a single transaction dictionary for the stream."""
        if not txn:
            return txn

        desc = txn.get("description_raw", "")
        if desc in ["", "None", "nan", "NaN", None]:
            desc = "NO DESCRIPTION"
            txn["description_raw"] = desc

        # We keep alphanumeric and spaces, convert to uppercase for easier rule matching
        cleaned_desc = (
            re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9\s]", " ", str(desc)))
            .strip()
            .upper()
        )
        txn["description"] = cleaned_desc

        # Ensure data types are strict
        try:
            # Handle empty strings or None
            amt = txn.get("amount")
            txn["amount"] = float(amt) if amt else 0.0
        except ValueError:
            txn["amount"] = 0.0

        if txn.get("transaction_date"):
            try:
                txn["transaction_date"] = pd.to_datetime(
                    txn["transaction_date"]
                ).strftime("%Y-%m-%d")
            except Exception:
                pass

        # Add placeholder columns for the classification stages
        if "category" not in txn:
            txn["category"] = "Uncategorized"
            txn["confidence"] = 0.0
            txn["classification_method"] = "none"

        # Add placeholders for manual review
        if "review_status" not in txn:
            txn["review_status"] = "pending"
            txn["reviewed_category"] = ""
            txn["reviewed_at"] = ""
            txn["reviewer_notes"] = ""

        # Fill missing values to pass audit
        if not txn.get("value_date"):
            txn["value_date"] = txn.get("transaction_date")
        if not txn.get("balance"):
            txn["balance"] = 0.0
        if not txn.get("ref_no") or str(txn.get("ref_no")).strip() in [
            "",
            "N/A",
            "nan",
            "NaN",
        ]:
            txn["ref_no"] = "Not Available"

        return txn
