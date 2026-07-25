from pipeline.classification_orchestrator import ClassificationOrchestrator
from output.gsheets_writer import GoogleSheetsWriter
from parsers.hdfc_pixel import HDFCPixelParser
from utils.detector import detect_source
import argparse
import os
import pandas as pd

# pyrefly: ignore [missing-import]
from rich.console import Console

# pyrefly: ignore [missing-import]
from rich.table import Table

# pyrefly: ignore [missing-import]
from rich.prompt import Prompt

# Import our pipeline modules
from parsers.icici_savings import ICICISavingsParser
from parsers.axis_myzone import AxisMyZoneParser
from parsers.sbi_cashback import SBICashbackParser
from parsers.icici_cc import ICICICreditCardParser
from pipeline.normalizer import Normalizer
from pipeline.drive_fetcher import DriveFetcher

# Setup Rich console for beautiful terminal UI
# Force UTF-8 to avoid UnicodeEncodeError with emojis on Windows cp1252 consoles
import sys, io

if sys.platform == "win32":
    # Wrap stdout in a UTF-8 text stream so Rich never touches the legacy Win32 console
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(file=sys.stdout, force_terminal=True, record=True)

# Map CLI source arguments to their respective parser classes
PARSER_MAP = {
    "icici_savings": ICICISavingsParser,
    "axis_myzone": AxisMyZoneParser,
    "sbi_cashback": SBICashbackParser,
    "icici_cc": ICICICreditCardParser,
    "hdfc_pixel": HDFCPixelParser,
}


def print_summary(df: pd.DataFrame):
    """Prints a beautiful summary table of the run."""
    console.print("\n[bold cyan]=== EXPENSE TRACKER RUN SUMMARY ===[/bold cyan]")

    total_txns = len(df)
    rule_count = len(df[df["classification_method"] == "rule"])
    ml_count = len(df[df["classification_method"] == "ml"])
    llm_count = len(df[df["classification_method"] == "llm"])
    manual_count = len(df[df["classification_method"] == "manual"])
    uncategorized = len(df[df["category"] == "Uncategorized"])

    console.print(f"Transactions found  : [bold]{total_txns}[/bold]")
    console.print(f"  |- Rule-classified  : {rule_count}")
    console.print(f"  |- ML-classified    : {ml_count}")
    console.print(f"  |- LLM-classified   : {llm_count}")
    console.print(f"  |- Manually Reviewed: {manual_count}")
    console.print(f"  |_ Uncategorized    : [bold red]{uncategorized}[/bold red]")

    # Top categories summary
    console.print("\n[bold yellow]Top Spending Categories:[/bold yellow]")
    spend_df = (
        df[df["transaction_type"] == "debit"]
        .groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    for cat, amount in spend_df.items():
        console.print(f"  {cat.ljust(20)}: Rs. {amount:,.2f}")
    console.print("[bold cyan]===================================[/bold cyan]\n")


def interactive_review(df: pd.DataFrame, threshold: float = 0.85):
    """Prompts the user to review low-confidence or uncategorized transactions."""
    # Find rows that need review
    mask = (df["category"] == "Uncategorized") | (df["confidence"] < threshold)
    review_df = df[mask]

    if review_df.empty:
        console.print("[green]No transactions require manual review![/green]")
        return df

    console.print(
        f"\n[bold yellow]Interactive Review: {len(review_df)} transactions need your attention.[/bold yellow]"
    )

    new_training_data = []

    for idx, row in review_df.iterrows():
        console.print(
            f"\n[cyan]Date:[/cyan] {row['transaction_date']} | [cyan]Amount:[/cyan] Rs. {row['amount']} ({row['transaction_type']})"
        )
        console.print(f"[cyan]Desc:[/cyan] [bold]{row['description']}[/bold]")
        console.print(
            f"[dim]Current guess: {row['category']} (Confidence: {row['confidence']:.2f})[/dim]"
        )

        user_cat = Prompt.ask("Enter category (or press Enter to accept guess)")

        if user_cat.strip():
            # User provided a new category
            df.at[idx, "category"] = user_cat.strip()
            df.at[idx, "confidence"] = 1.0
            df.at[idx, "classification_method"] = "manual"

            # Save for continuous learning
            new_training_data.append(
                {
                    "transaction_date": row.get("transaction_date", ""),
                    "description": row["description"],
                    "amount": row.get("amount", 0.0),
                    "transaction_type": row.get("transaction_type", ""),
                    "source_account": row.get("source_account", ""),
                    "category": user_cat.strip(),
                }
            )
        else:
            # User accepted the guess, just mark it as manually reviewed so it stops asking
            df.at[idx, "classification_method"] = "manual"
            new_training_data.append(
                {
                    "transaction_date": row.get("transaction_date", ""),
                    "description": row["description"],
                    "amount": row.get("amount", 0.0),
                    "transaction_type": row.get("transaction_type", ""),
                    "source_account": row.get("source_account", ""),
                    "category": row["category"],
                }
            )

    # Append new learnings to the training dataset
    if new_training_data:
        training_file = "models/training_data.csv"
        learnings_df = pd.DataFrame(new_training_data)

        if os.path.exists(training_file):
            learnings_df.to_csv(training_file, mode="a", header=False, index=False)
        else:
            learnings_df.to_csv(training_file, index=False)

        console.print(
            f"[green]Added {len(new_training_data)} new examples to training data. The ML model just got smarter![/green]"
        )

    return df


def main():
    parser = argparse.ArgumentParser(description="Personal Expense Tracker Pipeline")
    parser.add_argument(
        "--files", nargs="*", default=[], help="List of statement files to process"
    )
    parser.add_argument(
        "--drive-sync",
        action="store_true",
        help="Download new statements from Google Drive",
    )
    parser.add_argument(
        "--source",
        choices=list(PARSER_MAP.keys()) + ["auto"],
        default="auto",
        help="Source account type",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Skip syncing with Google Sheets"
    )
    parser.add_argument(
        "--reset-sheet",
        action="store_true",
        help="DANGER: Wipes Google Sheet tabs before writing",
    )
    parser.add_argument(
        "--setup-sheet",
        action="store_true",
        help="Setup Google Sheet data validation and formatting",
    )
    parser.add_argument(
        "--sync-feedback",
        action="store_true",
        help="Read corrected manual reviews from Google Sheets and append to ML training data",
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Trigger ML model retrain (rebuild embedding cache)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive review prompt for low-confidence or uncategorized transactions",
    )
    args = parser.parse_args()

    if args.setup_sheet:
        from output.gsheets_setup import setup_sheet

        setup_sheet("config.yaml")
        console.print(
            "[green]Successfully setup Google Sheets validation and formatting.[/green]"
        )
        return

    if args.sync_feedback:
        from pipeline.feedback_sync import FeedbackSync

        console.print("[bold cyan]=== SYNCING FEEDBACK FROM SHEETS ===[/bold cyan]")
        syncer = FeedbackSync("config.yaml")
        rows_synced, rows_confirmed, rows_skipped = syncer.sync(dry_run=args.dry_run)

        retrain_trigger = syncer.writer.config.get("retrain_trigger_count", 10)

        if args.retrain or (rows_synced >= retrain_trigger):
            if not args.retrain:
                console.print(
                    f"[bold cyan]=== AUTO-RETRAINING ML MODEL ({rows_synced} >= {retrain_trigger} threshold) ===[/bold cyan]"
                )
            else:
                console.print(
                    "[bold cyan]=== RETRAINING ML MODEL (Forced via --retrain) ===[/bold cyan]"
                )

            from pipeline.ml_classifier import MLClassifier

            if not args.dry_run:
                # Initialization alone drops cache & rebuilds embeddings if hash changed
                MLClassifier("config.yaml")
                console.print(
                    "[green]Successfully rebuilt ML embedding cache with new training data.[/green]"
                )
            else:
                console.print(
                    "[yellow][DRY-RUN] Would have rebuilt ML embedding cache.[/yellow]"
                )
        elif rows_synced > 0:
            remaining = retrain_trigger - rows_synced
            console.print(
                f"[dim]Auto-retrain skipped: {rows_synced} synced. Need {remaining} more for auto-retrain (threshold: {retrain_trigger}).[/dim]"
            )

        os.makedirs("logs", exist_ok=True)
        console.save_text("logs/pipeline.log")
        return

    if args.retrain and not args.sync_feedback:
        console.print(
            "[bold cyan]=== RETRAINING ML MODEL (Standalone via --retrain) ===[/bold cyan]"
        )
        from pipeline.ml_classifier import MLClassifier

        if not args.dry_run:
            MLClassifier("config.yaml")
            console.print(
                "[green]Successfully rebuilt ML embedding cache with new training data.[/green]"
            )
        else:
            console.print(
                "[yellow][DRY-RUN] Would have rebuilt ML embedding cache.[/yellow]"
            )
        os.makedirs("logs", exist_ok=True)
        console.save_text("logs/pipeline.log")
        return

    if not args.files and not args.drive_sync:
        console.print(
            "[red]Error: You must specify either --files or --drive-sync[/red]"
        )
        return

    # 1. Initialize Pipeline Components Once
    normalizer = Normalizer()

    # Initialize our new central stream manager
    orchestrator = ClassificationOrchestrator("config.yaml")

    if not args.dry_run:
        writer = GoogleSheetsWriter("config.yaml")
        if args.reset_sheet:
            writer.reset_worksheets()

    # Load passwords if available
    passwords = []
    if os.path.exists("passwords.txt"):
        with open("passwords.txt", "r") as pf:
            passwords = [line.strip() for line in pf if line.strip()]

    # Check for PDF_PASSWORDS env var
    env_passwords = os.getenv("PDF_PASSWORDS")
    if env_passwords:
        import re

        env_pw_list = [
            p.strip() for p in re.split(r"[:\n]+", env_passwords) if p.strip()
        ]
        passwords.extend(env_pw_list)

    passwords = list(set(passwords))  # Deduplicate

    # 2. Process Files in Batch
    all_raw_txns = []

    drive_fetcher = None
    drive_file_map = {}  # Maps local_path -> drive metadata

    if args.drive_sync:
        drive_fetcher = DriveFetcher("config.yaml")
        downloaded = drive_fetcher.sync_and_download()
        for d in downloaded:
            if d["local_path"] not in args.files:
                args.files.append(d["local_path"])
            drive_file_map[d["local_path"]] = d

    successful_files = []
    file_stats = []

    for filepath in args.files:
        if not os.path.exists(filepath):
            console.print(f"[red]File not found: {filepath}[/red]")
            continue

        source_key = detect_source(filepath) if args.source == "auto" else args.source
        ParserClass = PARSER_MAP.get(source_key)

        if not ParserClass:
            console.print(f"[red]No parser found for source: {source_key}[/red]")
            continue

        with console.status(f"[bold green]Parsing {filepath}..."):
            try:
                p = ParserClass(filepath, passwords=passwords)
                raw_stream = p.parse_stream()
                normalized_stream = [
                    normalizer.normalize_single(txn) for txn in raw_stream
                ]
                all_raw_txns.extend(normalized_stream)

                if len(normalized_stream) == 0:
                    console.print(
                        f"[bold yellow]WARNING: Parsed 0 transactions from {filepath}. It might be empty, or the parser could not extract any data.[/bold yellow]"
                    )
                    file_stats.append(
                        {
                            "file": os.path.basename(filepath),
                            "txns": 0,
                            "status": "0 Transactions",
                        }
                    )
                else:
                    console.print(
                        f"[green]Parsed {len(normalized_stream)} transactions from {filepath}.[/green]"
                    )
                    file_stats.append(
                        {
                            "file": os.path.basename(filepath),
                            "txns": len(normalized_stream),
                            "status": "Success",
                        }
                    )

                successful_files.append(filepath)
                if drive_fetcher and filepath in drive_file_map:
                    d = drive_file_map[filepath]
                    drive_fetcher.mark_processed(
                        d["drive_id"], d["drive_name"], d["modifiedTime"]
                    )
            except Exception as e:
                console.print(f"[red]Error parsing {filepath}: {e}[/red]")
                file_stats.append(
                    {
                        "file": os.path.basename(filepath),
                        "txns": 0,
                        "status": f"Error: {str(e)}",
                    }
                )
                continue

    console.print("\n[bold cyan]=== FILE PROCESSING SUMMARY ===[/bold cyan]")
    if drive_fetcher:
        total = getattr(drive_fetcher, "total_drive_files", 0)
        unprocessed = getattr(drive_fetcher, "unprocessed_drive_files", 0)
        skipped = total - unprocessed
        console.print(f"Total files in Google Drive folder : [bold]{total}[/bold]")
        console.print(f"Files previously processed/skipped : [bold]{skipped}[/bold]")
        console.print(
            f"Files fetched and processed today  : [bold]{unprocessed}[/bold]"
        )

    console.print("\n[bold]File-Level Extraction Details:[/bold]")
    if not file_stats:
        console.print("  [yellow]No files were processed in this run.[/yellow]")
    else:
        for stat in file_stats:
            color = (
                "green"
                if stat["status"] == "Success"
                else "yellow" if stat["status"] == "0 Transactions" else "red"
            )
            console.print(
                f"  - [{color}]{stat['file']}[/{color}]: {stat['txns']} transactions ({stat['status']})"
            )
    console.print()

    # Save all output to a log file
    os.makedirs("logs", exist_ok=True)
    console.save_text("logs/pipeline.log")
    console.print("[dim]A copy of these logs has been saved to logs/pipeline.log[/dim]")

    if not all_raw_txns:
        console.print("[yellow]No transactions found to process.[/yellow]")
        return

    # 3. Classify all transactions in bulk
    with console.status(
        f"[bold green]Classifying {len(all_raw_txns)} transactions in bulk..."
    ):
        all_processed_txns = orchestrator.process_batch(all_raw_txns)

    if args.interactive and all_processed_txns:
        threshold = orchestrator.config.get("review_confidence_threshold", 0.85)
        df_rev = pd.DataFrame(all_processed_txns)
        df_rev = interactive_review(df_rev, threshold=threshold)
        all_processed_txns = df_rev.to_dict(orient="records")

    # 4. Write to Google Sheets in a single pass
    if not args.dry_run:
        with console.status(f"[bold green]Writing to Google Sheets..."):
            writer.write_stream(all_processed_txns, is_reset=args.reset_sheet)
            console.print(
                f"[green]Successfully synced {len(all_processed_txns)} transactions to Google Sheets.[/green]"
            )
    else:
        console.print(
            f"[yellow]Dry Run: Processed {len(all_processed_txns)} transactions in memory.[/yellow]"
        )

    console.print("\n[bold cyan]=== PIPELINE EXECUTION COMPLETE ===[/bold cyan]\n")

    if all_processed_txns:
        df = pd.DataFrame(all_processed_txns)

        # Save to local CSV for auditing
        os.makedirs("output", exist_ok=True)
        df.to_csv("output/transactions.csv", index=False)
        console.print(
            "[dim]Saved local copy to output/transactions.csv for auditing.[/dim]"
        )

        # Print the breakdown of classification methods
        method_counts = df["classification_method"].value_counts()
        category_counts = df["category"].value_counts()

        console.print(
            "\n[bold magenta]Pipeline Classification Integrity Report:[/bold magenta]"
        )
        console.print(method_counts)
        console.print("\n[bold magenta]Category Distribution:[/bold magenta]")
        console.print(category_counts)

        # audit_data(df) # Deprecated local console audit
        try:
            from scripts.audit_output import run_audit

            console.print(
                "\n[bold cyan]Generating Full Markdown Audit Report...[/bold cyan]"
            )
            run_audit("output/transactions.csv", exit_on_fail=False)
        except Exception as e:
            console.print(f"[red]Failed to run markdown audit: {e}[/red]")


def audit_data(df: pd.DataFrame):
    """Checks the data quality and prints an audit report."""
    console.print("\n[bold red]=== DATA QUALITY AUDIT REPORT ===[/bold red]")
    issues_found = False

    # Check for empty or NaN descriptions
    empty_desc = df[
        df["description"].isna()
        | (df["description"] == "")
        | (df["description"].astype(str).str.lower() == "nan")
    ]
    if not empty_desc.empty:
        issues_found = True
        console.print(
            f"[red]⚠ Found {len(empty_desc)} transactions with empty/NaN descriptions.[/red]"
        )
        for _, row in empty_desc.head(5).iterrows():
            console.print(
                f"  - {row.get('transaction_date', 'Unknown Date')} | Rs. {row.get('amount', 0)} | {row.get('source_account', 'Unknown')}"
            )
        if len(empty_desc) > 5:
            console.print("  - ...and more")

    # Check for 0 amounts
    zero_amt = df[df["amount"] == 0]
    if not zero_amt.empty:
        issues_found = True
        console.print(
            f"[yellow]⚠ Found {len(zero_amt)} transactions with 0.0 amount.[/yellow]"
        )

    # Check for missing dates
    missing_date = df[df["transaction_date"].isna() | (df["transaction_date"] == "")]
    if not missing_date.empty:
        issues_found = True
        console.print(
            f"[red]⚠ Found {len(missing_date)} transactions with missing dates.[/red]"
        )

    if not issues_found:
        console.print(
            "[green]✔ All data quality checks passed! No empty descriptions or 0 amounts found.[/green]"
        )
    console.print("[bold red]=================================[/bold red]\n")


if __name__ == "__main__":
    main()
