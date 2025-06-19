import logging
import multiprocessing as mp
import threading
import time
from multiprocessing.pool import AsyncResult, Pool
from typing import Dict, Any, Callable, Optional

from ...interfaces.mne_interfaces import MNEProcessManagerInterface

# Check if MNE is available
try:
    import mne

    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class MNEProcessManager(MNEProcessManagerInterface):
    """Manages multiprocessing operations for MNE tasks."""

    def __init__(self) -> None:
        """Initialize the process manager."""
        self._process_pool: Optional[Pool] = None
        self._active_tasks: Dict[str, AsyncResult[Any]] = {}
        self._task_lock = threading.RLock()

        logging.info("MNE process manager initialized")

    def start_service(self) -> None:
        """Start the process pool."""
        if not MNE_AVAILABLE:
            logging.warning("MNE not available, process manager not started")
            return

        if self._process_pool is None:
            # Create process pool with 2 workers for MNE operations
            self._process_pool = mp.Pool(processes=2, initializer=_mne_worker_init)
            logging.info("MNE process pool started with 2 workers")

    def stop_service(self) -> None:
        """Stop the process pool and cleanup."""
        with self._task_lock:
            if self._process_pool is not None:
                self._active_tasks.clear()

                # Terminate process pool
                self._process_pool.terminate()
                self._process_pool.join()
                self._process_pool = None

                logging.info("MNE process pool stopped")

    def submit_task(
        self,
        worker_func: Callable[..., Any],
        *args: Any,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Submit a task to the process pool with a specific task ID."""
        if not self.is_available():
            raise RuntimeError("Process manager not available")

        # Extract callback from kwargs
        callback = kwargs.pop("callback", None)

        # Use provided task_id or generate one
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}"

        with self._task_lock:
            # Ensure process pool is available
            if self._process_pool is None:
                raise RuntimeError("Process pool not initialized")

            # Submit task to process pool
            async_result = self._process_pool.apply_async(
                worker_func, args=args, kwds=kwargs, callback=callback
            )

            # Store task with the provided/generated ID
            self._active_tasks[task_id] = async_result

        logging.debug(f"Submitted task: {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task."""
        with self._task_lock:
            if task_id in self._active_tasks:
                async_result = self._active_tasks[task_id]
                is_ready = async_result.ready()
                return {
                    "status": "completed" if is_ready else "running",
                    "ready": is_ready,
                    "successful": async_result.successful() if is_ready else None,
                }
            else:
                return {"status": "not_found", "ready": False, "successful": False}

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        with self._task_lock:
            if task_id in self._active_tasks:
                try:
                    del self._active_tasks[task_id]
                    logging.info(f"Cancelled task: {task_id}")
                    return True
                except Exception as e:
                    logging.error(f"Error cancelling task {task_id}: {e}")
            return False

    def is_available(self) -> bool:
        """Check if the service is available."""
        return MNE_AVAILABLE and self._process_pool is not None

    def cleanup_completed_tasks(self) -> None:
        """Clean up completed tasks from memory."""
        with self._task_lock:
            completed_tasks = []
            for task_id, async_result in self._active_tasks.items():
                if async_result.ready():
                    completed_tasks.append(task_id)

            for task_id in completed_tasks:
                del self._active_tasks[task_id]

            if completed_tasks:
                logging.debug(f"Cleaned up {len(completed_tasks)} completed tasks")


def _mne_worker_init() -> None:
    """Initialize MNE worker process."""
    import signal

    signal.signal(signal.SIGINT, signal.SIG_IGN)
