import pandas as pd
from abc import ABC, abstractmethod
import hashlib
from typing import Iterator, Dict, Any


class PasswordMismatchError(Exception):
    """Raised when a PDF stream cannot be read due to encryption (e.g., wrong/missing password)."""

    pass


class BaseParser(ABC):
    """Abstract base class for all bank/card statement parsers."""

    def __init__(self, file_source, passwords: list = None):
        self.file_source = file_source
        self.source_account = "UNKNOWN"
        self.passwords = passwords or []

    @abstractmethod
    def parse_stream(self) -> Iterator[Dict[str, Any]]:
        """Parses the file and returns a stream of dictionaries."""
        pass

    def generate_transaction_id(self, txn: Dict[str, Any], index: int) -> str:
        """
        Generates a deterministic hash for a transaction.
        Uses date, amount, description, and source account.
        Includes ref_no if available, otherwise falls back to index to prevent identical transactions on the same day from collapsing.
        """
        date_str = str(txn.get("transaction_date", ""))
        amt_str = str(txn.get("amount", ""))
        desc_str = str(txn.get("raw_description", "")).strip().lower()
        src_str = str(txn.get("source_account", ""))
        ref_no = str(txn.get("ref_no", "")).strip()

        if ref_no:
            raw = f"{date_str}|{amt_str}|{desc_str}|{src_str}|{ref_no}"
        else:
            raw = f"{date_str}|{amt_str}|{desc_str}|{src_str}|{index}"

        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _open_pdf(self):
        import pdfplumber

        passwords_to_try = self.passwords + [""] if self.passwords else [""]
        last_error = None
        for pw in passwords_to_try:
            if hasattr(self.file_source, "seek"):
                self.file_source.seek(0)
            try:
                pdf = pdfplumber.open(self.file_source, password=pw)
                return pdf
            except Exception as e:
                last_error = e
                # Check for password/encryption related strings in the exception
                err_str = str(e).lower() + str(type(e).__name__).lower()
                if hasattr(e, "__context__") and e.__context__:
                    err_str += (
                        str(e.__context__).lower()
                        + str(type(e.__context__).__name__).lower()
                    )

                if (
                    "password" in err_str
                    or "encrypt" in err_str
                    or "pdfminerexception" in err_str
                ):
                    continue
                # If it's a completely different error, just raise it
                raise e
        raise PasswordMismatchError(
            "Password mismatch or file encrypted."
        ) from last_error

    def _get_unified_schema(self) -> pd.DataFrame:
        """Returns an empty DataFrame with the unified schema."""
        return pd.DataFrame(
            columns=[
                "transaction_date",
                "value_date",
                "description",
                "raw_description",
                "amount",
                "transaction_type",
                "balance",
                "source_account",
                "transaction_id",
                "month",
                "year",
            ]
        )
