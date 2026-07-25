import pytest
from unittest.mock import MagicMock, patch
from pipeline.feedback_sync import FeedbackSync


@pytest.fixture
def mock_google_sheets_writer():
    with patch("pipeline.feedback_sync.GoogleSheetsWriter") as MockWriter:
        mock_instance = MockWriter.return_value
        mock_spreadsheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_instance.spreadsheet = mock_spreadsheet
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        yield mock_worksheet


def test_feedback_sync_no_data(mock_google_sheets_writer):
    # Setup
    mock_google_sheets_writer.get_all_values.return_value = []

    # Execute
    syncer = FeedbackSync("dummy_config.yaml")
    syncer.sync(dry_run=True)

    # Assert
    mock_google_sheets_writer.batch_update.assert_not_called()


def test_feedback_sync_process_rows(mock_google_sheets_writer):
    # Setup headers matching what we expect
    headers = [
        "transaction_date",
        "description",
        "amount",
        "transaction_type",
        "category",
        "source_account",
        "classification_method",
        "review_status",
        "reviewed_category",
        "reviewed_at",
        "reviewer_notes",
    ]

    # Setup rows
    row_corrected = [
        "2026-07-24",
        "AMAZON",
        "500",
        "debit",
        "Shopping",
        "HDFC",
        "ml",
        "corrected",
        "Food & Dining",
        "",
        "",
    ]
    row_confirmed = [
        "2026-07-24",
        "UBER",
        "100",
        "debit",
        "Transport",
        "ICICI",
        "ml",
        "confirmed",
        "",
        "",
        "",
    ]
    row_pending = [
        "2026-07-24",
        "SWIGGY",
        "200",
        "debit",
        "Food & Dining",
        "SBI",
        "ml",
        "pending",
        "",
        "",
        "",
    ]

    mock_google_sheets_writer.get_all_values.return_value = [
        headers,
        row_corrected,
        row_confirmed,
        row_pending,
    ]

    with patch(
        "pipeline.feedback_sync.FeedbackSync._append_to_training_data"
    ) as mock_append:
        syncer = FeedbackSync("dummy_config.yaml")
        # Run normal sync to trigger writebacks
        syncer.sync(dry_run=False)

        # Assert append was called for the corrected row
        assert mock_append.call_count == 1
        records = mock_append.call_args[0][0]
        assert len(records) == 1
        assert records[0]["description"] == "AMAZON"
        assert records[0]["category"] == "Food & Dining"  # The new category

        # Assert batch_update was called with updates for corrected and confirmed rows
        assert mock_google_sheets_writer.batch_update.call_count == 1
        updates = mock_google_sheets_writer.batch_update.call_args[0][0]

        # We expect 2 cell updates for corrected (status to 'synced', time)
        # We expect 1 cell update for confirmed (time)
        assert len(updates) == 3

        # Verify the A1 notations mapped correctly
        # headers mapping:
        # review_status -> H (8)
        # reviewed_category -> I (9)
        # reviewed_at -> J (10)
        # row_corrected is at index 2 (row 1 is header, 1-based index makes it row 2)
        # However, enumerate starts at 2 in code. So row_corrected is row_idx=2.

        # Check that 'synced' was pushed
        synced_updates = [u for u in updates if u["values"][0][0] == "synced"]
        assert len(synced_updates) == 1
        assert synced_updates[0]["range"] == "H2"

        # Check timestamp pushed
        time_updates = [u for u in updates if u["values"][0][0] != "synced"]
        assert len(time_updates) == 2
        assert time_updates[0]["range"] == "J2"
        assert time_updates[1]["range"] == "J3"
