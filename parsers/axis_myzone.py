# pyrefly: ignore [missing-import]
import gc
import io
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from typing import Iterator, Dict, Any
import io
from parsers.base_parser import BaseParser, PasswordMismatchError


class AxisMyZoneParser(BaseParser):
    def __init__(self, file_source, passwords: list = None):
        # Replaced 'filepath: str' with 'file_source' to accept BytesIO
        super().__init__(file_source, passwords=passwords)
        self.source_account = "AXIS_MYZONE"
        self.file_source = file_source

    def parse_stream(self) -> Iterator[Dict[str, Any]]:
        # use new _open_pdf helper to handle passwords
        with self._open_pdf() as pdf:
            index = 0
            for page in pdf.pages:
                table = page.extract_table()
                if not table:
                    continue

                for row in table:
                    # Skip None/short rows and the header row
                    if not row or len(row) < 5 or "DATE" in str(row[0]).upper():
                        continue

                    date_str = str(row[0]).strip()
                    # Axis dates look like 21/05/2026
                    if not re.match(r"\d{2}/\d{2}/\d{4}", date_str):
                        continue

                    # FIX: description is at index 2 (not 1 — index 1 is always None)
                    raw_desc = str(row[2]).replace("\n", " ").strip()
                    if raw_desc == "None" or raw_desc == "":
                        raw_desc = "NO DESCRIPTION"

                    # Merchant category at index 7; use it to enrich the description
                    # so the downstream ML categoriser has more signal
                    merchant_cat = str(row[7]).strip() if row[7] else ""
                    if merchant_cat and merchant_cat != "None":
                        enriched_desc = f"{raw_desc} [{merchant_cat}]"
                    else:
                        enriched_desc = raw_desc

                    amount_str = str(row[-1]).replace(",", "").strip()

                    if not amount_str or amount_str == "None":
                        continue

                    # Determine transaction type from Cr/Dr suffix
                    txn_type = "debit"
                    amount = 0.0

                    if amount_str.endswith("Cr"):
                        txn_type = "credit"
                        amount = float(amount_str.replace("Cr", "").strip())
                    elif amount_str.endswith("Dr"):
                        txn_type = "debit"
                        amount = float(amount_str.replace("Dr", "").strip())
                    else:
                        try:
                            amount = float(amount_str)
                        except ValueError:
                            continue  # Skip row if amount isn't parsable

                    if amount == 0.0:
                        continue

                    parsed_date = datetime.strptime(date_str, "%d/%m/%Y")

                    txn = {
                        "transaction_date": parsed_date.strftime("%Y-%m-%d"),
                        "value_date": None,
                        "description": enriched_desc,
                        "description_raw": raw_desc,
                        "amount": amount,
                        "transaction_type": txn_type,
                        "balance": None,  # CC statements don't show running balance per row
                        "source_account": self.source_account,
                        "month": parsed_date.strftime("%m"),
                        "year": parsed_date.strftime("%Y"),
                    }

                    index += 1
                    txn["transaction_id"] = self.generate_transaction_id(txn, index)
                    yield txn
                del table
                del page
                gc.collect()
