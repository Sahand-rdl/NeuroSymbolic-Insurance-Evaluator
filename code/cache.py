import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from code.config import CACHE_DIR

class DiskCache:
    """
    Thread-safe-ish read/write disk-backed cache.
    Saves raw VLM responses in .cache/ using SHA-256 hash of the input key dictionary.
    """
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_hash(self, key_data: Dict[str, Any]) -> str:
        # Standardize key serialization by sorting keys to guarantee deterministic hash
        serialized = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, key_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Retrieves the cached value for the given key_data.
        Returns None if not cached.
        """
        cache_id = self._compute_hash(key_data)
        cache_file = self.cache_dir / f"{cache_id}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                    return entry.get("val")
            except Exception:
                return None
        return None

    def set(self, key_data: Dict[str, Any], val_data: Dict[str, Any]) -> None:
        """
        Saves key_data and its associated value val_data to disk.
        """
        cache_id = self._compute_hash(key_data)
        cache_file = self.cache_dir / f"{cache_id}.json"
        data_to_save = {
            "key": key_data,
            "val": val_data
        }
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
