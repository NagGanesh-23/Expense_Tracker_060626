import pandas as pd

# pyrefly: ignore [missing-import]
import chardet

file_path = "models/training_data.csv"

# Detect current weird encodings (like Windows-1252 or UTF-16 BOM)
with open(file_path, "rb") as f:
    raw_bytes = f.read(10000)
    detected = chardet.detect(raw_bytes)

print(f"[INFO] Detected original encoding: {detected['encoding']}")

# Force read and strictly write back as pure UTF-8 without index
try:
    df = pd.read_csv(file_path, encoding=detected["encoding"])

    # Strip any hidden whitespaces from column names and text
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df.columns = df.columns.str.strip()

    df.to_csv(file_path, encoding="utf-8", index=False)
    print(
        "[OK] CSV successfully nuked, stripped of hidden spaces, and locked into strict UTF-8!"
    )
except Exception as e:
    print(f"[ERROR] Failed to nuke CSV: {e}")
