import os
import io
import json
import yaml
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
import pandas as pd

# pyrefly: ignore [missing-import]
from rich.console import Console

console = Console()


class DriveFetcher:
    """Fetches new PDF statements from Google Drive and tracks processed state."""

    def __init__(self, config_path: str = "config.yaml"):
        if os.path.exists(config_path):
            with open(config_path, "r") as file:
                self.config = yaml.safe_load(file) or {}
        else:
            self.config = {}

        self.creds_path = self.config.get("google_service_account_json") or os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_JSON"
        )
        # Hardcoding the requested Statement Scheduler folder ID for now, with env fallback
        self.folder_id = self.config.get("google_drive_folder_id") or os.getenv(
            "GOOGLE_DRIVE_FOLDER_ID", "1tdmsIw2Rj_TS1PZ9lSdIaN-rbcnsx9cd"
        )

        self.state_file = "data/processed_drive_files.json"
        self.download_dir = "data/raw_statements"

        # Ensure directories exist
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        # Load state
        self.processed_files = self._load_state()

        # Initialize Google Drive API client
        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        self.creds = Credentials.from_service_account_file(
            self.creds_path, scopes=scopes
        )
        self.service = build(
            "drive", "v3", credentials=self.creds, cache_discovery=False
        )

    def _load_state(self) -> dict:
        """Loads the processed files tracker."""
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def _save_state(self):
        """Saves the processed files tracker."""
        with open(self.state_file, "w") as f:
            json.dump(self.processed_files, f, indent=4)

    def list_new_files(self) -> list:
        """Lists PDF files in the folder that haven't been processed yet."""
        console.print("[cyan]Checking Google Drive for new statements...[/cyan]")
        query = f"'{self.folder_id}' in parents and mimeType='application/pdf' and trashed=false"

        results = (
            self.service.files()
            .list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, modifiedTime)",
            )
            .execute()
        )

        items = results.get("files", [])
        new_files = [f for f in items if f["id"] not in self.processed_files]

        if not items:
            console.print(
                "[yellow]No PDF files found in the specified Drive folder.[/yellow]"
            )
        else:
            console.print(
                f"[cyan]Found {len(items)} total PDFs, {len(new_files)} are new/unprocessed.[/cyan]"
            )

        self.total_drive_files = len(items)
        self.unprocessed_drive_files = len(new_files)
        return new_files

    def download_file(self, file_id: str, file_name: str) -> str:
        """Downloads a single file from Drive to the raw_statements directory."""
        request = self.service.files().get_media(fileId=file_id)

        # Make filename safe and prefix with Drive ID to prevent overwriting
        safe_name = "".join(
            [
                c
                for c in file_name
                if c.isalpha() or c.isdigit() or c in (" ", ".", "-", "_")
            ]
        ).rstrip()
        local_path = os.path.join(self.download_dir, f"{file_id}_{safe_name}")

        fh = io.FileIO(local_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False

        while done is False:
            status, done = downloader.next_chunk()

        return local_path

    def mark_processed(self, file_id: str, file_name: str, modified_time: str):
        """Marks a file as successfully parsed in the local JSON tracker."""
        self.processed_files[file_id] = {
            "name": file_name,
            "modifiedTime": modified_time,
            "processed_at": pd.Timestamp.now().isoformat(),
        }
        self._save_state()

    def sync_and_download(self) -> list:
        """High-level orchestrator: finds new files and downloads them."""
        new_files = self.list_new_files()
        downloaded_paths = []

        for f in new_files:
            console.print(f"[green]Downloading:[/green] {f['name']}...")
            try:
                local_path = self.download_file(f["id"], f["name"])
                # We return a dict containing both the local path and the Drive metadata
                # so the main orchestrator can mark it processed after parsing succeeds.
                downloaded_paths.append(
                    {
                        "local_path": local_path,
                        "drive_id": f["id"],
                        "drive_name": f["name"],
                        "modifiedTime": f.get("modifiedTime", ""),
                    }
                )
            except Exception as e:
                console.print(f"[red]Failed to download {f['name']}: {e}[/red]")

        return downloaded_paths
