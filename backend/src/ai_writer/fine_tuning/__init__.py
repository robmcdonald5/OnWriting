"""Fine-tuning infrastructure for Vertex AI SFT workflows.

This package provides:
- Training data management (JSONL validation, conversion)
- SFT job lifecycle (GCS upload, launch, monitor)
- A/B comparison testbed (base vs. tuned model evaluation)

All operations support mock mode (default) for development without GCP.
"""
