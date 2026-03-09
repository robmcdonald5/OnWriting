"""List available tuned models.

Usage:
    poetry run python scripts/ft_list_models.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.jobs.monitor import JobMonitor


def main():
    monitor = JobMonitor()
    models = monitor.list_tuned_models()

    if not models:
        print("No tuned models found.")
        return

    print(f"Found {len(models)} tuned model(s):\n")
    for m in models:
        print(f"  Name:    {m.model_name}")
        print(f"  Source:  {m.source_model}")
        print(f"  Endpoint: {m.endpoint}")
        print(f"  Created: {m.create_time}")
        print(f"  Mock:    {m.is_mock}")
        print()


if __name__ == "__main__":
    main()
