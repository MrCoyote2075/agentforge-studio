# AgentForge Studio - Architecture

## Overview

AgentForge Studio uses a multi-agent architecture where specialized AI agents collaborate to build complete websites.

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      AgentForge Studio                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Frontend   │  │   REST API   │  │  WebSocket   │          │
│  │   (React)    │  │   (FastAPI)  │  │   Handler    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────┐           │
│  │              Message Bus (Pub/Sub)               │           │
│  └────────────────────────┬────────────────────────┘           │
│                           │                                     │
│  ┌────────────────────────┼────────────────────────┐           │
│  │                        │                        │           │
│  │   ┌────────────────────┴───────────────────┐   │           │
│  │   │           Orchestrator Agent            │   │           │
│  │   └────────────────────┬───────────────────┘   │           │
│  │                        │                        │           │
│  │   ┌──────────┬────────┼────────┬──────────┐   │           │
│  │   │          │        │        │          │   │           │
│  │   ▼          ▼        ▼        ▼          ▼   │           │
│  │┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐│           │
│  ││Planner││Frontend││Backend││Reviewer││Tester││           │
│  │└──────┘ └──────┘ └──────┘ └──────┘ └──────┘│           │
│  │                        │                        │           │
│  │   ┌────────────────────┴───────────────────┐   │           │
│  │   │         Intermediator Agent             │   │           │
│  │   └─────────────────────────────────────────┘   │           │
│  │                                                 │           │
│  │                  Helper Agent                   │           │
│  │                                                 │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
│  ┌─────────────────────────────────────────────────┐           │
│  │           Workspace Manager                      │           │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐           │           │
│  │  │Project 1│ │Project 2│ │Project N│           │           │
│  │  └─────────┘ └─────────┘ └─────────┘           │           │
│  └─────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Roles

### Orchestrator Agent
- Coordinates all other agents
- Breaks down user requirements into tasks
- Manages workflow and dependencies
- Aggregates results from all agents

### Intermediator Agent
- Translates messages between agents
- Manages communication protocols
- Resolves conflicts between agent outputs
- Ensures message consistency

### Planner Agent
- Analyzes user requirements
- Creates detailed implementation plans
- Designs project architecture
- Defines task dependencies

### Frontend Agent
- Generates HTML/CSS/JavaScript
- Creates framework components (React/Vue/Angular)
- Implements responsive designs
- Manages frontend assets

### Backend Agent
- Creates API endpoints
- Designs database models
- Implements business logic
- Manages server configuration

### Reviewer Agent
- Reviews code quality
- Identifies potential bugs
- Suggests improvements
- Ensures best practices

### Tester Agent
- Generates unit tests
- Creates integration tests
- Runs test suites
- Reports coverage

### Helper Agent
- Provides utility functions
- Manages shared resources
- Handles common tasks
- Assists with data transformations

## Data Flow

1. User submits requirements via API/WebSocket
2. Orchestrator receives and analyzes requirements
3. Planner creates implementation plan
4. Tasks are distributed to specialized agents
5. Intermediator manages inter-agent communication
6. Frontend/Backend agents generate code
7. Reviewer validates generated code
8. Tester creates and runs tests
9. Results are aggregated and returned to user

## Communication

### Message Bus
- Pub/Sub pattern for loose coupling
- Priority-based message handling
- Topic-based subscriptions
- Message history tracking

### WebSocket
- Real-time updates to clients
- Topic-based subscriptions
- Bidirectional communication
- Connection management

## Storage

### Workspaces
- Isolated project directories
- Structured file organization
- Metadata tracking
- Version management
