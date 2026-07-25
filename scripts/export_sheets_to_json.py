import gspread
from google.oauth2.service_account import Credentials
import json
import os
import yaml


def export_sheet_data(
    config_path="config.yaml", output_path="dashboard/public/api/data.json"
):
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    creds_path = config.get("google_service_account_json") or os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON", "credentials/service_account.json"
    )
    if not os.path.exists(creds_path) and os.getenv("GOOGLE_CREDS_JSON"):
        os.makedirs(os.path.dirname(creds_path) or "credentials", exist_ok=True)
        with open(creds_path, "w", encoding="utf-8") as f:
            f.write(os.getenv("GOOGLE_CREDS_JSON"))
    sheet_id = config.get("google_sheet_id") or os.getenv(
        "GOOGLE_SHEET_ID", "1gnmlyYsQrzhBDEtsXrdjHZxcU40rzwtZpvSxxx5OSTI"
    )
    sheet_name = config.get("google_sheet_name") or os.getenv(
        "GOOGLE_SHEET_NAME", "My Expense Tracker"
    )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)

    try:
        if sheet_id:
            sh = client.open_by_key(sheet_id)
        else:
            sh = client.open(sheet_name)
    except Exception as e:
        print(f"Failed to open by ID {sheet_id}, trying by name {sheet_name}: {e}")
        sh = client.open(sheet_name)

    print(f"Connected to Google Sheet: '{sh.title}' (ID: {sh.id})")

    # Fetch tabs
    try:
        txns_ws = sh.worksheet("Transactions")
        raw_txns = txns_ws.get_all_records()
        txns = []
        for row in raw_txns:
            if str(row.get("possible_duplicate", "")).strip() == "⚠ Duplicate":
                continue
            if "description_raw" in row and len(str(row["description_raw"])) > 120:
                row["description_raw"] = str(row["description_raw"])[:120].strip()
            if "description" in row and len(str(row["description"])) > 120:
                row["description"] = str(row["description"])[:120].strip()
            txns.append(row)
    except Exception as e:
        print(f"Warning: Could not fetch Transactions tab: {e}")
        txns = []

    try:
        cat_ws = sh.worksheet("Category_Map")
        cat_map = cat_ws.get_all_records()
    except Exception as e:
        print(f"Warning: Could not fetch Category_Map tab: {e}")
        cat_map = []

    try:
        alias_ws = sh.worksheet("Merchant_Aliases")
        aliases = alias_ws.get_all_records()
    except Exception as e:
        print(f"Warning: Could not fetch Merchant_Aliases tab: {e}")
        aliases = []

    data = {"transactions": txns, "categoryMap": cat_map, "merchantAliases": aliases}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(
        f"Successfully exported {len(txns)} transactions, {len(cat_map)} categories, and {len(aliases)} aliases to {output_path}"
    )


if __name__ == "__main__":
    export_sheet_data()
