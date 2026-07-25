import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from output.gsheets_writer import GoogleSheetsWriter
from pipeline.feedback_sync import FeedbackSync


@pytest.fixture
def mock_gspread():
    with patch(
        "output.gsheets_writer.Credentials.from_service_account_file"
    ) as mock_creds, patch("output.gsheets_writer.gspread.authorize") as mock_auth:

        mock_client = MagicMock()
        mock_auth.return_value = mock_client

        mock_spreadsheet = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet

        mock_worksheet = MagicMock()
        mock_worksheet.spreadsheet = mock_spreadsheet
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_spreadsheet.add_worksheet.return_value = mock_worksheet

        yield mock_client, mock_spreadsheet, mock_worksheet


def test_gsheets_writer_init(mock_gspread):
    client, ss, ws = mock_gspread
    writer = GoogleSheetsWriter("config.yaml")
    assert writer.client == client
    assert writer.spreadsheet == ss


def test_gsheets_writer_write(mock_gspread):
    client, ss, ws = mock_gspread
    ws.get_all_values.return_value = []  # Empty sheet

    writer = GoogleSheetsWriter("config.yaml")

    df = pd.DataFrame(
        [
            {
                "transaction_date": "2026-05-21",
                "description": "SWIGGY BANGALORE",
                "amount": 500.0,
                "category": "Food & Dining",
                "transaction_id": "tx123",
            }
        ]
    )

    writer.write(df)
    # Since sheet was empty, update (for headers) and append_rows or update should be called
    assert ws.update.called or ws.append_rows.called


def test_feedback_sync_dry_run(mock_gspread):
    client, ss, ws = mock_gspread

    # Mock worksheet rows for feedback sync
    headers = [
        "transaction_date",
        "description",
        "amount",
        "transaction_type",
        "source_account",
        "category",
        "review_status",
        "reviewed_category",
        "reviewed_at",
        "reviewer_notes",
    ]
    row1 = [
        "2026-05-21",
        "SWIGGY BANGALORE",
        "500.0",
        "debit",
        "ICICI_CC",
        "Uncategorized",
        "corrected",
        "Food & Dining",
        "",
        "test note",
    ]
    ws.get_all_values.return_value = [headers, row1]

    syncer = FeedbackSync("config.yaml")

    with patch.object(syncer, "_append_to_training_data") as mock_append:
        rows_synced, rows_confirmed, rows_skipped = syncer.sync(dry_run=True)

        assert rows_synced == 1
        assert rows_confirmed == 0
        assert rows_skipped == 0

        # In dry run, append to training data and sheet batch update must NOT be called
        mock_append.assert_not_called()
        ws.batch_update.assert_not_called()


def test_feedback_sync_actual_run(mock_gspread):
    client, ss, ws = mock_gspread

    headers = [
        "transaction_date",
        "description",
        "amount",
        "transaction_type",
        "source_account",
        "category",
        "review_status",
        "reviewed_category",
        "reviewed_at",
        "reviewer_notes",
    ]
    row1 = [
        "2026-05-21",
        "SWIGGY BANGALORE",
        "500.0",
        "debit",
        "ICICI_CC",
        "Uncategorized",
        "corrected",
        "Food & Dining",
        "",
        "test note",
    ]
    ws.get_all_values.return_value = [headers, row1]

    syncer = FeedbackSync("config.yaml")

    with patch.object(syncer, "_append_to_training_data") as mock_append:
        rows_synced, rows_confirmed, rows_skipped = syncer.sync(dry_run=False)

        assert rows_synced == 1
        # In actual run, both should be called
        mock_append.assert_called_once()
        ws.batch_update.assert_called_once()
