import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from output.gsheets_writer import GoogleSheetsWriter

writer = GoogleSheetsWriter("config.yaml")

ws_transactions = writer._get_or_create_worksheet("Transactions")
ws_map = writer._get_or_create_worksheet("Category_Map")

print("--- Category Map Sheet ---")
print(ws_map.get_all_values())

print("\n--- Transactions Sheet Dropdown Config ---")
# We can't easily get the dropdown list via basic gspread without advanced API,
# but let's check what categories are actually present in the Transactions sheet data
txns = ws_transactions.get_all_values()
if len(txns) > 1:
    header = txns[0]
    try:
        cat_idx = header.index("category")
        cats = set([row[cat_idx] for row in txns[1:] if len(row) > cat_idx])
        print("Categories present in Transactions data:", cats)
    except Exception as e:
        print("Error getting categories:", e)
else:
    print("Transactions sheet is empty except header.")
