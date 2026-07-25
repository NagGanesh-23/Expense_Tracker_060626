import io
import pytest
from unittest.mock import MagicMock, patch
from parsers.axis_myzone import AxisMyZoneParser
from parsers.icici_cc import ICICICreditCardParser
from parsers.icici_savings import ICICISavingsParser
from parsers.sbi_cashback import SBICashbackParser
from parsers.hdfc_pixel import HDFCPixelParser


class MockPage:
    def __init__(self, text="", table=None, words=None):
        self._text = text
        self._table = table
        self._words = words or []

    def extract_text(self):
        return self._text

    def extract_table(self):
        return self._table

    def extract_words(self):
        return self._words


class MockPDF:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_axis_myzone_parser_empty_file():
    parser = AxisMyZoneParser(io.BytesIO(b"dummy"))
    with patch.object(
        parser, "_open_pdf", return_value=MockPDF([MockPage(table=None)])
    ):
        txns = list(parser.parse_stream())
        assert len(txns) == 0


def test_axis_myzone_parser_zero_amount_and_valid():
    table_data = [
        ["DATE", "REF", "DESC", "CHG", "CR/DR", "BAL", "CAT", "MERCHANT_CAT", "AMOUNT"],
        [
            "21/05/2026",
            None,
            "VALID STORE",
            None,
            None,
            None,
            None,
            "Shopping",
            "1,500.00",
        ],
        ["22/05/2026", None, "ZERO STORE", None, None, None, None, "None", "0.00"],
    ]
    parser = AxisMyZoneParser(io.BytesIO(b"dummy"))
    with patch.object(
        parser, "_open_pdf", return_value=MockPDF([MockPage(table=table_data)])
    ):
        txns = list(parser.parse_stream())
        assert len(txns) == 1
        assert txns[0]["amount"] == 1500.00
        assert txns[0]["description"] == "VALID STORE [Shopping]"


def test_icici_cc_parser_empty_file():
    parser = ICICICreditCardParser(io.BytesIO(b"dummy"))
    with patch.object(parser, "_open_pdf", return_value=MockPDF([MockPage(text="")])):
        txns = list(parser.parse_stream())
        assert len(txns) == 0


def test_icici_cc_parser_valid_transaction():
    text = "21/05/2026 123456 AMAZON INDIA 10 1,200.00\n"
    parser = ICICICreditCardParser(io.BytesIO(b"dummy"))
    with patch.object(parser, "_open_pdf", return_value=MockPDF([MockPage(text=text)])):
        txns = list(parser.parse_stream())
        assert len(txns) == 1
        assert txns[0]["amount"] == 1200.00
        assert "AMAZON INDIA" in txns[0]["description"]


def test_icici_savings_parser_empty_file():
    parser = ICICISavingsParser(io.BytesIO(b"dummy"))
    with patch.object(parser, "_open_pdf", return_value=MockPDF([MockPage(words=[])])):
        txns = list(parser.parse_stream())
        assert len(txns) == 0


def test_sbi_cashback_parser_empty_file():
    parser = SBICashbackParser(io.BytesIO(b"dummy"))
    with patch.object(parser, "_open_pdf", return_value=MockPDF([MockPage(text="")])):
        txns = list(parser.parse_stream())
        assert len(txns) == 0


def test_sbi_cashback_parser_valid_transaction():
    text = "21 May 26 SWIGGY DINEOUT 500.00 D\n"
    parser = SBICashbackParser(io.BytesIO(b"dummy"))
    with patch.object(parser, "_open_pdf", return_value=MockPDF([MockPage(text=text)])):
        txns = list(parser.parse_stream())
        assert len(txns) == 1
        assert txns[0]["amount"] == 500.00
        assert txns[0]["transaction_type"] == "debit"


def test_hdfc_pixel_parser_empty_file():
    parser = HDFCPixelParser(io.BytesIO(b"dummy"))
    with patch.object(parser, "_open_pdf", return_value=MockPDF([MockPage(text="")])):
        txns = list(parser.parse_stream())
        assert len(txns) == 0


def test_hdfc_pixel_parser_valid_transaction():
    text = "09 Jun 2026, 09:07 SWIGGY DINEOUT BENGALURU IND ₹50.00\n"
    parser = HDFCPixelParser(io.BytesIO(b"dummy"))
    with patch.object(parser, "_open_pdf", return_value=MockPDF([MockPage(text=text)])):
        txns = list(parser.parse_stream())
        assert len(txns) == 1
        assert txns[0]["amount"] == 50.00
        assert "SWIGGY DINEOUT" in txns[0]["description"]
