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
# To add a card in the future, simply add its prefix and column mappings here.
CARD_CONFIGS = {
    "sbi_cc": {
        "skiprows": 0,
        "date_col": "Date",
        "desc_col": "Transaction Details",
        "amt_col": "Amount",
        "is_split_amt": False
    },
    "icici_coral_amex": {
        "skiprows": 0,
        "date_col": "Transaction Date",
        "desc_col": "Description",
        "amt_col": "Amount",
        "is_split_amt": False
    },
    "axis_myzone": {
        "skiprows": 0,
        "date_col": "Date",
        "desc_col": "Transaction Description",
        "amt_col": "Amount",
        "is_split_amt": False
    }
}

# ==========================================
# 3. NORMALIZATION UTILITIES
# ==========================================
def normalize_icici_bank(file_path):
    """Parses your specific ICICI Savings Account CSV structure"""
    df = pd.read_csv(file_path, skiprows=12)
    df.dropna(subset=['Transaction Remarks'], inplace=True)
    
    normalized = pd.DataFrame()
    normalized['Date'] = df['Transaction Date']
    normalized['Narration'] = df['Transaction Remarks'].astype(str).str.strip()
    
    # Convert string amounts to clean floats
    w_amt = pd.to_numeric(df['Withdrawal Amount(INR)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    d_amt = pd.to_numeric(df['Deposit Amount(INR)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    normalized['Amount'] = w_amt + d_amt
    normalized['Type'] = ['DEBIT' if w > 0 else 'CREDIT' for w in w_amt]
    return normalized

def normalize_generic_card(file_path, config):
    """Parses standard credit card structures using mapping variables"""
    df = pd.read_csv(file_path, skiprows=config["skiprows"])
    
    normalized = pd.DataFrame()
    normalized['Date'] = df[config["date_col"]]
    normalized['Narration'] = df[config["desc_col"]].astype(str).str.strip()
    
    # Clean text characters out of the amount fields
    raw_amt = df[config["amt_col"]].astype(str).str.replace(',', '')
    
    # Detect credits marked via 'Cr' symbols or minus signs
    normalized['Type'] = ['CREDIT' if ('Cr' in val or '-' in val) else 'DEBIT' for val in raw_amt]
    normalized['Amount'] = pd.to_numeric(raw_amt.str.replace(' Cr', '').str.replace('-', ''), errors='coerce').fillna(0)
    return normalized

# ==========================================
# 4. FILTER MATRIX (Internal & Peer Transfers)
# ==========================================
def rule_based_classifier(narration, tx_type):
    n_upper = narration.upper()
    
    # Filter Group 1: Credit Card Bill Payments (Removes double counting)
    if any(x in n_upper for x in ["CRED CC", "NEFT-CARD PAYMENT", "CC PAYMT", "SBICARD"]):
        return "Credit Card Settlement", "Internal Transfer"
    
    # Filter Group 2: Self-Account / Internal Transfers
    if "OWN ACC" in n_upper or "TRANSFER TO" in n_upper or "INFT" in n_upper:
        return "Self Transfer", "Internal Transfer"
    
    # Filter Group 3: Peer-to-Peer UPI vs Merchant UPI
    if "UPI/" in n_upper and not any(x in n_upper for x in ["RETAIL", "MERCHANT", "INFRA", "AGENCY"]):
        # Strips out clean name from standard UPI string formats
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
        if not file.endswith('.csv'):
            continue
            
        print(f"Processing File: {file}")
        
        # Branch mapping strategy based on file prefixes
        if file.startswith("icici_bank"):
            df = normalize_icici_bank(path)
        else:
            # Dynamically look up configuration based on the prefix layout
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
            
        for _, row in df.iterrows():
            narration = row['Narration']
            tx_type = row['Type']
            
            # Layer 1: Rule Engine
            vendor, category = rule_based_classifier(narration, tx_type)
            
            # Layer 2: AI Fallback
            if not category:
                vendor, category = classify_with_ai(narration)
                time.sleep(1) # Protect free tier engine limits
                
            all_data.append([row['Date'], narration, row['Amount'], tx_type, vendor, category])

    # Synchronize execution matrix straight into Google Sheets
    if all_data:
        sheet.clear()
        sheet.append_row(["Date", "Original Narration", "Amount", "Type", "Vendor", "Category"])
        sheet.append_rows(all_data)
        print(f"Pipeline Execution Complete. Successfully loaded {len(all_data)} rows.")

if __name__ == "__main__":
    run_pipeline()
