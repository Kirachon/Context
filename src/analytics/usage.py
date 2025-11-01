"""
Usage Analytics (Story 5-3)

Counts events for insights and reporting.
"""

from typing import Dict
from collections import defaultdict


class UsageAnalytics:
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)

    def incr(self, key: str, count: int = 1):
        self._counters[key] += count

    def get(self, key: str) -> int:
        return self._counters.get(key, 0)

    def all(self) -> Dict[str, int]:
        return dict(self._counters)

    def reset(self):
        self._counters.clear()


_usage: UsageAnalytics = UsageAnalytics()


def usage() -> UsageAnalytics:
    return _usage

