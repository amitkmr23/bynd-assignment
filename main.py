#!/usr/bin/env python3
"""
Company One-Pager Generator
Usage:
    python main.py "Bharat Forge Limited"
    python main.py "Brakes India Private Limited"
    python main.py "Bharat Forge Limited" outputs/my_report.md
"""
import sys
import os
from pathlib import Path

# Load .env before any src imports
from dotenv import load_dotenv
load_dotenv()

# Make src importable from the project root
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline import run_pipeline
from src.output.formatter import format_onepager


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    company_name = sys.argv[1].strip()
    if not company_name:
        print("Error: company name cannot be empty.")
        sys.exit(1)

    # Determine output path
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        safe = company_name.lower().replace(" ", "_")
        safe = "".join(c for c in safe if c.isalnum() or c == "_")[:40]
        output_path = Path("outputs") / f"{safe}.md"

    # Run the pipeline
    onepager = run_pipeline(company_name)

    # Render to Markdown
    markdown = format_onepager(onepager)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Saved → {output_path}\n")
    print(markdown)


if __name__ == "__main__":
    main()
