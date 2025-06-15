import logging
import threading
from typing import Dict, Any, Optional

from ...interfaces.mne_interfaces import MNEResultStorageInterface


class MNEResultStorage(MNEResultStorageInterface):
    """Thread-safe storage for MNE task results."""
    
    def __init__(self) -> None:
        """Initialize the result storage."""
        self._results: Dict[str, Any] = {}
        self._lock = threading.RLock()
        logging.debug("MNE result storage initialized")
    
    def store_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Store a task result."""
        with self._lock:
            self._results[task_id] = result
            logging.debug(f"Stored result for task: {task_id}")
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a stored result."""
        with self._lock:
            return self._results.get(task_id)
    
    def remove_result(self, task_id: str) -> bool:
        """Remove a stored result."""
        with self._lock:
            if task_id in self._results:
                del self._results[task_id]
                logging.debug(f"Removed result for task: {task_id}")
                return True
            return False
    
    def clear_all_results(self) -> None:
        """Clear all stored results."""
        with self._lock:
            count = len(self._results)
            self._results.clear()
            logging.debug(f"Cleared {count} stored results")
    
    def get_all_task_ids(self) -> list:
        """Get all stored task IDs."""
        with self._lock:
            return list(self._results.keys())
