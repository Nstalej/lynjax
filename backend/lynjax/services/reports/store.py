"""In-memory store for rendered assessments.

Reports are held in the process rather than written to the database, which is an
honest trade for a field tool: they do not survive a restart, and the API says so.

Two properties matter and neither is decorative.

**Bounded.** Every audit used to be kept forever, so a long-running server grew
without limit.

**Purgeable.** `lynjax purge` clears the database, but these live in memory and
survived it, so a technician who ran it believing the client's data was gone
still had device names, addresses and findings sitting in the process.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

logger = logging.getLogger("lynjax.reports")

#: Enough to cover a day of work without letting the process grow unbounded.
DEFAULT_LIMIT = 20


class ReportStore:
    """Keeps the most recent assessments, oldest evicted first."""

    def __init__(self, limit: int = DEFAULT_LIMIT) -> None:
        self._limit = max(1, limit)
        self._items: OrderedDict[str, tuple[Any, str]] = OrderedDict()

    def add(self, assessment_id: str, assessment: Any, locale: str) -> None:
        self._items[assessment_id] = (assessment, locale)
        self._items.move_to_end(assessment_id)
        while len(self._items) > self._limit:
            evicted, _ = self._items.popitem(last=False)
            logger.info("Evicted report %s to stay within the limit", evicted)

    def get(self, assessment_id: str) -> tuple[Any, str] | None:
        return self._items.get(assessment_id)

    def purge(self) -> int:
        """Drop everything. Returns how many were held."""
        count = len(self._items)
        self._items.clear()
        if count:
            logger.warning("Purged %s held report(s)", count)
        return count

    def __len__(self) -> int:
        return len(self._items)
