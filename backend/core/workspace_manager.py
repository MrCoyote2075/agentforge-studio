"""
Workspace Manager module for AgentForge Studio.

This module provides management of project workspaces where
generated websites are stored.
"""

import json
import shutil
from typing import Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
import uuid


class WorkspaceStatus(Enum):
    """Workspace status enumeration."""
    CREATED = "created"
    ACTIVE = "active"
    BUILDING = "building"
    COMPLETED = "completed"
    ERROR = "error"
    ARCHIVED = "archived"


@dataclass
class Workspace:
    """
    Represents a project workspace.
    
    Attributes:
        id: Unique workspace identifier.
        name: Human-readable workspace name.
        path: Filesystem path to workspace.
        status: Current workspace status.
        created_at: When the workspace was created.
        updated_at: When the workspace was last updated.
        metadata: Additional workspace metadata.
    """
    name: str
    path: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: WorkspaceStatus = WorkspaceStatus.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert workspace to dictionary.
        
        Returns:
            Dictionary representation of workspace.
        """
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workspace":
        """
        Create workspace from dictionary.
        
        Args:
            data: Dictionary with workspace data.
            
        Returns:
            Workspace instance.
        """
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            path=data["path"],
            status=WorkspaceStatus(data.get("status", "created")),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.utcnow().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                data.get("updated_at", datetime.utcnow().isoformat())
            ),
            metadata=data.get("metadata", {})
        )


class WorkspaceManager:
    """
    Manager for project workspaces.
    
    Handles creation, deletion, and management of workspaces
    where generated website projects are stored.
    
    Attributes:
        base_path: Base directory for all workspaces.
        workspaces: Dictionary of workspace ID to Workspace.
    """
    
    def __init__(self, base_path: str = "./workspaces") -> None:
        """
        Initialize the workspace manager.
        
        Args:
            base_path: Base directory for workspaces.
        """
        self.base_path = Path(base_path).resolve()
        self._workspaces: dict[str, Workspace] = {}
        self._ensure_base_directory()
        self._load_workspaces()
    
    def _ensure_base_directory(self) -> None:
        """Ensure the base workspace directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _load_workspaces(self) -> None:
        """Load existing workspaces from disk."""
        index_file = self.base_path / "workspaces.json"
        if index_file.exists():
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    for ws_data in data.get("workspaces", []):
                        workspace = Workspace.from_dict(ws_data)
                        self._workspaces[workspace.id] = workspace
            except (json.JSONDecodeError, KeyError):
                pass
    
    def _save_workspaces(self) -> None:
        """Save workspaces index to disk."""
        index_file = self.base_path / "workspaces.json"
        data = {
            "workspaces": [
                ws.to_dict() for ws in self._workspaces.values()
            ]
        }
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def create(
        self,
        name: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> Workspace:
        """
        Create a new workspace.
        
        Args:
            name: Name for the workspace.
            metadata: Optional metadata.
            
        Returns:
            The created Workspace.
        """
        workspace_id = str(uuid.uuid4())
        workspace_path = self.base_path / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        workspace = Workspace(
            id=workspace_id,
            name=name,
            path=str(workspace_path),
            metadata=metadata or {}
        )
        
        self._workspaces[workspace_id] = workspace
        self._save_workspaces()
        
        # Create workspace structure
        self._create_workspace_structure(workspace)
        
        return workspace
    
    def _create_workspace_structure(self, workspace: Workspace) -> None:
        """
        Create the standard workspace directory structure.
        
        Args:
            workspace: The workspace to create structure for.
        """
        ws_path = Path(workspace.path)
        
        # Create standard directories
        directories = [
            "src",
            "src/frontend",
            "src/backend",
            "assets",
            "config",
            "docs",
            "tests"
        ]
        
        for directory in directories:
            (ws_path / directory).mkdir(parents=True, exist_ok=True)
        
        # Create workspace config file
        config_data = {
            "workspace_id": workspace.id,
            "name": workspace.name,
            "created_at": workspace.created_at.isoformat(),
            "version": "1.0.0"
        }
        
        with open(ws_path / "workspace.json", "w") as f:
            json.dump(config_data, f, indent=2)
    
    def get(self, workspace_id: str) -> Optional[Workspace]:
        """
        Get a workspace by ID.
        
        Args:
            workspace_id: The workspace ID.
            
        Returns:
            The Workspace or None if not found.
        """
        return self._workspaces.get(workspace_id)
    
    def get_by_name(self, name: str) -> Optional[Workspace]:
        """
        Get a workspace by name.
        
        Args:
            name: The workspace name.
            
        Returns:
            The Workspace or None if not found.
        """
        for workspace in self._workspaces.values():
            if workspace.name == name:
                return workspace
        return None
    
    def list(self) -> list[Workspace]:
        """
        List all workspaces.
        
        Returns:
            List of all workspaces.
        """
        return list(self._workspaces.values())
    
    def update(
        self,
        workspace_id: str,
        name: Optional[str] = None,
        status: Optional[WorkspaceStatus] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Workspace]:
        """
        Update a workspace.
        
        Args:
            workspace_id: The workspace ID.
            name: New name (optional).
            status: New status (optional).
            metadata: New metadata (optional).
            
        Returns:
            The updated Workspace or None if not found.
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        if name is not None:
            workspace.name = name
        if status is not None:
            workspace.status = status
        if metadata is not None:
            workspace.metadata.update(metadata)
        
        workspace.updated_at = datetime.utcnow()
        self._save_workspaces()
        
        return workspace
    
    def delete(self, workspace_id: str, remove_files: bool = True) -> bool:
        """
        Delete a workspace.
        
        Args:
            workspace_id: The workspace ID.
            remove_files: Whether to remove workspace files.
            
        Returns:
            True if deleted, False if not found.
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        if remove_files:
            workspace_path = Path(workspace.path)
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
        
        del self._workspaces[workspace_id]
        self._save_workspaces()
        
        return True
    
    def archive(self, workspace_id: str) -> Optional[Workspace]:
        """
        Archive a workspace.
        
        Args:
            workspace_id: The workspace ID.
            
        Returns:
            The archived Workspace or None if not found.
        """
        return self.update(
            workspace_id,
            status=WorkspaceStatus.ARCHIVED
        )
    
    def get_workspace_path(self, workspace_id: str) -> Optional[Path]:
        """
        Get the filesystem path for a workspace.
        
        Args:
            workspace_id: The workspace ID.
            
        Returns:
            Path to the workspace or None if not found.
        """
        workspace = self._workspaces.get(workspace_id)
        if workspace:
            return Path(workspace.path)
        return None
    
    def write_file(
        self,
        workspace_id: str,
        relative_path: str,
        content: str
    ) -> bool:
        """
        Write a file to a workspace.
        
        Args:
            workspace_id: The workspace ID.
            relative_path: Path relative to workspace root.
            content: File content.
            
        Returns:
            True if successful, False otherwise.
        """
        workspace_path = self.get_workspace_path(workspace_id)
        if not workspace_path:
            return False
        
        file_path = workspace_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w") as f:
            f.write(content)
        
        return True
    
    def read_file(
        self,
        workspace_id: str,
        relative_path: str
    ) -> Optional[str]:
        """
        Read a file from a workspace.
        
        Args:
            workspace_id: The workspace ID.
            relative_path: Path relative to workspace root.
            
        Returns:
            File content or None if not found.
        """
        workspace_path = self.get_workspace_path(workspace_id)
        if not workspace_path:
            return None
        
        file_path = workspace_path / relative_path
        if not file_path.exists():
            return None
        
        with open(file_path, "r") as f:
            return f.read()
    
    def list_files(
        self,
        workspace_id: str,
        directory: str = ""
    ) -> List[str]:
        """
        List files in a workspace directory.
        
        Args:
            workspace_id: The workspace ID.
            directory: Subdirectory to list (optional).
            
        Returns:
            List of file paths relative to workspace.
        """
        workspace_path = self.get_workspace_path(workspace_id)
        if not workspace_path:
            return []
        
        target_path = workspace_path / directory if directory else workspace_path
        if not target_path.exists():
            return []
        
        files: List[str] = []
        for item in target_path.rglob("*"):
            if item.is_file():
                files.append(str(item.relative_to(workspace_path)))
        
        return files
