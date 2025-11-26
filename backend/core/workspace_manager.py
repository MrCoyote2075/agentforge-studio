"""
AgentForge Studio - Workspace Manager.

This module handles file CRUD operations, project folder management,
and file locking for the generated project workspaces.
"""

import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from backend.core.config import get_settings


class FileLock:
    """
    Simple async file lock implementation.

    Prevents concurrent access to the same file during write operations.
    """

    def __init__(self) -> None:
        """Initialize the file lock manager."""
        self._locks: dict[str, asyncio.Lock] = {}

    def get_lock(self, file_path: str) -> asyncio.Lock:
        """
        Get or create a lock for a file path.

        Args:
            file_path: Path to the file.

        Returns:
            asyncio.Lock for the file.
        """
        if file_path not in self._locks:
            self._locks[file_path] = asyncio.Lock()
        return self._locks[file_path]

    def release_lock(self, file_path: str) -> None:
        """
        Release and remove a lock for a file path.

        Args:
            file_path: Path to the file.
        """
        if file_path in self._locks:
            del self._locks[file_path]


class WorkspaceManager:
    """
    Manages project workspaces and file operations.

    The WorkspaceManager handles creating project directories, file CRUD
    operations, and ensures proper file locking during writes.

    Attributes:
        workspace_path: Base path for all workspaces.
        file_lock: File locking manager.

    Example:
        >>> manager = WorkspaceManager()
        >>> await manager.create_project("my-project")
        >>> await manager.write_file("my-project", "index.html", "<html>...")
    """

    def __init__(self, workspace_path: Path | None = None) -> None:
        """
        Initialize the workspace manager.

        Args:
            workspace_path: Optional custom workspace path.
        """
        settings = get_settings()
        self._workspace_path = workspace_path or settings.workspace_path
        self._file_lock = FileLock()
        self.logger = logging.getLogger("workspace_manager")

    @property
    def workspace_path(self) -> Path:
        """Get the base workspace path."""
        return self._workspace_path

    async def initialize(self) -> None:
        """
        Initialize the workspace manager.

        Ensures the workspace directory exists.
        """
        await aiofiles.os.makedirs(self._workspace_path, exist_ok=True)
        self.logger.info(f"Workspace initialized at {self._workspace_path}")

    async def create_project(self, project_id: str) -> Path:
        """
        Create a new project workspace.

        Args:
            project_id: Unique project identifier.

        Returns:
            Path to the created project directory.

        Raises:
            FileExistsError: If the project already exists.
        """
        project_path = self._workspace_path / project_id

        if await aiofiles.os.path.exists(project_path):
            raise FileExistsError(f"Project '{project_id}' already exists")

        await aiofiles.os.makedirs(project_path)
        self.logger.info(f"Created project workspace: {project_path}")
        return project_path

    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a project workspace.

        Args:
            project_id: Project identifier.

        Returns:
            bool: True if deleted successfully.

        Raises:
            FileNotFoundError: If the project doesn't exist.
        """
        project_path = self._workspace_path / project_id

        if not await aiofiles.os.path.exists(project_path):
            raise FileNotFoundError(f"Project '{project_id}' not found")

        # Use sync shutil for directory removal
        await asyncio.to_thread(shutil.rmtree, project_path)
        self.logger.info(f"Deleted project workspace: {project_path}")
        return True

    async def project_exists(self, project_id: str) -> bool:
        """
        Check if a project exists.

        Args:
            project_id: Project identifier.

        Returns:
            bool: True if the project exists.
        """
        project_path = self._workspace_path / project_id
        return await aiofiles.os.path.exists(project_path)

    async def list_projects(self) -> list[str]:
        """
        List all project workspaces.

        Returns:
            List of project identifiers.
        """
        if not await aiofiles.os.path.exists(self._workspace_path):
            return []

        entries = await aiofiles.os.listdir(self._workspace_path)
        projects = []
        for entry in entries:
            entry_path = self._workspace_path / entry
            if await aiofiles.os.path.isdir(entry_path):
                projects.append(entry)
        return projects

    async def write_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
    ) -> Path:
        """
        Write content to a file in a project.

        Args:
            project_id: Project identifier.
            file_path: Relative path within the project.
            content: File content to write.

        Returns:
            Path to the written file.

        Raises:
            FileNotFoundError: If the project doesn't exist.
        """
        project_path = self._workspace_path / project_id

        if not await aiofiles.os.path.exists(project_path):
            raise FileNotFoundError(f"Project '{project_id}' not found")

        full_path = project_path / file_path
        parent_dir = full_path.parent

        # Create parent directories if needed
        await aiofiles.os.makedirs(parent_dir, exist_ok=True)

        # Acquire lock for this file
        lock = self._file_lock.get_lock(str(full_path))

        async with lock:
            async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
                await f.write(content)

        self.logger.debug(f"Wrote file: {full_path}")
        return full_path

    async def read_file(self, project_id: str, file_path: str) -> str:
        """
        Read content from a file in a project.

        Args:
            project_id: Project identifier.
            file_path: Relative path within the project.

        Returns:
            str: File content.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        full_path = self._workspace_path / project_id / file_path

        if not await aiofiles.os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(full_path, encoding="utf-8") as f:
            content = await f.read()

        return content

    async def delete_file(self, project_id: str, file_path: str) -> bool:
        """
        Delete a file from a project.

        Args:
            project_id: Project identifier.
            file_path: Relative path within the project.

        Returns:
            bool: True if deleted successfully.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        full_path = self._workspace_path / project_id / file_path

        if not await aiofiles.os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        await aiofiles.os.remove(full_path)
        self._file_lock.release_lock(str(full_path))
        self.logger.debug(f"Deleted file: {full_path}")
        return True

    async def file_exists(self, project_id: str, file_path: str) -> bool:
        """
        Check if a file exists in a project.

        Args:
            project_id: Project identifier.
            file_path: Relative path within the project.

        Returns:
            bool: True if the file exists.
        """
        full_path = self._workspace_path / project_id / file_path
        return await aiofiles.os.path.exists(full_path)

    async def list_files(
        self,
        project_id: str,
        directory: str = "",
        recursive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List files in a project directory.

        Args:
            project_id: Project identifier.
            directory: Subdirectory to list (empty for root).
            recursive: Whether to list files recursively.

        Returns:
            List of file info dictionaries.
        """
        project_path = self._workspace_path / project_id / directory

        if not await aiofiles.os.path.exists(project_path):
            return []

        files = []

        async def scan_dir(path: Path, base: str = "") -> None:
            entries = await aiofiles.os.listdir(path)
            for entry in entries:
                entry_path = path / entry
                relative_path = f"{base}/{entry}" if base else entry
                is_dir = await aiofiles.os.path.isdir(entry_path)

                if is_dir:
                    if recursive:
                        await scan_dir(entry_path, relative_path)
                    files.append({
                        "name": entry,
                        "path": relative_path,
                        "type": "directory",
                    })
                else:
                    stat = await aiofiles.os.stat(entry_path)
                    files.append({
                        "name": entry,
                        "path": relative_path,
                        "type": "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })

        await scan_dir(project_path)
        return files

    async def create_directory(
        self,
        project_id: str,
        directory_path: str,
    ) -> Path:
        """
        Create a directory in a project.

        Args:
            project_id: Project identifier.
            directory_path: Relative directory path.

        Returns:
            Path to the created directory.
        """
        full_path = self._workspace_path / project_id / directory_path
        await aiofiles.os.makedirs(full_path, exist_ok=True)
        self.logger.debug(f"Created directory: {full_path}")
        return full_path

    async def copy_file(
        self,
        project_id: str,
        source_path: str,
        dest_path: str,
    ) -> Path:
        """
        Copy a file within a project.

        Args:
            project_id: Project identifier.
            source_path: Source file path.
            dest_path: Destination file path.

        Returns:
            Path to the copied file.
        """
        content = await self.read_file(project_id, source_path)
        return await self.write_file(project_id, dest_path, content)

    async def move_file(
        self,
        project_id: str,
        source_path: str,
        dest_path: str,
    ) -> Path:
        """
        Move a file within a project.

        Args:
            project_id: Project identifier.
            source_path: Source file path.
            dest_path: Destination file path.

        Returns:
            Path to the moved file.
        """
        new_path = await self.copy_file(project_id, source_path, dest_path)
        await self.delete_file(project_id, source_path)
        return new_path

    async def get_project_size(self, project_id: str) -> int:
        """
        Get the total size of a project in bytes.

        Args:
            project_id: Project identifier.

        Returns:
            int: Total size in bytes.
        """
        project_path = self._workspace_path / project_id

        if not await aiofiles.os.path.exists(project_path):
            return 0

        total_size = 0
        files = await self.list_files(project_id, recursive=True)
        for file_info in files:
            if file_info["type"] == "file":
                total_size += file_info.get("size", 0)

        return total_size
