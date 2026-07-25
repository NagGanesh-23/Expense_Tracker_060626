import pandas as pd
import os

# Import our newly built parsers
from parsers.icici_savings import ICICISavingsParser
from parsers.axis_myzone import AxisMyZoneParser
from parsers.sbi_cashback import SBICashbackParser
from parsers.icici_cc import ICICICreditCardParser
from pipeline.normalizer import Normalizer


def main():
    # 1. Map your PDF files to their respective parsers
    # Make sure these filenames match exactly what you have in your folder
    statement_files = [
        {"file": "ICICI Savings Statement.pdf", "parser": ICICISavingsParser},
        {"file": "Axis CC Statement.pdf", "parser": AxisMyZoneParser},
        {"file": "SBI CC Statement.pdf", "parser": SBICashbackParser},
        {"file": "ICICI CC Statement.pdf", "parser": ICICICreditCardParser},
    ]

    all_transactions = []
    normalizer = Normalizer()

    print("Starting PDF Extraction...")

    # 2. Loop through and parse each file
    for item in statement_files:
        filepath = item["file"]
        ParserClass = item["parser"]

        if not os.path.exists(filepath):
            print(f"Skipping {filepath} - File not found in current directory.")
            continue

        print(f"Parsing {filepath}...")
        try:
            parser = ParserClass(filepath)
            raw_df = parser.parse()

            # Run it through the normalizer to clean up the descriptions
            clean_df = normalizer.normalize(raw_df)

            all_transactions.append(clean_df)
            print(f"  Found {len(clean_df)} transactions.")
        except Exception as e:
            print(f"  Error parsing {filepath}: {e}")

    # 3. Combine everything and export
    # Filter out empty DataFrames first
    all_transactions = [df for df in all_transactions if not df.empty]

    if all_transactions:
        final_df = pd.concat(all_transactions, ignore_index=True)

        # Sort by date just to make it neat
        final_df = final_df.sort_values(by="transaction_date")

        # Select only the columns you actually need for labeling to keep the Excel sheet clean
        export_df = final_df[
            [
                "transaction_date",
                "description",
                "amount",
                "transaction_type",
                "source_account",
            ]
        ].copy()

        # Add a blank column for you to fill in!
        export_df["category"] = ""

        # Write to Excel
        output_filename = "unlabeled_transactions.xlsx"
        try:
            export_df.to_excel(output_filename, index=False)
            print(
                f"\nSuccess! Combined {len(export_df)} transactions into '{output_filename}'."
            )
            print(
                "Next Step: Open the Excel file, fill in the 'category' column, and then save it as 'training_data.csv' inside your 'models' folder!"
            )
        except Exception as e:
            print(f"\nFailed to write Excel file: {e}")
            print("Did you forget to install openpyxl? Run: pip install openpyxl")
    else:
        print("\nNo transactions were found to export.")


if __name__ == "__main__":
    main()
