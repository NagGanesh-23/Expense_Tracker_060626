import os
import pandas as pd
import numpy as np
from google import genai
from google.genai import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time
import re
from pypdf import PdfReader
from pydantic import BaseModel, Field
from typing import Literal, List, Dict

# ==========================================
# 1. SECURITY & CLIENT INITIALIZATION
# ==========================================
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

creds_dict = json.loads(os.environ.get("GOOGLE_CREDS_JSON"))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gspread_client = gspread.authorize(creds)

SPREADSHEET_NAME = "My Expense Tracker"
sheet = gspread_client.open(SPREADSHEET_NAME).sheet1 

# Global Cache to eliminate redundant AI calls across duplicate merchant names
AI_CLASSIFICATION_CACHE: Dict[str, Dict[str, str]] = {}

# ==========================================
# 2. STRATEGIC SCHEMA STRUCTS
# ==========================================
class TransactionItem(BaseModel):
    date: str = Field(description="The transaction date found in the statement row.")
    narration: str = Field(description="The merchant or transfer raw narration string.")
    amount: float = Field(description="The transaction currency value numerical amount.")
    type: Literal["DEBIT", "CREDIT"] = Field(description="DEBIT for spends/withdrawals, CREDIT for settlements/refunds.")

class StatementExtractionSchema(BaseModel):
    transactions: List[TransactionItem]

class BatchClassificationItem(BaseModel):
    original_narration: str = Field(description="The exact raw narration string sent in the input list.")
    vendor: str = Field(description="Cleaned business entity or person name.")
    category: Literal["Food", "Transport", "Utilities", "Shopping", "Entertainment", "Investment", "Salary", "Internal Transfer", "Peer Transfer", "Unknown"]

class BatchClassificationSchema(BaseModel):
    results: List[BatchClassificationItem]

def clean_dataframe_headers(df):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = df.columns.str.strip()
    return df

def sanitize_float(val):
    try:
        f_val = float(val)
        if np.isnan(f_val) or np.isinf(f_val):
            return 0.0
        return f_val
    except:
        return 0.0

# ==========================================
# 3. CSV NORMALIZATION (ICICI SAVINGS BANK)
# ==========================================
def normalize_icici_bank_csv(file_path):
    try:
        with open(file_path, 'r') as f:
            line_count = sum(1 for _ in f)
        rows_to_skip = 12 if line_count > 12 else 0
        df = pd.read_csv(file_path, skiprows=rows_to_skip)
    except Exception as e:
        print(f"CSV Read error on {file_path}: {e}")
        return []
        
    df = clean_dataframe_headers(df)
    remarks_col = [col for col in df.columns if any(x in col.upper() for x in ['REMARKS', 'NARRATION', 'DETAILS'])]
    date_col = [col for col in df.columns if 'DATE' in col.upper()]
    
    if not remarks_col or not date_col:
        return []
        
    df.dropna(subset=[remarks_col[0]], inplace=True)
    w_match = [c for c in df.columns if 'WITHDRAWAL' in c.upper() or 'DEBIT' in c.upper()]
    d_match = [c for c in df.columns if 'DEPOSIT' in c.upper() or 'CREDIT' in c.upper()]
    
    parsed_rows = []
    for _, row in df.iterrows():
        narration = str(row[remarks_col[0]]).strip()
        date = str(row[date_col[0]]).strip()
        
        if not narration or "DETAILED STATEMENT" in narration or "Transactions List" in narration:
            continue
            
        if w_match and d_match:
            w_str = str(row[w_match[0]]).replace(',', '').strip()
            d_str = str(row[d_match[0]]).replace(',', '').strip()
            w_amt = sanitize_float(pd.to_numeric(w_str, errors='coerce') or 0)
            d_amt = sanitize_float(pd.to_numeric(d_str, errors='coerce') or 0)
            
            if w_amt > 0:
                amt, tx_type = w_amt, 'DEBIT'
            else:
                amt, tx_type = d_amt, 'CREDIT'
        else:
            amt, tx_type = 0, 'DEBIT'
            
        if amt == 0 and not narration:
            continue
            
        parsed_rows.append({"date": date, "narration": narration, "amount": amt, "type": tx_type})
    return parsed_rows

# ==========================================
# 4. LLM-BASED PDF STATEMENT EXTRACTION
# ==========================================
def extract_transactions_from_pdf_via_ai(file_path):
    text_content = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text: text_content += text + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return []

    if not text_content.strip():
        return []

    prompt = f"Extract all individual transactions, purchases, fees, reversals, and settlements from this text layout dump:\n\n{text_content}"
    
    # Implements Exponential Backoff to gracefully bypass 429 errors
    for attempt in range(3):
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StatementExtractionSchema,
                    system_instruction="You are a financial analysis tool. Extract every transaction row from the card text block. Output pure clean float numbers."
                )
            )
            data = json.loads(response.text)
            return data.get("transactions", [])
        except Exception as e:
            if "429" in str(e):
                wait_time = 40 * (attempt + 1)
                print(f"Rate ceiling triggered during PDF parsing. Pausing for {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"AI PDF Extraction Failure: {e}")
                break
    return []


# ==========================================
# 5. PRIORITIZED LOCAL DETERMINISTIC FILTER
# ==========================================
def rule_based_classifier(narration):
    n_upper = narration.upper()
    
    # Priority 1: Investment & Asset Management Houses (Captures Zerodha, Mutual Funds, ICCL)
    if any(x in n_upper for x in ["ZERODHA", "INDIAN CLEARING", "ICCL", "GROWW", "INDMONEY"]):
        return "Zerodha / Stock Investment", "Investment"
        
    # Priority 2: High-Frequency Merchant Matches
    if "SWIGGY" in n_upper: return "Swiggy", "Food"
    if "ZOMATO" in n_upper: return "Zomato", "Food"
    if "ZEPTO" in n_upper or "BLINKIT" in n_upper: return "Quick Commerce", "Shopping"
    
    # Priority 3: Credit Card Bill Payments (Removes double counting)
    if any(x in n_upper for x in ["CRED CC", "NEFT-CARD PAYMENT", "CC PAYMT", "SBICARD", "IMPS-CARD"]):
        return "Credit Card Settlement", "Internal Transfer"
        
    # Priority 4: Self-Account / Internal Bank Transfers
    if "OWN ACC" in n_upper or "TRANSFER TO" in n_upper or "INFT" in n_upper:
        return "Self Transfer", "Internal Transfer"
        
    # Priority 5: True Personal Peer-to-Peer UPI Transfers
    if "UPI/" in n_upper and not any(x in n_upper for x in ["RETAIL", "MERCHANT", "INFRA", "AGENCY"]):
        parts = narration.split('/')
        if len(parts) > 1: return parts[1], "Peer Transfer"
        return "UPI Personal Transfer", "Peer Transfer"
        
    return None, None

# ==========================================
# 6. BULK BATCHING CLASSIFICATION ENGINE
# ==========================================
def batch_classify_with_ai(unclassified_narrations: List[str]) -> Dict[str, Dict[str, str]]:
    """Sends a block of unique transactions to Gemini simultaneously to conserve rate constraints"""
    if not unclassified_narrations:
        return {}
        
    results_map = {}
    # Chunk inputs into groups of 25 lines maximum
    chunk_size = 25
    
    for i in range(0, len(unclassified_narrations), chunk_size):
        chunk = unclassified_narrations[i:i+chunk_size]
        payload = [{"narration": n} for n in chunk]
        
        prompt = f"Categorize this batch array list of transaction lines:\n\n{json.dumps(payload)}"
        
        for attempt in range(3):
            try:
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=BatchClassificationSchema,
                        system_instruction="Analyze financial narration array lines and map them cleanly into the categorization schema logic."
                    ),
                )
                batch_data = json.loads(response.text)
                for item in batch_data.get("results", []):
                    results_map[item["original_narration"]] = {
                        "vendor": item["vendor"],
                        "category": item["category"]
                    }
                break # Exit wait retry loop on successful query match
            except Exception as e:
                if "429" in str(e):
                    print("Batch categorization hit a rate limit block. Backing off for 45s...")
                    time.sleep(45)
                else:
                    print(f"Batch analysis runtime exception: {e}")
                    break
        time.sleep(5) # Standard spacing cushion between bulk operations
        
    return results_map

# ==========================================
# 7. MAIN ENGINE RUN PIPELINE
# ==========================================
def run_pipeline():
    all_raw_transactions = []
    statement_dir = "./statements"
    
    if not os.path.exists(statement_dir): return

    # Phase 1: Ingest and Normalize across document streams
    for file in os.listdir(statement_dir):
        path = os.path.join(statement_dir, file)
        f_lower = file.lower()
        if "keep.txt" in f_lower: continue
            
        transactions = []
        print(f"Processing target file signature: {file}")
        
        if f_lower.endswith('.csv') and f_lower.startswith('icici_bank'):
            transactions = normalize_icici_bank_csv(path)
        elif f_lower.endswith('.pdf'):
            if any(f_lower.startswith(prefix) for prefix in ['sbi_cc', 'icici_coral_amex', 'axis_myzone']):
                transactions = extract_transactions_from_pdf_via_ai(path)
                time.sleep(5) 
            else:
                continue
        else:
            continue

        for tx in transactions:
            all_raw_transactions.append({
                "date": str(tx["date"]).strip(),
                "narration": str(tx["narration"]).strip(),
                "amount": sanitize_float(tx["amount"]),
                "type": str(tx["type"]).strip()
            })

    # Phase 2: Separate Rule Matches from complex AI lines
    needed_ai_classification = set()
    final_classified_rows = []
    
    for tx in all_raw_transactions:
        # Step A: Apply local rules first
        vendor, category = rule_based_classifier(tx["narration"])
        if category:
            AI_CLASSIFICATION_CACHE[tx["narration"]] = {"vendor": vendor, "category": category}
        else:
            needed_ai_classification.add(tx["narration"])

    # Phase 3: Execute Batch AI processing for unmapped lines
    print(f"Total entries needing AI verification: {len(needed_ai_classification)}")
    ai_results = batch_classify_with_ai(list(needed_ai_classification))
    
    # Merge AI output down into master execution cache layer
    AI_CLASSIFICATION_CACHE.update(ai_results)

    # Phase 4: Construct final payload array
    for tx in all_raw_transactions:
        lookup = AI_CLASSIFICATION_CACHE.get(tx["narration"], {"vendor": "Unknown", "category": "Unknown"})
        final_classified_rows.append([
            tx["date"],
            tx["narration"],
            tx["amount"],
            tx["type"],
            lookup.get("vendor", "Unknown"),
            lookup.get("category", "Unknown")
        ])

    # Phase 5: Push clear synchronization update down to Google Sheet
    if final_classified_rows:
        sheet.clear()
        sheet.append_row(["Date", "Original Narration", "Amount", "Type", "Vendor", "Category"])
        sheet.append_rows(final_classified_rows)
        print(f"Pipeline executed successfully. Synchronized {len(final_classified_rows)} rows.")
    else:
        print("Zero rows populated.")

if __name__ == "__main__":
    run_pipeline()
