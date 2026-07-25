#!/usr/bin/env python3
import json
import os

SYNC_LOG_PATH = os.path.expanduser("~/.config/fin_pipeline/failed_sync.json")


def render_contextual_peek():
    if not os.path.exists(SYNC_LOG_PATH):
        return

    try:
        with open(SYNC_LOG_PATH, "r") as f:
            events = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    if not events:
        return

    # Visual layout configuration
    print("\n\033[1;31m⚠️  FINANCIAL PIPELINE: DECRYPTION QUARANTINE ACTIVE\033[0m")
    print("\033[90m=" * 75 + "\033[0m")
    print(
        f"\033[1;37m{'Target Filename':<35} | {'Size':<10} | {'Failed Target Routings':<25}\033[0m"
    )
    print("\033[90m-" * 75 + "\033[0m")

    for event in events:
        filename = event["filename"]
        # Truncate aggressively to prevent terminal wrapping issues
        if len(filename) > 32:
            filename = filename[:29] + "..."

        routers = ", ".join(event["attempted_routers"])
        size_str = f"{event['size_kb']} KB"

        print(
            f"\033[91m{filename:<35}\033[0m | {size_str:<10} | \033[33m{routers:<25}\033[0m"
        )

    print("\033[90m=" * 75 + "\033[0m")

    # Destructive read: Evaporate the disk footprint immediately
    try:
        os.remove(SYNC_LOG_PATH)
        print(
            "\033[32m✔ Persistent sync footprint successfully cleared from disk.\033[0m\n"
        )
    except OSError:
        print("\033[31m✕ Warning: Failed to clear sync footprint safely.\033[0m\n")


if __name__ == "__main__":
    render_contextual_peek()
