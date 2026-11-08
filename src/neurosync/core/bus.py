"""Event bus with one bounded queue per subscriber.

Replaces the two dispatchers of the original code: the ``eeg_processor`` one
started a new thread per subscriber and event (``EEG-17``, ``CON-04`` in the
analysis) and the ``input_collector`` one ran subscribers inside the producer
thread (``INP-04``).

Rules:

- :meth:`EventBus.publish` **never runs subscriber code**: it only enqueues.
  Each subscriber drains its own queue from its own thread with
  :meth:`Subscription.drain`.
- Every queue has a maximum size and a policy. Nothing is dropped silently:
  drops are counted in :class:`SubStats`.
- ``Policy.BLOCK`` is only for consumers that cannot lose anything (the
  recorder). Even then the publisher waits at most ``block_timeout_s``; if it
  runs out, the message is counted as dropped and as ``timed_out``.
- The bus assigns a global, increasing ``seq`` to every publication: a total
  order across sources.
"""

from __future__ import annotations

import itertools
import threading
from collections import deque
from dataclasses import dataclass
from enum import Enum


class Policy(Enum):
    """What to do when a subscriber queue is full."""

    #: Wait up to ``block_timeout_s``; if it runs out, drop and count it.
    BLOCK = "block"
    #: Drop the oldest queued item (the usual choice for plotting).
    DROP_OLDEST = "drop_oldest"
    #: Drop the new item.
    DROP_NEWEST = "drop_newest"


@dataclass(slots=True)
class SubStats:
    """Counters of one subscriber."""

    delivered: int = 0
    dropped: int = 0
    timed_out: int = 0
    max_depth: int = 0


@dataclass(frozen=True, slots=True)
class Envelope[T]:
    """What a subscriber receives: the message with its global order."""

    seq: int
    topic: str
    msg: T


class Subscription[T]:
    """Bounded queue of one subscriber. Created by :meth:`EventBus.subscribe`."""

    def __init__(
        self,
        bus: EventBus[T],
        topic: str,
        name: str,
        maxsize: int,
        policy: Policy,
        block_timeout_s: float,
    ) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._bus = bus
        self.topic = topic
        self.name = name
        self.maxsize = maxsize
        self.policy = policy
        self.block_timeout_s = block_timeout_s
        self.stats = SubStats()
        self._q: deque[Envelope[T]] = deque()
        self._cond = threading.Condition(threading.Lock())
        self._closed = False

    def _offer(self, env: Envelope[T]) -> None:
        with self._cond:
            if self._closed:
                return
            if len(self._q) >= self.maxsize:
                if self.policy is Policy.DROP_NEWEST:
                    self.stats.dropped += 1
                    return
                if self.policy is Policy.DROP_OLDEST:
                    self._q.popleft()
                    self.stats.dropped += 1
                else:  # BLOCK
                    ok = self._cond.wait_for(
                        lambda: len(self._q) < self.maxsize or self._closed,
                        timeout=self.block_timeout_s,
                    )
                    if not ok or self._closed:
                        self.stats.dropped += 1
                        self.stats.timed_out += 1
                        return
            self._q.append(env)
            self.stats.delivered += 1
            self.stats.max_depth = max(self.stats.max_depth, len(self._q))
            self._cond.notify_all()

    def drain(self, max_n: int = 4096, timeout_s: float | None = None) -> list[Envelope[T]]:
        """Take up to ``max_n`` items; wait up to ``timeout_s`` if empty.

        With ``timeout_s=None`` it does not wait.
        """
        with self._cond:
            if not self._q and timeout_s is not None and not self._closed:
                self._cond.wait_for(lambda: bool(self._q) or self._closed, timeout=timeout_s)
            out: list[Envelope[T]] = []
            while self._q and len(out) < max_n:
                out.append(self._q.popleft())
            if out:
                self._cond.notify_all()  # wake a publisher waiting in BLOCK
            return out

    def depth(self) -> int:
        """Items queued right now."""
        with self._cond:
            return len(self._q)

    def close(self) -> None:
        """Unsubscribe. Whatever is still queued is lost (and counted)."""
        with self._cond:
            if self._closed:
                return
            self._closed = True
            self.stats.dropped += len(self._q)
            self._q.clear()
            self._cond.notify_all()
        self._bus._remove(self)


class EventBus[T]:
    """In-process pub/sub bus, by topic."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Subscription[T]]] = {}
        self._lock = threading.Lock()
        self._seq = itertools.count()

    def subscribe(
        self,
        topic: str,
        name: str,
        *,
        maxsize: int,
        policy: Policy,
        block_timeout_s: float = 0.5,
    ) -> Subscription[T]:
        """Create a subscription to ``topic``."""
        sub = Subscription(self, topic, name, maxsize, policy, block_timeout_s)
        with self._lock:
            self._subs.setdefault(topic, []).append(sub)
        return sub

    def publish(self, topic: str, msg: T) -> int:
        """Enqueue ``msg`` for every subscriber of ``topic``. Returns its ``seq``."""
        with self._lock:
            seq = next(self._seq)
            subs = list(self._subs.get(topic, ()))
        env = Envelope(seq, topic, msg)
        for sub in subs:
            sub._offer(env)
        return seq

    def stats(self) -> dict[str, SubStats]:
        """Counters per subscriber, keyed ``"topic/name"``."""
        with self._lock:
            return {f"{s.topic}/{s.name}": s.stats for subs in self._subs.values() for s in subs}

    def _remove(self, sub: Subscription[T]) -> None:
        with self._lock:
            subs = self._subs.get(sub.topic)
            if subs and sub in subs:
                subs.remove(sub)
