# AgentForge Studio

> **AI-Powered Software Development Agency**

Automate website building using a team of specialized AI agents. A human client communicates with ONE intermediary agent, which coordinates multiple AI agents working together like a real development team.

## 🚀 Vision

AgentForge Studio reimagines software development by orchestrating a team of specialized AI agents that collaborate like a real development agency. Each agent has distinct expertise, from project planning to frontend development, backend architecture, code review, and testing.

## ✨ Features

- **Single Point of Contact**: Communicate with one Intermediator agent who manages your entire project
- **Specialized AI Agents**: Each agent is expert in their domain (frontend, backend, review, testing)
- **Real-time Collaboration**: Agents communicate via a message bus, sharing context and coordinating work
- **Live Preview**: See your website come to life with automatic preview updates
- **Version Control**: Built-in Git integration for tracking all changes
- **Project Management**: Track tasks, dependencies, and progress across all agents
- **WebSocket Updates**: Real-time status updates and chat interface
- **Extensible Architecture**: Easy to add new agents or customize existing ones

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AgentForge Studio                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐                                                    │
│  │   Client    │◄──────── WebSocket ────────►┌──────────────┐      │
│  │  (Browser)  │                              │  API Server  │      │
│  └─────────────┘                              └──────┬───────┘      │
│                                                      │              │
│                                              ┌───────▼───────┐      │
│                                              │ Intermediator │      │
│                                              │    Agent      │      │
│                                              └───────┬───────┘      │
│                                                      │              │
│                                              ┌───────▼───────┐      │
│                                              │  Orchestrator │      │
│                                              └───────┬───────┘      │
│                                                      │              │
│              ┌───────────────────────────────────────┼───────┐      │
│              │                Message Bus            │       │      │
│              │◄──────────────────────────────────────┼──────►│      │
│              └───────────────────────────────────────┼───────┘      │
│                              │                       │              │
│         ┌────────────────────┼───────────────────────┼──────┐       │
│         ▼                    ▼                       ▼      ▼       │
│  ┌───────────┐       ┌───────────┐           ┌──────────┐ ┌──────┐  │
│  │  Planner  │       │ Frontend  │           │ Backend  │ │Helper│  │
│  │   Agent   │       │   Agent   │           │  Agent   │ │Agent │  │
│  └───────────┘       └───────────┘           └──────────┘ └──────┘  │
│         │                    │                       │              │
│         └────────────────────┼───────────────────────┘              │
│                              ▼                                      │
│                     ┌─────────────────┐                             │
│                     │ Workspace Files │                             │
│                     └────────┬────────┘                             │
│                              │                                      │
│              ┌───────────────┼───────────────┐                      │
│              ▼               ▼               ▼                      │
│       ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│       │ Reviewer │    │  Tester  │    │ Preview  │                  │
│       │  Agent   │    │  Agent   │    │  Server  │                  │
│       └──────────┘    └──────────┘    └──────────┘                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🤖 Agent Team

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **Intermediator** | Client Liaison | Single point of contact for client communication. Translates requirements and reports progress. |
| **Orchestrator** | Project Manager | Coordinates all agents, manages task distribution, and ensures project completion. |
| **Planner** | Architect | Breaks down requirements into technical specifications and creates project roadmap. |
| **Frontend Agent** | UI Developer | Creates HTML, CSS, JavaScript, and React components for the user interface. |
| **Backend Agent** | Server Developer | Builds APIs, database schemas, and server-side logic. |
| **Reviewer** | Code Reviewer | Reviews code quality, suggests improvements, and ensures best practices. |
| **Tester** | QA Engineer | Writes and runs tests, validates functionality, and reports bugs. |
| **Helper** | Utility Agent | Handles auxiliary tasks like documentation, file organization, and research. |

## 🛠️ Tech Stack

### Backend
- **Python 3.10+**: Core programming language
- **FastAPI**: High-performance async web framework
- **WebSockets**: Real-time bidirectional communication
- **Pydantic**: Data validation and serialization

### AI Integration
- **Google Gemini API**: Primary AI model for agents
- **OpenAI API**: Alternative AI provider
- **Anthropic Claude API**: Additional AI capabilities

### Frontend (Planned)
- **React**: Modern UI framework
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first styling

### Infrastructure
- **Git**: Version control for generated projects
- **HTTP Preview Server**: Live website preview
- **Async I/O**: Non-blocking file operations

## 📁 Project Structure

```
agentforge-studio/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── pyproject.toml        # Python project configuration
├── backend/
│   ├── __init__.py
│   ├── main.py           # Application entry point
│   ├── agents/           # AI agent implementations
│   │   ├── base_agent.py
│   │   ├── orchestrator.py
│   │   ├── intermediator.py
│   │   ├── planner.py
│   │   ├── frontend_agent.py
│   │   ├── backend_agent.py
│   │   ├── reviewer.py
│   │   ├── tester.py
│   │   └── helper.py
│   ├── core/             # Core utilities
│   │   ├── message_bus.py
│   │   ├── workspace_manager.py
│   │   ├── git_manager.py
│   │   ├── preview_server.py
│   │   └── config.py
│   ├── api/              # REST & WebSocket API
│   │   ├── server.py
│   │   ├── routes.py
│   │   └── websocket.py
│   └── models/           # Data models
│       └── schemas.py
├── frontend/             # React frontend (future)
├── workspaces/           # Generated project files
├── outputs/              # Exported projects
└── docs/                 # Documentation
    ├── architecture.md
    ├── agents.md
    ├── workflow.md
    └── api.md
```

## 🚦 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/MrCoyote2075/agentforge-studio.git
   cd agentforge-studio
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the development server**
   ```bash
   python -m backend.main
   ```

6. **Access the API**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Preview Server: http://localhost:8080

## 📖 Documentation

- [Architecture Guide](docs/architecture.md) - System design and component overview
- [Agent Documentation](docs/agents.md) - Detailed agent roles and capabilities
- [Workflow Guide](docs/workflow.md) - Development process and stages
- [API Reference](docs/api.md) - REST and WebSocket API documentation

## 🔧 Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black backend/
isort backend/
```

### Type Checking
```bash
mypy backend/
```

## 🗺️ Roadmap

- [x] Project structure and base architecture
- [ ] Core agent implementations
- [ ] Message bus and agent communication
- [ ] Workspace and file management
- [ ] Git integration
- [ ] REST API endpoints
- [ ] WebSocket real-time updates
- [ ] Live preview server
- [ ] React frontend dashboard
- [ ] Multi-project support
- [ ] Agent learning and improvement

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI, Google, and Anthropic for their powerful AI APIs
- The FastAPI team for the excellent framework
- The open-source community for inspiration and tools

---

<p align="center">
  Built with ❤️ by the AgentForge Studio Team
</p>
