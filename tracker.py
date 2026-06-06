import os
import pandas as pd
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time

# ==========================================
# 1. SECURITY & CLIENT INITIALIZATION
# ==========================================
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

creds_dict = json.loads(os.environ.get("GOOGLE_CREDS_JSON"))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("My Expense Tracker").sheet1 

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={"response_mime_type": "application/json"}
)

# ==========================================
# 2. THE PLATFORM CONFIGURATION ENGINE (Future-Proof)
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

# ==========================================
# 3. NORMALIZATION UTILITIES
# ==========================================
def clean_dataframe_headers(df):
    """Helper to strip unnamed columns, clean trailing whitespaces, and normalize headers"""
    # Remove entirely unnamed or empty spacer columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    # Strip whitespaces from column labels
    df.columns = df.columns.str.strip()
    return df

def normalize_icici_bank(file_path):
    """Parses your specific ICICI Savings Account CSV structure"""
    df = pd.read_csv(file_path, skiprows=12)
    df = clean_dataframe_headers(df)
    
    # Fallback lookup in case of shifting row indices
    remarks_col = [col for col in df.columns if 'Remarks' in col or 'Narration' in col]
    date_col = [col for col in df.columns if 'Transaction Date' in col]
    
    if not remarks_col or not date_col:
        print(f"Crucial header mapping missed in ICICI Bank file format. Available columns: {list(df.columns)}")
        return pd.DataFrame()
        
    df.dropna(subset=[remarks_col[0]], inplace=True)
    
    normalized = pd.DataFrame()
    normalized['Date'] = df[date_col[0]]
    normalized['Narration'] = df[remarks_col[0]].astype(str).str.strip()
    
    # Locate currency amount columns resiliently
    w_col = [c for c in df.columns if 'Withdrawal' in c][0]
    d_col = [c for c in df.columns if 'Deposit' in c][0]
    
    w_amt = pd.to_numeric(df[w_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    d_amt = pd.to_numeric(df[d_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    normalized['Amount'] = w_amt + d_amt
    normalized['Type'] = ['DEBIT' if w > 0 else 'CREDIT' for w in w_amt]
    return normalized

def normalize_generic_card(file_path, config):
    """Parses standard credit card structures using mapping variables safely"""
    df = pd.read_csv(file_path, skiprows=config["skiprows"])
    df = clean_dataframe_headers(df)
    
    # Verify required headers are present dynamically
    for key in ["date_col", "desc_col", "amt_col"]:
        if config[key] not in df.columns:
            # Dynamic fallback strategy if names don't match exactly
            matched = [c for c in df.columns if config[key].lower() in c.lower()]
            if matched:
                config[key] = matched[0]
            else:
                print(f"Missing expected header column: {config[key]} in file. Headers: {list(df.columns)}")
                return pd.DataFrame()

    normalized = pd.DataFrame()
    normalized['Date'] = df[config["date_col"]]
    normalized['Narration'] = df[config["desc_col"]].astype(str).str.strip()
    
    raw_amt = df[config["amt_col"]].astype(str).str.replace(',', '')
    normalized['Type'] = ['CREDIT' if ('Cr' in val or '-' in val) else 'DEBIT' for val in raw_amt]
    normalized['Amount'] = pd.to_numeric(raw_amt.str.replace(' Cr', '').str.replace('-', ''), errors='coerce').fillna(0)
    return normalized

# ==========================================
# 4. FILTER MATRIX (Internal & Peer Transfers)
# ==========================================
def rule_based_classifier(narration, tx_type):
    n_upper = narration.upper()
    
    if any(x in n_upper for x in ["CRED CC", "NEFT-CARD PAYMENT", "CC PAYMT", "SBICARD"]):
        return "Credit Card Settlement", "Internal Transfer"
    
    if "OWN ACC" in n_upper or "TRANSFER TO" in n_upper or "INFT" in n_upper:
        return "Self Transfer", "Internal Transfer"
    
    if "UPI/" in n_upper and not any(x in n_upper for x in ["RETAIL", "MERCHANT", "INFRA", "AGENCY"]):
        parts = narration.split('/')
        if len(parts) > 1:
            return parts[1], "Peer Transfer"
        return "UPI Personal Transfer", "Peer Transfer"
            
    return None, None

# ==========================================
# 5. CORE EXECUTION ENGINE
# ==========================================
def classify_with_ai(narration):
    system_prompt = """
    You are an expert financial auditing engine. Categorize this bank statement narration.
    Respond ONLY with a valid JSON object matching this schema exactly:
    {"vendor": "Cleaned Merchant Name", "category": "Food" | "Transport" | "Utilities" | "Shopping" | "Entertainment" | "Investment" | "Salary" | "Unknown"}
    """
    try:
        response = model.generate_content(f"{system_prompt}\n\nNarration: {narration}")
        result = json.loads(response.text)
        return result.get("vendor", "Unknown"), result.get("category", "Unknown")
    except:
        return "Unknown", "Unknown"

def run_pipeline():
    all_data = []
    statement_dir = "./statements"
    
    if not os.path.exists(statement_dir):
        print("No statements folder directory discovered.")
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
                print(f"Skipping {file}: Prefix configuration mapping missing.")
                continue
            
        if df.empty:
            print(f"Skipping empty dataframe iteration layout for file: {file}")
            continue

        for _, row in df.iterrows():
            narration = row['Narration']
            tx_type = row['Type']
            
            vendor, category = rule_based_classifier(narration, tx_type)
            if not category:
                vendor, category = classify_with_ai(narration)
                time.sleep(1) # Protect free tier engine limits
                
            all_data.append([row['Date'], narration, row['Amount'], tx_type, vendor, category])

    if all_data:
        sheet.clear()
        sheet.append_row(["Date", "Original Narration", "Amount", "Type", "Vendor", "Category"])
        sheet.append_rows(all_data)
        print(f"Pipeline Execution Complete. Successfully loaded {len(all_data)} rows.")
    else:
        print("No valid transaction histories were detected to synchronize.")

if __name__ == "__main__":
    run_pipeline()
