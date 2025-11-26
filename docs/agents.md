# AgentForge Studio - Agent Documentation

## Overview

AgentForge Studio uses a team of specialized AI agents that collaborate to build software projects. Each agent has a specific role and expertise, working together like a real development team.

## Agent Hierarchy

```
                    ┌─────────────────┐
                    │  Intermediator  │ ◄── User Communication
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Orchestrator  │ ◄── Coordination
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌────────▼────────┐   ┌───────▼───────┐
│    Planner    │   │     Helper      │   │   Reviewer    │
│  (Architect)  │   │   (Utility)     │   │    (QA)       │
└───────┬───────┘   └─────────────────┘   └───────────────┘
        │
        │ Specifications
        │
┌───────▼───────────────────┐
│                           │
▼                           ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Frontend    │   │   Backend     │   │    Tester     │
│    Agent      │   │    Agent      │   │    Agent      │
└───────────────┘   └───────────────┘   └───────────────┘
```

## Agent Details

### Intermediator

**Role**: Client Liaison

**Responsibilities**:
- Single point of contact for all user communication
- Translates natural language requirements into technical specifications
- Presents technical progress in user-friendly terms
- Manages user expectations and provides updates

**Capabilities**:
- Natural language understanding
- Requirement extraction
- Progress summarization
- Clarifying questions

**Example Interaction**:
```
User: "I want a portfolio website with a modern look"

Intermediator: "I'd be happy to help you create a portfolio website! 
Let me understand your needs better:
- Would you like sections for About Me, Projects, and Contact?
- Do you have any color preferences?
- Should it include a blog section?

I'll coordinate with our development team to bring your vision to life."
```

### Orchestrator

**Role**: Project Manager

**Responsibilities**:
- Coordinates all agent activities
- Creates and assigns tasks
- Manages dependencies between tasks
- Tracks progress and handles failures
- Ensures project completion

**Capabilities**:
- Task decomposition
- Agent assignment
- Dependency resolution
- Progress monitoring
- Error recovery

**Task Distribution Example**:
```python
# Orchestrator breaks down a project
tasks = [
    Task(id="1", description="Create specifications", assigned_to="Planner"),
    Task(id="2", description="Build HTML structure", assigned_to="FrontendAgent", dependencies=["1"]),
    Task(id="3", description="Create CSS styles", assigned_to="FrontendAgent", dependencies=["1"]),
    Task(id="4", description="Add interactivity", assigned_to="FrontendAgent", dependencies=["2", "3"]),
    Task(id="5", description="Review code", assigned_to="Reviewer", dependencies=["4"]),
    Task(id="6", description="Write tests", assigned_to="Tester", dependencies=["4"]),
]
```

### Planner

**Role**: System Architect

**Responsibilities**:
- Analyzes project requirements
- Creates technical specifications
- Designs file structure
- Defines component architecture
- Creates implementation roadmap

**Outputs**:
- Technical specification document
- File structure diagram
- Component breakdown
- Task sequence
- Technology recommendations

**Specification Example**:
```json
{
  "project_name": "Portfolio Website",
  "technologies": ["HTML5", "CSS3", "JavaScript"],
  "components": [
    {"name": "Hero", "type": "section", "features": ["animated background"]},
    {"name": "About", "type": "section", "features": ["profile image"]},
    {"name": "Projects", "type": "gallery", "features": ["filtering", "modal"]},
    {"name": "Contact", "type": "form", "features": ["validation"]}
  ],
  "file_structure": {
    "src/": ["index.html", "styles.css", "script.js"],
    "src/assets/": ["images/", "fonts/"]
  }
}
```

### Frontend Agent

**Role**: UI Developer

**Responsibilities**:
- Creates HTML structure
- Writes CSS styles
- Implements JavaScript functionality
- Builds React components (when applicable)
- Ensures responsive design
- Follows accessibility best practices

**Capabilities**:
- HTML5 semantic markup
- CSS3 with Flexbox/Grid
- Vanilla JavaScript
- React components
- Responsive design
- Animation effects

**Generated Code Example**:
```html
<!-- Hero Section -->
<section class="hero">
    <div class="hero-content">
        <h1 class="hero-title">John Doe</h1>
        <p class="hero-subtitle">Full Stack Developer</p>
        <a href="#contact" class="btn btn-primary">Get in Touch</a>
    </div>
</section>
```

### Backend Agent

**Role**: Server Developer

**Responsibilities**:
- Creates API endpoints
- Designs database schemas
- Implements business logic
- Sets up authentication
- Handles server configuration

**Capabilities**:
- RESTful API design
- Database modeling
- Authentication/authorization
- Input validation
- Error handling

**Generated Code Example**:
```python
@router.post("/contact")
async def submit_contact(form: ContactForm):
    """
    Handle contact form submission.
    """
    # Validate input
    if not form.email or not form.message:
        raise HTTPException(400, "Email and message required")
    
    # Process submission
    await send_notification(form)
    
    return {"status": "success", "message": "Thank you for your message!"}
```

### Reviewer

**Role**: Code Reviewer

**Responsibilities**:
- Reviews code quality
- Identifies potential issues
- Suggests improvements
- Checks security vulnerabilities
- Ensures best practices

**Review Categories**:
- **Security**: XSS, injection, secrets
- **Performance**: Optimization opportunities
- **Maintainability**: Code organization, naming
- **Best Practices**: Standards compliance

**Review Output Example**:
```json
{
  "file": "script.js",
  "findings": [
    {
      "line": 15,
      "severity": "warning",
      "message": "Consider using const instead of let for unchanging values",
      "suggestion": "const API_URL = 'https://api.example.com'"
    },
    {
      "line": 42,
      "severity": "error",
      "message": "Potential XSS vulnerability - unsanitized input",
      "suggestion": "Use textContent instead of innerHTML"
    }
  ]
}
```

### Tester

**Role**: QA Engineer

**Responsibilities**:
- Writes unit tests
- Creates integration tests
- Validates functionality
- Reports bugs
- Generates test coverage

**Capabilities**:
- Unit testing
- Integration testing
- End-to-end testing
- Test automation
- Coverage reporting

**Test Example**:
```javascript
describe('Contact Form', () => {
    it('should validate email format', () => {
        const form = new ContactForm();
        expect(form.isValidEmail('test@example.com')).toBe(true);
        expect(form.isValidEmail('invalid')).toBe(false);
    });
    
    it('should submit successfully with valid data', async () => {
        const response = await submitForm({
            email: 'test@example.com',
            message: 'Hello!'
        });
        expect(response.status).toBe('success');
    });
});
```

### Helper

**Role**: Utility Agent

**Responsibilities**:
- Generates documentation
- Organizes files
- Conducts research
- Formats code
- Creates configuration files

**Capabilities**:
- README generation
- API documentation
- Code formatting
- .gitignore creation
- Research summaries

**Documentation Example**:
```markdown
# Portfolio Website

A modern, responsive portfolio website built with HTML, CSS, and JavaScript.

## Features

- Responsive design for all devices
- Smooth scroll navigation
- Project gallery with filtering
- Contact form with validation
- Dark/light mode toggle

## Getting Started

1. Clone the repository
2. Open `index.html` in your browser

## Project Structure

```
src/
├── index.html      # Main HTML file
├── styles.css      # Stylesheets
├── script.js       # JavaScript functionality
└── assets/         # Images and fonts
```
```

## Agent Communication

### Message Format

Agents communicate using the `Message` schema:

```python
Message(
    from_agent="Orchestrator",
    to_agent="FrontendAgent",
    content="Build the hero section with animation",
    message_type="request",
    metadata={
        "task_id": "task-001",
        "priority": "high"
    }
)
```

### Message Types

| Type | Description | Example |
|------|-------------|---------|
| `request` | Task assignment or information request | "Build the navbar" |
| `response` | Reply to a request | "Navbar completed" |
| `notification` | Status update or event | "Task 50% complete" |
| `error` | Error report | "Failed to parse HTML" |
| `status` | Agent status update | "Going idle" |

## Agent States

| State | Description |
|-------|-------------|
| `idle` | Ready for new tasks |
| `busy` | Currently processing a task |
| `waiting` | Waiting for dependencies |
| `error` | Encountered an error |
| `offline` | Not available |

## Extending Agents

To create a custom agent:

```python
from backend.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    """Custom agent for specific tasks."""
    
    def __init__(self):
        super().__init__(
            name="CustomAgent",
            model="gemini-pro"
        )
    
    async def process(self, message):
        # Implement your logic
        result = await self.do_work(message.content)
        
        return Message(
            from_agent=self.name,
            to_agent=message.from_agent,
            content=result,
            message_type="response"
        )
```

## Best Practices

1. **Single Responsibility**: Each agent focuses on one domain
2. **Clear Communication**: Use structured messages
3. **Error Handling**: Report errors through proper channels
4. **Logging**: Log activities for debugging
5. **State Management**: Keep track of agent status
