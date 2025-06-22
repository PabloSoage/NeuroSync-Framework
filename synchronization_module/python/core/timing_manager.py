"""
Timing and synchronization precision management.
"""
import time
import threading
from typing import Dict, Any, Optional, Callable
import logging


class TimingManager:
    """Manages timing and synchronization precision."""
    
    def __init__(self):
        """Initialize timing manager."""
        self.precision_ms = 1.0  # Default 1ms precision
        self.sync_callbacks: Dict[str, Callable] = {}
        self.is_active = False
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
    def set_precision(self, precision_ms: float) -> None:
        """Set synchronization precision in milliseconds."""
        if precision_ms < 0.1:
            precision_ms = 0.1  # Minimum 0.1ms
        elif precision_ms > 1000.0:
            precision_ms = 1000.0  # Maximum 1s
            
        with self._lock:
            self.precision_ms = precision_ms
            logging.info(f"Synchronization precision set to {precision_ms}ms")
    
    def register_sync_callback(self, name: str, callback: Callable) -> None:
        """Register a synchronization callback."""
        with self._lock:
            self.sync_callbacks[name] = callback
            logging.info(f"Registered sync callback: {name}")
    
    def unregister_sync_callback(self, name: str) -> None:
        """Unregister a synchronization callback."""
        with self._lock:
            if name in self.sync_callbacks:
                del self.sync_callbacks[name]
                logging.info(f"Unregistered sync callback: {name}")
    
    def start_synchronization(self) -> bool:
        """Start synchronization timer."""
        if self.is_active:
            return True
            
        try:
            self.is_active = True
            self._stop_event.clear()
            self._timer_thread = threading.Thread(
                target=self._sync_loop,
                daemon=True
            )
            self._timer_thread.start()
            
            logging.info("Synchronization timer started")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start synchronization: {e}")
            self.is_active = False
            return False
    
    def stop_synchronization(self) -> bool:
        """Stop synchronization timer."""
        if not self.is_active:
            return True
            
        try:
            self.is_active = False
            self._stop_event.set()
            
            if self._timer_thread and self._timer_thread.is_alive():
                self._timer_thread.join(timeout=2.0)
            
            logging.info("Synchronization timer stopped")
            return True
            
        except Exception as e:
            logging.error(f"Failed to stop synchronization: {e}")
            return False
    
    def _sync_loop(self) -> None:
        """Main synchronization loop."""
        interval = self.precision_ms / 1000.0  # Convert to seconds
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            # Call all registered callbacks
            with self._lock:
                for name, callback in list(self.sync_callbacks.items()):
                    try:
                        callback(start_time)
                    except Exception as e:
                        logging.error(f"Error in sync callback {name}: {e}")
            
            # Calculate sleep time to maintain precision
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            
            if sleep_time > 0:
                self._stop_event.wait(sleep_time)
    
    def get_timestamp(self) -> float:
        """Get high-precision timestamp."""
        return time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Get timing manager status."""
        return {
            "active": self.is_active,
            "precision_ms": self.precision_ms,
            "callback_count": len(self.sync_callbacks),
            "thread_alive": self._timer_thread.is_alive() if self._timer_thread else False
        }