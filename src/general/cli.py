"""CLI utilities for progress bars and user interaction."""

from tqdm import tqdm
from typing import Optional


class ProgressTracker:
    """Wrapper around tqdm for consistent progress tracking across pipeline stages."""

    def __init__(self, total: int, desc: str, unit: str = "example"):
        """
        Initialize progress tracker.

        Args:
            total: Total number of items to process
            desc: Description of the task
            unit: Unit name for items being processed
        """
        self.pbar = tqdm(
            total=total,
            desc=desc,
            unit=unit,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
            dynamic_ncols=True,
            leave=True,
            position=0
        )

    def update(self, n: int = 1):
        """Update progress by n items."""
        self.pbar.update(n)

    def set_postfix(self, **kwargs):
        """Set postfix status (e.g., success/fail counts)."""
        self.pbar.set_postfix(**kwargs)

    def close(self):
        """Close the progress bar."""
        self.pbar.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False  # Don't suppress exceptions
