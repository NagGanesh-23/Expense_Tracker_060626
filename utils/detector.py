# pyrefly: ignore [missing-import]
import pdfplumber


def detect_source(filepath: str) -> str:
    """Reads the filename or first page of a PDF to auto-detect the bank/card type."""
    # First, try to guess from filename to avoid decryption issues
    name = filepath.upper()
    if "SBI" in name:
        return "sbi_cashback"
    if "HDFC" in name:
        return "hdfc_pixel"
    if "AXIS" in name or "MYZONE" in name:
        return "axis_myzone"
    if "CREDITCARD" in name.replace("_", "") or "CC" in name:
        if "ICICI" in name:
            return "icici_cc"
    if "SAVING" in name or "BANKSTATEMENT" in name.replace("_", ""):
        if "ICICI" in name:
            return "icici_savings"

    try:
        with pdfplumber.open(filepath) as pdf:
            if not pdf.pages:
                return "icici_savings"  # Fallback

            first_page_text = pdf.pages[0].extract_text().upper()

            # 1. Axis MyZone
            if "MY ZONE" in first_page_text or "AXIS BANK" in first_page_text:
                return "axis_myzone"

            # 2. SBI Cashback
            elif "SBI CARD" in first_page_text or "CASHBACK SBI" in first_page_text:
                return "sbi_cashback"

            # 3. ICICI Savings
            elif "SAVING ACCOUNT" in first_page_text and "ICICI" in first_page_text:
                return "icici_savings"

            # 4. ICICI Credit Card
            elif (
                "CREDIT CARD STATEMENT" in first_page_text
                and "ICICI" in first_page_text
            ):
                return "icici_cc"

            # 5. HDFC Pixel (NEW)
            elif "HDFC" in first_page_text or "PIXEL" in first_page_text:
                return "hdfc_pixel"

            # Default fallback if it can't figure it out
            else:
                return "icici_savings"

    except Exception as e:
        print(f"[WARNING] Error auto-detecting {filepath}: {e}")
        return "icici_savings"
