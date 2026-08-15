import io
import gc
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from typing import Iterator, Dict, Any
from parsers.base_parser import BaseParser, PasswordMismatchError


class SBICashbackParser(BaseParser):
    def __init__(self, file_source: io.BytesIO, passwords: list = None):
        super().__init__(file_source, passwords=passwords)
        self.source_account = "SBI_CASHBACK"
        self.file_source = file_source

    def parse_stream(self) -> Iterator[Dict[str, Any]]:
        """
        Streams transactions one by one, destroying page artifacts immediately
        to maintain a zero-disk, low-memory footprint.
        """
        date_start_pattern = re.compile(r"^(\d{2} [A-Za-z]{3} \d{2})\s+(.*)")
        amount_end_pattern = re.compile(
            r"(.*?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+([CD])$"
        )

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
                        if not line:
                            continue

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

                            date_str = date_match.group(1)
                            remainder = date_match.group(2)
                            parsed_date = datetime.strptime(date_str, "%d %b %y")

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

                            amt_match = amount_end_pattern.search(remainder)
                            if amt_match:
                                current_txn["description"] = (
                                    amt_match.group(1).strip()
                                    if amt_match.group(1).strip()
                                    else "NO DESCRIPTION"
                                )
                                current_txn["description_raw"] = current_txn[
                                    "description"
                                ]
                                current_txn["amount"] = float(
                                    amt_match.group(2).replace(",", "")
                                )
                                current_txn["transaction_type"] = (
                                    "credit" if amt_match.group(3) == "C" else "debit"
                                )
                            else:
                                current_txn["description"] = (
                                    remainder.strip()
                                    if remainder.strip()
                                    else "NO DESCRIPTION"
                                )
                                current_txn["description_raw"] = current_txn[
                                    "description"
                                ]

                        elif current_txn:
                            amt_match = amount_end_pattern.search(line)
                            if amt_match:
                                desc_part = amt_match.group(1).strip()
                                full_desc = (
                                    f"{current_txn['description']} {desc_part}".strip()
                                )
                                current_txn["description"] = (
                                    full_desc if full_desc else "NO DESCRIPTION"
                                )
                                current_txn["description_raw"] = current_txn[
                                    "description"
                                ]
                                current_txn["amount"] = float(
                                    amt_match.group(2).replace(",", "")
                                )
                                current_txn["transaction_type"] = (
                                    "credit" if amt_match.group(3) == "C" else "debit"
                                )
                            else:
                                full_desc = (
                                    f"{current_txn['description']} {line}".strip()
                                )
                                current_txn["description"] = (
                                    full_desc if full_desc else "NO DESCRIPTION"
                                )
                                current_txn["description_raw"] = current_txn[
                                    "description"
                                ]

                    # Aggressively delete page text to prevent pdfplumber memory leaks
                    del text
                    del page
                    gc.collect()

                # Flush the final buffered transaction at the end of the document
                if current_txn and current_txn.get("amount") is not None:
                    index += 1
                    txn_series = pd.Series(current_txn)
                    current_txn["transaction_id"] = self.generate_transaction_id(
                        current_txn, index
                    )
                    yield current_txn

        except Exception as e:
            raise e
