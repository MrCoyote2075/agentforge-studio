# AgentForge Studio

AI-Powered Software Development Agency - Automated website building using a team of specialized AI agents.

## Overview

AgentForge Studio is a Python FastAPI-based platform that leverages multiple specialized AI agents to automatically build websites. Each agent has a specific role in the development process, from planning and frontend development to testing and review.

## Features

- **Multi-Agent Architecture**: Specialized AI agents work together to build complete websites
- **Real-time Communication**: WebSocket support for live updates during generation
- **Workspace Management**: Organized project workspaces with version control
- **RESTful API**: Comprehensive API for project management and code generation
- **Extensible Design**: Easy to add new agents and capabilities

## Architecture

### Agents

| Agent | Description |
|-------|-------------|
| **Orchestrator** | Coordinates all agents and manages the overall workflow |
| **Intermediator** | Facilitates communication between agents and handles message translation |
| **Planner** | Analyzes requirements and creates detailed implementation plans |
| **FrontendAgent** | Generates HTML, CSS, JavaScript, and framework components |
| **BackendAgent** | Creates API endpoints, database models, and server logic |
| **Reviewer** | Reviews generated code for quality, security, and best practices |
| **Tester** | Generates and runs unit, integration, and e2e tests |
| **Helper** | Provides utility functions and assistance to other agents |

### Core Modules

- **Config**: Application configuration management
- **MessageBus**: Pub/sub messaging system for inter-agent communication
- **WorkspaceManager**: Project workspace management and file operations

### API

- **Server**: FastAPI application with CORS and lifespan management
- **Routes**: RESTful endpoints for projects, tasks, and generation
- **WebSocket**: Real-time communication for live updates

## Getting Started

### Prerequisites

- Python 3.11+
- pip or poetry

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/agentforge-studio.git
   cd agentforge-studio
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. Run the server:
   ```bash
   uvicorn backend.api.server:app --reload
   ```

### API Documentation

Once running, access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
agentforge-studio/
├── backend/
│   ├── agents/               # AI Agents
│   │   ├── __init__.py
│   │   ├── base_agent.py     # Base agent class
│   │   ├── orchestrator.py   # Workflow coordinator
│   │   ├── intermediator.py  # Agent communication
│   │   ├── planner.py        # Requirements analysis
│   │   ├── frontend_agent.py # Frontend generation
│   │   ├── backend_agent.py  # Backend generation
│   │   ├── reviewer.py       # Code review
│   │   ├── tester.py         # Test generation
│   │   └── helper.py         # Utility functions
│   ├── core/                 # Core utilities
│   │   ├── __init__.py
│   │   ├── config.py         # Configuration
│   │   ├── message_bus.py    # Pub/sub messaging
│   │   └── workspace_manager.py # Workspace management
│   ├── api/                  # API layer
│   │   ├── __init__.py
│   │   ├── server.py         # FastAPI app
│   │   ├── routes.py         # REST endpoints
│   │   └── websocket.py      # WebSocket handlers
│   └── __init__.py
├── frontend/                 # Frontend application (TBD)
├── docs/                     # Documentation
├── workspaces/               # Generated project workspaces
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## API Endpoints

### Projects

- `POST /api/v1/projects` - Create a new project
- `GET /api/v1/projects` - List all projects
- `GET /api/v1/projects/{id}` - Get project details
- `DELETE /api/v1/projects/{id}` - Delete a project

### Tasks

- `POST /api/v1/projects/{id}/tasks` - Create a task
- `GET /api/v1/projects/{id}/tasks/{task_id}` - Get task status

### Generation

- `POST /api/v1/generate` - Start code generation
- `GET /api/v1/projects/{id}/files` - List generated files
- `GET /api/v1/projects/{id}/files/{path}` - Get file content

### Agents

- `GET /api/v1/agents` - List available agents

### WebSocket

- `WS /ws/connect/{client_id}` - Connect for real-time updates

## Development

### Running Tests

```bash
pytest tests/ -v --cov=backend
```

### Linting

```bash
ruff check backend/
black backend/
isort backend/
mypy backend/
```

### Type Checking

```bash
mypy backend/
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting a PR.
