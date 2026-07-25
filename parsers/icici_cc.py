# pyrefly: ignore [missing-import]
import gc
import io
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from typing import Iterator, Dict, Any
from parsers.base_parser import BaseParser, PasswordMismatchError

_SKIP_KEYWORDS = [
    "date",
    "ref no.",
    "transaction details",
    "reward points",
    "amount",
    "previous balance",
    "current balance",
    "total amount due",
    "minimum amount due",
    "please note",
    "reward points summary",
    "available credit limit",
    "available cash limit",
    "page",
    "statement date",
    "not billed",
    "for exclusive offers",
    "transactions highlighted",
    "the available credit limit",
]


class ICICICreditCardParser(BaseParser):
    def __init__(self, file_source, passwords: list = None):
        super().__init__(file_source, passwords=passwords)
        self.source_account = "ICICI_CC"
        self.file_source = file_source

    def parse_stream(self) -> Iterator[Dict[str, Any]]:

        # Split regex to support multi-line transactions
        date_start_pattern = re.compile(r".*?(\d{2}/\d{2}/\d{4})\s+(\S+)\s+(.*)")
        amount_end_pattern = re.compile(r"(.*?)\s+(\d+)\s+([\d\.\,]+(?:\s*[Cc][Rr])?)$")

        current_txn = None

        try:
            with self._open_pdf() as pdf:
                index = 0
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue

                    for line in text.split("\n"):
                        line = line.strip()

                        # Skip non-transaction lines or empty lines
                        if not line or any(kw in line.lower() for kw in _SKIP_KEYWORDS):
                            continue

                        # Check if this line starts a new transaction
                        date_match = date_start_pattern.match(line)

                        if date_match:
                            # Flush the previous transaction if one is holding in the buffer
                            if current_txn and current_txn.get("amount") is not None:
                                index += 1
                                txn_series = pd.Series(current_txn)
                                current_txn["transaction_id"] = (
                                    self.generate_transaction_id(current_txn, index)
                                )
                                yield current_txn

                            # Start a new buffer
                            date_str = date_match.group(1)
                            ref_no = date_match.group(2)
                            remainder = date_match.group(3)

                            parsed_date = datetime.strptime(date_str, "%d/%m/%Y")

                            current_txn = {
                                "transaction_date": parsed_date.strftime("%Y-%m-%d"),
                                "value_date": None,
                                "description": "",
                                "raw_description": "",
                                "amount": None,
                                "transaction_type": None,
                                "balance": None,
                                "source_account": self.source_account,
                                "month": parsed_date.strftime("%m"),
                                "year": parsed_date.strftime("%Y"),
                                "ref_no": ref_no.strip() if ref_no else None,
                            }

                            # Check if the amount is on this first line
                            amt_match = amount_end_pattern.search(remainder)
                            if amt_match:
                                desc_part = amt_match.group(1).strip()
                                rewards = amt_match.group(2)
                                amount_str = amt_match.group(3)

                                current_txn["description"] = desc_part
                                current_txn["raw_description"] = desc_part

                                # Determine transaction type from CR suffix
                                txn_type = "debit"
                                if amount_str.upper().endswith("CR"):
                                    txn_type = "credit"
                                    clean_amt = (
                                        amount_str.upper().replace("CR", "").strip()
                                    )
                                else:
                                    clean_amt = amount_str.strip()

                                # Handle potential OCR formatting
                                if clean_amt.count(".") > 1:
                                    clean_amt = clean_amt.replace(".", "", 1)

                                try:
                                    current_txn["amount"] = float(
                                        clean_amt.replace(",", "")
                                    )
                                except ValueError:
                                    pass
                                current_txn["transaction_type"] = txn_type
                            else:
                                # Amount isn't here, it might be on the next line. Just store the text.
                                current_txn["description"] = remainder.strip()
                                current_txn["raw_description"] = remainder.strip()

                        # If it doesn't start with a date, it's either overflow text or garbage
                        elif current_txn:
                            # Check if this overflow line contains the amount/type at the end
                            amt_match = amount_end_pattern.search(line)

                            if amt_match:
                                desc_part = amt_match.group(1).strip()
                                rewards = amt_match.group(2)
                                amount_str = amt_match.group(3)

                                # Append to existing description
                                full_desc = (
                                    f"{current_txn['description']} {desc_part}".strip()
                                )
                                current_txn["description"] = full_desc
                                current_txn["raw_description"] = full_desc

                                # Determine transaction type from CR suffix
                                txn_type = "debit"
                                if amount_str.upper().endswith("CR"):
                                    txn_type = "credit"
                                    clean_amt = (
                                        amount_str.upper().replace("CR", "").strip()
                                    )
                                else:
                                    clean_amt = amount_str.strip()

                                # Handle potential OCR formatting
                                if clean_amt.count(".") > 1:
                                    clean_amt = clean_amt.replace(".", "", 1)

                                try:
                                    current_txn["amount"] = float(
                                        clean_amt.replace(",", "")
                                    )
                                except ValueError:
                                    pass
                                current_txn["transaction_type"] = txn_type
                            else:
                                # Pure text overflow (no amounts). Append it to the description.
                                full_desc = (
                                    f"{current_txn['description']} {line}".strip()
                                )
                                current_txn["description"] = full_desc
                                current_txn["raw_description"] = full_desc

                # End of document: flush the final buffered transaction
                if current_txn and current_txn.get("amount") is not None:
                    index += 1
                    txn_series = pd.Series(current_txn)
                    current_txn["transaction_id"] = self.generate_transaction_id(
                        current_txn, index
                    )
                    yield current_txn

                    del text
                    del page
                    gc.collect()

        except Exception as e:
            raise e
