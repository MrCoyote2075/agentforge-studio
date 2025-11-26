"""
AgentForge Studio - Helper Agent.

The Helper Agent handles auxiliary tasks such as documentation,
file organization, research, and other utility operations.
"""

from datetime import datetime
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.core.ai_clients.base_client import AIClientError
from backend.models.schemas import Message


class Helper(BaseAgent):
    """
    Helper Agent that handles utility tasks.

    The Helper Agent assists other agents by performing auxiliary
    tasks like documentation generation, file organization, research,
    and other supporting operations.

    Attributes:
        generated_docs: Dictionary of generated documentation.
        research_cache: Cache of research results.

    Example:
        >>> helper = Helper()
        >>> readme = await helper.generate_readme(project_info)
    """

    def __init__(
        self,
        name: str = "Helper",
        model: str = "gemini-pro",
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Helper agent.

        Args:
            name: The agent's name. Defaults to 'Helper'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._generated_docs: dict[str, str] = {}
        self._research_cache: dict[str, Any] = {}

    async def process(self, message: Message) -> Message:
        """
        Process a helper task request.

        Args:
            message: The incoming message with task details.

        Returns:
            Message: Response with task status.
        """
        await self._set_busy(f"Helping with: {message.content[:50]}")

        try:
            # Analyze the request and determine task type
            content = message.content.lower()

            if "readme" in content:
                result = await self.generate_readme({"description": message.content})
                response_content = f"README generated ({len(result)} chars)"
            elif "document" in content or "doc" in content:
                result = await self.generate_documentation(message.content)
                response_content = f"Documentation generated ({len(result)} chars)"
            elif "gitignore" in content:
                result = await self.create_gitignore("web")
                response_content = f".gitignore created ({len(result)} chars)"
            elif "package" in content and "json" in content:
                result = await self.create_package_json({"name": "project"})
                response_content = f"package.json created ({len(result)} chars)"
            else:
                # General help request
                response = await self.get_ai_response(
                    f"Help with the following request: {message.content}"
                )
                response_content = response

        except AIClientError as e:
            self.logger.error(f"AI helper task failed: {e}")
            response_content = (
                "I encountered an issue while processing your request. "
                "Please try again with more details."
            )
            await self._set_error(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected helper error: {e}")
            response_content = f"Helper error: {str(e)}"
            await self._set_error(str(e))

        await self._set_idle()

        return Message(
            from_agent=self.name,
            to_agent=message.from_agent,
            content=response_content,
            message_type="response",
            timestamp=datetime.utcnow(),
        )

    async def send_message(
        self,
        to_agent: str,
        content: str,
        message_type: str = "request",
    ) -> bool:
        """
        Send a message to another agent.

        Args:
            to_agent: Target agent name.
            content: Message content.
            message_type: Type of message.

        Returns:
            bool: True if sent successfully.
        """
        if not self._message_bus:
            self.logger.warning("No message bus configured")
            return False

        message = Message(
            from_agent=self.name,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            timestamp=datetime.utcnow(),
        )

        await self._log_activity("Sending message", f"To: {to_agent}")
        return True

    async def receive_message(self, message: Message) -> None:
        """
        Handle a received message.

        Args:
            message: The received message.
        """
        await self._log_activity(
            "Received message",
            f"From: {message.from_agent}",
        )

    async def generate_readme(self, project_info: dict[str, Any]) -> str:
        """
        Generate a README.md file for a project.

        Args:
            project_info: Dictionary with project information.

        Returns:
            str: Generated README content.
        """
        await self._set_busy("Generating README")

        try:
            name = project_info.get("name", "Project")
            description = project_info.get("description", "A new web project.")
            technologies = project_info.get(
                "technologies", ["HTML", "CSS", "JavaScript"]
            )
            features = project_info.get("features", [])

            default_tech = "HTML, CSS, JavaScript"
            tech_list = ", ".join(technologies) if technologies else default_tech
            feature_info = ""
            if features:
                feature_info = "Key features:\n" + "\n".join(
                    f"- {f.get('name', f) if isinstance(f, dict) else f}"
                    for f in features
                )

            prompt = f"""Create a professional README.md for this web project:

Project name: {name}
Description: {description}
Technologies: {tech_list}
{feature_info}

Include:
- Project title and description
- Features list
- Prerequisites and installation instructions
- Usage instructions
- Project structure
- Contributing guidelines
- License section (MIT)

Make it clear, well-formatted, and professional."""

            readme = await self.get_ai_response(prompt)

            # Clean up any markdown code blocks
            readme = readme.strip()
            if readme.startswith("```markdown"):
                readme = readme[11:]
            if readme.startswith("```"):
                readme = readme[3:]
            if readme.endswith("```"):
                readme = readme[:-3]
            readme = readme.strip()

            self._generated_docs["README.md"] = readme

        except Exception as e:
            self.logger.error(f"README generation failed: {e}")
            name = project_info.get("name", "Project")
            description = project_info.get("description", "A new project.")

            readme = f"""# {name}

{description}

## Features

- Modern, responsive design
- Clean and maintainable code
- Cross-browser compatible

## Getting Started

### Prerequisites

- A modern web browser
- (Optional) A local web server for development

### Installation

1. Clone the repository
2. Open `index.html` in your browser

## Usage

Open the project in your browser to view the website.

## Project Structure

```
project/
├── index.html
├── css/
│   └── styles.css
├── js/
│   └── script.js
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see LICENSE file for details
"""
            self._generated_docs["README.md"] = readme

        await self._set_idle()
        return readme

    async def generate_documentation(
        self,
        code: str,
        doc_type: str = "api",
    ) -> str:
        """
        Generate documentation for code.

        Args:
            code: The code to document.
            doc_type: Type of documentation (api, user, developer).

        Returns:
            str: Generated documentation.
        """
        await self._set_busy(f"Generating {doc_type} documentation")

        try:
            prompt = f"""Generate {doc_type} documentation for the following:

{code}

Create clear, well-structured documentation that includes:
- Overview/introduction
- Main sections based on the content
- Examples where appropriate
- Any important notes or warnings

Format as Markdown."""

            docs = await self.get_ai_response(prompt)

            # Clean up
            docs = docs.strip()
            if docs.startswith("```"):
                lines = docs.split("\n")
                docs = "\n".join(lines[1:-1])

            self._generated_docs[f"{doc_type}_docs.md"] = docs

        except Exception as e:
            self.logger.error(f"Documentation generation failed: {e}")
            docs = f"""# {doc_type.upper()} Documentation

## Overview

Documentation for the provided code/content.

## Details

{code[:500]}...

## Notes

This documentation was auto-generated.
"""
            self._generated_docs[f"{doc_type}_docs.md"] = docs

        await self._set_idle()
        return docs

    async def organize_files(
        self,
        file_list: list[str],
        structure: dict[str, list[str]],
    ) -> dict[str, str]:
        """
        Organize files according to a structure.

        Args:
            file_list: List of files to organize.
            structure: Target directory structure.

        Returns:
            Dict mapping original paths to new paths.
        """
        await self._set_busy("Organizing files")

        mappings: dict[str, str] = {}

        # Simple organization based on file extensions
        for file_path in file_list:
            ext = file_path.split(".")[-1].lower() if "." in file_path else ""

            if ext in ["html", "htm"]:
                mappings[file_path] = file_path  # Keep in root
            elif ext == "css":
                mappings[file_path] = f"css/{file_path.split('/')[-1]}"
            elif ext in ["js", "jsx", "ts", "tsx"]:
                mappings[file_path] = f"js/{file_path.split('/')[-1]}"
            elif ext in ["png", "jpg", "jpeg", "gif", "svg", "webp"]:
                mappings[file_path] = f"assets/images/{file_path.split('/')[-1]}"
            else:
                mappings[file_path] = file_path

        await self._set_idle()
        return mappings

    async def research_topic(self, topic: str) -> dict[str, Any]:
        """
        Research a topic for implementation guidance.

        Args:
            topic: The topic to research.

        Returns:
            Dict with research findings.
        """
        await self._set_busy(f"Researching: {topic}")

        # Check cache first
        if topic in self._research_cache:
            await self._set_idle()
            return self._research_cache[topic]

        try:
            prompt = f"""Research and summarize best practices for: {topic}

Provide:
1. Brief summary (2-3 sentences)
2. Key best practices (bullet points)
3. Common pitfalls to avoid
4. Recommended resources or approaches

Be concise and practical."""

            response = await self.get_ai_response(prompt)

            findings = {
                "topic": topic,
                "summary": response,
                "best_practices": [],
                "examples": [],
                "resources": [],
            }

            self._research_cache[topic] = findings

        except Exception as e:
            self.logger.error(f"Research failed: {e}")
            findings = {
                "topic": topic,
                "summary": f"Research on {topic} is pending.",
                "best_practices": [],
                "examples": [],
                "resources": [],
                "error": str(e),
            }

        await self._set_idle()
        return findings

    async def format_code(self, code: str, language: str) -> str:
        """
        Format code according to language standards.

        Args:
            code: The code to format.
            language: Programming language.

        Returns:
            str: Formatted code.
        """
        await self._set_busy(f"Formatting {language} code")

        try:
            prompt = f"""Format the following {language} code according to best practices and standards:

```{language}
{code}
```

Return only the formatted code, no explanations."""

            formatted = await self.get_ai_response(prompt)

            # Clean up
            formatted = formatted.strip()
            if formatted.startswith("```"):
                lines = formatted.split("\n")
                formatted = "\n".join(lines[1:-1])

            await self._set_idle()
            return formatted

        except Exception as e:
            self.logger.error(f"Code formatting failed: {e}")
            await self._set_idle()
            return code

    async def create_gitignore(self, project_type: str) -> str:
        """
        Create a .gitignore file for the project type.

        Args:
            project_type: Type of project (python, node, web, etc.).

        Returns:
            str: Generated .gitignore content.
        """
        await self._set_busy(f"Creating .gitignore for {project_type}")

        try:
            prompt = f"""Create a comprehensive .gitignore file for a {project_type} project.

Include common patterns for:
- Dependencies
- Build outputs
- IDE/editor files
- OS-specific files
- Environment files
- Logs

Return only the gitignore content, no explanations."""

            gitignore = await self.get_ai_response(prompt)

            # Clean up
            gitignore = gitignore.strip()
            if gitignore.startswith("```"):
                lines = gitignore.split("\n")
                gitignore = "\n".join(lines[1:-1])

            self._generated_docs[".gitignore"] = gitignore

        except Exception as e:
            self.logger.error(f"gitignore creation failed: {e}")
            gitignore = """# Dependencies
node_modules/
__pycache__/
venv/
.venv/

# Build outputs
dist/
build/
*.min.js
*.min.css

# IDE/Editor
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local
.env.*.local

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Cache
.cache/
.parcel-cache/
"""
            self._generated_docs[".gitignore"] = gitignore

        await self._set_idle()
        return gitignore

    async def create_package_json(self, project_info: dict[str, Any]) -> str:
        """
        Create a package.json file for a Node.js project.

        Args:
            project_info: Dictionary with project information.

        Returns:
            str: Generated package.json content.
        """
        await self._set_busy("Creating package.json")

        name = project_info.get("name", "project").lower().replace(" ", "-")
        description = project_info.get("description", "A web project")
        version = project_info.get("version", "1.0.0")

        package_json = f'''{{
  "name": "{name}",
  "version": "{version}",
  "description": "{description}",
  "main": "index.js",
  "scripts": {{
    "start": "http-server . -p 3000",
    "dev": "http-server . -p 3000 -c-1",
    "test": "echo \\"No tests specified\\" && exit 0"
  }},
  "keywords": [],
  "author": "",
  "license": "MIT",
  "devDependencies": {{
    "http-server": "^14.1.1"
  }}
}}'''

        self._generated_docs["package.json"] = package_json
        await self._set_idle()
        return package_json

    async def get_generated_docs(self) -> dict[str, str]:
        """
        Get all generated documentation.

        Returns:
            Dict mapping filenames to content.
        """
        return self._generated_docs.copy()

    def clear_generated_docs(self) -> None:
        """Clear all generated documentation."""
        self._generated_docs = {}
        self._research_cache = {}
