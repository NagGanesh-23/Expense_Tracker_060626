import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yaml
import re
from gspread_formatting import *
import time


def main():
    print("Starting cleanup...")
    # 1. Connect to Google Sheets
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    creds = Credentials.from_service_account_file(
        config.get("google_service_account_json"),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.get("google_sheet_id"))
    ws = sheet.worksheet("Transactions")

    data = ws.get_all_values()
    if not data:
        print("No data found.")
        return

    df = pd.DataFrame(data[1:], columns=data[0])

    # 2. Delete empty rows
    initial_len = len(df)
    df = df[df["transaction_id"].astype(str).str.strip() != ""]
    df = df[df["transaction_id"].notna()]
    print(f"Removed {initial_len - len(df)} empty rows.")

    # 3. Delete exact transaction_id duplicates
    initial_len = len(df)
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")
    print(f"Removed {initial_len - len(df)} exact transaction_id duplicates.")

    # 4. Add columns if not present
    new_cols = ["description_raw", "merchant_normalized", "review_status"]
    for c in new_cols:
        if c not in df.columns:
            df[c] = ""

    # Copy original descriptions to description_raw
    mask = df["description_raw"] == ""
    df.loc[mask, "description_raw"] = df.loc[mask, "description"]

    # 5. Apply truncation heuristic
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
        return s[:120].strip()

    df["description_raw"] = df["description_raw"].apply(
        lambda d: truncate_corrupted(d)[:120].strip()
    )
    df["description"] = df["description_raw"].apply(truncate_corrupted)

    # 6. Normalize merchant
    def normalize_merchant(desc):
        desc = str(desc).upper()
        # Common prefixes to strip
        desc = re.sub(r"^(CAS\s+|RAZ\s+|UPI\s+|CRED\s+CLUB\s+|BILLDESK\s+)", "", desc)
        # Extract first 1-2 words
        words = re.findall(r"[A-Z]+", desc)
        if len(words) >= 2:
            return f"{words[0]} {words[1]}"
        elif len(words) == 1:
            return words[0]
        return ""

    df["merchant_normalized"] = df["description"].apply(normalize_merchant)

    # 7. Create/Update Merchant_Aliases tab
    try:
        ws_aliases = sheet.worksheet("Merchant_Aliases")
    except gspread.exceptions.WorksheetNotFound:
        ws_aliases = sheet.add_worksheet(
            title="Merchant_Aliases", rows="1000", cols="5"
        )
        ws_aliases.update("A1", [["raw_pattern", "normalized_name"]])
        print("Created Merchant_Aliases tab.")

    # Let's ensure the column order is exactly what we want, plus the new ones
    final_cols = [
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
        "transaction_id",
        "clean_amount",
        "bucket",
        "signed_amount",
        "display_description",
        "needs_review",
        "possible_duplicate",
        "description_raw",
        "merchant_normalized",
        "review_status",
    ]

    # Keep only final_cols and fill NA
    for c in final_cols:
        if c not in df.columns:
            df[c] = ""
    df = df[final_cols].fillna("")

    # 8. Write back to Transactions
    print("Clearing and rewriting Transactions...")
    ws.clear()
    write_data = [final_cols] + df.values.tolist()

    # Batch the updates or write in one go
    for attempt in range(3):
        try:
            ws.update(values=write_data, range_name="A1")
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Update failed: {e}. Retrying...")
            time.sleep(2)

    # Reset header formatting
    header_fmt = CellFormat(
        backgroundColor=Color(red=0.1, green=0.2, blue=0.4),
        textFormat=TextFormat(bold=True, foregroundColor=Color(red=1, green=1, blue=1)),
        horizontalAlignment="CENTER",
    )
    format_cell_range(ws, "A1:T1", header_fmt)
    ws.freeze(rows=1)

    print("Cleanup complete!")


if __name__ == "__main__":
    main()
