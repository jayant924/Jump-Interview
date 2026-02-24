"""
Entry point for cron/scheduled jobs.
Usage: python -m scripts.run_cron
Or from project root: python scripts/run_cron.py
"""
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.process_data import run_pipeline

if __name__ == "__main__":
    try:
        run_pipeline()
        print("Cron job completed successfully.")
    except Exception as e:
        print(f"Cron job failed: {e}", file=sys.stderr)
        sys.exit(1)
