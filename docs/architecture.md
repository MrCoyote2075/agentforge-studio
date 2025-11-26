# AgentForge Studio - Architecture

## Overview

AgentForge Studio is built on a multi-agent architecture where specialized AI agents collaborate to build software projects. The system uses an event-driven design with asynchronous message passing for inter-agent communication.

## System Components

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           AgentForge Studio                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐         ┌─────────────────┐                          │
│  │   Web Client   │◄───────►│   API Server    │                          │
│  │   (React App)  │   REST  │   (FastAPI)     │                          │
│  └───────┬────────┘   +WS   └────────┬────────┘                          │
│          │                           │                                   │
│          │                   ┌───────▼────────┐                          │
│          │                   │  Intermediator │                          │
│          └──────WebSocket───►│     Agent      │                          │
│                              └───────┬────────┘                          │
│                                      │                                   │
│                              ┌───────▼────────┐                          │
│                              │  Orchestrator  │                          │
│                              └───────┬────────┘                          │
│                                      │                                   │
│                     ┌────────────────┼────────────────┐                  │
│                     │         Message Bus             │                  │
│                     └────────────────┬────────────────┘                  │
│                                      │                                   │
│         ┌──────────┬─────────────────┼─────────────────┬───────────┐     │
│         │          │                 │                 │           │     │
│         ▼          ▼                 ▼                 ▼           ▼     │
│   ┌──────────┐ ┌────────┐     ┌───────────┐    ┌──────────┐ ┌──────────┐ │
│   │ Planner  │ │Frontend│     │  Backend  │    │ Reviewer │ │  Tester  │ │
│   │  Agent   │ │ Agent  │     │   Agent   │    │  Agent   │ │  Agent   │ │
│   └──────────┘ └────────┘     └───────────┘    └──────────┘ └──────────┘ │
│         │          │                 │                 │           │     │
│         └──────────┴─────────────────┼─────────────────┴───────────┘     │
│                                      │                                   │
│                              ┌───────▼────────┐                          │
│                              │    Workspace   │                          │
│                              │    Manager     │                          │
│                              └───────┬────────┘                          │
│                                      │                                   │
│                     ┌────────────────┼────────────────┐                  │
│                     │                │                │                  │
│                     ▼                ▼                ▼                  │
│              ┌───────────┐   ┌─────────────┐   ┌──────────────┐          │
│              │ Git Repo  │   │ Project     │   │   Preview    │          │
│              │           │   │ Files       │   │   Server     │          │
│              └───────────┘   └─────────────┘   └──────────────┘          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### API Layer

#### FastAPI Server (`backend/api/server.py`)
- Main application entry point
- CORS middleware configuration
- Health check endpoints
- Router mounting

#### REST Routes (`backend/api/routes.py`)
- `/api/chat` - Chat with the Intermediator agent
- `/api/projects` - Project CRUD operations
- `/api/projects/{id}/files` - File management
- `/api/projects/{id}/download` - Export project as ZIP

#### WebSocket Handler (`backend/api/websocket.py`)
- Real-time bidirectional communication
- Project-specific subscriptions
- Agent status updates
- Chat streaming

### Agent Layer

#### Base Agent (`backend/agents/base_agent.py`)
- Abstract base class for all agents
- Common properties: name, model, status
- Message sending/receiving interface
- Logging functionality

#### Intermediator Agent
- Single point of contact for users
- Natural language understanding
- Requirement translation
- Progress reporting

#### Orchestrator Agent
- Coordinates all agent activities
- Task creation and assignment
- Dependency management
- Progress tracking

#### Specialized Agents
- **Planner**: Creates technical specifications
- **Frontend Agent**: Generates UI components
- **Backend Agent**: Creates server-side code
- **Reviewer**: Performs code review
- **Tester**: Writes and runs tests
- **Helper**: Handles utility tasks

### Core Layer

#### Message Bus (`backend/core/message_bus.py`)
- Pub/sub pattern implementation
- Async message delivery
- Topic-based routing
- Direct agent messaging

#### Workspace Manager (`backend/core/workspace_manager.py`)
- File CRUD operations
- Directory management
- File locking
- Project isolation

#### Git Manager (`backend/core/git_manager.py`)
- Repository initialization
- Commit management
- Branch operations
- History tracking

#### Preview Server (`backend/core/preview_server.py`)
- HTTP file serving
- Auto-refresh support
- File change watching
- Project switching

#### Config (`backend/core/config.py`)
- Environment variable loading
- Settings management
- Path configuration
- API key management

### Data Layer

#### Pydantic Schemas (`backend/models/schemas.py`)
- `Message`: Inter-agent messages
- `Task`: Work units for agents
- `Project`: Project metadata
- `AgentStatus`: Agent state
- `ChatMessage`: User conversations

## Data Flow

### User Request Flow

```
User → HTTP Request → FastAPI → Intermediator → Orchestrator
                                                      ↓
                                              [Task Distribution]
                                                      ↓
                                    Planner → Frontend → Backend
                                                      ↓
                                              [Code Generation]
                                                      ↓
                                    Reviewer → Tester → Helper
                                                      ↓
                                              [Quality Check]
                                                      ↓
                                              Workspace Files
                                                      ↓
User ← WebSocket Update ← Intermediator ← Orchestrator
```

### Message Flow

```
Agent A                    Message Bus                    Agent B
   │                           │                             │
   │── Publish(topic, msg) ───►│                             │
   │                           │── Deliver(msg) ────────────►│
   │                           │                             │
   │                           │◄── Response(msg) ───────────│
   │◄── Receive(msg) ─────────│                             │
   │                           │                             │
```

## Technology Stack

### Backend
- **Python 3.10+**: Core language
- **FastAPI**: Web framework
- **Pydantic**: Data validation
- **aiofiles**: Async file I/O
- **uvicorn**: ASGI server

### AI Integration
- **Google Gemini API**: Primary AI model
- **OpenAI API**: Alternative provider
- **Anthropic API**: Additional capability

### Frontend (Planned)
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **WebSocket**: Real-time updates

## Security Considerations

1. **API Key Management**: Keys stored in environment variables, never in code
2. **Input Validation**: Pydantic models validate all inputs
3. **Path Traversal Prevention**: Workspace manager sanitizes paths
4. **CORS Configuration**: Configurable for production
5. **WebSocket Authentication**: Token-based (planned)

## Scalability

The architecture supports:
- Multiple concurrent projects
- Parallel agent operations
- Horizontal scaling of API servers
- Distributed message bus (future)

## Future Enhancements

1. **Database Integration**: Persistent storage for projects and history
2. **Agent Learning**: Improve based on feedback
3. **Plugin System**: Custom agent extensions
4. **Multi-tenant Support**: Isolated user workspaces
5. **Distributed Processing**: Run agents on separate nodes
