"""Audit history.

Rendered assessments used to live only in the running process, capped at twenty
and erased by a restart, so the Audits screen had nothing to list and "View
Report" could only show what happened to still be in memory.

Storing the findings with the run matters more than it looks: re-deriving a past
report would mean collecting from the client's network again, which changes the
answer and touches equipment for the sake of redrawing history.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from lynjax.core.database import Database

logger = logging.getLogger("lynjax.audits")

AuditType = Literal["network", "device", "ad", "trace"]
Verdict = Literal["pass", "warning", "fail"]


class AuditNotFoundError(RuntimeError):
    """No stored audit matches."""


@dataclass(frozen=True)
class AuditRecord:
    """One stored audit run, as the history list shows it."""

    id: int
    assessment_id: str
    client: str | None
    target: str
    audit_type: str
    device_id: int | None
    status: str
    verdict: str
    checks_total: int
    issues_total: int
    summary: str | None
    locale: str
    started_at: str
    completed_at: str | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> AuditRecord:
        return cls(
            id=int(row["id"]),
            assessment_id=row["assessment_id"],
            client=row["client"],
            target=row["target"],
            audit_type=row["audit_type"],
            device_id=row["device_id"],
            status=row["status"],
            verdict=row["verdict"],
            checks_total=int(row["checks_total"]),
            issues_total=int(row["issues_total"]),
            summary=row["summary"],
            locale=row["locale"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "client": self.client,
            "target": self.target,
            "audit_type": self.audit_type,
            "device_id": self.device_id,
            "status": self.status,
            "verdict": self.verdict,
            "checks_total": self.checks_total,
            "issues_total": self.issues_total,
            "summary": self.summary,
            "locale": self.locale,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class AuditRepository:
    """Reads and writes audit history."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def save(
        self,
        *,
        assessment_id: str,
        payload: dict[str, Any],
        target: str = "Global Network",
        audit_type: AuditType = "network",
        device_id: int | None = None,
        client: str | None = None,
        verdict: Verdict = "pass",
        checks_total: int = 0,
        issues_total: int = 0,
        summary: str | None = None,
        locale: str = "es",
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> AuditRecord:
        """Store a run. Re-running the same assessment id replaces it."""
        await self._db.execute(
            """
            INSERT INTO audits
                (assessment_id, client, target, audit_type, device_id, status,
                 verdict, checks_total, issues_total, summary, payload_json,
                 locale, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(assessment_id) DO UPDATE SET
                verdict = excluded.verdict,
                checks_total = excluded.checks_total,
                issues_total = excluded.issues_total,
                summary = excluded.summary,
                payload_json = excluded.payload_json,
                completed_at = excluded.completed_at
            """,
            (
                assessment_id,
                client,
                target,
                audit_type,
                device_id,
                "success",
                verdict,
                checks_total,
                issues_total,
                summary,
                json.dumps(payload, ensure_ascii=False, default=str),
                locale,
                (started_at or datetime.now()).isoformat(),
                completed_at.isoformat() if completed_at else None,
            ),
        )
        logger.info(
            "Stored audit %s (%s, %s issue(s))", assessment_id, verdict, issues_total
        )
        return await self.get_by_assessment(assessment_id)

    async def list(
        self,
        *,
        audit_type: str | None = None,
        verdict: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Most recent first, which is the order the history screen wants."""
        query = "SELECT * FROM audits"
        clauses: list[str] = []
        params: list[Any] = []

        if audit_type:
            clauses.append("audit_type = ?")
            params.append(audit_type)
        if verdict:
            clauses.append("verdict = ?")
            params.append(verdict)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))

        rows = await self._db.fetch_all(query, tuple(params))
        return [AuditRecord.from_row(row) for row in rows]

    async def get(self, audit_id: int) -> tuple[AuditRecord, dict[str, Any]]:
        row = await self._db.fetch_one("SELECT * FROM audits WHERE id = ?", (audit_id,))
        if row is None:
            raise AuditNotFoundError(f"No audit with id {audit_id}")
        return AuditRecord.from_row(row), json.loads(row["payload_json"])

    async def get_by_assessment(self, assessment_id: str) -> AuditRecord:
        row = await self._db.fetch_one(
            "SELECT * FROM audits WHERE assessment_id = ?", (assessment_id,)
        )
        if row is None:
            raise AuditNotFoundError(f"No audit {assessment_id!r}")
        return AuditRecord.from_row(row)

    async def payload(self, assessment_id: str) -> dict[str, Any]:
        row = await self._db.fetch_one(
            "SELECT payload_json FROM audits WHERE assessment_id = ?", (assessment_id,)
        )
        if row is None:
            raise AuditNotFoundError(f"No audit {assessment_id!r}")
        return json.loads(row["payload_json"])

    async def recent_activity(self, limit: int = 10) -> list[dict[str, Any]]:
        """Compact rows for the dashboard's activity trail."""
        rows = await self._db.fetch_all(
            "SELECT assessment_id, target, audit_type, verdict, issues_total, "
            "started_at FROM audits ORDER BY started_at DESC LIMIT ?",
            (max(1, limit),),
        )
        return [dict(row) for row in rows]

    async def counts_by_verdict(self) -> dict[str, int]:
        rows = await self._db.fetch_all(
            "SELECT verdict, COUNT(*) AS n FROM audits GROUP BY verdict"
        )
        return {row["verdict"]: int(row["n"]) for row in rows}

    async def purge_all(self) -> int:
        rows = await self._db.fetch_all("SELECT COUNT(*) AS n FROM audits")
        count = int(rows[0]["n"]) if rows else 0
        await self._db.execute("DELETE FROM audits")
        if count:
            logger.warning("Purged %s stored audit(s)", count)
        return count
