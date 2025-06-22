"""
WebSocket worker pool for high-performance message processing.
"""

import asyncio
import logging
import multiprocessing
import queue
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class WorkerStats:
    """Statistics for a worker."""

    messages_processed: int = 0
    total_processing_time: float = 0.0
    last_activity: float = 0.0
    queue_size: int = 0

    @property
    def avg_processing_time(self) -> float:
        """Calculate the average processing time per message."""
        return self.total_processing_time / max(1, self.messages_processed)


class WebSocketWorkerPool:
    """Pool of workers for processing WebSocket messages."""

    def __init__(self, pool_size: Optional[int] = None):
        if pool_size is None:
            pool_size = min(8, max(2, multiprocessing.cpu_count() - 1))

        self.pool_size = pool_size
        self.workers: List[asyncio.Task] = []
        self.worker_queues: List[queue.Queue] = []
        self.worker_stats: List[WorkerStats] = []
        self.shutdown_event = asyncio.Event()
        self.round_robin_index = 0
        self.load_balancer_lock = asyncio.Lock()

        print(f"Initializing WebSocket worker pool with {pool_size} workers")

        for i in range(pool_size):
            self.worker_queues.append(queue.Queue(maxsize=5000))
            self.worker_stats.append(WorkerStats())

    async def start_workers(self, module_id: str, connections: List[Any]) -> None:
        """Start all worker tasks."""
        for i in range(self.pool_size):
            worker_task = asyncio.create_task(
                self._worker_loop(i, module_id, connections)
            )
            self.workers.append(worker_task)

    async def stop_workers(self) -> None:
        """Stop all workers."""
        self.shutdown_event.set()

        for worker in self.workers:
            worker.cancel()

        try:
            await asyncio.gather(*self.workers, return_exceptions=True)
        except Exception as e:
            logging.error(f"Error stopping workers: {e}")

        self.workers.clear()

    def distribute_message(self, message: str) -> bool:
        """Distribute message to the least loaded worker."""
        try:
            best_worker_idx = 0
            min_queue_size = self.worker_queues[0].qsize()

            for i in range(1, self.pool_size):
                queue_size = self.worker_queues[i].qsize()
                if queue_size < min_queue_size:
                    min_queue_size = queue_size
                    best_worker_idx = i

            self.worker_queues[best_worker_idx].put_nowait(message)
            self.worker_stats[best_worker_idx].queue_size = self.worker_queues[
                best_worker_idx
            ].qsize()
            return True

        except queue.Full:
            for i in range(self.pool_size):
                worker_idx = (self.round_robin_index + i) % self.pool_size
                try:
                    worker_queue = self.worker_queues[worker_idx]
                    if worker_queue.full():
                        for _ in range(min(10, worker_queue.qsize())):
                            try:
                                worker_queue.get_nowait()
                            except queue.Empty:
                                break

                    worker_queue.put_nowait(message)
                    self.worker_stats[worker_idx].queue_size = worker_queue.qsize()
                    self.round_robin_index = (worker_idx + 1) % self.pool_size
                    return True
                except queue.Full:
                    continue

            return False

    async def _worker_loop(
        self, worker_id: int, module_id: str, connections: List[Any]
    ) -> None:
        """Main loop for a worker."""
        worker_queue = self.worker_queues[worker_id]
        worker_stats = self.worker_stats[worker_id]

        print(f"Worker {worker_id} started for module {module_id}")

        while not self.shutdown_event.is_set():
            try:
                messages_to_send = []
                start_time = time.time()

                batch_size = 50
                for _ in range(batch_size):
                    try:
                        message = worker_queue.get_nowait()
                        messages_to_send.append(message)
                    except queue.Empty:
                        break

                if messages_to_send:
                    await self._send_batch_to_connections(
                        worker_id, messages_to_send, connections
                    )

                    processing_time = time.time() - start_time
                    worker_stats.messages_processed += len(messages_to_send)
                    worker_stats.total_processing_time += processing_time
                    worker_stats.last_activity = time.time()
                    worker_stats.queue_size = worker_queue.qsize()
                else:
                    await asyncio.sleep(0.001)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in worker {worker_id}: {e}")
                await asyncio.sleep(0.01)

        print(f"Worker {worker_id} stopped")

    async def _send_batch_to_connections(
        self, worker_id: int, messages: List[str], connections: List[Any]
    ) -> None:
        """Send a batch of messages to all connections."""
        if not connections:
            return

        current_connections = connections[:]
        dead_connections = []

        for connection in current_connections:
            try:
                for message in messages:
                    await connection.send_text(message)
            except Exception as e:
                logging.error(f"Worker {worker_id}: Error sending to WebSocket: {e}")
                dead_connections.append(connection)

        for dead_conn in dead_connections:
            if dead_conn in connections:
                connections.remove(dead_conn)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all workers."""
        workers_list: List[Dict[str, Any]] = []
        stats = {"pool_size": self.pool_size, "workers": workers_list}

        total_processed = 0
        total_queue_size = 0

        for i, worker_stats in enumerate(self.worker_stats):
            worker_data = {
                "worker_id": i,
                "messages_processed": worker_stats.messages_processed,
                "avg_processing_time_ms": worker_stats.avg_processing_time * 1000,
                "queue_size": worker_stats.queue_size,
                "last_activity": worker_stats.last_activity,
            }
            workers_list.append(worker_data)
            total_processed += worker_stats.messages_processed
            total_queue_size += worker_stats.queue_size

        stats["total_messages_processed"] = total_processed
        stats["total_queue_size"] = total_queue_size
        stats["avg_queue_size"] = (
            total_queue_size / self.pool_size if self.pool_size > 0 else 0
        )

        return stats
