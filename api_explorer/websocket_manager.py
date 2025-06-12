"""
WebSocket connection management with worker pools and message throttling.
"""

import time
import random
import logging
import asyncio
from typing import Dict, List, Any, Callable, Optional
from fastapi import WebSocket

from .worker_pool import WebSocketWorkerPool
from .serialization import FastJSONSerializer


class WebSocketManager:
    """Manages WebSocket connections with thread-safe message queuing and worker pools."""

    def __init__(self) -> None:
        self.connections: Dict[str, List[WebSocket]] = {}
        self.worker_pools: Dict[str, WebSocketWorkerPool] = {}
        self.shutdown_events: Dict[str, asyncio.Event] = {}

        self.json_serializer = FastJSONSerializer()
        self._setup_json_templates()

        self.stats_last_update = time.time()
        self.stats_update_interval = 30.0
        self._message_throttle: Dict[str, Dict[str, Any]] = {}

    def _setup_json_templates(self) -> None:
        """Setup precompiled JSON templates for common event types."""
        vis_template = {
            "event_type": "${event_type}",
            "timestamp": "${timestamp}",
            "visualization_data": {"list_view": "${list_view}"},
        }
        self.json_serializer.precompile_template("visualization", vis_template)

        simple_template = {
            "event_type": "${event_type}",
            "timestamp": "${timestamp}",
            "key": "${key}",
            "value": "${value}",
        }
        self.json_serializer.precompile_template("simple", simple_template)

    async def add_connection(self, module_id: str, websocket: WebSocket) -> None:
        """Add a WebSocket connection for a module."""
        if module_id not in self.connections:
            self.connections[module_id] = []
            self.shutdown_events[module_id] = asyncio.Event()

            pool_size = self._determine_pool_size(module_id)
            self.worker_pools[module_id] = WebSocketWorkerPool(pool_size)

            await self.worker_pools[module_id].start_workers(
                module_id, self.connections[module_id]
            )

        self.connections[module_id].append(websocket)

    async def remove_connection(self, module_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if module_id in self.connections:
            if websocket in self.connections[module_id]:
                self.connections[module_id].remove(websocket)

            if not self.connections[module_id]:
                if module_id in self.shutdown_events:
                    self.shutdown_events[module_id].set()

                if module_id in self.worker_pools:
                    await self.worker_pools[module_id].stop_workers()
                    del self.worker_pools[module_id]

                del self.connections[module_id]
                del self.shutdown_events[module_id]

    def _determine_pool_size(self, module_id: str) -> int:
        """Determine optimal pool size based on module characteristics."""
        high_freq_modules = ["eeg", "emg", "sensor_data", "biosignals"]
        if any(keyword in module_id.lower() for keyword in high_freq_modules):
            return 6

        medium_freq_modules = ["controller", "input", "audio"]
        if any(keyword in module_id.lower() for keyword in medium_freq_modules):
            return 4

        return 2

    def queue_message(self, module_id: str, message: str) -> bool:
        """Queue a message for sending via worker pool."""
        if module_id not in self.worker_pools:
            return False

        return self.worker_pools[module_id].distribute_message(message)

    def apply_throttling(self, module_id: str, event_data: Dict[str, Any]) -> bool:
        """Apply message throttling logic. Returns True if message should be sent."""
        current_time = time.time()
        if module_id not in self._message_throttle:
            self._message_throttle[module_id] = {
                "last_log_time": 0,
                "event_count": 0,
                "last_rate_time": current_time,
                "rate": 0,
                "message_batch": {},
                "last_send_time": 0,
                "high_frequency_mode": False,
                "drop_counter": 0,
                "last_important_event": 0,
            }

        throttle_data = self._message_throttle[module_id]
        throttle_data["event_count"] += 1

        # Calculate rate every 500ms
        if current_time - throttle_data["last_rate_time"] >= 0.5:
            elapsed = current_time - throttle_data["last_rate_time"]
            if elapsed > 0:
                throttle_data["rate"] = int(throttle_data["event_count"] / elapsed)
            throttle_data["event_count"] = 0
            throttle_data["last_rate_time"] = current_time

            if throttle_data["rate"] > 500:
                throttle_data["high_frequency_mode"] = True
            elif throttle_data["rate"] < 100:
                throttle_data["high_frequency_mode"] = False

            log_interval = 10.0 if throttle_data["high_frequency_mode"] else 5.0
            if current_time - throttle_data["last_log_time"] >= log_interval:
                mode_str = (
                    " (HIGH FREQ MODE)" if throttle_data["high_frequency_mode"] else ""
                )
                dropped_str = (
                    f", dropped: {throttle_data['drop_counter']}"
                    if throttle_data["drop_counter"] > 0
                    else ""
                )
                print(
                    f"Broadcasting events for module {module_id} (rate: ~{throttle_data['rate']}/sec{dropped_str}){mode_str}"
                )
                throttle_data["last_log_time"] = current_time
                throttle_data["drop_counter"] = 0

        # Apply high frequency filtering
        if throttle_data["high_frequency_mode"]:
            is_important = self._is_important_event(event_data)

            if not is_important:
                sample_rate = max(0.02, min(0.1, 50.0 / throttle_data["rate"]))

                if random.random() > sample_rate:
                    throttle_data["drop_counter"] += 1
                    return False
            else:
                throttle_data["last_important_event"] = current_time

        return True

    def _is_important_event(self, event_data: Dict[str, Any]) -> bool:
        """Determine if an event is important and should not be dropped."""
        event_type = event_data.get("event_type", event_data.get("type", ""))

        if any(
            keyword in event_type.lower()
            for keyword in [
                "connect",
                "disconnect",
                "error",
                "state_change",
                "start",
                "stop",
            ]
        ):
            return True

        if any(
            keyword in event_type.lower()
            for keyword in ["button_press", "button_release", "key_down", "key_up"]
        ):
            return True

        if "visualization_data" in event_data:
            return True

        return False

    def serialize_event(self, event_data: Dict[str, Any], module_id: str) -> str:
        """Serialize event data using appropriate strategy."""
        throttle_data = self._message_throttle.get(module_id, {})
        high_freq = throttle_data.get("high_frequency_mode", False)

        if high_freq:
            if "visualization_data" in event_data:
                return self.json_serializer.serialize_from_template(
                    "visualization", event_data
                )
            else:
                return self.json_serializer.serialize_from_template(
                    "simple", event_data
                )
        else:
            return self.json_serializer.serialize_event(event_data, compact=False)

    def get_module_stats(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific module's worker pool."""
        if module_id in self.worker_pools:
            return self.worker_pools[module_id].get_stats()
        return None

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all modules."""
        current_time = time.time()

        # Build modules stats dict to satisfy type checking
        modules: Dict[str, Any] = {}
        for module_id, worker_pool in self.worker_pools.items():
            modules[module_id] = worker_pool.get_stats()

        stats: Dict[str, Any] = {"timestamp": current_time, "modules": modules}

        if current_time - self.stats_last_update > self.stats_update_interval:
            self._log_performance_stats(stats)
            self.stats_last_update = current_time

        return stats

    def _log_performance_stats(self, stats: Dict[str, Any]) -> None:
        """Log performance statistics."""
        print("\n=== WebSocket Worker Pool Statistics ===")

        for module_id, module_stats in stats["modules"].items():
            total_processed = module_stats["total_messages_processed"]
            avg_queue_size = module_stats["avg_queue_size"]
            pool_size = module_stats["pool_size"]

            print(f"Module {module_id}:")
            print(f"  Pool size: {pool_size} workers")
            print(f"  Total processed: {total_processed}")
            print(f"  Avg queue size: {avg_queue_size:.1f}")

            for worker in module_stats["workers"]:
                worker_id = worker["worker_id"]
                processed = worker["messages_processed"]
                queue_size = worker["queue_size"]
                avg_time = worker["avg_processing_time_ms"]

                print(
                    f"    Worker {worker_id}: {processed} msgs, queue: {queue_size}, avg: {avg_time:.2f}ms"
                )

        print("=" * 45)
