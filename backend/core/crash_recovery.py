"""
AgentForge Studio - Crash Recovery.

This module implements crash recovery functionality using SQLite
to store checkpoints and recover from application crashes.
"""

import json
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any


class CrashRecovery:
    """
    Manages crash recovery through checkpoint-based persistence.

    Saves checkpoints after each stage completion and can restore
    project state after an application crash.

    Attributes:
        db_path: Path to the SQLite database file.
        logger: Logger instance.

    Example:
        >>> recovery = CrashRecovery()
        >>> await recovery.initialize()
        >>> await recovery.save_checkpoint("proj-1", "development", state_dict)
        >>> projects = await recovery.get_incomplete_projects()
    """

    def __init__(self, db_path: str = "./data/app_memory.db") -> None:
        """
        Initialize CrashRecovery.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._initialized = False
        self.logger = logging.getLogger("crash_recovery")

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get a database connection with context management.

        Yields:
            SQLite connection object.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    async def initialize(self) -> None:
        """Create database tables if not exist."""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Checkpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    project_id TEXT PRIMARY KEY,
                    stage TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Recovery history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recovery_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    recovered_from_stage TEXT NOT NULL,
                    recovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success INTEGER DEFAULT 1,
                    notes TEXT
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_stage
                ON checkpoints(stage)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_recovery_project
                ON recovery_history(project_id)
            """)

        self._initialized = True
        self.logger.info("CrashRecovery initialized")

    async def save_checkpoint(
        self,
        project_id: str,
        stage: str,
        state: dict[str, Any],
    ) -> None:
        """
        Save checkpoint for a project.

        Args:
            project_id: The project identifier.
            stage: Current stage of the project.
            state: Project state to save.
        """
        state_json = json.dumps(state, default=str)
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO checkpoints
                (project_id, stage, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    stage = excluded.stage,
                    state = excluded.state,
                    updated_at = excluded.updated_at
                """,
                (project_id, stage, state_json, now, now),
            )

        self.logger.debug(f"Saved checkpoint for project {project_id} at stage {stage}")

    async def get_incomplete_projects(self) -> list[dict[str, Any]]:
        """
        Get projects that didn't complete.

        Returns:
            List of incomplete project checkpoints.
        """
        terminal_stages = {"delivered", "failed", "cancelled"}

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT project_id, stage, state, created_at, updated_at
                FROM checkpoints
                """
            )
            rows = cursor.fetchall()

        incomplete = []
        for row in rows:
            if row["stage"].lower() not in terminal_stages:
                try:
                    state = json.loads(row["state"])
                except json.JSONDecodeError:
                    state = {}

                incomplete.append({
                    "project_id": row["project_id"],
                    "stage": row["stage"],
                    "state": state,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })

        self.logger.info(f"Found {len(incomplete)} incomplete projects")
        return incomplete

    async def restore_project(self, project_id: str) -> dict[str, Any] | None:
        """
        Restore project state from checkpoint.

        Args:
            project_id: The project identifier.

        Returns:
            Restored project state, or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT stage, state, created_at, updated_at
                FROM checkpoints WHERE project_id = ?
                """,
                (project_id,),
            )
            row = cursor.fetchone()

        if not row:
            self.logger.warning(f"No checkpoint found for project {project_id}")
            return None

        try:
            state = json.loads(row["state"])
        except json.JSONDecodeError:
            state = {}

        # Record recovery attempt
        await self._record_recovery(project_id, row["stage"], success=True)

        self.logger.info(
            f"Restored project {project_id} from stage {row['stage']}"
        )

        return {
            "project_id": project_id,
            "stage": row["stage"],
            "state": state,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "recovered": True,
        }

    async def mark_completed(self, project_id: str) -> None:
        """
        Mark a project as completed (remove checkpoint).

        Args:
            project_id: The project identifier.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM checkpoints WHERE project_id = ?",
                (project_id,),
            )

        self.logger.debug(f"Marked project {project_id} as completed")

    async def get_checkpoint(self, project_id: str) -> dict[str, Any] | None:
        """
        Get the current checkpoint for a project.

        Args:
            project_id: The project identifier.

        Returns:
            Checkpoint data or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT stage, state, created_at, updated_at
                FROM checkpoints WHERE project_id = ?
                """,
                (project_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        try:
            state = json.loads(row["state"])
        except json.JSONDecodeError:
            state = {}

        return {
            "project_id": project_id,
            "stage": row["stage"],
            "state": state,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def _record_recovery(
        self,
        project_id: str,
        stage: str,
        success: bool = True,
        notes: str | None = None,
    ) -> None:
        """
        Record a recovery attempt.

        Args:
            project_id: The project identifier.
            stage: Stage from which recovery was attempted.
            success: Whether recovery was successful.
            notes: Optional notes about the recovery.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO recovery_history
                (project_id, recovered_from_stage, success, notes)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, stage, 1 if success else 0, notes),
            )

    async def get_recovery_history(
        self, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get recovery history.

        Args:
            project_id: Optional project ID to filter by.

        Returns:
            List of recovery records.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if project_id:
                cursor.execute(
                    """
                    SELECT * FROM recovery_history
                    WHERE project_id = ?
                    ORDER BY recovered_at DESC
                    """,
                    (project_id,),
                )
            else:
                cursor.execute(
                    "SELECT * FROM recovery_history ORDER BY recovered_at DESC"
                )
            rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "recovered_from_stage": row["recovered_from_stage"],
                "recovered_at": row["recovered_at"],
                "success": bool(row["success"]),
                "notes": row["notes"],
            }
            for row in rows
        ]

    async def cleanup_old_checkpoints(self, days: int = 30) -> int:
        """
        Remove checkpoints older than specified days.

        Args:
            days: Number of days to keep checkpoints.

        Returns:
            Number of checkpoints removed.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM checkpoints
                WHERE datetime(updated_at) < datetime('now', ? || ' days')
                """,
                (f"-{days}",),
            )
            deleted = cursor.rowcount

        self.logger.info(f"Cleaned up {deleted} old checkpoints")
        return deleted

    async def get_stats(self) -> dict[str, Any]:
        """
        Get crash recovery statistics.

        Returns:
            Dictionary with recovery statistics.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count checkpoints
            cursor.execute("SELECT COUNT(*) as count FROM checkpoints")
            checkpoint_count = cursor.fetchone()["count"]

            # Count by stage
            cursor.execute(
                "SELECT stage, COUNT(*) as count FROM checkpoints GROUP BY stage"
            )
            by_stage = {row["stage"]: row["count"] for row in cursor.fetchall()}

            # Count recoveries
            cursor.execute("SELECT COUNT(*) as count FROM recovery_history")
            recovery_count = cursor.fetchone()["count"]

            # Count successful recoveries
            cursor.execute(
                "SELECT COUNT(*) as count FROM recovery_history WHERE success = 1"
            )
            successful_recoveries = cursor.fetchone()["count"]

        return {
            "total_checkpoints": checkpoint_count,
            "checkpoints_by_stage": by_stage,
            "total_recoveries": recovery_count,
            "successful_recoveries": successful_recoveries,
            "recovery_success_rate": (
                successful_recoveries / recovery_count if recovery_count > 0 else 1.0
            ),
        }

    async def close(self) -> None:
        """Close any open resources (cleanup)."""
        # SQLite connections are managed per-operation
        self.logger.debug("CrashRecovery closed")
