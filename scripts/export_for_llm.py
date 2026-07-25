#!/usr/bin/env python3
import os


def export_for_llm(output_file="llm_context_export.txt"):
    # Directories and file extensions to ignore
    ignore_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        "data",
        ".config",
        ".idea",
        ".vscode",
    }
    ignore_exts = {".pdf", ".pyc", ".whl", ".zip", ".jsonl", ".sqlite3"}

    print(f"[*] Compiling repository into {output_file}...")

    with open(output_file, "w", encoding="utf-8") as out:
        out.write("# Repository Export for LLM Context\n\n")

        # First, generate a tree structure
        out.write("## Directory Structure\n```\n")
        for root, dirs, files in os.walk("."):
            # Filter directories in place
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            level = root.replace(".", "").count(os.sep)
            indent = " " * 4 * (level)
            out.write(f"{indent}{os.path.basename(root)}/\n")
            subindent = " " * 4 * (level + 1)
            for f in files:
                if not any(f.endswith(ext) for ext in ignore_exts):
                    out.write(f"{subindent}{f}\n")
        out.write("```\n\n")

        # Next, dump the file contents
        out.write("## File Contents\n\n")
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in ignore_exts):
                    continue

                filepath = os.path.join(root, file)

                # Skip the output file itself
                if file == output_file:
                    continue

                out.write(f"\n{'='*80}\n")
                out.write(f"File: {filepath}\n")
                out.write(f"{'='*80}\n")
                out.write("```python\n" if file.endswith(".py") else "```text\n")

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        out.write(f.read())
                except Exception as e:
                    out.write(f"# [Error reading file: {str(e)}]\n")

                out.write("\n```\n")

    print(f"[+] Successfully exported to {output_file} in the project root!")


if __name__ == "__main__":
    export_for_llm()
