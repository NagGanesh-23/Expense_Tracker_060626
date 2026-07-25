import os
import pandas as pd
import pytest
from scripts.audit_output import run_audit


@pytest.fixture
def temp_csv(tmp_path):
    """Fixture to provide a temporary CSV path."""
    return str(tmp_path / "test_transactions.csv")


def test_audit_optional_fields_pass(temp_csv):
    # A row with blank reviewed_category (optional) should NOT fail
    df = pd.DataFrame(
        {
            "transaction_date": ["2026-07-24"],
            "description": ["Valid Description"],
            "amount": [100.0],
            "source_account": ["AXIS"],
            "review_status": ["pending"],
            "reviewed_category": [""],  # Optional
            "reviewed_at": [""],  # Optional
            "reviewer_notes": [""],  # Optional
        }
    )
    df.to_csv(temp_csv, index=False)

    # Audit should pass (returns True)
    assert run_audit(csv_path=temp_csv, exit_on_fail=False) is True


def test_audit_missing_review_status_fails(temp_csv):
    # A row with blank review_status SHOULD fail
    df = pd.DataFrame(
        {
            "transaction_date": ["2026-07-24"],
            "description": ["Valid Description"],
            "amount": [100.0],
            "source_account": ["AXIS"],
            "review_status": [""],  # Required, blank -> FAIL
            "reviewed_category": [""],
            "reviewed_at": [""],
            "reviewer_notes": [""],
        }
    )
    df.to_csv(temp_csv, index=False)

    # Audit should fail (returns False)
    assert run_audit(csv_path=temp_csv, exit_on_fail=False) is False


def test_audit_missing_core_field_fails(temp_csv):
    # A row with blank core field (e.g. description) should still fail as before
    df = pd.DataFrame(
        {
            "transaction_date": ["2026-07-24"],
            "description": [""],  # Core field missing -> FAIL
            "amount": [100.0],
            "source_account": ["AXIS"],
            "review_status": ["pending"],
            "reviewed_category": [""],
            "reviewed_at": [""],
            "reviewer_notes": [""],
        }
    )
    df.to_csv(temp_csv, index=False)

    # Audit should fail (returns False)
    assert run_audit(csv_path=temp_csv, exit_on_fail=False) is False
