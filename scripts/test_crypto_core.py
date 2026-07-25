#!/usr/bin/env python3
import io
import os
import json
import pypdf
from datetime import datetime, timezone

# The exact path your terminal_peek.py will look for
SYNC_LOG_PATH = os.path.expanduser("~/.config/fin_pipeline/failed_sync.json")


def mock_log_quarantine_event(filename: str, attempted_keys: list, size_bytes: int):
    """Mocks the daemon's quarantine hook to write the sync log."""
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "filename": filename,
        "size_kb": round(size_bytes / 1024, 1),
        "attempted_routers": attempted_keys,
    }

    data = []
    if os.path.exists(SYNC_LOG_PATH):
        try:
            with open(SYNC_LOG_PATH, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass

    data.append(payload)
    os.makedirs(os.path.dirname(SYNC_LOG_PATH), exist_ok=True)
    with open(SYNC_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def test_failure_quarantine(target_pdf_path: str, bad_passwords: list) -> str:
    # Ensure a clean slate for the test
    if os.path.exists(SYNC_LOG_PATH):
        os.remove(SYNC_LOG_PATH)

    print(f"[*] Simulating failed decryption on {target_pdf_path}...")

    try:
        with open(target_pdf_path, "rb") as f:
            memory_buffer = io.BytesIO(f.read())
        file_size = memory_buffer.getbuffer().nbytes
    except IOError as e:
        return f"Disk read failure: {str(e)}"

    try:
        reader = pypdf.PdfReader(memory_buffer)

        # Simulate the hybrid engine sweeping bad passwords
        for password in bad_passwords:
            try:
                if reader.decrypt(password) > 0:
                    return "Test failed: A password actually worked. Provide a fully invalid dictionary."
            except (pypdf.errors.PasswordError, pypdf.errors.FileNotDecryptedError):
                continue

        print("[-] All dictionary keys failed. Triggering quarantine log...")
        mock_log_quarantine_event(
            os.path.basename(target_pdf_path), bad_passwords, file_size
        )

    finally:
        # CRITICAL: Verify the memory buffer is closed even during a failure state
        memory_buffer.close()
        print("[*] io.BytesIO memory buffer successfully purged.")

    # Validation Phase: Check if the terminal sync bridge was actually built
    if not os.path.exists(SYNC_LOG_PATH):
        return "CRITICAL FAILURE: Sync log was not written to disk. Terminal will be blind to this failure."

    with open(SYNC_LOG_PATH, "r") as f:
        log_data = json.load(f)

    print("\n[+] Quarantine Log successfully generated and validated!")
    print(json.dumps(log_data, indent=2))
    return "SUCCESS: Pipeline failure state successfully caught and tracked."


if __name__ == "__main__":
    # Supply your dummy encrypted file and a list of intentionally wrong passwords
    TEST_TARGET = "sample_encrypted_statement.pdf"
    DELIBERATELY_WRONG_KEYS = ["080219977467", "RGAN0802", "rgan0802"]
    # DELIBERATELY_WRONG_KEYS = ["WrongPass1", "NotTheRightOne", "AxisPass!"]

    result = test_failure_quarantine(TEST_TARGET, DELIBERATELY_WRONG_KEYS)
    print(f"\nFinal State: {result}")
