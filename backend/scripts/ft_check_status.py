"""Check the status of a Vertex AI tuning job.

Usage:
    poetry run python scripts/ft_check_status.py <job-name>
    poetry run python scripts/ft_check_status.py projects/my-project/locations/us-central1/tuningJobs/123
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.jobs.monitor import JobMonitor


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ft_check_status.py <job-name>")
        sys.exit(1)

    job_name = sys.argv[1]
    monitor = JobMonitor()
    status = monitor.check_status(job_name)

    print(f"Job:      {status.job_name}")
    print(f"State:    {status.state}")
    print(f"Created:  {status.create_time}")
    print(f"Updated:  {status.update_time}")
    print(f"Mock:     {status.is_mock}")
    if status.tuned_model_endpoint:
        print(f"Endpoint: {status.tuned_model_endpoint}")
    if status.error_message:
        print(f"Error:    {status.error_message}")


if __name__ == "__main__":
    main()
