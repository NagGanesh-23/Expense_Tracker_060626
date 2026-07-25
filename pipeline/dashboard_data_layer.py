import pandas as pd
from typing import Dict, Any, List, Optional


class DashboardDataLayer:
    """Read-only data resolution and rollup layer for the Interactive Expense Dashboard.

    Enforces all Section 6.1 resolution rules:
    1. effective_category override from reviewed_category on Corrected status.
    2. effective_bucket lookup against live Category_Map (never trust stored bucket).
    3. Spend/Income/Investment separation; total exclusion of Transfer rows.
    4. Bank derivation from source_account prefix before '_'.
    5. Truncation of description and description_raw to ~60 characters.
    6. First-class boolean extraction for possible_duplicate and needs_review.
    """

    def __init__(
        self,
        cat_map: Optional[Dict[str, str]] = None,
        alias_map: Optional[Dict[str, str]] = None,
    ):
        self.cat_map = cat_map or {}
        self.alias_map = alias_map or {}

    def resolve_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Applies resolution rules to a single raw transaction row."""
        # 1. effective_category
        rev_status = str(row.get("review_status", "")).strip()
        rev_cat = str(row.get("reviewed_category", "")).strip()
        orig_cat = str(row.get("category", "Uncategorized")).strip()

        if rev_status.lower() == "corrected" and rev_cat != "":
            effective_category = rev_cat
        else:
            effective_category = orig_cat if orig_cat else "Uncategorized"

        # 2. effective_bucket
        # Never use stored 'bucket' directly as it goes stale after correction
        effective_bucket = self.cat_map.get(effective_category, "Expense")
        if not effective_bucket:
            effective_bucket = "Expense"

        # 3. signed_amount & math normalization
        raw_signed = row.get("signed_amount")
        if raw_signed is not None and str(raw_signed).strip() != "":
            try:
                signed_amount = float(
                    str(raw_signed).replace("₹", "").replace(",", "").strip()
                )
            except ValueError:
                signed_amount = 0.0
        else:
            # Fallback derivation from amount / clean_amount and transaction_type
            raw_amt = row.get("clean_amount", row.get("amount", 0))
            try:
                amt = float(str(raw_amt).replace("₹", "").replace(",", "").strip())
            except ValueError:
                amt = 0.0
            tx_type = str(row.get("transaction_type", "")).strip().lower()
            signed_amount = amt if tx_type == "credit" else -amt

        abs_amount = abs(signed_amount)

        # Buckets separation
        is_spend = effective_bucket == "Expense"
        is_income = effective_bucket == "Income"
        is_investment = effective_bucket == "Investment"
        is_transfer = effective_bucket == "Transfer"

        # 4. bank derivation
        source_account = str(row.get("source_account", "")).strip()
        if "_" in source_account:
            bank = source_account.split("_")[0]
        else:
            bank = source_account if source_account else "UNKNOWN"

        # 5. truncation of descriptions to ~60 chars
        desc = str(row.get("description", "")).strip()[:60]
        desc_raw = str(
            row.get("description_raw", row.get("raw_description", ""))
        ).strip()[:60]

        # 6. audit flags as first-class booleans
        dup_val = str(row.get("possible_duplicate", "")).strip()
        possible_duplicate = bool(
            dup_val and dup_val.lower() != "false" and dup_val != "0"
        )

        rev_val = str(row.get("needs_review", "")).strip()
        needs_review = bool(rev_val and rev_val.lower() != "false" and rev_val != "0")

        # Confidence & method
        try:
            confidence = float(row.get("confidence", 0.0))
        except (ValueError, TypeError):
            confidence = 0.0

        method = str(row.get("classification_method", "")).strip().lower()
        if not method:
            method = "none"

        # Merchant normalization fallback
        merchant_norm = str(row.get("merchant_normalized", "")).strip()
        if not merchant_norm:
            merchant_norm = desc.upper()

        return {
            "transaction_id": str(row.get("transaction_id", "")).strip(),
            "transaction_date": str(row.get("transaction_date", "")).strip(),
            "description": desc,
            "description_raw": desc_raw,
            "amount": abs_amount,
            "signed_amount": signed_amount,
            "transaction_type": str(row.get("transaction_type", "")).strip().lower(),
            "source_account": source_account,
            "bank": bank,
            "category": orig_cat,
            "review_status": rev_status,
            "reviewed_category": rev_cat,
            "effective_category": effective_category,
            "effective_bucket": effective_bucket,
            "is_spend": is_spend,
            "is_income": is_income,
            "is_investment": is_investment,
            "is_transfer": is_transfer,
            "confidence": confidence,
            "classification_method": method,
            "possible_duplicate": possible_duplicate,
            "needs_review": needs_review,
            "merchant_normalized": merchant_norm,
            "month": row.get("month", ""),
            "year": row.get("year", ""),
            "reviewer_notes": str(row.get("reviewer_notes", "")).strip(),
        }

    def resolve_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies resolution rules across a DataFrame and returns a clean, typed DataFrame."""
        if df.empty:
            return pd.DataFrame()
        records = df.to_dict(orient="records")
        resolved = [self.resolve_row(r) for r in records]
        return pd.DataFrame(resolved)

    def compute_kpis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Computes all confirmed KPIs from Section 6 over a resolved DataFrame."""
        if df.empty:
            return {
                "total_spend": 0.0,
                "total_income": 0.0,
                "total_investment": 0.0,
                "net_cash_flow": 0.0,
                "spend_by_category": {},
                "spend_by_bank": {},
                "spend_by_account": {},
                "tx_count_by_bank": {},
                "tx_count_by_account": {},
                "method_distribution": {},
                "correction_rate": 0.0,
                "has_confidence_variance": False,
                "avg_confidence": 0.0,
                "possible_duplicates_count": 0,
                "needs_review_count": 0,
                "top_merchants": {},
            }

        # Spend rows only (excludes Transfer and Investment)
        spend_df = df[df["is_spend"] == True]
        total_spend = float(spend_df["amount"].sum())

        # Income rows only
        income_df = df[df["is_income"] == True]
        total_income = float(income_df["signed_amount"].sum())

        # Investment rows only
        invest_df = df[df["is_investment"] == True]
        total_investment = float(invest_df["amount"].sum())

        # Net cash flow = Income - Spend (Transfer and Investment excluded)
        net_cash_flow = total_income - total_spend

        # Groupings
        spend_by_cat = spend_df.groupby("effective_category")["amount"].sum().to_dict()
        spend_by_bank = spend_df.groupby("bank")["amount"].sum().to_dict()
        spend_by_acct = spend_df.groupby("source_account")["amount"].sum().to_dict()

        tx_count_by_bank = spend_df.groupby("bank").size().to_dict()
        tx_count_by_acct = spend_df.groupby("source_account").size().to_dict()

        # Classification health
        total_count = len(df)
        method_counts = df["classification_method"].value_counts().to_dict()
        method_dist = (
            {m: (c / total_count) * 100.0 for m, c in method_counts.items()}
            if total_count > 0
            else {}
        )

        corrected_count = len(df[df["review_status"].str.lower() == "corrected"])
        correction_rate = (
            (corrected_count / total_count) * 100.0 if total_count > 0 else 0.0
        )

        conf_series = df["confidence"]
        has_conf_variance = (
            bool(conf_series.max() != conf_series.min())
            if not conf_series.empty
            else False
        )
        avg_conf = float(conf_series.mean()) if not conf_series.empty else 0.0

        # Audit & anomalies
        dup_count = (
            int(df["possible_duplicate"].sum())
            if "possible_duplicate" in df.columns
            else 0
        )
        rev_count = int(df["needs_review"].sum()) if "needs_review" in df.columns else 0

        # Top payees/merchants (Expense bucket only)
        top_merchants = (
            spend_df.groupby("merchant_normalized")["amount"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .to_dict()
        )

        return {
            "total_spend": total_spend,
            "total_income": total_income,
            "total_investment": total_investment,
            "net_cash_flow": net_cash_flow,
            "spend_by_category": spend_by_cat,
            "spend_by_bank": spend_by_bank,
            "spend_by_account": spend_by_acct,
            "tx_count_by_bank": tx_count_by_bank,
            "tx_count_by_account": tx_count_by_acct,
            "method_distribution": method_dist,
            "correction_rate": correction_rate,
            "has_confidence_variance": has_conf_variance,
            "avg_confidence": avg_conf,
            "possible_duplicates_count": dup_count,
            "needs_review_count": rev_count,
            "top_merchants": top_merchants,
        }
