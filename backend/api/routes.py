"""
API Routes module for AgentForge Studio.

This module provides the REST API endpoints for the application.
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from backend.core.workspace_manager import WorkspaceManager, WorkspaceStatus


router = APIRouter(tags=["api"])


# Request/Response Models

class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    requirements: Optional[dict[str, Any]] = None


class ProjectResponse(BaseModel):
    """Response model for project data."""
    id: str
    name: str
    status: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any]


class TaskRequest(BaseModel):
    """Request model for creating a task."""
    type: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    parameters: Optional[dict[str, Any]] = None


class TaskResponse(BaseModel):
    """Response model for task data."""
    id: str
    status: str
    result: Optional[dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Response model for agent data."""
    name: str
    description: str
    status: str


class GenerateRequest(BaseModel):
    """Request model for code generation."""
    project_id: str
    prompt: str = Field(..., min_length=1)
    options: Optional[dict[str, Any]] = None


class GenerateResponse(BaseModel):
    """Response model for code generation."""
    status: str
    message: str
    files: list[str] = []


# Dependency to get workspace manager
def get_workspace_manager(request: Request) -> WorkspaceManager:
    """
    Get the workspace manager from app state.
    
    Args:
        request: The current request.
        
    Returns:
        The WorkspaceManager instance.
    """
    return request.app.state.workspace_manager


# Projects Endpoints

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> ProjectResponse:
    """
    Create a new project.
    
    Args:
        request: Project creation request.
        workspace_manager: Workspace manager instance.
        
    Returns:
        Created project data.
    """
    metadata = {
        "description": request.description,
        "requirements": request.requirements or {}
    }
    
    workspace = workspace_manager.create(
        name=request.name,
        metadata=metadata
    )
    
    return ProjectResponse(
        id=workspace.id,
        name=workspace.name,
        status=workspace.status.value,
        created_at=workspace.created_at.isoformat(),
        updated_at=workspace.updated_at.isoformat(),
        metadata=workspace.metadata
    )


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> list[ProjectResponse]:
    """
    List all projects.
    
    Args:
        workspace_manager: Workspace manager instance.
        
    Returns:
        List of projects.
    """
    workspaces = workspace_manager.list()
    return [
        ProjectResponse(
            id=ws.id,
            name=ws.name,
            status=ws.status.value,
            created_at=ws.created_at.isoformat(),
            updated_at=ws.updated_at.isoformat(),
            metadata=ws.metadata
        )
        for ws in workspaces
    ]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> ProjectResponse:
    """
    Get a specific project.
    
    Args:
        project_id: The project ID.
        workspace_manager: Workspace manager instance.
        
    Returns:
        Project data.
        
    Raises:
        HTTPException: If project not found.
    """
    workspace = workspace_manager.get(project_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(
        id=workspace.id,
        name=workspace.name,
        status=workspace.status.value,
        created_at=workspace.created_at.isoformat(),
        updated_at=workspace.updated_at.isoformat(),
        metadata=workspace.metadata
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> dict[str, str]:
    """
    Delete a project.
    
    Args:
        project_id: The project ID.
        workspace_manager: Workspace manager instance.
        
    Returns:
        Success message.
        
    Raises:
        HTTPException: If project not found.
    """
    success = workspace_manager.delete(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"message": "Project deleted successfully"}


# Tasks Endpoints

@router.post("/projects/{project_id}/tasks", response_model=TaskResponse)
async def create_task(
    project_id: str,
    request: TaskRequest,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> TaskResponse:
    """
    Create a new task for a project.
    
    Args:
        project_id: The project ID.
        request: Task creation request.
        workspace_manager: Workspace manager instance.
        
    Returns:
        Created task data.
        
    Raises:
        HTTPException: If project not found.
    """
    workspace = workspace_manager.get(project_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create task (placeholder implementation)
    import uuid
    task_id = str(uuid.uuid4())
    
    return TaskResponse(
        id=task_id,
        status="pending",
        result=None
    )


@router.get("/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    project_id: str,
    task_id: str,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> TaskResponse:
    """
    Get a specific task.
    
    Args:
        project_id: The project ID.
        task_id: The task ID.
        workspace_manager: Workspace manager instance.
        
    Returns:
        Task data.
    """
    return TaskResponse(
        id=task_id,
        status="pending",
        result=None
    )


# Agents Endpoints

@router.get("/agents", response_model=list[AgentResponse])
async def list_agents() -> list[AgentResponse]:
    """
    List all available agents.
    
    Returns:
        List of agents.
    """
    agents = [
        AgentResponse(
            name="Orchestrator",
            description="Coordinates all agents and manages workflow",
            status="available"
        ),
        AgentResponse(
            name="Intermediator",
            description="Facilitates communication between agents",
            status="available"
        ),
        AgentResponse(
            name="Planner",
            description="Analyzes requirements and creates plans",
            status="available"
        ),
        AgentResponse(
            name="FrontendAgent",
            description="Generates frontend code and components",
            status="available"
        ),
        AgentResponse(
            name="BackendAgent",
            description="Generates backend code and APIs",
            status="available"
        ),
        AgentResponse(
            name="Reviewer",
            description="Reviews code for quality and improvements",
            status="available"
        ),
        AgentResponse(
            name="Tester",
            description="Generates and runs tests",
            status="available"
        ),
        AgentResponse(
            name="Helper",
            description="Provides utility functions",
            status="available"
        ),
    ]
    return agents


# Generation Endpoints

@router.post("/generate", response_model=GenerateResponse)
async def generate_code(
    request: GenerateRequest,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> GenerateResponse:
    """
    Generate code for a project.
    
    Args:
        request: Code generation request.
        workspace_manager: Workspace manager instance.
        
    Returns:
        Generation result.
        
    Raises:
        HTTPException: If project not found.
    """
    workspace = workspace_manager.get(request.project_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update workspace status
    workspace_manager.update(
        request.project_id,
        status=WorkspaceStatus.BUILDING
    )
    
    # Placeholder for actual generation
    return GenerateResponse(
        status="started",
        message="Code generation started",
        files=[]
    )


@router.get("/projects/{project_id}/files")
async def list_project_files(
    project_id: str,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> list[str]:
    """
    List files in a project.
    
    Args:
        project_id: The project ID.
        workspace_manager: Workspace manager instance.
        
    Returns:
        List of file paths.
        
    Raises:
        HTTPException: If project not found.
    """
    workspace = workspace_manager.get(project_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return workspace_manager.list_files(project_id)


@router.get("/projects/{project_id}/files/{file_path:path}")
async def get_project_file(
    project_id: str,
    file_path: str,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
) -> dict[str, str]:
    """
    Get a file from a project.
    
    Args:
        project_id: The project ID.
        file_path: Path to the file.
        workspace_manager: Workspace manager instance.
        
    Returns:
        File content.
        
    Raises:
        HTTPException: If project or file not found.
    """
    workspace = workspace_manager.get(project_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Project not found")
    
    content = workspace_manager.read_file(project_id, file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"path": file_path, "content": content}
