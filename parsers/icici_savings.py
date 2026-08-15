# pyrefly: ignore [missing-import]
import gc
import io
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from typing import Iterator, Dict, Any
from parsers.base_parser import BaseParser, PasswordMismatchError


class ICICISavingsParser(BaseParser):
    def __init__(self, file_source, passwords: list = None):
        super().__init__(file_source, passwords=passwords)
        self.source_account = "ICICI_SAVINGS"
        self.file_source = file_source

    def parse_stream(self) -> Iterator[Dict[str, Any]]:

        # Collect and filter lines across all pages
        all_lines = []
        ignore_keywords = [
            "Statement of Transactions",
            "Transaction Remarks",
            "Withdrawal Amount",
            "Deposit Amount",
            "Cheque Number",
            "S No.",
            "www.icici.bank.in",
            "Please call from",
            "Never share your OTP",
            "Sincerly,",
            "Team ICICI Bank",
            "system generated statement",
            "Legends for transactions",
            "Legends",
            "Legends for",
            " legends",
            "SMO - Smart",
            "VPS/IPS -",
            "TOP - Mobile",
            "BCTT - Banking",
            "UCCBRN CMS",
            "LCCBRN CMS",
            "IMPS - Immediate",
            "VAT/MAT/NFS -",
            "ATM MMT",
            "IMPS)",
            "EBA - Transaction",
            "T Chg -",
            "SGB - Sovereign",
            "Transaction Withdrawal",
            "Date Amount (INR)",
            "Your Base Branch :",
            "ACCOUNT DETAILS",
            "ACCOUNT HOLDERS",
            "ACCOUNT TYPE ACCOUNT BALANCE",
            "Note: Amount available",
            "DATE MODE PARTICULARS",
            "Dial your Bank",
            "STATEMENT SUMMARY for Customer",
            "B/F ",
        ]

        try:
            with self._open_pdf() as pdf:
                index = 0
                for page in pdf.pages:
                    words = page.extract_words()
                    # Group words into lines
                    lines = {}
                    for w in words:
                        top = round(w["top"], 1)
                        found = False
                        for t in lines:
                            if abs(t - top) < 3:
                                lines[t].append(w)
                                found = True
                                break
                        if not found:
                            lines[top] = [w]

                    # Sort lines by top coordinate
                    sorted_tops = sorted(lines.keys())
                    for t in sorted_tops:
                        line_words = sorted(lines[t], key=lambda x: x["x0"])
                        line_str = " ".join([w["text"] for w in line_words]).strip()

                        if not line_str:
                            continue
                        if re.match(r"^\d+$", line_str):
                            continue

                        skip = False
                        for kw in ignore_keywords:
                            if kw.lower() in line_str.lower():
                                skip = True
                                break
                        if not skip:
                            all_lines.append((line_str, line_words))
                    del words
                    del page
                    gc.collect()
        except Exception as e:
            raise e

        # Find indices of transaction lines
        # Allows optional SNo and either dots or hyphens for the date separator, plus optional text between date and amount
        txn_pattern = re.compile(
            r"^(?:(\d+)\s+)?(\d{2}[\.\-]\d{2}[\.\-]\d{4})\s*(.*?)\s+([\d\.\,]+)\s+([\d\.\,]+)$"
        )
        txn_indices = []
        for idx, (line_str, _) in enumerate(all_lines):
            if txn_pattern.match(line_str):
                txn_indices.append(idx)

        # Process each transaction
        for k, idx in enumerate(txn_indices):
            line_str, line_words = all_lines[idx]
            match = txn_pattern.match(line_str)
            sno_str = match.group(1)
            date_str = match.group(2).replace("-", ".")
            mid_text = match.group(3).strip()
            amount_str = match.group(4)
            balance_str = match.group(5)

            # Start index of remarks
            if k == 0:
                start_remarks_idx = 0
            else:
                prev_idx = txn_indices[k - 1]
                start_remarks_idx = (prev_idx + idx) // 2 + 1
                if start_remarks_idx <= prev_idx:
                    start_remarks_idx = prev_idx + 1

            # End index of remarks
            if k == len(txn_indices) - 1:
                end_remarks_idx = len(all_lines) - 1
            else:
                next_idx = txn_indices[k + 1]
                end_remarks_idx = (idx + next_idx) // 2
                if end_remarks_idx >= next_idx:
                    end_remarks_idx = next_idx - 1

            # Compile remarks
            remarks_lines = []
            if mid_text:
                remarks_lines.append(mid_text)

            for r_idx in range(start_remarks_idx, end_remarks_idx + 1):
                if r_idx == idx:
                    continue
                remarks_lines.append(all_lines[r_idx][0])

            remarks = " ".join(remarks_lines).strip()
            if remarks == "None" or remarks == "":
                remarks = "NO DESCRIPTION"

            # Bounding box of the amount word
            # DEPOSITS (credit) column x0 is ~370-390, WITHDRAWALS (debit) column x0 is > 450
            amount_word = line_words[-2]
            if amount_word["x0"] < 420:
                txn_type = "credit"
            else:
                txn_type = "debit"

            parsed_date = datetime.strptime(date_str, "%d.%m.%Y")
            amount = float(amount_str.replace(",", ""))
            balance = float(balance_str.replace(",", ""))

            txn = {
                "transaction_date": parsed_date.strftime("%Y-%m-%d"),
                "value_date": None,
                "description": remarks,
                "description_raw": remarks,
                "amount": amount,
                "transaction_type": txn_type,
                "balance": balance,
                "source_account": self.source_account,
                "month": parsed_date.strftime("%m"),
                "year": parsed_date.strftime("%Y"),
            }

            index += 1
            txn["transaction_id"] = self.generate_transaction_id(txn, index)
            yield txn
