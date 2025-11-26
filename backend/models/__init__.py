"""
AgentForge Studio - Models Package.

This package contains Pydantic models for data validation
and serialization throughout the application.
"""

from backend.models.memory import (
    AgentContext,
    AgentNote,
    BestPractice,
    ClientPreference,
    Decision,
    ErrorRecord,
    Importance,
    MistakeRecord,
    Pattern,
    TaskRecord,
)
from backend.models.messages import (
    AgentInfo,
    AgentStatusType,
    ErrorMessage,
    Event,
    EventType,
    MessageType,
    ResultMessage,
    StatusMessage,
    TaskMessage,
    TaskPriority,
    TaskState,
)
from backend.models.messages import Message as BusMessage
from backend.models.messages import Task as BusTask
from backend.models.project import (
    DevelopmentPlan,
    GeneratedFile,
    PlanTask,
    ProjectRequirements,
    ProjectStage,
    ProjectSummary,
)
from backend.models.project import Project as WorkflowProject
from backend.models.schemas import (
    AgentStatus,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Message,
    Project,
    ProjectCreate,
    ProjectStatus,
    Task,
    TaskStatus,
)

__all__ = [
    # schemas.py models (existing)
    "Message",
    "Task",
    "TaskStatus",
    "Project",
    "ProjectCreate",
    "ProjectStatus",
    "AgentStatus",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    # messages.py models (new)
    "MessageType",
    "TaskPriority",
    "TaskState",
    "AgentStatusType",
    "EventType",
    "BusMessage",
    "TaskMessage",
    "ResultMessage",
    "StatusMessage",
    "ErrorMessage",
    "Event",
    "BusTask",
    "AgentInfo",
    # project.py models (workflow)
    "ProjectStage",
    "ProjectRequirements",
    "PlanTask",
    "DevelopmentPlan",
    "GeneratedFile",
    "WorkflowProject",
    "ProjectSummary",
    # memory.py models
    "Importance",
    "ClientPreference",
    "TaskRecord",
    "ErrorRecord",
    "AgentNote",
    "Decision",
    "Pattern",
    "BestPractice",
    "MistakeRecord",
    "AgentContext",
]
