import pytest
import pandas as pd
from pipeline.dashboard_data_layer import DashboardDataLayer


@pytest.fixture
def sample_cat_map():
    return {
        "Groceries & Supermarket": "Expense",
        "Food & Dining": "Expense",
        "DIVIDEND": "Income",
        "Investments & Finance": "Investment",
        "Self Transfer": "Transfer",
        "CC Bill Payment": "Transfer",
    }


def test_corrected_category_resolution_and_stale_bucket_override(sample_cat_map):
    """Proves: a transaction with review_status = Corrected and a reviewed_category
    that maps to a different bucket than its original category ends up in the correct
    (new) bucket, not the stale one.
    """
    layer = DashboardDataLayer(cat_map=sample_cat_map)

    # Originally categorized as 'Self Transfer' (bucket='Transfer'), but later corrected
    # by human review to 'Groceries & Supermarket' (which maps to 'Expense').
    raw_row = {
        "transaction_id": "tx001",
        "category": "Self Transfer",
        "bucket": "Transfer",  # Stale bucket in sheet
        "review_status": "Corrected",
        "reviewed_category": "Groceries & Supermarket",
        "signed_amount": "-1500.00",
        "amount": "1500.00",
        "transaction_type": "debit",
    }

    resolved = layer.resolve_row(raw_row)
    assert resolved["effective_category"] == "Groceries & Supermarket"
    assert resolved["effective_bucket"] == "Expense"
    assert resolved["is_spend"] is True
    assert resolved["is_transfer"] is False
    assert resolved["amount"] == 1500.0


def test_transfer_exclusion_from_totals(sample_cat_map):
    """Proves Transfer-bucket rows never appear in any spend/income/investment total."""
    layer = DashboardDataLayer(cat_map=sample_cat_map)

    df = pd.DataFrame(
        [
            {
                "transaction_id": "tx_exp",
                "category": "Food & Dining",
                "signed_amount": -500.0,
                "amount": 500.0,
                "transaction_type": "debit",
            },
            {
                "transaction_id": "tx_trans_1",
                "category": "Self Transfer",
                "signed_amount": -10000.0,
                "amount": 10000.0,
                "transaction_type": "debit",
            },
            {
                "transaction_id": "tx_trans_2",
                "category": "CC Bill Payment",
                "signed_amount": 25000.0,
                "amount": 25000.0,
                "transaction_type": "credit",
            },
            {
                "transaction_id": "tx_inc",
                "category": "DIVIDEND",
                "signed_amount": 1200.0,
                "amount": 1200.0,
                "transaction_type": "credit",
            },
            {
                "transaction_id": "tx_inv",
                "category": "Investments & Finance",
                "signed_amount": -5000.0,
                "amount": 5000.0,
                "transaction_type": "debit",
            },
        ]
    )

    resolved_df = layer.resolve_dataframe(df)
    kpis = layer.compute_kpis(resolved_df)

    # Spend total should ONLY include Food & Dining (500.0)
    assert kpis["total_spend"] == 500.0
    # Income total should ONLY include DIVIDEND (1200.0)
    assert kpis["total_income"] == 1200.0
    # Investment total should ONLY include Investments & Finance (5000.0)
    assert kpis["total_investment"] == 5000.0
    # Net cash flow = Income (1200) - Spend (500) = 700.0 (excludes Transfer and Investment!)
    assert kpis["net_cash_flow"] == 700.0


def test_description_truncation(sample_cat_map):
    """Proves truncation is verified against at least one real long description_raw value."""
    layer = DashboardDataLayer(cat_map=sample_cat_map)

    # Real long boilerplate string observed in actual GSheets export
    long_boilerplate = (
        "SWIGGY LIMITED BANGALORE IN TRANSACTIONS HIGHLIGHTED IN GREY COLOR "
        "IF ANY DO NOT FORM PART OF PURCHASES OTHER DEBITS TRANSACTIONS FULLY PARTIALLY CONV "
        "AND TERMS AND CONDITIONS APPLY SEE DETAILS ON STATEMENT FOOTER PAGE 2 OF 4"
    )
    raw_row = {
        "transaction_id": "tx_long",
        "description": long_boilerplate,
        "description_raw": long_boilerplate,
        "category": "Food & Dining",
        "amount": 350.0,
    }

    resolved = layer.resolve_row(raw_row)
    assert len(resolved["description"]) <= 60
    assert len(resolved["description_raw"]) <= 60
    assert resolved["description"] == long_boilerplate[:60].strip()


def test_bank_derivation_and_account_preservation():
    layer = DashboardDataLayer()
    row1 = {"source_account": "ICICI_CC", "amount": 100}
    row2 = {"source_account": "ICICI_SAVINGS", "amount": 200}
    row3 = {"source_account": "SBI_CASHBACK", "amount": 300}

    res1 = layer.resolve_row(row1)
    res2 = layer.resolve_row(row2)
    res3 = layer.resolve_row(row3)

    assert res1["bank"] == "ICICI"
    assert res1["source_account"] == "ICICI_CC"
    assert res2["bank"] == "ICICI"
    assert res2["source_account"] == "ICICI_SAVINGS"
    assert res3["bank"] == "SBI"


def test_audit_flags_as_booleans():
    layer = DashboardDataLayer()
    row1 = {"possible_duplicate": "⚠ Duplicate", "needs_review": ""}
    row2 = {"possible_duplicate": "", "needs_review": "⚠ Review"}

    res1 = layer.resolve_row(row1)
    res2 = layer.resolve_row(row2)

    assert res1["possible_duplicate"] is True
    assert res1["needs_review"] is False
    assert res2["possible_duplicate"] is False
    assert res2["needs_review"] is True


def test_confidence_variance_check():
    layer = DashboardDataLayer()
    df = pd.DataFrame(
        [
            {"confidence": 1.0, "classification_method": "rule"},
            {"confidence": 1.0, "classification_method": "ml_exact"},
        ]
    )
    res_df = layer.resolve_dataframe(df)
    kpis = layer.compute_kpis(res_df)

    assert kpis["has_confidence_variance"] is False
    assert kpis["avg_confidence"] == 1.0
