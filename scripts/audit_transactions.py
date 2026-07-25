import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yaml
import re


def main():
    import sys, io

    sys.stdout = io.TextIOWrapper(open("audit_output.txt", "wb"), encoding="utf-8")
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

    # Filter out empty rows
    df = df[df["transaction_id"].str.strip() != ""]

    # 2. Corrupted Descriptions
    # Look for long strings or specific boilerplate words
    def is_corrupted(desc):
        if len(desc) > 150:
            return True
        boilerplate = ["MITC", "TERMS AND CONDITIONS", "FINANCE CHARGE", "DAYS 0 145"]
        for b in boilerplate:
            if b in desc.upper():
                return True
        return False

    df["is_corrupted"] = df["description"].apply(is_corrupted)
    corrupted_df = df[df["is_corrupted"]]

    print(f"--- CORRUPTED DESCRIPTIONS ({len(corrupted_df)}) ---")
    for _, row in corrupted_df.head(10).iterrows():
        print(f"ID: {row.get('transaction_id')}")
        print(f"Amt: {row.get('clean_amount')}")
        print(f"Desc Preview: {str(row['description'])[:100]}...\n")

    # 3. Duplicate Groups
    # Let's clean the amount first just in case
    df["numeric_amount"] = pd.to_numeric(df["clean_amount"], errors="coerce").fillna(0)

    # Let's use a truncated description for duplicate matching to bypass trailing garbage
    df["trunc_desc"] = df["description"].apply(lambda x: x[:30])

    dup_mask = df.duplicated(
        subset=["transaction_date", "numeric_amount", "trunc_desc"], keep=False
    )
    duplicates_df = df[dup_mask].sort_values(["transaction_date", "numeric_amount"])

    dup_groups = duplicates_df.groupby(
        ["transaction_date", "numeric_amount", "trunc_desc"]
    )

    print(
        f"--- TRUE DUPLICATES ({len(dup_groups)} groups affecting {len(duplicates_df)} rows) ---"
    )
    count = 0
    for name, group in dup_groups:
        if count < 10:
            print(f"Group: Date={name[0]}, Amt={name[1]}, Desc={name[2]}")
            for _, row in group.iterrows():
                print(
                    f"  -> ID: {row.get('transaction_id')} | Category: {row.get('category')} | Source: {row.get('source_account')}"
                )
            print()
            count += 1

    # 4. Category Inconsistencies
    # Simple merchant normalization for audit
    def normalize_merchant(desc):
        desc = str(desc).upper()
        # Common prefixes to strip
        desc = re.sub(r"^(CAS\s+|RAZ\s+|UPI\s+|CRED\s+CLUB\s+)", "", desc)
        # Extract first 1-2 words
        words = re.findall(r"[A-Z]+", desc)
        if len(words) >= 2:
            return f"{words[0]} {words[1]}"
        elif len(words) == 1:
            return words[0]
        return "UNKNOWN"

    df["norm_merchant"] = df["description"].apply(normalize_merchant)

    # Filter out empty/unknown and low frequency
    cat_counts = df.groupby("norm_merchant")["category"].nunique()
    inconsistent_merchants = cat_counts[cat_counts > 1].index

    print(f"--- CATEGORY INCONSISTENCIES ({len(inconsistent_merchants)} groups) ---")
    for m in list(inconsistent_merchants)[:10]:
        cats = df[df["norm_merchant"] == m]["category"].unique()
        print(f"Merchant '{m}' classified as: {list(cats)}")
        # Print a sample description to see if it makes sense
        samples = df[df["norm_merchant"] == m]["description"].unique()[:2]
        print(f"  Samples: {list(samples)}\n")


if __name__ == "__main__":
    main()
