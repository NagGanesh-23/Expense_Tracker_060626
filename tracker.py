import os
import pandas as pd
from google import genai
from google.genai import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time
from pydantic import BaseModel, Field
from typing import Literal

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
# 2. THE PLATFORM CONFIGURATION ENGINE
# ==========================================
CARD_CONFIGS = {
    "sbi_cc": {
        "skiprows": 0,
        "date_col": "Date",
        "desc_col": "Transaction Details",
        "amt_col": "Amount"
    },
    "icici_coral_amex": {
        "skiprows": 0,
        "date_col": "Transaction Date",
        "desc_col": "Description",
        "amt_col": "Amount"
    },
    "axis_myzone": {
        "skiprows": 0,
        "date_col": "Date",
        "desc_col": "Transaction Description",
        "amt_col": "Amount"
    }
}

class TransactionClassification(BaseModel):
    vendor: str = Field(description="The cleaned name of the merchant or destination vendor.")
    category: Literal["Food", "Transport", "Utilities", "Shopping", "Entertainment", "Investment", "Salary", "Unknown"]

# ==========================================
# 3. NORMALIZATION UTILITIES
# ==========================================
def clean_dataframe_headers(df):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = df.columns.str.strip()
    return df

def normalize_icici_bank(file_path):
    try:
        with open(file_path, 'r') as f:
            line_count = sum(1 for _ in f)
        
        rows_to_skip = 12 if line_count > 12 else 0
        df = pd.read_csv(file_path, skiprows=rows_to_skip)
    except Exception as e:
        print(f"File reading error on path {file_path}: {e}")
        return pd.DataFrame()
        
    df = clean_dataframe_headers(df)
    
    remarks_col = [col for col in df.columns if 'Remarks' in col or 'Narration' in col or 'Remarks' in col]
    date_col = [col for col in df.columns if 'Date' in col]
    
    if not remarks_col or not date_col:
        print(f"Skipping processing matrix: Column structural match failed. Headers found: {list(df.columns)}")
        return pd.DataFrame()
        
    df.dropna(subset=[remarks_col[0]], inplace=True)
    
    normalized = pd.DataFrame()
    normalized['Date'] = df[date_col[0]]
    normalized['Narration'] = df[remarks_col[0]].astype(str).str.strip()
    
    w_match = [c for c in df.columns if 'Withdrawal' in c]
    d_match = [c for c in df.columns if 'Deposit' in c]
    
    if w_match and d_match:
        w_amt = pd.to_numeric(df[w_match[0]].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        d_amt = pd.to_numeric(df[d_match[0]].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        normalized['Amount'] = w_amt + d_amt
        normalized['Type'] = ['DEBIT' if w > 0 else 'CREDIT' for w in w_amt]
    else:
        amt_match = [c for c in df.columns if 'Amount' in c or 'Amt' in c][0]
        raw_amt = df[amt_match].astype(str).str.replace(',', '')
        normalized['Type'] = ['CREDIT' if ('Cr' in val or '-' in val) else 'DEBIT' for val in raw_amt]
        normalized['Amount'] = pd.to_numeric(raw_amt.str.replace(' Cr', '').str.replace('-', ''), errors='coerce').fillna(0)
        
    return normalized

def normalize_generic_card(file_path, config):
    df = pd.read_csv(file_path, skiprows=config["skiprows"])
    df = clean_dataframe_headers(df)
    
    for key in ["date_col", "desc_col", "amt_col"]:
        if config[key] not in df.columns:
            matched = [c for c in df.columns if config[key].lower() in c.lower()]
            if matched:
                config[key] = matched[0]
            else:
                return pd.DataFrame()

    normalized = pd.DataFrame()
    normalized['Date'] = df[config["date_col"]]
    normalized['Narration'] = df[config["desc_col"]].astype(str).str.strip()
    
    raw_amt = df[config["amt_col"]].astype(str).str.replace(',', '')
    normalized['Type'] = ['CREDIT' if ('Cr' in val or '-' in val) else 'DEBIT' for val in raw_amt]
    normalized['Amount'] = pd.to_numeric(raw_amt.str.replace(' Cr', '').str.replace('-', ''), errors='coerce').fillna(0)
    return normalized

# ==========================================
# 4. FILTER MATRIX (Prioritized Overrides)
# ==========================================
def rule_based_classifier(narration, tx_type):
    n_upper = narration.upper()
    
    # Priority 1: High-Frequency Deterministic Merchant Matches
    if "SWIGGY" in n_upper:
        return "Swiggy", "Food"
    if "ZOMATO" in n_upper:
        return "Zomato", "Food"
    if "ZEPTO" in n_upper or "BLINKIT" in n_upper:
        return "Quick Commerce Grocery", "Shopping"
    
    # Priority 2: Credit Card Bill Payments (Removes double counting)
    if any(x in n_upper for x in ["CRED CC", "NEFT-CARD PAYMENT", "CC PAYMT", "SBICARD"]):
        return "Credit Card Settlement", "Internal Transfer"
    
    # Priority 3: Self-Account / Internal Transfers
    if "OWN ACC" in n_upper or "TRANSFER TO" in n_upper or "INFT" in n_upper:
        return "Self Transfer", "Internal Transfer"
    
    # Priority 4: True Peer-to-Peer UPI Transfers
    if "UPI/" in n_upper and not any(x in n_upper for x in ["RETAIL", "MERCHANT", "INFRA", "AGENCY"]):
        parts = narration.split('/')
        if len(parts) > 1:
            return parts[1], "Peer Transfer"
        return "UPI Personal Transfer", "Peer Transfer"
            
    return None, None

# ==========================================
# 5. CORE EXECUTION ENGINE (With Debugging)
# ==========================================
def classify_with_ai(narration):
    try:
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"Categorize this transaction narration: {narration}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TransactionClassification,
                system_instruction="You are an expert financial tracking engine. Categorize narration segments cleanly into the provided schema structural boundaries."
            ),
        )
        result = json.loads(response.text)
        return result.get("vendor", "Unknown"), result.get("category", "Unknown")
    except Exception as e:
        # Expose the precise API error inside your GitHub Action log stream
        print(f"CRITICAL AI FALLBACK ERROR for text [{narration}]: {e}")
        return "AI Error Fallback", "Unknown"

def run_pipeline():
    all_data = []
    statement_dir = "./statements"
    
    if not os.path.exists(statement_dir):
        return

    for file in os.listdir(statement_dir):
        path = os.path.join(statement_dir, file)
        if not file.endswith('.csv') or "keep.txt" in file:
            continue
            
        print(f"Processing File: {file}")
        
        if file.startswith("icici_bank"):
            df = normalize_icici_bank(path)
        else:
            matched_config = None
            for prefix, config in CARD_CONFIGS.items():
                if file.startswith(prefix):
                    matched_config = config
                    break
            
            if matched_config:
                df = normalize_generic_card(path, matched_config)
            else:
                continue
            
        if df is None or df.empty:
            print(f"File layout resulting in zero rows for execution framework: {file}")
            continue

        for _, row in df.iterrows():
            narration = row['Narration']
            tx_type = row['Type']
            
            vendor, category = rule_based_classifier(narration, tx_type)
            if not category:
                vendor, category = classify_with_ai(narration)
                time.sleep(1) 
                
            all_data.append([row['Date'], narration, row['Amount'], tx_type, vendor, category])

    if all_data:
        sheet.clear()
        sheet.append_row(["Date", "Original Narration", "Amount", "Type", "Vendor", "Category"])
        sheet.append_rows(all_data)
        print(f"Pipeline Execution Complete. Successfully loaded {len(all_data)} rows.")
    else:
        print("No metrics synchronized to Google Sheets.")

if __name__ == "__main__":
    run_pipeline()
