import pytest
import pandas as pd
from pipeline.normalizer import Normalizer


def test_normalize_single_empty():
    norm = Normalizer()
    assert norm.normalize_single({}) == {}
    assert norm.normalize_single(None) is None


def test_normalize_single_standard():
    norm = Normalizer()
    raw_txn = {
        "description_raw": "amazon!!! india - 123 ",
        "amount": "1250.50",
        "transaction_date": "2026-05-21",
        "source_account": "ICICI_CC",
    }
    result = norm.normalize_single(raw_txn)

    assert result["description"] == "AMAZON INDIA 123"
    assert result["amount"] == 1250.50
    assert result["transaction_date"] == "2026-05-21"
    assert result["category"] == "Uncategorized"
    assert result["confidence"] == 0.0
    assert result["classification_method"] == "none"
    assert result["review_status"] == "pending"
    assert result["reviewed_category"] == ""
    assert result["value_date"] == "2026-05-21"
    assert result["balance"] == 0.0
    assert result["ref_no"] == "Not Available"


def test_normalize_single_invalid_amount_and_date():
    norm = Normalizer()
    raw_txn = {
        "description_raw": "test desc",
        "amount": "invalid_amt",
        "transaction_date": "not-a-date",
    }
    result = norm.normalize_single(raw_txn)
    assert result["amount"] == 0.0
    # Date should remain unchanged if pd.to_datetime fails
    assert result["transaction_date"] == "not-a-date"


def test_normalize_dataframe():
    norm = Normalizer()
    df = pd.DataFrame(
        [
            {
                "description_raw": "swiggy @ bangalore",
                "amount": 450,
                "transaction_date": "05/21/2026",
            }
        ]
    )
    res_df = norm.normalize(df)
    assert len(res_df) == 1
    assert res_df.iloc[0]["description"] == "SWIGGY BANGALORE"
    assert res_df.iloc[0]["category"] == "Uncategorized"
    assert res_df.iloc[0]["review_status"] == "pending"
