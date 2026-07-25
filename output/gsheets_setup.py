import gspread
from google.oauth2.service_account import Credentials
import yaml
import os
from gspread_formatting import *


def setup_sheet(config_path: str = "config.yaml"):
    print("\n[..] Connecting to Google Sheets for setup...")

    if os.path.exists(config_path):
        with open(config_path, "r") as file:
            config = yaml.safe_load(file) or {}
    else:
        config = {}

    creds_path = config.get("google_service_account_json") or os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON"
    )
    sheet_id = config.get("google_sheet_id") or os.getenv("GOOGLE_SHEET_ID")
    threshold = config.get("review_confidence_threshold", 0.70)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        ws_transactions = spreadsheet.worksheet("Transactions")
    except gspread.exceptions.WorksheetNotFound:
        print("  [WARN] 'Transactions' worksheet not found. Please run a sync first.")
        return

    try:
        ws_map = spreadsheet.worksheet("Category_Map")
        existing_map = ws_map.get_all_values()
        categories = []
        if existing_map and len(existing_map) > 1:
            for row in existing_map[1:]:
                if len(row) > 0 and row[0].strip() != "":
                    categories.append(row[0].strip())
    except gspread.exceptions.WorksheetNotFound:
        categories = list(config.get("category_keywords", {}).keys())

    # Remove duplicates and add Uncategorized
    categories = sorted(list(set(categories).union({"Uncategorized"})))

    # 1. Freeze header
    print("  [..] Freezing header row...")
    ws_transactions.freeze(rows=1)

    batch = batch_updater(spreadsheet)

    # 2. Data Validation for reviewed_category (Column L)
    print("  [..] Adding data validation dropdowns...")
    if categories:
        validation_rule = DataValidationRule(
            BooleanCondition("ONE_OF_LIST", categories), showCustomUi=True
        )
        batch.set_data_validation_for_cell_range(
            ws_transactions, "L2:L3000", validation_rule
        )

    # Also add Data Validation for review_status (Column K)
    status_rule = DataValidationRule(
        BooleanCondition(
            "ONE_OF_LIST", ["pending", "confirmed", "corrected", "synced"]
        ),
        showCustomUi=True,
    )
    batch.set_data_validation_for_cell_range(ws_transactions, "K2:K3000", status_rule)

    # 3. Conditional Formatting for review_status (Column K) based on Method/Confidence
    print("  [..] Applying conditional formatting...")
    # Yellow if Method is LLM or Confidence is low or Method is none/rule (depending on how you want to review)
    # Actually, we want to highlight rows that need review.
    # Formula: =OR($J2="llm", $I2<0.7, $J2="none")
    formula = f'=OR($J2="llm", $I2<{threshold}, $J2="none")'
    rule = ConditionalFormatRule(
        ranges=[GridRange.from_a1_range("K2:K3000", ws_transactions)],
        booleanRule=BooleanRule(
            condition=BooleanCondition("CUSTOM_FORMULA", [formula]),
            format=CellFormat(backgroundColor=Color(red=1.0, green=0.9, blue=0.6)),
        ),
    )

    # Also format review_status text colors (e.g. green if synced/confirmed)
    rule_synced = ConditionalFormatRule(
        ranges=[GridRange.from_a1_range("K2:K3000", ws_transactions)],
        booleanRule=BooleanRule(
            condition=BooleanCondition("TEXT_EQ", ["synced"]),
            format=CellFormat(backgroundColor=Color(red=0.8, green=1.0, blue=0.8)),
        ),
    )

    rules = get_conditional_format_rules(ws_transactions)
    rules.clear()
    rules.append(rule)
    rules.append(rule_synced)
    rules.save()

    # Execute batch formatting
    try:
        batch.execute()
    except Exception as e:
        print(f"  [WARN] Batch formatting failed: {e}")

    # 4. Basic Filter
    print("  [..] Applying basic filter...")
    try:
        ws_transactions.set_basic_filter("A1:V3000")
    except Exception as e:
        print(f"  [WARN] Could not set basic filter: {e}")

    print("  [OK] Setup complete!")


if __name__ == "__main__":
    setup_sheet()
