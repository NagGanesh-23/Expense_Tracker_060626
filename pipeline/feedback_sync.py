import os
import csv
import logging
import sys
import argparse
import collections
from datetime import datetime, timezone
from output.gsheets_writer import GoogleSheetsWriter

# Set up logging for the feedback sync module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class FeedbackSync:
    """Reads manual reviews from Google Sheets and feeds them back into the ML training data."""

    def __init__(self, config_path: str = "config.yaml"):
        # Re-use the existing GoogleSheetsWriter for robust auth & connection logic
        self.writer = GoogleSheetsWriter(config_path)
        self.training_file = "models/training_data.csv"

        # Determine the columns to write to training_data.csv based on the schema
        self.training_schema = [
            "transaction_date",
            "description",
            "amount",
            "transaction_type",
            "source_account",
            "category",
        ]

    def sync(self, dry_run: bool = False):
        """Fetches transactions from the sheet, applies feedback, and triggers a batch write-back."""
        worksheet = self.writer.spreadsheet.worksheet("Transactions")

        logger.info(f"Fetching rows from 'Transactions' worksheet...")
        all_values = worksheet.get_all_values()

        if not all_values:
            logger.warning("No data found in the 'Transactions' worksheet.")
            return 0, 0, 0

        headers = all_values[0]

        # Safe column indexing mapping
        header_map = {h: i for i, h in enumerate(headers)}

        required_headers = [
            "review_status",
            "category",
            "transaction_date",
            "description",
            "amount",
            "transaction_type",
            "source_account",
        ]

        missing_headers = [h for h in required_headers if h not in header_map]
        if missing_headers:
            logger.error(f"Missing required headers in sheet: {missing_headers}")
            return 0, 0, 0

        new_training_records = []
        cells_to_update = []

        rows_synced = 0
        rows_confirmed = 0
        rows_skipped = 0

        current_iso_time = datetime.now(timezone.utc).isoformat()

        for row_idx, row in enumerate(
            all_values[1:], start=2
        ):  # 1-based index, row 1 is headers

            # Pad row to match headers length if needed
            if len(row) < len(headers):
                row.extend([""] * (len(headers) - len(row)))

            review_status = row[header_map["review_status"]].strip().lower()
            reviewed_category = row[header_map["reviewed_category"]].strip()
            category = row[header_map["category"]].strip()

            if review_status == "corrected":
                if reviewed_category and reviewed_category != category:
                    # Construct training record
                    record = {
                        "transaction_date": row[header_map["transaction_date"]],
                        "description": row[header_map["description"]],
                        "amount": row[header_map["amount"]],
                        "transaction_type": row[header_map["transaction_type"]],
                        "source_account": row[header_map["source_account"]],
                        "category": reviewed_category,
                    }
                    new_training_records.append(record)

                    # Prepare update: set review_status to 'synced' and timestamp
                    col_status_idx = header_map["review_status"] + 1
                    col_time_idx = header_map["reviewed_at"] + 1

                    # Keep track of cell updates
                    cells_to_update.append(
                        {
                            "range": gspread_cell_name(row_idx, col_status_idx),
                            "values": [["synced"]],
                        }
                    )
                    cells_to_update.append(
                        {
                            "range": gspread_cell_name(row_idx, col_time_idx),
                            "values": [[current_iso_time]],
                        }
                    )

                    rows_synced += 1
                else:
                    logger.warning(
                        f"Row {row_idx}: marked 'corrected' but missing or matching reviewed_category. Skipping."
                    )
                    rows_skipped += 1

            elif review_status == "confirmed":
                # Stamp the time but leave it as confirmed
                col_time_idx = header_map["reviewed_at"] + 1
                cells_to_update.append(
                    {
                        "range": gspread_cell_name(row_idx, col_time_idx),
                        "values": [[current_iso_time]],
                    }
                )
                rows_confirmed += 1

        # Commit to training file if there are records
        if new_training_records:
            if not dry_run:
                self._append_to_training_data(new_training_records)
                logger.info(
                    f"Appended {len(new_training_records)} corrected records to {self.training_file}."
                )
            else:
                logger.info(
                    f"[DRY-RUN] Would append {len(new_training_records)} records to {self.training_file}."
                )

        # Batch update google sheet
        if cells_to_update:
            if not dry_run:
                worksheet.batch_update(cells_to_update)
                logger.info(
                    "Successfully updated Google Sheet with new statuses and timestamps."
                )
            else:
                logger.info(
                    f"[DRY-RUN] Would batch_update {len(cells_to_update)} cells in Google Sheet."
                )

        # Logging summary
        logger.info(f"=== Feedback Sync Summary ===")
        logger.info(f"Corrected rows synced: {rows_synced}")
        logger.info(f"Confirmed rows stamped: {rows_confirmed}")
        logger.info(f"Corrected rows skipped (malformed): {rows_skipped}")

        return rows_synced, rows_confirmed, rows_skipped

    def _append_to_training_data(self, records: list):
        """Appends the list of dictionaries to the local training CSV file."""
        if not records:
            return

        file_exists = os.path.isfile(self.training_file)

        # Ensure the models directory exists
        os.makedirs(os.path.dirname(self.training_file), exist_ok=True)

        with open(self.training_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.training_schema)
            if not file_exists:
                writer.writeheader()
            for record in records:
                writer.writerow(record)

    def rebuild_training_data(self):
        """Completely overwrites the training data file with all rows from Google Sheets."""
        worksheet = self.writer.spreadsheet.worksheet("Transactions")

        logger.info(
            f"Fetching ALL rows from 'Transactions' worksheet for full rebuild..."
        )
        all_values = worksheet.get_all_values()

        if len(all_values) <= 1:
            logger.warning("No data found in the 'Transactions' worksheet.")
            return

        headers = all_values[0]
        header_map = {h: i for i, h in enumerate(headers)}

        new_training_records = []
        rows_skipped = 0
        category_counts = collections.defaultdict(int)

        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) < len(headers):
                row.extend([""] * (len(headers) - len(row)))

            def get_val(col_name):
                return (
                    row[header_map[col_name]].strip()
                    if col_name in header_map and header_map[col_name] < len(row)
                    else ""
                )

            reviewed_cat = get_val("reviewed_category")
            base_cat = get_val("category")

            # Ground truth is reviewed_category if present, else category
            final_cat = reviewed_cat if reviewed_cat else base_cat

            if not final_cat or final_cat.lower() == "uncategorized":
                logger.warning(
                    f"Row {row_idx}: Skipped due to blank or 'Uncategorized' label."
                )
                rows_skipped += 1
                continue

            record = {
                "transaction_date": get_val("transaction_date"),
                "description": get_val("description"),
                "amount": get_val("amount"),
                "transaction_type": get_val("transaction_type"),
                "source_account": get_val("source_account"),
                "category": final_cat,
            }
            new_training_records.append(record)
            category_counts[final_cat] += 1

        # Overwrite the file
        if os.path.exists(self.training_file):
            os.remove(self.training_file)

        self._append_to_training_data(new_training_records)

        logger.info(f"=== REBUILD COMPLETE ===")
        logger.info(f"Total rows written: {len(new_training_records)}")
        logger.info(f"Rows skipped: {rows_skipped}")
        logger.info(f"Category Distribution: {dict(category_counts)}")


def gspread_cell_name(row: int, col: int) -> str:
    """Helper to convert row, col to A1 notation."""
    dividend = col
    column_name = ""
    while dividend > 0:
        modulo = (dividend - 1) % 26
        column_name = chr(65 + modulo) + column_name
        dividend = int((dividend - modulo) / 26)
    return f"{column_name}{row}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Sheets Feedback Sync")
    parser.add_argument(
        "--rebuild-training-data",
        action="store_true",
        help="DANGER: Completely overwrite training_data.csv with all rows from Google Sheets.",
    )
    parser.add_argument(
        "--yes", action="store_true", help="Confirm destructive overwrite."
    )
    args = parser.parse_args()

    sync = FeedbackSync("config.yaml")

    if args.rebuild_training_data:
        if not args.yes:
            print(
                "ERROR: --rebuild-training-data is a destructive operation. You must append --yes to confirm."
            )
            sys.exit(1)
        sync.rebuild_training_data()
    else:
        sync.sync()
