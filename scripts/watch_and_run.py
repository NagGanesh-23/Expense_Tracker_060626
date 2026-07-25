import json
import os
from datetime import datetime, timezone

# Placed in a hidden, restricted dotfile directory
SYNC_LOG_PATH = os.path.expanduser("~/.config/fin_pipeline/failed_sync.json")


def log_quarantine_event(file_path: str, attempted_keys: list):
    """Logs minimal structural metadata for the terminal overview."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filename": os.path.basename(file_path),
        "size_kb": round(os.path.getsize(file_path) / 1024, 1),
        "attempted_routers": attempted_keys,
    }

    # Read existing payload or initialize empty array
    data = []
    if os.path.exists(SYNC_LOG_PATH):
        try:
            with open(SYNC_LOG_PATH, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass  # Handle corrupted sync log gracefully

    data.append(payload)

    # Secure the directory permissions to owner-only (chmod 700 equivalent)
    os.makedirs(os.path.dirname(SYNC_LOG_PATH), exist_ok=True)

    with open(SYNC_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)
