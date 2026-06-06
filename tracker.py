import os
import pandas as pd
from google import genai
from google.genai import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time
from pypdf import PdfReader
from pydantic import BaseModel, Field
from typing import Literal, List

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

# ==========================================
# 2. DATA UTILITIES & STRATEGIC SCHEMAS
# ==========================================
class TransactionItem(BaseModel):
    date: str = Field(description="The transaction date found in the statement row.")
    narration: str = Field(description="The merchant or transfer raw narration string.")
    amount: float = Field(description="The transaction currency value numerical amount.")
    type: Literal["DEBIT", "CREDIT"] = Field(description="DEBIT for spends/withdrawals, CREDIT for settlements/refunds.")

class StatementExtractionSchema(BaseModel):
    transactions: List[TransactionItem]

class FinalRowSchema(BaseModel):
    vendor: str = Field(description="Cleaned business entity or person name.")
    category: Literal["Food", "Transport", "Utilities", "Shopping", "Entertainment", "Investment", "Salary", "Internal Transfer", "Peer Transfer", "Unknown"]

def clean_dataframe_headers(df):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = df.columns.str.strip()
    return df

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
        
        if w_match and d_match:
            w_amt = pd.to_numeric(str(row[w_match[0]]).replace(',', ''), errors='coerce') or 0
            d_amt = pd.to_numeric(str(row[d_match[0]]).replace(',', ''), errors='coerce') or 0
            if w_amt > 0:
                amt, tx_type = w_amt, 'DEBIT'
            else:
                amt, tx_type = d_amt, 'CREDIT'
        else:
            amt, tx_type = 0, 'DEBIT'
            
        parsed_rows.append({"date": date, "narration": narration, "amount": amt, "type": tx_type})
    return parsed_rows

# ==========================================
# 4. LLM-BASED PDF STATEMENT EXTRACTION
# ==========================================
def extract_transactions_from_pdf_via_ai(file_path):
    """Extracts text contents via pypdf and uses Gemini to map columns with absolute structural accuracy"""
    text_content = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content += text + "\n"
    except Exception as e:
        print(f"Error accessing file path matrix {file_path}: {e}")
        return []

    if not text_content.strip():
        return []

    prompt = f"Extract all individual transactions, purchases, fees, reversals, and settlements from this text layout dump:\n\n{text_content}"
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StatementExtractionSchema,
                system_instruction="You are a financial analysis tool. Extract every transaction row from the card text block. Ignore rewards balances or summary stats. Ensure all monetary figures are parsed as clean floats."
            )
        )
        data = json.loads(response.text)
        return data.get("transactions", [])
    except Exception as e:
        print(f"AI Statement Parsing Failure on document: {e}")
        return []

# ==========================================
# 5. ENHANCED RULE-BASED AND AI CLASSIFIER
# ==========================================
def rule_based_classifier(narration):
    n_upper = narration.upper()
    
    if "SWIGGY" in n_upper: return "Swiggy", "Food"
    if "ZOMATO" in n_upper: return "Zomato", "Food"
    if "ZEPTO" in n_upper or "BLINKIT" in n_upper: return "Quick Commerce", "Shopping"
    
    if any(x in n_upper for x in ["CRED CC", "NEFT-CARD PAYMENT", "CC PAYMT", "SBICARD", "IMPS-CARD"]):
        return "Credit Card Settlement", "Internal Transfer"
    if "OWN ACC" in n_upper or "TRANSFER TO" in n_upper or "INFT" in n_upper:
        return "Self Transfer", "Internal Transfer"
        
    if "UPI/" in n_upper and not any(x in n_upper for x in ["RETAIL", "MERCHANT", "INFRA", "AGENCY"]):
        parts = narration.split('/')
        if len(parts) > 1: return parts[1], "Peer Transfer"
        return "UPI Personal Transfer", "Peer Transfer"
            
    return None, None

def enrich_and_categorize(narration, tx_type):
    # Rule engine layer
    vendor, category = rule_based_classifier(narration)
    if category:
        return vendor, category
        
    # AI Fallback categorization layer
    try:
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"Classify this narration: {narration} (Type: {tx_type})",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FinalRowSchema,
                system_instruction="Analyze financial narration segments and map them into the categorization boundaries. Clean vendor names down to corporate equivalents."
            ),
        )
        result = json.loads(response.text)
        return result.get("vendor", "Unknown"), result.get("category", "Unknown")
    except:
        return "Unknown", "Unknown"

# ==========================================
# 6. SYSTEM RUN PIPELINE Execution
# ==========================================
def run_pipeline():
    all_rows = []
    statement_dir = "./statements"
    
    if not os.path.exists(statement_dir):
        return

    for file in os.listdir(statement_dir):
        path = os.path.join(statement_dir, file)
        f_lower = file.lower()
        
        if "keep.txt" in f_lower:
            continue
            
        transactions = []
        print(f"Processing target file signature: {file}")
        
        if f_lower.endswith('.csv') and f_lower.startswith('icici_bank'):
            transactions = normalize_icici_bank_csv(path)
        elif f_lower.endswith('.pdf'):
            if any(f_lower.startswith(prefix) for prefix in ['sbi_cc', 'icici_coral_amex', 'axis_myzone']):
                transactions = extract_transactions_from_pdf_via_ai(path)
                time.sleep(2) # Protect API context limits
            else:
                continue
        else:
            continue

        for tx in transactions:
            narration = tx["narration"]
            tx_type = tx["type"]
            date = tx["date"]
            amount = tx["amount"]
            
            vendor, category = enrich_and_categorize(narration, tx_type)
            all_rows.append([date, narration, amount, tx_type, vendor, category])

    if all_rows:
        sheet.clear()
        sheet.append_row(["Date", "Original Narration", "Amount", "Type", "Vendor", "Category"])
        sheet.append_rows(all_rows)
        print(f"Pipeline executed successfully. Synchronized {len(all_rows)} rows.")
    else:
        print("Zero transactions written.")

if __name__ == "__main__":
    run_pipeline()
