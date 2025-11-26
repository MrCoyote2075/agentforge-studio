"""
AgentForge Studio - File Lock Manager.

This module implements a file locking mechanism to prevent conflicts
when multiple agents work simultaneously on the same files.
"""

import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class FileLock:
    """
    Represents a lock on a file.

    Attributes:
        path: Path to the locked file.
        owner: Name of the agent holding the lock.
        acquired_at: When the lock was acquired.
        timeout: Lock timeout in seconds.
        metadata: Optional additional lock metadata.
    """

    path: str
    owner: str
    acquired_at: datetime
    timeout: float
    metadata: dict[str, Any] | None = None

    @property
    def is_expired(self) -> bool:
        """Check if the lock has expired."""
        elapsed = (datetime.utcnow() - self.acquired_at).total_seconds()
        return elapsed > self.timeout


class FileLockManager:
    """
    File lock manager for preventing conflicts.

    This class provides a mechanism to acquire and release locks on files,
    preventing multiple agents from modifying the same file simultaneously.
    It supports:
    - Lock acquisition with timeout
    - Automatic lock expiration
    - Lock owner tracking
    - Deadlock prevention through timeouts

    Example:
        >>> lock_manager = FileLockManager()
        >>> await lock_manager.acquire("index.html", "frontend_agent")
        >>> # ... write to file ...
        >>> await lock_manager.release("index.html", "frontend_agent")
    """

    def __init__(self, default_timeout: float = 60.0) -> None:
        """
        Initialize the file lock manager.

        Args:
            default_timeout: Default lock timeout in seconds.
        """
        self._locks: dict[str, FileLock] = {}
        self._default_timeout = default_timeout
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()
        self._waiting: dict[str, list[asyncio.Event]] = {}
        self.logger = logging.getLogger("file_lock_manager")

    async def acquire(
        self,
        path: str,
        owner: str,
        timeout: float | None = None,
        wait: bool = True,
        wait_timeout: float = 30.0,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Acquire a lock on a file.

        Args:
            path: Path to the file to lock.
            owner: Name of the agent acquiring the lock.
            timeout: Lock timeout in seconds (uses default if not specified).
            wait: Whether to wait if file is already locked.
            wait_timeout: Maximum time to wait for the lock in seconds.
            metadata: Optional metadata to store with the lock.

        Returns:
            bool: True if lock was acquired, False otherwise.

        Raises:
            TimeoutError: If wait_timeout is exceeded while waiting.
        """
        lock_timeout = timeout if timeout is not None else self._default_timeout
        start_time = datetime.utcnow()

        while True:
            async with self._async_lock:
                # Clean up expired locks first
                self._cleanup_expired_locks()

                # Check if lock is available
                existing_lock = self._locks.get(path)

                if existing_lock is None or existing_lock.is_expired:
                    # Acquire the lock
                    self._locks[path] = FileLock(
                        path=path,
                        owner=owner,
                        acquired_at=datetime.utcnow(),
                        timeout=lock_timeout,
                        metadata=metadata,
                    )
                    self.logger.info(
                        f"Lock acquired on '{path}' by '{owner}' "
                        f"(timeout: {lock_timeout}s)"
                    )
                    return True

                if existing_lock.owner == owner:
                    # Same owner can re-acquire (refresh the lock)
                    existing_lock.acquired_at = datetime.utcnow()
                    existing_lock.timeout = lock_timeout
                    self.logger.debug(f"Lock refreshed on '{path}' by '{owner}'")
                    return True

                if not wait:
                    self.logger.debug(
                        f"Lock on '{path}' held by '{existing_lock.owner}', "
                        f"not waiting"
                    )
                    return False

            # Check wait timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= wait_timeout:
                self.logger.warning(
                    f"Timeout waiting for lock on '{path}' by '{owner}'"
                )
                return False

            # Wait a bit and retry
            await asyncio.sleep(0.1)

    async def release(self, path: str, owner: str) -> bool:
        """
        Release a lock on a file.

        Args:
            path: Path to the file to unlock.
            owner: Name of the agent releasing the lock.

        Returns:
            bool: True if lock was released, False if not found or wrong owner.
        """
        async with self._async_lock:
            lock = self._locks.get(path)

            if lock is None:
                self.logger.debug(f"No lock found on '{path}' to release")
                return False

            if lock.owner != owner and not lock.is_expired:
                self.logger.warning(
                    f"Cannot release lock on '{path}': owned by '{lock.owner}', "
                    f"not '{owner}'"
                )
                return False

            del self._locks[path]
            self.logger.info(f"Lock released on '{path}' by '{owner}'")

            # Notify waiting tasks
            if path in self._waiting:
                for event in self._waiting[path]:
                    event.set()
                del self._waiting[path]

            return True

    async def is_locked(self, path: str) -> bool:
        """
        Check if a file is locked.

        Args:
            path: Path to the file.

        Returns:
            bool: True if file is locked, False otherwise.
        """
        async with self._async_lock:
            lock = self._locks.get(path)
            return lock is not None and not lock.is_expired

    async def get_lock_owner(self, path: str) -> str | None:
        """
        Get the owner of a file lock.

        Args:
            path: Path to the file.

        Returns:
            str: Owner name or None if not locked.
        """
        async with self._async_lock:
            lock = self._locks.get(path)
            if lock and not lock.is_expired:
                return lock.owner
            return None

    async def get_lock_info(self, path: str) -> FileLock | None:
        """
        Get full lock information for a file.

        Args:
            path: Path to the file.

        Returns:
            FileLock: Lock information or None if not locked.
        """
        async with self._async_lock:
            lock = self._locks.get(path)
            if lock and not lock.is_expired:
                return lock
            return None

    async def get_agent_locks(self, owner: str) -> list[FileLock]:
        """
        Get all locks held by an agent.

        Args:
            owner: Agent name.

        Returns:
            List of locks held by the agent.
        """
        async with self._async_lock:
            self._cleanup_expired_locks()
            return [lock for lock in self._locks.values() if lock.owner == owner]

    async def release_all(self, owner: str) -> int:
        """
        Release all locks held by an agent.

        Args:
            owner: Agent name.

        Returns:
            int: Number of locks released.
        """
        async with self._async_lock:
            to_release = [
                path for path, lock in self._locks.items()
                if lock.owner == owner
            ]

            count = 0
            for path in to_release:
                del self._locks[path]
                count += 1
                self.logger.info(f"Force released lock on '{path}' for '{owner}'")

            return count

    async def extend_lock(
        self,
        path: str,
        owner: str,
        additional_time: float,
    ) -> bool:
        """
        Extend the timeout of an existing lock.

        Args:
            path: Path to the file.
            owner: Agent name (must be the lock owner).
            additional_time: Time in seconds to add to the lock timeout.

        Returns:
            bool: True if lock was extended, False otherwise.
        """
        async with self._async_lock:
            lock = self._locks.get(path)

            if lock is None:
                return False

            if lock.owner != owner:
                return False

            if lock.is_expired:
                return False

            lock.timeout += additional_time
            self.logger.debug(
                f"Extended lock on '{path}' by {additional_time}s"
            )
            return True

    async def get_all_locks(self) -> list[FileLock]:
        """
        Get all active locks.

        Returns:
            List of all active locks.
        """
        async with self._async_lock:
            self._cleanup_expired_locks()
            return list(self._locks.values())

    async def get_lock_count(self) -> int:
        """
        Get the number of active locks.

        Returns:
            int: Number of active locks.
        """
        async with self._async_lock:
            self._cleanup_expired_locks()
            return len(self._locks)

    async def clear_all(self) -> None:
        """Clear all locks (use with caution)."""
        async with self._async_lock:
            self._locks.clear()
            self._waiting.clear()
            self.logger.info("All locks cleared")

    def _cleanup_expired_locks(self) -> int:
        """
        Clean up expired locks.

        Returns:
            int: Number of locks cleaned up.
        """
        expired = [
            path for path, lock in self._locks.items()
            if lock.is_expired
        ]

        for path in expired:
            del self._locks[path]
            self.logger.debug(f"Expired lock on '{path}' cleaned up")

        return len(expired)


class FileLockContext:
    """
    Context manager for file locks.

    Provides a convenient way to acquire and release locks using async with.

    Example:
        >>> async with FileLockContext(lock_manager, "file.txt", "agent"):
        ...     # File is locked here
        ...     await write_to_file("file.txt", content)
        >>> # Lock is automatically released
    """

    def __init__(
        self,
        manager: FileLockManager,
        path: str,
        owner: str,
        timeout: float | None = None,
        wait: bool = True,
        wait_timeout: float = 30.0,
    ) -> None:
        """
        Initialize the lock context.

        Args:
            manager: The file lock manager.
            path: Path to the file to lock.
            owner: Name of the agent acquiring the lock.
            timeout: Lock timeout in seconds.
            wait: Whether to wait if file is already locked.
            wait_timeout: Maximum time to wait for the lock.
        """
        self._manager = manager
        self._path = path
        self._owner = owner
        self._timeout = timeout
        self._wait = wait
        self._wait_timeout = wait_timeout
        self._acquired = False

    async def __aenter__(self) -> "FileLockContext":
        """Acquire the lock."""
        self._acquired = await self._manager.acquire(
            self._path,
            self._owner,
            timeout=self._timeout,
            wait=self._wait,
            wait_timeout=self._wait_timeout,
        )

        if not self._acquired:
            raise LockAcquisitionError(
                f"Failed to acquire lock on '{self._path}' for '{self._owner}'"
            )

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Release the lock."""
        if self._acquired:
            await self._manager.release(self._path, self._owner)


class LockAcquisitionError(Exception):
    """Exception raised when lock acquisition fails."""

    pass
