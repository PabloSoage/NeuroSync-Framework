"""EventBus and Subscription (phase F2)."""

from __future__ import annotations

import threading
import time

from neurosync.core.bus import EventBus, Policy


def test_publish_does_not_run_subscriber_and_assigns_order() -> None:
    bus: EventBus[str] = EventBus()
    sub = bus.subscribe("t", "a", maxsize=10, policy=Policy.DROP_OLDEST)
    s0 = bus.publish("t", "x")
    s1 = bus.publish("t", "y")
    assert s1 > s0
    got = sub.drain()
    assert [e.msg for e in got] == ["x", "y"]
    assert [e.seq for e in got] == [s0, s1]


def test_topics_are_separate() -> None:
    bus: EventBus[int] = EventBus()
    a = bus.subscribe("a", "x", maxsize=10, policy=Policy.DROP_OLDEST)
    b = bus.subscribe("b", "x", maxsize=10, policy=Policy.DROP_OLDEST)
    bus.publish("a", 1)
    assert [e.msg for e in a.drain()] == [1]
    assert b.drain() == []


def test_drop_oldest_counts_drops() -> None:
    bus: EventBus[int] = EventBus()
    sub = bus.subscribe("t", "slow", maxsize=3, policy=Policy.DROP_OLDEST)
    for i in range(10):
        bus.publish("t", i)
    assert [e.msg for e in sub.drain()] == [7, 8, 9]
    assert sub.stats.dropped == 7
    assert sub.stats.max_depth == 3


def test_drop_newest_counts_drops() -> None:
    bus: EventBus[int] = EventBus()
    sub = bus.subscribe("t", "slow", maxsize=3, policy=Policy.DROP_NEWEST)
    for i in range(10):
        bus.publish("t", i)
    assert [e.msg for e in sub.drain()] == [0, 1, 2]
    assert sub.stats.dropped == 7


def test_slow_subscriber_does_not_affect_another() -> None:
    bus: EventBus[int] = EventBus()
    slow = bus.subscribe("t", "slow", maxsize=2, policy=Policy.DROP_OLDEST)
    fast = bus.subscribe("t", "fast", maxsize=1000, policy=Policy.DROP_OLDEST)
    for i in range(100):
        bus.publish("t", i)
    assert len(fast.drain(max_n=1000)) == 100
    assert slow.stats.dropped == 98


def test_block_waits_for_room() -> None:
    bus: EventBus[int] = EventBus()
    sub = bus.subscribe("t", "rec", maxsize=1, policy=Policy.BLOCK, block_timeout_s=2.0)
    bus.publish("t", 0)

    def consumer() -> None:
        time.sleep(0.05)
        sub.drain()

    t = threading.Thread(target=consumer)
    t.start()
    bus.publish("t", 1)  # waits until the consumer takes the 0
    t.join()
    assert [e.msg for e in sub.drain()] == [1]
    assert sub.stats.dropped == 0


def test_block_timeout_drops_and_counts() -> None:
    bus: EventBus[int] = EventBus()
    sub = bus.subscribe("t", "rec", maxsize=1, policy=Policy.BLOCK, block_timeout_s=0.01)
    bus.publish("t", 0)
    bus.publish("t", 1)
    assert sub.stats.dropped == 1
    assert sub.stats.timed_out == 1


def test_drain_waits_when_asked() -> None:
    bus: EventBus[int] = EventBus()
    sub = bus.subscribe("t", "a", maxsize=10, policy=Policy.DROP_OLDEST)
    threading.Timer(0.05, lambda: bus.publish("t", 5)).start()
    got = sub.drain(timeout_s=2.0)
    assert [e.msg for e in got] == [5]


def test_close_unsubscribes_and_counts_pending() -> None:
    bus: EventBus[int] = EventBus()
    sub = bus.subscribe("t", "a", maxsize=10, policy=Policy.DROP_OLDEST)
    bus.publish("t", 1)
    sub.close()
    assert sub.stats.dropped == 1
    bus.publish("t", 2)
    assert "t/a" not in bus.stats()
