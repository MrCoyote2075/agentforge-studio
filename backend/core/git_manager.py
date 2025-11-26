"""
AgentForge Studio - Git Manager.

This module handles Git operations for project version control,
including initialization, commits, and repository management.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


class GitManager:
    """
    Manages Git operations for project workspaces.

    The GitManager handles initializing repositories, committing changes,
    and other Git operations for generated projects.

    Attributes:
        workspace_path: Base path for workspaces.

    Example:
        >>> git = GitManager()
        >>> await git.init_repo("my-project")
        >>> await git.commit("my-project", "Initial commit")
    """

    def __init__(self, workspace_path: Path | None = None) -> None:
        """
        Initialize the Git manager.

        Args:
            workspace_path: Optional custom workspace path.
        """
        from backend.core.config import get_settings

        settings = get_settings()
        self._workspace_path = workspace_path or settings.workspace_path
        self.logger = logging.getLogger("git_manager")

    async def _run_git_command(
        self,
        project_id: str,
        *args: str,
    ) -> tuple[int, str, str]:
        """
        Run a git command in the project directory.

        Args:
            project_id: Project identifier.
            *args: Git command arguments.

        Returns:
            Tuple of (return_code, stdout, stderr).
        """
        project_path = self._workspace_path / project_id

        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        return (
            process.returncode or 0,
            stdout.decode("utf-8"),
            stderr.decode("utf-8"),
        )

    async def is_git_available(self) -> bool:
        """
        Check if git is available on the system.

        Returns:
            bool: True if git is available.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except FileNotFoundError:
            return False

    async def init_repo(self, project_id: str) -> bool:
        """
        Initialize a Git repository for a project.

        Args:
            project_id: Project identifier.

        Returns:
            bool: True if initialization was successful.
        """
        project_path = self._workspace_path / project_id
        git_dir = project_path / ".git"

        if git_dir.exists():
            self.logger.info(f"Git repository already exists for {project_id}")
            return True

        code, stdout, stderr = await self._run_git_command(project_id, "init")

        if code == 0:
            self.logger.info(f"Initialized Git repository for {project_id}")
            # Set default user info for commits
            await self._run_git_command(
                project_id,
                "config",
                "user.email",
                "agentforge@studio.local",
            )
            await self._run_git_command(
                project_id,
                "config",
                "user.name",
                "AgentForge Studio",
            )
            return True
        else:
            self.logger.error(f"Failed to initialize Git: {stderr}")
            return False

    async def commit(
        self,
        project_id: str,
        message: str,
        add_all: bool = True,
    ) -> str | None:
        """
        Create a Git commit.

        Args:
            project_id: Project identifier.
            message: Commit message.
            add_all: Whether to add all changes before committing.

        Returns:
            Optional[str]: Commit hash if successful, None otherwise.
        """
        if add_all:
            await self._run_git_command(project_id, "add", "-A")

        code, stdout, stderr = await self._run_git_command(
            project_id,
            "commit",
            "-m",
            message,
        )

        if code == 0:
            # Get the commit hash
            hash_code, hash_out, _ = await self._run_git_command(
                project_id,
                "rev-parse",
                "HEAD",
            )
            if hash_code == 0:
                commit_hash = hash_out.strip()
                self.logger.info(f"Created commit {commit_hash[:8]} for {project_id}")
                return commit_hash
        else:
            if "nothing to commit" in stderr:
                self.logger.info(f"No changes to commit for {project_id}")
                return None
            self.logger.error(f"Failed to commit: {stderr}")

        return None

    async def get_log(
        self,
        project_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get the commit log for a project.

        Args:
            project_id: Project identifier.
            limit: Maximum number of commits to return.

        Returns:
            List of commit dictionaries.
        """
        code, stdout, stderr = await self._run_git_command(
            project_id,
            "log",
            f"-{limit}",
            "--format=%H|%an|%ae|%at|%s",
        )

        if code != 0:
            self.logger.error(f"Failed to get log: {stderr}")
            return []

        commits = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0],
                    "author_name": parts[1],
                    "author_email": parts[2],
                    "timestamp": datetime.fromtimestamp(int(parts[3])).isoformat(),
                    "message": parts[4],
                })

        return commits

    async def get_status(self, project_id: str) -> dict[str, Any]:
        """
        Get the Git status for a project.

        Args:
            project_id: Project identifier.

        Returns:
            Dict with status information.
        """
        code, stdout, stderr = await self._run_git_command(
            project_id,
            "status",
            "--porcelain",
        )

        if code != 0:
            return {"error": stderr}

        modified = []
        added = []
        deleted = []
        untracked = []

        for line in stdout.strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            file_path = line[3:]

            if "M" in status:
                modified.append(file_path)
            elif "A" in status:
                added.append(file_path)
            elif "D" in status:
                deleted.append(file_path)
            elif "?" in status:
                untracked.append(file_path)

        return {
            "modified": modified,
            "added": added,
            "deleted": deleted,
            "untracked": untracked,
            "clean": not (modified or added or deleted or untracked),
        }

    async def get_diff(
        self,
        project_id: str,
        file_path: str | None = None,
    ) -> str:
        """
        Get the diff for a project or specific file.

        Args:
            project_id: Project identifier.
            file_path: Optional specific file to diff.

        Returns:
            str: Diff output.
        """
        args = ["diff"]
        if file_path:
            args.append(file_path)

        code, stdout, stderr = await self._run_git_command(project_id, *args)

        if code != 0:
            self.logger.error(f"Failed to get diff: {stderr}")
            return ""

        return stdout

    async def create_branch(self, project_id: str, branch_name: str) -> bool:
        """
        Create a new branch.

        Args:
            project_id: Project identifier.
            branch_name: Name of the branch to create.

        Returns:
            bool: True if successful.
        """
        code, stdout, stderr = await self._run_git_command(
            project_id,
            "checkout",
            "-b",
            branch_name,
        )

        if code == 0:
            self.logger.info(f"Created branch {branch_name} for {project_id}")
            return True
        else:
            self.logger.error(f"Failed to create branch: {stderr}")
            return False

    async def switch_branch(self, project_id: str, branch_name: str) -> bool:
        """
        Switch to a different branch.

        Args:
            project_id: Project identifier.
            branch_name: Name of the branch to switch to.

        Returns:
            bool: True if successful.
        """
        code, stdout, stderr = await self._run_git_command(
            project_id,
            "checkout",
            branch_name,
        )

        if code == 0:
            self.logger.info(f"Switched to branch {branch_name} for {project_id}")
            return True
        else:
            self.logger.error(f"Failed to switch branch: {stderr}")
            return False

    async def list_branches(self, project_id: str) -> list[str]:
        """
        List all branches in a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of branch names.
        """
        code, stdout, stderr = await self._run_git_command(
            project_id,
            "branch",
            "--list",
        )

        if code != 0:
            return []

        branches = []
        for line in stdout.strip().split("\n"):
            if line:
                branch = line.strip().lstrip("* ")
                branches.append(branch)

        return branches

    async def get_current_branch(self, project_id: str) -> str | None:
        """
        Get the current branch name.

        Args:
            project_id: Project identifier.

        Returns:
            Optional[str]: Branch name or None.
        """
        code, stdout, stderr = await self._run_git_command(
            project_id,
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        )

        if code == 0:
            return stdout.strip()
        return None

    async def add_remote(
        self,
        project_id: str,
        name: str,
        url: str,
    ) -> bool:
        """
        Add a remote repository.

        Args:
            project_id: Project identifier.
            name: Remote name (e.g., 'origin').
            url: Remote URL.

        Returns:
            bool: True if successful.
        """
        code, stdout, stderr = await self._run_git_command(
            project_id,
            "remote",
            "add",
            name,
            url,
        )

        if code == 0:
            self.logger.info(f"Added remote {name} for {project_id}")
            return True
        else:
            self.logger.error(f"Failed to add remote: {stderr}")
            return False

    async def push(
        self,
        project_id: str,
        remote: str = "origin",
        branch: str | None = None,
    ) -> bool:
        """
        Push commits to a remote repository.

        Args:
            project_id: Project identifier.
            remote: Remote name.
            branch: Branch to push (defaults to current).

        Returns:
            bool: True if successful.
        """
        args = ["push", remote]
        if branch:
            args.append(branch)

        code, stdout, stderr = await self._run_git_command(project_id, *args)

        if code == 0:
            self.logger.info(f"Pushed {project_id} to {remote}")
            return True
        else:
            self.logger.error(f"Failed to push: {stderr}")
            return False
