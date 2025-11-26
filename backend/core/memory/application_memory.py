"""
AgentForge Studio - Application Memory.

This module implements permanent memory that learns from all projects.
Stored in SQLite database for persistence across server restarts.
"""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.models.memory import BestPractice, MistakeRecord, Pattern


class ApplicationMemory:
    """
    Permanent memory that learns from all projects.
    Stored in SQLite database for persistence.

    This class provides long-term storage for patterns, best practices,
    and mistakes learned from past projects to improve future work.

    Attributes:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str = "./data/app_memory.db") -> None:
        """
        Initialize application memory.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._initialized = False

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

            # Patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    code_example TEXT,
                    category TEXT,
                    times_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Best practices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS best_practices (
                    id TEXT PRIMARY KEY,
                    practice TEXT NOT NULL,
                    context TEXT,
                    learned_from TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Mistakes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mistakes (
                    id TEXT PRIMARY KEY,
                    mistake TEXT NOT NULL,
                    consequence TEXT,
                    how_to_avoid TEXT,
                    agent TEXT,
                    occurrences INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Feedback learnings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback_learnings (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    feedback TEXT,
                    rating INTEGER,
                    extracted_learning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_category
                ON patterns(category)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mistakes_agent
                ON mistakes(agent)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_best_practices_context
                ON best_practices(context)
            """)

        self._initialized = True

    # Pattern methods

    async def store_pattern(
        self,
        name: str,
        description: str,
        code_example: str,
        category: str,
    ) -> str:
        """
        Store a successful pattern.

        Args:
            name: Pattern name.
            description: Pattern description.
            code_example: Example code for the pattern.
            category: Pattern category.

        Returns:
            ID of the stored pattern.
        """
        pattern_id = str(uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO patterns (id, name, description, code_example, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pattern_id, name, description, code_example, category),
            )
        return pattern_id

    async def get_patterns(self, category: str | None = None) -> list[Pattern]:
        """
        Get stored patterns.

        Args:
            category: Optional category to filter by.

        Returns:
            List of patterns.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    """
                    SELECT * FROM patterns
                    WHERE category = ?
                    ORDER BY times_used DESC
                    """,
                    (category,),
                )
            else:
                cursor.execute(
                    "SELECT * FROM patterns ORDER BY times_used DESC"
                )
            rows = cursor.fetchall()

        return [
            Pattern(
                id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                code_example=row["code_example"] or "",
                category=row["category"] or "",
                times_used=row["times_used"],
                created_at=datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.utcnow(),
            )
            for row in rows
        ]

    async def search_patterns(self, query: str) -> list[Pattern]:
        """
        Search patterns by keyword.

        Args:
            query: Search query.

        Returns:
            List of matching patterns.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            search_term = f"%{query}%"
            cursor.execute(
                """
                SELECT * FROM patterns
                WHERE name LIKE ? OR description LIKE ? OR category LIKE ?
                ORDER BY times_used DESC
                """,
                (search_term, search_term, search_term),
            )
            rows = cursor.fetchall()

        return [
            Pattern(
                id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                code_example=row["code_example"] or "",
                category=row["category"] or "",
                times_used=row["times_used"],
                created_at=datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.utcnow(),
            )
            for row in rows
        ]

    async def increment_pattern_usage(self, pattern_id: str) -> bool:
        """
        Increment the usage count for a pattern.

        Args:
            pattern_id: ID of the pattern.

        Returns:
            True if pattern was found and updated.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE patterns SET times_used = times_used + 1 WHERE id = ?",
                (pattern_id,),
            )
            return cursor.rowcount > 0

    # Best practices methods

    async def store_best_practice(
        self, practice: str, context: str, learned_from: str
    ) -> str:
        """
        Store a best practice.

        Args:
            practice: The best practice.
            context: Context where it applies.
            learned_from: Source of the practice.

        Returns:
            ID of the stored best practice.
        """
        practice_id = str(uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO best_practices (id, practice, context, learned_from)
                VALUES (?, ?, ?, ?)
                """,
                (practice_id, practice, context, learned_from),
            )
        return practice_id

    async def get_best_practices(
        self, context: str | None = None
    ) -> list[BestPractice]:
        """
        Get best practices.

        Args:
            context: Optional context to filter by.

        Returns:
            List of best practices.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if context:
                cursor.execute(
                    """
                    SELECT * FROM best_practices
                    WHERE context LIKE ?
                    ORDER BY created_at DESC
                    """,
                    (f"%{context}%",),
                )
            else:
                cursor.execute(
                    "SELECT * FROM best_practices ORDER BY created_at DESC"
                )
            rows = cursor.fetchall()

        return [
            BestPractice(
                id=row["id"],
                practice=row["practice"],
                context=row["context"] or "",
                learned_from=row["learned_from"] or "manual",
                created_at=datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.utcnow(),
            )
            for row in rows
        ]

    # Mistakes methods

    async def store_mistake(
        self,
        mistake: str,
        consequence: str,
        how_to_avoid: str,
        agent: str,
    ) -> str:
        """
        Store a mistake to avoid.

        Args:
            mistake: Description of the mistake.
            consequence: What happens if the mistake is made.
            how_to_avoid: How to avoid the mistake.
            agent: Agent type this applies to.

        Returns:
            ID of the stored mistake.
        """
        mistake_id = str(uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if similar mistake exists
            cursor.execute(
                """
                SELECT id, occurrences FROM mistakes
                WHERE mistake = ? AND agent = ?
                """,
                (mistake, agent),
            )
            existing = cursor.fetchone()

            if existing:
                # Increment occurrences
                cursor.execute(
                    """
                    UPDATE mistakes SET occurrences = occurrences + 1
                    WHERE id = ?
                    """,
                    (existing["id"],),
                )
                return existing["id"]
            else:
                cursor.execute(
                    """
                    INSERT INTO mistakes
                    (id, mistake, consequence, how_to_avoid, agent)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (mistake_id, mistake, consequence, how_to_avoid, agent),
                )
                return mistake_id

    async def get_mistakes_for_agent(self, agent: str) -> list[MistakeRecord]:
        """
        Get mistakes relevant to an agent.

        Args:
            agent: Agent name to filter by.

        Returns:
            List of mistake records.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM mistakes
                WHERE agent = ? OR agent = ''
                ORDER BY occurrences DESC
                """,
                (agent,),
            )
            rows = cursor.fetchall()

        return [
            MistakeRecord(
                id=row["id"],
                mistake=row["mistake"],
                consequence=row["consequence"] or "",
                how_to_avoid=row["how_to_avoid"] or "",
                agent=row["agent"] or "",
                occurrences=row["occurrences"],
                created_at=datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.utcnow(),
            )
            for row in rows
        ]

    async def get_all_mistakes(self) -> list[MistakeRecord]:
        """
        Get all recorded mistakes.

        Returns:
            List of all mistake records.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM mistakes ORDER BY occurrences DESC"
            )
            rows = cursor.fetchall()

        return [
            MistakeRecord(
                id=row["id"],
                mistake=row["mistake"],
                consequence=row["consequence"] or "",
                how_to_avoid=row["how_to_avoid"] or "",
                agent=row["agent"] or "",
                occurrences=row["occurrences"],
                created_at=datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.utcnow(),
            )
            for row in rows
        ]

    # Learning methods

    async def learn_from_feedback(
        self, project_id: str, feedback: str, rating: int
    ) -> str:
        """
        Store feedback learning for future extraction.

        Args:
            project_id: Project the feedback is about.
            feedback: The feedback text.
            rating: Rating given (1-5).

        Returns:
            ID of the stored learning.
        """
        learning_id = str(uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO feedback_learnings
                (id, project_id, feedback, rating, extracted_learning)
                VALUES (?, ?, ?, ?, ?)
                """,
                (learning_id, project_id, feedback, rating, ""),
            )
        return learning_id

    async def update_extracted_learning(
        self, learning_id: str, extracted_learning: str
    ) -> bool:
        """
        Update the extracted learning from feedback.

        Args:
            learning_id: ID of the learning record.
            extracted_learning: The extracted learning text.

        Returns:
            True if learning was found and updated.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE feedback_learnings
                SET extracted_learning = ?
                WHERE id = ?
                """,
                (extracted_learning, learning_id),
            )
            return cursor.rowcount > 0

    async def get_learnings_for_task(self, task_type: str) -> dict[str, Any]:
        """
        Get relevant learnings for a specific task type.

        Args:
            task_type: Type of task (e.g., "html", "css", "review").

        Returns:
            Dictionary containing relevant patterns, practices, and mistakes.
        """
        patterns = await self.search_patterns(task_type)
        practices = await self.get_best_practices(context=task_type)

        # Get mistakes for common agent types based on task
        agent_mapping = {
            "html": "FrontendAgent",
            "css": "FrontendAgent",
            "js": "FrontendAgent",
            "javascript": "FrontendAgent",
            "review": "Reviewer",
            "test": "Tester",
            "plan": "Planner",
        }
        agent = agent_mapping.get(task_type.lower(), "")
        mistakes = await self.get_mistakes_for_agent(agent) if agent else []

        return {
            "task_type": task_type,
            "patterns": patterns[:5],  # Limit to top 5
            "best_practices": practices[:5],
            "mistakes_to_avoid": mistakes[:5],
        }

    async def close(self) -> None:
        """Close database connections (cleanup)."""
        # SQLite connections are managed per-operation, nothing to close
        pass
