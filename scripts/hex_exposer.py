# pyrefly: ignore [missing-import]
import pdfplumber

# 1. The clean baseline from your CSV
target_csv_string = "AYISHA"

# 2. The corrupted target from your PDF
pdf_path = "HDFC Pixel CC Statement.pdf"
extracted_pdf_string = None

print("🔍 Hunting for the target string in the PDF...")
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue

        # We are looking for the exact line containing our target
        for line in text.split("\n"):
            if target_csv_string in line:
                # Isolate the name using basic splitting for the test
                words = line.split()
                for word in words:
                    if target_csv_string in word:
                        extracted_pdf_string = word
                        break
        if extracted_pdf_string:
            break

if not extracted_pdf_string:
    print("❌ Could not find target in PDF.")
else:
    print("\n=== HEXADECIMAL EXPOSER RESULTS ===")
    print(f"CSV Version: '{target_csv_string}'")
    print(f"CSV Hex    : {[hex(ord(c)) for c in target_csv_string]}")
    print("-" * 35)
    print(f"PDF Version: '{extracted_pdf_string}'")
    print(f"PDF Hex    : {[hex(ord(c)) for c in extracted_pdf_string]}")
    print("-" * 35)
    print(f"Exact Match: {target_csv_string == extracted_pdf_string}")
    print("===================================")
