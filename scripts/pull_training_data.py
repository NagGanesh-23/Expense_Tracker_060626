import os
import sys
import pandas as pd
import gspread
import yaml
from google.oauth2.service_account import Credentials

# Add parent directory to path to allow imports if needed, though this is a standalone script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return

    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    creds_path = config.get("google_service_account_json")
    sheet_id = config.get("google_sheet_id")

    if not creds_path or not sheet_id:
        print(
            "Error: Missing google_service_account_json or google_sheet_id in config.yaml"
        )
        return

    print("Connecting to Google Sheets...")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id)
        ws = spreadsheet.worksheet("Transactions")
    except Exception as e:
        print(f"Failed to connect to Google Sheets: {e}")
        return

    print("Downloading Transactions data...")
    data = ws.get_all_records()
    if not data:
        print("No data found in Transactions sheet.")
        return

    df_remote = pd.DataFrame(data)

    # Required columns for training_data.csv:
    # transaction_date,description,amount,transaction_type,source_account,category

    # Map description_raw to description if available, otherwise use description
    if "description_raw" in df_remote.columns:
        # Fallback to description if description_raw is empty
        df_remote["description"] = (
            df_remote["description_raw"]
            .replace("", pd.NA)
            .fillna(df_remote.get("description", ""))
        )

    # Filter out Uncategorized and blanks (but keep 'Un Wanted' as requested)
    if "category" not in df_remote.columns:
        print("Error: 'category' column not found in Google Sheets data.")
        return

    df_remote["category"] = df_remote["category"].astype(str).str.strip()
    mask_valid = (df_remote["category"] != "") & (
        df_remote["category"].str.lower() != "uncategorized"
    )
    df_remote = df_remote[mask_valid].copy()

    if df_remote.empty:
        print("No valid categorized transactions found to pull.")
        return

    # Standardize columns
    expected_cols = [
        "transaction_date",
        "description",
        "amount",
        "transaction_type",
        "source_account",
        "category",
    ]
    for col in expected_cols:
        if col not in df_remote.columns:
            df_remote[col] = ""

    df_remote = df_remote[expected_cols]

    training_file = "models/training_data.csv"
    print(f"Loading local training data from {training_file}...")

    if os.path.exists(training_file):
        df_local = pd.read_csv(training_file)
        # Ensure string types for description and category
        df_local["description"] = df_local["description"].astype(str)
        df_local["category"] = df_local["category"].astype(str)
        initial_len = len(df_local)
    else:
        df_local = pd.DataFrame(columns=expected_cols)
        initial_len = 0
        os.makedirs(os.path.dirname(training_file), exist_ok=True)

    print(f"Found {initial_len} existing records and {len(df_remote)} remote records.")

    # Merge and deduplicate
    # We drop duplicates based on 'description' and 'category'.
    # Keeping 'last' ensures if a category changes for the exact same description, we keep the newest one (from remote).
    df_combined = pd.concat([df_local, df_remote], ignore_index=True)

    # We want to deduplicate primarily by description, keeping the latest category label.
    df_combined = df_combined.drop_duplicates(subset=["description"], keep="last")

    final_len = len(df_combined)
    added = final_len - initial_len

    if added > 0 or initial_len != len(df_combined):
        df_combined.to_csv(training_file, index=False)
        print(f"Successfully updated {training_file}!")
        print(
            f"Total training examples: {final_len} (Net Change: {len(df_combined) - initial_len})"
        )

        cache_file = "models/training_embeddings_cache.npz"
        if os.path.exists(cache_file):
            print(
                f"Clearing cache file {cache_file} to force re-embedding on next run..."
            )
            os.remove(cache_file)

    else:
        print("No new unique descriptions found. Training data is already up to date!")


if __name__ == "__main__":
    main()
