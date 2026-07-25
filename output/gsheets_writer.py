import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yaml
import os
import re
from gspread_formatting import *


class GoogleSheetsWriter:
    """Handles bulletproof local-compute writing and formatting of Google Sheets with True Upsert."""

    def __init__(self, config_path: str = "config.yaml"):
        if os.path.exists(config_path):
            with open(config_path, "r") as file:
                self.config = yaml.safe_load(file) or {}
        else:
            self.config = {}

        self.creds_path = self.config.get("google_service_account_json") or os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_JSON"
        )
        self.sheet_id = self.config.get("google_sheet_id") or os.getenv(
            "GOOGLE_SHEET_ID"
        )

        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        self.creds = Credentials.from_service_account_file(
            self.creds_path, scopes=self.scopes
        )
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_key(self.sheet_id)

        self.default_category_map = {
            "Food & Dining": "Expense",
            "Shopping": "Expense",
            "Fuel & Transport": "Expense",
            "Groceries & Supermarket": "Expense",
            "Medical & Health": "Expense",
            "Travel & Accommodation": "Expense",
            "Subscriptions & Software": "Expense",
            "Chicken": "Expense",
            "Mutton": "Expense",
            "Jewellery & Gifts": "Expense",
            "Domestic Help & Services": "Expense",
            "Bank Charges & Fees": "Expense",
            "Un Wanted": "Expense",
            "Uncategorized": "Expense",
            "EMI": "Expense",
            "DIVIDEND": "Income",
            "Cashback & Rewards": "Income",
            "Others": "Expense",
            "Investments & Finance": "Investment",
            "Credit Card Payment": "Transfer",
            "CC Bill Payment": "Transfer",
            "Self Transfer": "Transfer",
        }

        self.cols = [
            "transaction_date",
            "description",
            "amount",
            "transaction_type",
            "category",
            "source_account",
            "month",
            "year",
            "confidence",
            "classification_method",
            "review_status",
            "reviewed_category",
            "reviewed_at",
            "reviewer_notes",
            "transaction_id",
            "clean_amount",
            "bucket",
            "signed_amount",
            "needs_review",
            "possible_duplicate",
            "description_raw",
            "merchant_normalized",
        ]

    def _get_or_create_worksheet(self, title: str) -> gspread.Worksheet:
        try:
            return self.spreadsheet.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(title=title, rows="1000", cols="20")

    def reset_worksheets(self):
        """Safe nuke to recreate core tracking tabs."""
        print("\n" + "=" * 60)
        print("  🚨 DANGER: INITIATING NUKE AND PAVE! 🚨")
        print("  WARNING: This will PERMANENTLY DESTROY all historical")
        print("  ledger data, manual reviews, and category mappings.")
        print("  Do NOT interrupt this process.")
        print("=" * 60 + "\n")
        try:
            temp_sheet = self.spreadsheet.add_worksheet(
                title="TEMP_SAFE_TAB", rows="1", cols="1"
            )
        except gspread.exceptions.APIError:
            temp_sheet = self.spreadsheet.worksheet("TEMP_SAFE_TAB")

        for title in [
            "Transactions",
            "Category_Map",
            "Monthly Summary",
            "Category Totals",
            "Merchant_Aliases",
        ]:
            try:
                ws = self.spreadsheet.worksheet(title)
                self.spreadsheet.del_worksheet(ws)
            except gspread.exceptions.WorksheetNotFound:
                pass

        self._get_or_create_worksheet("Transactions")
        self._get_or_create_worksheet("Category_Map")
        self._get_or_create_worksheet("Merchant_Aliases")
        self.spreadsheet.del_worksheet(temp_sheet)
        print("  [OK] Clean slate generated successfully!")

    def _sync_category_map(self) -> dict:
        """Reads Category_Map, seeds defaults if missing, and returns the map."""
        ws_map = self._get_or_create_worksheet("Category_Map")
        existing = ws_map.get_all_values()

        current_map = {}
        if existing and len(existing) > 1:
            for row in existing[1:]:
                if len(row) >= 2:
                    current_map[row[0]] = row[1]

        # Add any missing defaults
        needs_update = False
        for cat, bucket in self.default_category_map.items():
            if cat not in current_map:
                current_map[cat] = bucket
                needs_update = True

        # If it was blank or missing defaults, rewrite it
        if not existing or needs_update:
            ws_map.clear()
            header = ["category", "bucket"]
            rows = [header] + [[c, b] for c, b in current_map.items()]
            try:
                ws_map.update(values=rows, range_name="A1")
            except TypeError:
                ws_map.update("A1", rows)

            fmt = CellFormat(
                backgroundColor=Color(red=0.1, green=0.2, blue=0.4),
                textFormat=TextFormat(
                    bold=True, foregroundColor=Color(red=1, green=1, blue=1)
                ),
            )
            format_cell_range(ws_map, "A1:B1", fmt)

        return current_map

    def _sync_merchant_aliases(self) -> dict:
        ws_alias = self._get_or_create_worksheet("Merchant_Aliases")
        existing = ws_alias.get_all_values()

        default_aliases = {
            "AMZN": "Amazon",
            "AMAZON": "Amazon",
            "FLIPKART": "Flipkart",
            "SWIGGY": "Swiggy",
            "ZOMATO": "Zomato",
            "BLINKIT": "Blinkit",
            "ZEPTO": "Zepto",
            "UBER": "Uber",
            "OLA": "Ola",
            "DMART": "DMart",
        }

        current_map = {}
        if existing and len(existing) > 1:
            for row in existing[1:]:
                if len(row) >= 2 and row[0].strip() != "":
                    current_map[row[0].strip()] = row[1].strip()

        needs_update = False
        for pat, norm in default_aliases.items():
            if pat not in current_map:
                current_map[pat] = norm
                needs_update = True

        if not existing or needs_update:
            ws_alias.clear()
            header = ["raw_pattern", "normalized_name"]
            rows = [header] + [[k, v] for k, v in current_map.items()]
            try:
                ws_alias.update(values=rows, range_name="A1")
            except TypeError:
                ws_alias.update("A1", rows)

            fmt = CellFormat(
                backgroundColor=Color(red=0.1, green=0.2, blue=0.4),
                textFormat=TextFormat(
                    bold=True, foregroundColor=Color(red=1, green=1, blue=1)
                ),
            )
            format_cell_range(ws_alias, "A1:B1", fmt)

        return current_map

    def _compute_helpers(
        self, df: pd.DataFrame, cat_map: dict, alias_map: dict
    ) -> pd.DataFrame:
        """Computes all requested helper columns on a DataFrame."""
        if df.empty:
            return df

        # Ensure description_raw exists
        if "description_raw" not in df.columns:
            df["description_raw"] = ""
        mask = df["description_raw"] == ""
        df.loc[mask, "description_raw"] = df.loc[mask, "description"]

        # Apply truncation heuristic for future rows
        def truncate_corrupted(desc):
            s = str(desc)
            if len(s) < 80:
                return s
            boilerplate = [
                " DAYS 0 145",
                " OTHERS ",
                " TRANSACTIONS HIGHLIGHTED ",
                " APPAREL GROCERY ",
                " MITC ",
                " TERMS AND CONDITIONS ",
                " FINANCE CHARGE ",
                " INTERNATIONAL SPENDS ",
            ]
            for b in boilerplate:
                if b in s:
                    return s.split(b)[0].strip()
            return s

        df["description"] = df["description_raw"].apply(truncate_corrupted)

        # Normalize merchant using basic rules or alias map
        def normalize_merchant(desc):
            desc = str(desc).upper()
            # If matches an alias exactly
            for pat, norm in alias_map.items():
                if pat.upper() in desc:
                    return norm

            desc = re.sub(
                r"^(CAS\s+|RAZ\s+|UPI\s+|CRED\s+CLUB\s+|BILLDESK\s+)", "", desc
            )
            words = re.findall(r"[A-Z]+", desc)
            if len(words) >= 2:
                return f"{words[0]} {words[1]}"
            elif len(words) == 1:
                return words[0]
            return ""

        df["merchant_normalized"] = df["description"].apply(normalize_merchant)

        for col in [
            "review_status",
            "reviewed_category",
            "reviewed_at",
            "reviewer_notes",
        ]:
            if col not in df.columns:
                df[col] = "pending" if col == "review_status" else ""

        # 1. clean_amount
        def clean_amt(val):
            s = str(val).replace("₹", "").replace(",", "").strip()
            try:
                return float(s)
            except ValueError:
                return 0.0

        df["clean_amount"] = df["amount"].apply(clean_amt)

        # 2. bucket
        def get_bucket(cat):
            b = cat_map.get(cat, "")
            if not b:
                print(
                    f"    [WARN] Category '{cat}' has no bucket mapping! Defaulting to 'Expense'."
                )
                b = "Expense"
            return b

        df["bucket"] = df["category"].apply(get_bucket)

        # 3. signed_amount
        df["signed_amount"] = df.apply(
            lambda row: (
                row["clean_amount"]
                if str(row["transaction_type"]).lower() == "credit"
                else -row["clean_amount"]
            ),
            axis=1,
        )

        # 5. needs_review
        def check_review(row):
            if (
                str(row["confidence"]) == "0"
                or str(row["confidence"]) == "0.0"
                or str(row["classification_method"]).lower() == "none"
            ):
                return "⚠ Review"
            return ""

        df["needs_review"] = df.apply(check_review, axis=1)

        # 6. possible_duplicate
        df["possible_duplicate"] = ""
        # Group by date, amount, description and flag if size > 1
        dup_mask = df.duplicated(
            subset=["transaction_date", "clean_amount", "description"], keep=False
        )
        df.loc[dup_mask, "possible_duplicate"] = "⚠ Duplicate"

        return df

    def write_stream(self, transaction_stream, is_reset: bool = False):
        print("  [..] Consuming classification stream...")
        records = list(transaction_stream)
        if not records:
            print("  [OK] No valid transactions found in stream.")
            return 0
        df = pd.DataFrame(records)
        return self.write(df, is_reset)

    def write(self, df: pd.DataFrame, is_reset: bool = False):
        if df.empty:
            return 0

        # IMPORTANT: Drop any in-batch duplicates with the same transaction_id
        # This occurs when parsing overlapping PDFs from scratch.
        if "transaction_id" in df.columns:
            df = df.drop_duplicates(subset=["transaction_id"], keep="first")

        print("  [..] Connecting to Google Sheets...")
        ws_transactions = self._get_or_create_worksheet("Transactions")

        # Ensure base columns exist in df (up to reviewed_notes)
        for c in self.cols[:14]:
            if c not in df.columns:
                df[c] = ""

        # 1. Sync and load Category Map & Alias Map
        cat_map = self._sync_category_map()
        alias_map = self._sync_merchant_aliases()

        # 2. Fetch existing data to find duplicates and row indices
        existing_data = ws_transactions.get_all_values()
        existing_ids = {}

        # If reset or completely blank
        if is_reset or not existing_data:
            existing_df = pd.DataFrame(columns=self.cols)
            # Add header to sheet if it's blank
            if not is_reset and not existing_data:
                ws_transactions.update(values=[self.cols], range_name="A1")
        else:
            header = existing_data[0]
            # Map column names to their indices
            col_idx = {name: i for i, name in enumerate(header)}
            id_col = col_idx.get("transaction_id")

            if id_col is not None:
                # Store row index (1-based, plus 1 for header) for each transaction_id
                for i, row in enumerate(existing_data[1:]):
                    if len(row) > id_col:
                        existing_ids[row[id_col]] = i + 2  # i=0 is row 2 in sheets

            # Build existing DF for duplicate checking
            existing_df = pd.DataFrame(existing_data[1:], columns=header)

        # 3. Split into New vs Existing
        new_records = []
        updates = []

        # To accurately flag duplicates, we should combine the existing sheet data with the new data in Pandas.
        # But we must preserve the exact existing `category` for existing rows.

        # Create a working copy of all data to compute helpers
        working_data = []

        # Add existing rows to working set, preserving their sheet category
        for idx, row in existing_df.iterrows():
            rec = row.to_dict()
            working_data.append(rec)

        # Add new rows to working set
        for idx, row in df.iterrows():
            tid = row["transaction_id"]
            if tid not in existing_ids:
                working_data.append(row.to_dict())
            else:
                # For existing rows, we might want to update confidence/method from the pipeline run
                # but we MUST NOT update category.
                row_idx = existing_ids[tid]
                # Find the record in working_data and update it
                for w in working_data:
                    if w["transaction_id"] == tid:
                        w["confidence"] = row["confidence"]
                        w["classification_method"] = row["classification_method"]
                        break

        working_df = pd.DataFrame(working_data)

        # Compute helpers on entire dataset
        working_df = self._compute_helpers(working_df, cat_map, alias_map)

        # 4. Prepare Batches
        new_df = working_df[
            ~working_df["transaction_id"].isin(existing_ids.keys())
        ].copy()

        for tid, row_num in existing_ids.items():
            # Get the updated row from working_df
            updated_row = working_df[working_df["transaction_id"] == tid].iloc[0]

            # Columns to update: confidence(I), method(J)
            # We preserve K, L, M, N (review fields) which are maintained by the user in the sheet.
            # clean_amount(P), bucket(Q), signed_amount(R), needs_review(S),
            # possible_duplicate(T), description_raw(U), merchant_normalized(V)

            # Format update for I:J
            updates.append(
                {
                    "range": f"I{row_num}:J{row_num}",
                    "values": [
                        [
                            updated_row.get("confidence", 0),
                            updated_row.get("classification_method", ""),
                        ]
                    ],
                }
            )

            # Format update for P:V
            updates.append(
                {
                    "range": f"P{row_num}:V{row_num}",
                    "values": [
                        [
                            updated_row.get("clean_amount", 0),
                            updated_row.get("bucket", ""),
                            updated_row.get("signed_amount", 0),
                            updated_row.get("needs_review", ""),
                            updated_row.get("possible_duplicate", ""),
                            updated_row.get("description_raw", ""),
                            updated_row.get("merchant_normalized", ""),
                        ]
                    ],
                }
            )

        # 5. Write to Sheets

        # If reset, we write the entire working_df
        if is_reset:
            ws_transactions.clear()
            working_df = working_df.sort_values(by="transaction_date", ascending=False)
            write_data = [self.cols] + working_df[self.cols].fillna("").values.tolist()
            import time

            for attempt in range(3):
                try:
                    try:
                        ws_transactions.update(values=write_data, range_name="A1")
                    except TypeError:
                        ws_transactions.update("A1", write_data)
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    print(f"    [WARN] Grid update failed: {e}. Retrying...")
                    time.sleep(2)
            print(f"  [OK] Wrote {len(working_df)} total transactions to the ledger.")

        else:
            # Batch update existing rows
            if updates:
                ws_transactions.batch_update(updates)
                print(
                    f"  [OK] Updated helper columns for {len(existing_ids)} existing transactions."
                )

            # Append new rows
            if not new_df.empty:
                # Ensure they are sorted
                new_df = new_df.sort_values(by="transaction_date", ascending=False)
                append_data = new_df[self.cols].fillna("").values.tolist()
                ws_transactions.append_rows(append_data)
                print(f"  [OK] Appended {len(new_df)} new transactions to the ledger.")
            else:
                print("  [OK] No new transactions to append.")

        # 6. Formatting & Validation
        print("  [..] Applying UI Polish & Dropdowns...")
        ws_transactions.freeze(rows=1)

        header_fmt = CellFormat(
            backgroundColor=Color(red=0.1, green=0.2, blue=0.4),
            textFormat=TextFormat(
                bold=True, foregroundColor=Color(red=1, green=1, blue=1)
            ),
            horizontalAlignment="CENTER",
        )

        # Get dynamic list of categories for dropdown
        # Combine default map keys and any new categories in working_df
        all_cats = set(cat_map.keys()).union(
            set(working_df["category"].astype(str).unique())
        )
        all_cats.discard("")  # Remove empty
        all_cats.discard("nan")  # Remove nan
        validation_rule = DataValidationRule(
            BooleanCondition("ONE_OF_LIST", sorted(list(all_cats))), showCustomUi=True
        )

        batch = batch_updater(self.spreadsheet)
        batch.format_cell_range(ws_transactions, "A1:S1", header_fmt)
        batch.set_data_validation_for_cell_range(
            ws_transactions, "E2:E3000", validation_rule
        )

        import time

        for attempt in range(3):
            try:
                batch.execute()
                break
            except Exception as e:
                if attempt == 2:
                    raise
                print(f"    [WARN] Batch format execution failed: {e}. Retrying...")
                time.sleep(2)

        # 7. Print Summary
        rev_count = len(working_df[working_df["needs_review"] != ""])
        dup_count = len(working_df[working_df["possible_duplicate"] != ""])
        print(f"\n  [INFO] Final Sheet Status:")
        print(
            f"         - New Transactions Added: {len(new_df) if not is_reset else len(working_df)}"
        )
        print(f"         - Flagged for Review: {rev_count}")
        print(f"         - Flagged as Duplicates: {dup_count}")

        return len(df) - len(new_df)
