# AgentForge Studio - API Reference

## Overview

AgentForge Studio provides a RESTful API for project management and a WebSocket interface for real-time communication with agents.

**Base URL**: `http://localhost:8000`

## Authentication

> **Note**: Authentication is not yet implemented. This section will be updated when authentication is added.

Future authentication will use JWT tokens:
```
Authorization: Bearer <token>
```

## REST API Endpoints

### Health Check

#### `GET /`

Root endpoint for basic health check.

**Response**:
```json
{
    "service": "AgentForge Studio",
    "status": "healthy",
    "version": "0.1.0"
}
```

#### `GET /health`

Detailed health check including AI provider status.

**Response**:
```json
{
    "status": "healthy",
    "api": "running",
    "ai_providers": ["gemini", "openai"],
    "has_credentials": true
}
```

---

### Chat

#### `POST /api/chat`

Send a chat message to the Intermediator agent.

**Request Body**:
```json
{
    "message": "Build me a portfolio website",
    "project_id": "optional-project-id"
}
```

**Response**:
```json
{
    "message": "I'll coordinate the team to build your portfolio website. Let me ask a few questions...",
    "project_id": "generated-project-id",
    "agent_statuses": [
        {
            "name": "Intermediator",
            "status": "busy",
            "current_task": "Processing request"
        }
    ]
}
```

**Status Codes**:
- `200 OK`: Message processed successfully
- `404 Not Found`: Project ID doesn't exist

#### `GET /api/chat/{project_id}/history`

Get chat history for a project.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Maximum messages (1-200) |

**Response**:
```json
[
    {
        "content": "Build me a portfolio",
        "project_id": "proj-123",
        "role": "user",
        "timestamp": "2024-01-15T10:30:00Z"
    },
    {
        "content": "I'll help you build that!",
        "project_id": "proj-123",
        "role": "assistant",
        "timestamp": "2024-01-15T10:30:05Z"
    }
]
```

---

### Projects

#### `GET /api/projects`

List all projects.

**Response**:
```json
[
    {
        "id": "proj-123",
        "name": "Portfolio Website",
        "status": "in_progress",
        "requirements": "Build a portfolio with...",
        "files": ["index.html", "styles.css"],
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T12:30:00Z"
    }
]
```

#### `POST /api/projects`

Create a new project.

**Request Body**:
```json
{
    "name": "My Portfolio",
    "requirements": "I need a portfolio website with a hero section, about page, project gallery, and contact form."
}
```

**Response** (201 Created):
```json
{
    "id": "proj-456",
    "name": "My Portfolio",
    "status": "created",
    "requirements": "I need a portfolio website...",
    "files": [],
    "created_at": "2024-01-15T14:00:00Z"
}
```

**Status Codes**:
- `201 Created`: Project created successfully
- `400 Bad Request`: Project name already exists or validation failed

#### `GET /api/projects/{project_id}`

Get a specific project.

**Response**:
```json
{
    "id": "proj-123",
    "name": "Portfolio Website",
    "status": "in_progress",
    "requirements": "Build a portfolio with...",
    "files": ["index.html", "styles.css", "script.js"],
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T12:30:00Z"
}
```

**Status Codes**:
- `200 OK`: Project found
- `404 Not Found`: Project doesn't exist

#### `DELETE /api/projects/{project_id}`

Delete a project and its workspace.

**Status Codes**:
- `204 No Content`: Project deleted successfully
- `404 Not Found`: Project doesn't exist

#### `GET /api/projects/{project_id}/download`

Download project as a ZIP file.

**Response**: Binary ZIP file download

**Headers**:
```
Content-Type: application/zip
Content-Disposition: attachment; filename=My_Portfolio.zip
```

**Status Codes**:
- `200 OK`: Download started
- `404 Not Found`: Project or workspace not found
- `500 Internal Server Error`: ZIP creation failed

---

### Project Files

#### `GET /api/projects/{project_id}/files`

List files in a project.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | "" | Subdirectory path |
| `recursive` | bool | false | List files recursively |

**Response**:
```json
[
    {
        "name": "index.html",
        "path": "index.html",
        "type": "file",
        "size": 2048,
        "modified": "2024-01-15T12:30:00Z"
    },
    {
        "name": "css",
        "path": "css",
        "type": "directory"
    }
]
```

#### `GET /api/projects/{project_id}/files/{file_path}`

Get file content.

**Response**:
```json
{
    "path": "index.html",
    "content": "<!DOCTYPE html>\n<html>..."
}
```

**Status Codes**:
- `200 OK`: File found
- `404 Not Found`: File doesn't exist

---

### Git Operations

#### `GET /api/projects/{project_id}/git/status`

Get Git status for a project.

**Response**:
```json
{
    "modified": ["styles.css"],
    "added": ["script.js"],
    "deleted": [],
    "untracked": ["new-file.txt"],
    "clean": false
}
```

#### `GET /api/projects/{project_id}/git/log`

Get Git commit log.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Maximum commits (1-100) |

**Response**:
```json
[
    {
        "hash": "abc123def456...",
        "author_name": "AgentForge Studio",
        "author_email": "agentforge@studio.local",
        "timestamp": "2024-01-15T12:30:00Z",
        "message": "Add navigation component"
    }
]
```

---

## WebSocket API

### Connection

#### `ws://localhost:8000/ws`

General WebSocket connection.

#### `ws://localhost:8000/ws/project/{project_id}`

Project-specific WebSocket connection with automatic subscription.

### Message Format

All WebSocket messages use JSON:

```json
{
    "type": "message_type",
    "payload": {}
}
```

### Client → Server Messages

#### Ping

```json
{
    "type": "ping"
}
```

#### Subscribe to Project

```json
{
    "type": "subscribe",
    "project_id": "proj-123"
}
```

#### Send Chat Message

```json
{
    "type": "chat",
    "content": "Build me a website",
    "project_id": "proj-123"
}
```

### Server → Client Messages

#### Connected

Sent immediately after connection:

```json
{
    "type": "connected",
    "connection_id": "conn-abc123",
    "project_id": "proj-123",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Pong

Response to ping:

```json
{
    "type": "pong",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Subscribed

Confirmation of project subscription:

```json
{
    "type": "subscribed",
    "project_id": "proj-123"
}
```

#### Chat Response

Response to chat message:

```json
{
    "type": "chat_response",
    "content": "I'll help you build that website!",
    "project_id": "proj-123",
    "timestamp": "2024-01-15T10:30:05Z"
}
```

#### Agent Status Update

Broadcast when agent status changes:

```json
{
    "type": "agent_status",
    "agents": [
        {
            "name": "FrontendAgent",
            "status": "busy",
            "current_task": "Building homepage"
        }
    ]
}
```

#### File Update

Broadcast when project files change:

```json
{
    "type": "file_update",
    "project_id": "proj-123",
    "action": "created",
    "path": "index.html"
}
```

#### Error

Error message:

```json
{
    "type": "error",
    "message": "Invalid message format"
}
```

---

## Error Responses

All errors follow this format:

```json
{
    "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Input validation failed |
| 500 | Internal Server Error |

### Validation Error Example

```json
{
    "detail": [
        {
            "loc": ["body", "name"],
            "msg": "ensure this value has at least 1 characters",
            "type": "value_error.any_str.min_length"
        }
    ]
}
```

---

## Rate Limiting

> **Note**: Rate limiting is not yet implemented.

Future rate limits:
- 100 requests per minute for REST endpoints
- 50 messages per minute for WebSocket

---

## SDK Examples

### Python

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Create project
        response = await client.post("/api/projects", json={
            "name": "My Website",
            "requirements": "Build a landing page"
        })
        project = response.json()
        print(f"Created project: {project['id']}")
        
        # Chat with agent
        response = await client.post("/api/chat", json={
            "message": "Add a contact form",
            "project_id": project["id"]
        })
        print(f"Agent response: {response.json()['message']}")

asyncio.run(main())
```

### JavaScript

```javascript
// REST API
const response = await fetch('http://localhost:8000/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        name: 'My Website',
        requirements: 'Build a landing page'
    })
});
const project = await response.json();

// WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/project/${project.id}`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'chat',
        content: 'Add a contact form',
        project_id: project.id
    }));
};
```

---

## OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`
