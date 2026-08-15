# pyrefly: ignore [missing-import]
import gc
import io
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from typing import Iterator, Dict, Any
from parsers.base_parser import BaseParser, PasswordMismatchError

# HDFC Pixel CC statements use a custom font that maps digits and punctuation
# to Unicode Private Use Area (PUA) characters. This table decodes them back.
_PUA_MAP = {}
for _i in range(10):
    _PUA_MAP[chr(0xE071 + _i)] = str(_i)  # \ue071='0' ... \ue07a='9'
_PUA_MAP[chr(0xE093)] = ","
_PUA_MAP[chr(0xE094)] = "."
_PUA_MAP[chr(0xEE47)] = ":"
_PUA_MAP[chr(0xEE6A)] = "*"  # Cashpoints marker
_PUA_MAP[chr(0xEE48)] = "("
_PUA_MAP[chr(0xEE49)] = ")"
_PUA_MAP[chr(0xEE55)] = "-"
_PUA_MAP["\x00"] = " "  # Null bytes used as spaces


def _decode_pua(text: str) -> str:
    """Translates PUA-encoded characters back to standard ASCII."""
    return "".join(_PUA_MAP.get(c, c) for c in text)


# Matches transaction lines like:
#   09 Jun 2026, 09:07 SWIGGY DINEOUT BENGALURU IND ₹50.00
#   13 Jun 2026, 13:21 DMART AVENUE SUPERMART BANGALORE IND *60 ₹6,055.19
#   10 Jun 2026, 15:14 PAYZAPP *₹2.00
_TXN_PATTERN = re.compile(
    r"^(\d{2}\s+\w{3}\s+\d{4}),\s*\d{2}:\d{2}\s+"  # Date & time
    r"(.+?)\s+"  # Description (non-greedy)
    r"\*?₹([\d,]+\.\d{2})\s*$"  # Amount with ₹ prefix
)

# Lines to skip (headers, footers, summaries)
_SKIP_KEYWORDS = [
    "DATE & TIME",
    "TRANSACTION DESCRIPTION",
    "CASHPOINTS AMOUNT",
    "Note :",
    "Important Information",
    "Reward Points",
    "OPENING BALANCE",
    "MINIMUM DUE",
    "TOTAL CREDIT",
    "Past Dues",
    "OVERLIMIT",
    "Consolidated Summary",
    "HSN Code",
    "Card no.",
    "Domestic Transactions",
    "Useful Links",
    "Digitally signed",
    "Click to view",
    "GST ENTRY",
    "SGST",
    "CGST",
]


class HDFCPixelParser(BaseParser):
    def __init__(self, file_source, passwords: list = None):
        super().__init__(file_source, passwords=passwords)
        self.source_account = "HDFC_PIXEL"
        self.file_source = file_source

    def parse_stream(self) -> Iterator[Dict[str, Any]]:

        # Split regex to support multi-line transactions
        date_start_pattern = re.compile(
            r"^(\d{2}\s+\w{3}\s+\d{4}),\s*\d{2}:\d{2}\s+(.*)"
        )
        amount_end_pattern = re.compile(r"(.*?)\s+\*?₹([\d,]+\.\d{2})\s*$")

        current_txn = None

        try:
            with self._open_pdf() as pdf:
                index = 0
                for page in pdf.pages:
                    raw_text = page.extract_text()
                    if not raw_text:
                        continue

                    decoded_text = _decode_pua(raw_text)

                    for line in decoded_text.split("\n"):
                        line = line.strip()

                        # Skip non-transaction lines or empty lines
                        if not line or any(kw in line for kw in _SKIP_KEYWORDS):
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
                            remainder = date_match.group(2)

                            parsed_date = datetime.strptime(date_str, "%d %b %Y")

                            current_txn = {
                                "transaction_date": parsed_date.strftime("%Y-%m-%d"),
                                "value_date": None,
                                "description": "",
                                "description_raw": "",
                                "amount": None,
                                "transaction_type": None,
                                "balance": None,
                                "source_account": self.source_account,
                                "month": parsed_date.strftime("%m"),
                                "year": parsed_date.strftime("%Y"),
                            }

                            # Check if the amount is on this first line
                            amt_match = amount_end_pattern.search(remainder)
                            if amt_match:
                                desc_part = amt_match.group(1).strip()
                                amount_str = amt_match.group(2)

                                # Clean description: strip trailing cashpoints like "*60"
                                desc_part = re.sub(r"\s*\*\d+\s*$", "", desc_part)

                                current_txn["description"] = (
                                    desc_part if desc_part else "NO DESCRIPTION"
                                )
                                current_txn["description_raw"] = (
                                    desc_part if desc_part else "NO DESCRIPTION"
                                )

                                try:
                                    amount = float(amount_str.replace(",", ""))
                                    current_txn["amount"] = amount
                                except ValueError:
                                    pass

                                # Determine credit vs debit from description hints
                                txn_type = "debit"
                                credit_keywords = [
                                    "PAYMENT RECEIVED",
                                    "CASHBACK",
                                    "REFUND",
                                    "REVERSAL",
                                ]
                                if any(
                                    kw in desc_part.upper() for kw in credit_keywords
                                ):
                                    txn_type = "credit"
                                current_txn["transaction_type"] = txn_type
                            else:
                                # Amount isn't here, it might be on the next line. Just store the text.
                                current_txn["description"] = (
                                    remainder.strip()
                                    if remainder.strip()
                                    else "NO DESCRIPTION"
                                )
                                current_txn["description_raw"] = (
                                    remainder.strip()
                                    if remainder.strip()
                                    else "NO DESCRIPTION"
                                )

                        # If it doesn't start with a date, it's either overflow text or garbage
                        elif current_txn:
                            # Check if this overflow line contains the amount/type at the end
                            amt_match = amount_end_pattern.search(line)

                            if amt_match:
                                desc_part = amt_match.group(1).strip()
                                amount_str = amt_match.group(2)

                                # Append to existing description
                                full_desc = (
                                    f"{current_txn['description']} {desc_part}".strip()
                                )
                                full_desc = re.sub(r"\s*\*\d+\s*$", "", full_desc)

                                current_txn["description"] = (
                                    full_desc if full_desc else "NO DESCRIPTION"
                                )
                                current_txn["description_raw"] = (
                                    full_desc if full_desc else "NO DESCRIPTION"
                                )

                                try:
                                    amount = float(amount_str.replace(",", ""))
                                    current_txn["amount"] = amount
                                except ValueError:
                                    pass

                                txn_type = "debit"
                                credit_keywords = [
                                    "PAYMENT RECEIVED",
                                    "CASHBACK",
                                    "REFUND",
                                    "REVERSAL",
                                ]
                                if any(
                                    kw in full_desc.upper() for kw in credit_keywords
                                ):
                                    txn_type = "credit"
                                current_txn["transaction_type"] = txn_type
                            else:
                                # Pure text overflow (no amounts). Append it to the description.
                                full_desc = (
                                    f"{current_txn['description']} {line}".strip()
                                )
                                current_txn["description"] = (
                                    full_desc if full_desc else "NO DESCRIPTION"
                                )
                                current_txn["description_raw"] = (
                                    full_desc if full_desc else "NO DESCRIPTION"
                                )

                # End of document: flush the final buffered transaction
                if current_txn and current_txn.get("amount") is not None:
                    # Ignore 0 amount transactions
                    if current_txn["amount"] != 0.0:
                        index += 1
                        txn_series = pd.Series(current_txn)
                        current_txn["transaction_id"] = self.generate_transaction_id(
                            current_txn, index
                        )
                        yield current_txn

                    del raw_text
                    del decoded_text
                    del page
                    gc.collect()

        except Exception as e:
            raise e
