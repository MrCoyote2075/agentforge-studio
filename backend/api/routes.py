"""
AgentForge Studio - API Routes.

This module defines the REST API endpoints for project management,
chat interactions, and file operations.
"""

import io
import logging
import mimetypes
import zipfile
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from backend.agents.intermediator import Intermediator
from backend.core.flow_controller import FlowController
from backend.core.git_manager import GitManager
from backend.core.workspace_manager import WorkspaceManager
from backend.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Project,
    ProjectCreate,
    ProjectStatus,
)

router = APIRouter(tags=["api"])
logger = logging.getLogger(__name__)

# In-memory storage for demo purposes
# TODO: Replace with proper database
_projects: dict[str, Project] = {}
_chat_history: dict[str, list[ChatMessage]] = {}


# Dependency instances
_workspace_manager: WorkspaceManager | None = None
_git_manager: GitManager | None = None
_intermediator: Intermediator | None = None
_flow_controller: FlowController | None = None


def get_workspace_manager() -> WorkspaceManager:
    """Get or create the workspace manager instance."""
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()
    return _workspace_manager


def get_git_manager() -> GitManager:
    """Get or create the git manager instance."""
    global _git_manager
    if _git_manager is None:
        _git_manager = GitManager()
    return _git_manager


def get_intermediator() -> Intermediator:
    """Get or create the Intermediator agent instance."""
    global _intermediator
    if _intermediator is None:
        _intermediator = Intermediator()
    return _intermediator


def get_flow_controller() -> FlowController:
    """Get or create the FlowController instance."""
    global _flow_controller
    if _flow_controller is None:
        _flow_controller = FlowController(
            workspace_manager=get_workspace_manager(),
        )
    return _flow_controller


# Chat endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a chat message to the Intermediator agent.

    When the user confirms requirements, this triggers the full
    website generation flow through the FlowController.

    Args:
        request: Chat request containing the message and optional project ID.

    Returns:
        ChatResponse: The agent's response.

    Raises:
        HTTPException: If the project doesn't exist.
    """
    if request.project_id and request.project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    # Store user message
    user_message = ChatMessage(
        content=request.message,
        project_id=request.project_id,
        role="user",
    )

    if request.project_id:
        if request.project_id not in _chat_history:
            _chat_history[request.project_id] = []
        _chat_history[request.project_id].append(user_message)

    # Get response from Intermediator agent via FlowController
    try:
        intermediator = get_intermediator()
        flow_controller = get_flow_controller()

        # Process through flow controller for full flow support
        if request.project_id:
            result = await flow_controller.process_user_message(
                project_id=request.project_id,
                message=request.message,
                intermediator=intermediator,
            )

            # Handle structured response
            if isinstance(result, dict):
                response_content = result.get("response", "")

                # Update project status if generation completed
                if result.get("files_generated"):
                    project = _projects.get(request.project_id)
                    if project:
                        project.status = ProjectStatus.COMPLETED
                        project.files = result.get("files", [])
            else:
                response_content = result
        else:
            # No project ID - just chat with intermediator
            chat_result = await intermediator.chat(
                user_message=request.message,
                project_id=request.project_id,
            )
            if isinstance(chat_result, dict):
                response_content = chat_result.get("response", "")
            else:
                response_content = chat_result

    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        response_content = (
            "I apologize, but I'm having trouble processing your request. "
            "Please try again in a moment."
        )

    assistant_message = ChatMessage(
        content=response_content,
        project_id=request.project_id,
        role="assistant",
    )

    if request.project_id:
        _chat_history[request.project_id].append(assistant_message)

    return ChatResponse(
        message=response_content,
        project_id=request.project_id,
    )


@router.get("/chat/{project_id}/history", response_model=list[ChatMessage])
async def get_chat_history(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ChatMessage]:
    """
    Get chat history for a project.

    Args:
        project_id: The project identifier.
        limit: Maximum number of messages to return.

    Returns:
        List of chat messages.

    Raises:
        HTTPException: If the project doesn't exist.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    history = _chat_history.get(project_id, [])
    return history[-limit:]


# Project endpoints
@router.get("/projects", response_model=list[Project])
async def list_projects() -> list[Project]:
    """
    List all projects.

    Returns:
        List of all projects.
    """
    return list(_projects.values())


@router.post("/projects", response_model=Project, status_code=201)
async def create_project(project: ProjectCreate) -> Project:
    """
    Create a new project.

    Args:
        project: Project creation data.

    Returns:
        Project: The created project.

    Raises:
        HTTPException: If a project with the same name exists.
    """
    # Check for duplicate names
    for existing in _projects.values():
        if existing.name == project.name:
            raise HTTPException(
                status_code=400,
                detail="Project with this name already exists",
            )

    # Create the project
    project_id = str(uuid4())
    new_project = Project(
        id=project_id,
        name=project.name,
        status=ProjectStatus.CREATED,
        requirements=project.requirements,
        files=[],
        created_at=datetime.utcnow(),
    )

    _projects[project_id] = new_project
    _chat_history[project_id] = []

    # Create workspace
    workspace_manager = get_workspace_manager()
    try:
        await workspace_manager.create_project(project_id)
    except Exception as e:
        del _projects[project_id]
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {e}")

    # Initialize git repository
    git_manager = get_git_manager()
    await git_manager.init_repo(project_id)

    return new_project


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str) -> Project:
    """
    Get a specific project by ID.

    Args:
        project_id: The project identifier.

    Returns:
        Project: The requested project.

    Raises:
        HTTPException: If the project doesn't exist.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    return _projects[project_id]


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    """
    Delete a project.

    Args:
        project_id: The project identifier.

    Raises:
        HTTPException: If the project doesn't exist.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete workspace
    workspace_manager = get_workspace_manager()
    try:
        await workspace_manager.delete_project(project_id)
    except Exception:
        pass  # Workspace might not exist

    del _projects[project_id]
    if project_id in _chat_history:
        del _chat_history[project_id]


@router.get("/projects/{project_id}/download")
async def download_project(project_id: str) -> StreamingResponse:
    """
    Download a project as a ZIP file.

    Args:
        project_id: The project identifier.

    Returns:
        StreamingResponse: ZIP file download.

    Raises:
        HTTPException: If the project doesn't exist.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace_manager = get_workspace_manager()

    # Check if project has files
    if not await workspace_manager.project_exists(project_id):
        raise HTTPException(status_code=404, detail="Project workspace not found")

    # Create a ZIP file in memory
    zip_buffer = io.BytesIO()

    try:
        files = await workspace_manager.list_files(project_id, recursive=True)

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_info in files:
                if file_info["type"] == "file":
                    file_path = file_info["path"]
                    content = await workspace_manager.read_file(project_id, file_path)
                    zip_file.writestr(file_path, content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP: {e}")

    zip_buffer.seek(0)

    project = _projects[project_id]
    filename = f"{project.name.replace(' ', '_')}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# Project files endpoints
@router.get("/projects/{project_id}/files")
async def list_project_files(
    project_id: str,
    path: str = "",
    recursive: bool = False,
) -> list[dict[str, Any]]:
    """
    List files in a project.

    Args:
        project_id: The project identifier.
        path: Subdirectory path.
        recursive: Whether to list recursively.

    Returns:
        List of file information dictionaries.

    Raises:
        HTTPException: If the project doesn't exist.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace_manager = get_workspace_manager()
    files = await workspace_manager.list_files(project_id, path, recursive)
    return files


@router.get("/projects/{project_id}/files/{file_path:path}")
async def get_project_file(project_id: str, file_path: str) -> dict[str, str]:
    """
    Get the content of a file.

    Args:
        project_id: The project identifier.
        file_path: Path to the file.

    Returns:
        Dict with file content.

    Raises:
        HTTPException: If the file doesn't exist.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace_manager = get_workspace_manager()

    try:
        content = await workspace_manager.read_file(project_id, file_path)
        return {"path": file_path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


# Git endpoints
@router.get("/projects/{project_id}/git/status")
async def get_git_status(project_id: str) -> dict[str, Any]:
    """
    Get Git status for a project.

    Args:
        project_id: The project identifier.

    Returns:
        Dict with Git status information.

    Raises:
        HTTPException: If the project doesn't exist.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    git_manager = get_git_manager()
    status = await git_manager.get_status(project_id)
    return status


@router.get("/projects/{project_id}/git/log")
async def get_git_log(
    project_id: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict[str, Any]]:
    """
    Get Git commit log for a project.

    Args:
        project_id: The project identifier.
        limit: Maximum number of commits.

    Returns:
        List of commit information.

    Raises:
        HTTPException: If the project doesn't exist.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    git_manager = get_git_manager()
    log = await git_manager.get_log(project_id, limit)
    return log


# Preview endpoint
@router.get("/preview/{project_id}")
@router.get("/preview/{project_id}/{file_path:path}")
async def serve_preview(
    project_id: str,
    file_path: str = "index.html",
) -> Response:
    """
    Serve generated files for iframe preview.

    Args:
        project_id: The project identifier.
        file_path: Path to the file to serve.

    Returns:
        Response: File content with appropriate content type.

    Raises:
        HTTPException: If the file doesn't exist.
    """
    workspace_manager = get_workspace_manager()

    # Security: prevent directory traversal
    if ".." in file_path:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Check if project exists
    if not await workspace_manager.project_exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # Default to index.html if no path specified
    if not file_path or file_path == "/":
        file_path = "index.html"

    try:
        content = await workspace_manager.read_file(project_id, file_path)

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = "text/plain"

        # Inject auto-refresh script for HTML files
        if content_type == "text/html":
            refresh_script = """
<script>
// Auto-refresh when files change
(function() {
    let lastCheck = Date.now();
    setInterval(async () => {
        try {
            const response = await fetch('/__refresh_check?t=' + lastCheck);
            const data = await response.json();
            if (data.refresh) {
                location.reload();
            }
            lastCheck = Date.now();
        } catch (e) {}
    }, 2000);
})();
</script>
"""
            if "</body>" in content:
                content = content.replace("</body>", refresh_script + "</body>")
            else:
                content = content + refresh_script

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
            },
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/projects/{project_id}/stage")
async def get_project_stage(project_id: str) -> dict[str, Any]:
    """
    Get the current generation stage for a project.

    Args:
        project_id: The project identifier.

    Returns:
        Dict with stage information.
    """
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    flow_controller = get_flow_controller()
    stage = flow_controller.get_stage(project_id)
    files = flow_controller.get_generated_files(project_id)

    return {
        "project_id": project_id,
        "stage": stage.value,
        "files_generated": len(files) > 0,
        "files": [f.get("path", "") for f in files],
        "preview_ready": stage.value == "complete",
    }
