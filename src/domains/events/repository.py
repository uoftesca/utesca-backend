"""
Event repository.

Handles data persistence for events using a JSON file store.
"""

from pathlib import Path
import json
from typing import Dict


# Data file location
BASE_DIR = Path(__file__).resolve().parent
STORE_PATH = BASE_DIR / "data" / "events_store.json"


def load_store() -> Dict:
    """
    Load the events store from the JSON file.

    Returns:
        Dict containing the events data
    """
    if STORE_PATH.exists():
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    return {"events": []}


def save_store(store: dict) -> None:
    """
    Save the events store to the JSON file.

    Args:
        store: Dict containing the events data to save
    """
    STORE_PATH.write_text(
        json.dumps(store, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

