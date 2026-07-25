import pandas as pd
import os
import sys
from datetime import datetime
import glob
import yaml


def run_audit(csv_path="output/transactions.csv", exit_on_fail=True):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        if exit_on_fail:
            sys.exit(1)
        return False

    print(f"Auditing {csv_path}...")
    df = pd.read_csv(csv_path)

    # Load optional fields from config
    optional_fields = ["reviewed_category", "reviewed_at", "reviewer_notes"]
    try:
        if os.path.exists("config.yaml"):
            with open("config.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                optional_fields = config.get("audit_optional_fields", optional_fields)
    except Exception as e:
        print(f"Warning: could not load config.yaml: {e}")

    issues_found = False

    # 1. Total transaction count
    total_txns = len(df)

    # 2. Breakdown by source
    source_col = "source_account" if "source_account" in df.columns else "source"
    if source_col in df.columns:
        source_breakdown = df[source_col].value_counts().to_dict()
    else:
        source_breakdown = {"Unknown": total_txns}

    # 3. Null / Empty / NaN per column
    column_stats = {}
    for col in df.columns:
        # Nulls or NaNs
        null_count = int(df[col].isna().sum())

        # Empty strings or whitespace only (only for string/object columns)
        if df[col].dtype == "object":
            empty_count = int(df[col].astype(str).str.strip().eq("").sum())
            # Also catch literal "nan" or "NaN" strings
            literal_nan_count = int(df[col].astype(str).str.lower().eq("nan").sum())
        else:
            empty_count = 0
            literal_nan_count = 0

        total_issues = null_count + empty_count + literal_nan_count
        if total_issues > 0 and col not in optional_fields:
            issues_found = True

        column_stats[col] = {
            "null_or_nan": null_count,
            "empty_string": empty_count,
            "literal_nan": literal_nan_count,
            "total_issues": total_issues,
        }

    # 4. Duplicate rows
    full_duplicates = df[df.duplicated(keep=False)]
    full_dup_count = len(full_duplicates)
    if full_dup_count > 0:
        issues_found = True

    # Duplicate by transaction ID
    id_dup_count = 0
    id_dup_samples = []
    if "transaction_id" in df.columns:
        id_duplicates = df[df.duplicated(subset=["transaction_id"], keep=False)]
        id_dup_count = len(id_duplicates)
        if id_dup_count > 0:
            issues_found = True
            id_dup_samples = id_duplicates["transaction_id"].unique()[:10].tolist()

    # Prepare Report
    os.makedirs("audit", exist_ok=True)
    existing_reports = glob.glob("audit/audit_report_*.md")
    run_num = len(existing_reports) + 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_path = f"audit/audit_report_{timestamp}_run{run_num}.md"

    status = "FAIL" if issues_found else "PASS"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Data Quality Audit Report\n\n")
        f.write(f"**Status:** {'❌ FAIL' if issues_found else '✅ PASS'}\n")
        f.write(f"**Timestamp:** {timestamp}\n")
        f.write(f"**Run ID:** {run_num}\n")
        f.write(f"**Total Transactions Processed:** {total_txns}\n\n")

        f.write("## Transactions by Source\n")
        f.write("| Source | Count |\n")
        f.write("|--------|-------|\n")
        for src, count in source_breakdown.items():
            f.write(f"| {src} | {count} |\n")
        f.write("\n")

        f.write("## Column-Level Checks (Nulls, Empties, NaNs)\n")
        f.write(
            "| Column | Null/NaN | Empty Strings | Literal 'NaN' | Total Issues |\n"
        )
        f.write(
            "|--------|----------|---------------|---------------|--------------|\n"
        )
        for col, stats in column_stats.items():
            f.write(
                f"| {col} | {stats['null_or_nan']} | {stats['empty_string']} | {stats['literal_nan']} | {stats['total_issues']} |\n"
            )
        f.write("\n")

        f.write("## Duplicates\n")
        f.write(f"- **Full Row Duplicates:** {full_dup_count}\n")
        f.write(f"- **Transaction ID Duplicates:** {id_dup_count}\n")
        if id_dup_count > 0:
            f.write(f"- **Sample of Duplicate IDs (max 10):**\n")
            for sample_id in id_dup_samples:
                f.write(f"  - `{sample_id}`\n")

    print(f"Audit completed. Status: {status}. Report saved to {report_path}")

    if exit_on_fail:
        if issues_found:
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        return not issues_found


if __name__ == "__main__":
    run_audit()
