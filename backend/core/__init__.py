"""
AgentForge Studio - Core Package.

This package contains core utilities and infrastructure components
for the AgentForge Studio system.
"""

from backend.core import ai_clients
from backend.core.agent_registry import AgentRegistry
from backend.core.api_key_manager import APIKeyManager, KeyStats, RotationStrategy
from backend.core.config import Settings, get_settings
from backend.core.event_emitter import EventEmitter
from backend.core.file_lock_manager import (
    FileLock,
    FileLockContext,
    FileLockManager,
    LockAcquisitionError,
)
from backend.core.git_manager import GitManager
from backend.core.memory import (
    ApplicationMemory,
    ContextBuilder,
    MemoryManager,
    ProjectMemory,
)
from backend.core.message_bus import MessageBus
from backend.core.orchestrator import Orchestrator
from backend.core.preview_server import PreviewServer
from backend.core.project_manager import ProjectManager
from backend.core.task_dispatcher import (
    DispatchedTask,
    DispatchedTaskState,
    TaskDispatcher,
)
from backend.core.task_queue import AsyncTaskQueue, TaskQueue
from backend.core.workflow_engine import WorkflowEngine
from backend.core.workspace_manager import WorkspaceManager

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    # Communication
    "MessageBus",
    "EventEmitter",
    # Task Management
    "TaskQueue",
    "AsyncTaskQueue",
    # File Management
    "FileLockManager",
    "FileLock",
    "FileLockContext",
    "LockAcquisitionError",
    # Agent Management
    "AgentRegistry",
    # Orchestration
    "Orchestrator",
    "WorkflowEngine",
    "ProjectManager",
    "TaskDispatcher",
    "DispatchedTask",
    "DispatchedTaskState",
    # Memory
    "ProjectMemory",
    "ApplicationMemory",
    "MemoryManager",
    "ContextBuilder",
    # API Key Management
    "APIKeyManager",
    "RotationStrategy",
    "KeyStats",
    # Other
    "WorkspaceManager",
    "GitManager",
    "PreviewServer",
    "ai_clients",
]
