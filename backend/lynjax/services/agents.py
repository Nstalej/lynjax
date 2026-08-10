"""Remote agent registry.

The Windows AD collector itself is not ported yet. This is the registry it will
register against: an operator needs to see whether an agent is alive before the
agent exists to be looked at, and a screen that can only ever say "no agents"
because nothing can register is worse than no screen.

Liveness is derived from the last heartbeat rather than stored as a flag. A
stored `status` column goes stale the moment a process dies without telling
anyone, which is exactly the case the screen exists to show.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from lynjax.core.database import Database

logger = logging.getLogger("lynjax.agents")

#: An agent that has not checked in for this long is treated as offline.
OFFLINE_AFTER = timedelta(minutes=5)


class AgentNotFoundError(RuntimeError):
    """No agent matches that identifier."""


@dataclass(frozen=True)
class Agent:
    id: int
    agent_id: str
    name: str
    host: str
    agent_type: str
    version: str | None
    last_heartbeat: str | None
    registered_at: str

    @property
    def status(self) -> str:
        """Derived, never stored: a dead process cannot update a flag."""
        if not self.last_heartbeat:
            return "unknown"

        try:
            seen = datetime.fromisoformat(self.last_heartbeat)
        except ValueError:
            return "unknown"

        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=UTC)

        return "online" if datetime.now(UTC) - seen < OFFLINE_AFTER else "offline"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "host": self.host,
            "agent_type": self.agent_type,
            "version": self.version,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Agent:
        return cls(
            id=int(row["id"]),
            agent_id=row["agent_id"],
            name=row["name"],
            host=row["host"],
            agent_type=row["agent_type"],
            version=row["version"],
            last_heartbeat=row["last_heartbeat"],
            registered_at=row["registered_at"],
        )


class AgentRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def register(
        self,
        *,
        agent_id: str,
        name: str,
        host: str,
        agent_type: str = "windows_ad",
        version: str | None = None,
    ) -> Agent:
        """Register or update an agent, and count it as a heartbeat."""
        now = datetime.now(UTC).isoformat()
        await self._db.execute(
            """
            INSERT INTO agents (agent_id, name, host, agent_type, version,
                                last_heartbeat)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                name = excluded.name,
                host = excluded.host,
                agent_type = excluded.agent_type,
                version = excluded.version,
                last_heartbeat = excluded.last_heartbeat
            """,
            (agent_id, name, host, agent_type, version, now),
        )
        logger.info("Agent %s registered from %s", agent_id, host)
        return await self.get(agent_id)

    async def heartbeat(self, agent_id: str) -> Agent:
        agent = await self.get(agent_id)
        await self._db.execute(
            "UPDATE agents SET last_heartbeat = ? WHERE agent_id = ?",
            (datetime.now(UTC).isoformat(), agent.agent_id),
        )
        return await self.get(agent_id)

    async def get(self, agent_id: str) -> Agent:
        row = await self._db.fetch_one(
            "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
        )
        if row is None:
            raise AgentNotFoundError(f"No agent {agent_id!r}")
        return Agent.from_row(row)

    async def list(self) -> list[Agent]:
        rows = await self._db.fetch_all("SELECT * FROM agents ORDER BY name")
        return [Agent.from_row(row) for row in rows]

    async def delete(self, agent_id: str) -> None:
        await self.get(agent_id)
        await self._db.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
        logger.info("Agent %s removed", agent_id)

    async def purge_all(self) -> int:
        rows = await self._db.fetch_all("SELECT COUNT(*) AS n FROM agents")
        count = int(rows[0]["n"]) if rows else 0
        await self._db.execute("DELETE FROM agents")
        return count
