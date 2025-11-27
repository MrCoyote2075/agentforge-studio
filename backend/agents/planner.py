"""
AgentForge Studio - Planner Agent.

The Planner agent is responsible for architectural decisions and
project roadmap creation. It breaks down high-level requirements
into detailed technical specifications and task sequences.
"""

import json
from datetime import datetime
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.core.ai_clients.base_client import AIClientError
from backend.models.schemas import Message, Task


class Planner(BaseAgent):
    """
    Planner agent that handles project architecture and planning.

    The Planner analyzes project requirements and creates detailed
    technical specifications, file structures, and implementation
    roadmaps that guide other agents in their work.

    Attributes:
        project_specs: Current project specifications.
        file_structure: Planned file structure for the project.

    Example:
        >>> planner = Planner()
        >>> specs = await planner.create_specification(requirements)
    """

    def __init__(
        self,
        name: str = "Planner",
        model: str = "gemini-pro",
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Planner agent.

        Args:
            name: The agent's name. Defaults to 'Planner'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._project_specs: dict[str, Any] = {}
        self._file_structure: dict[str, list[str]] = {}

    async def process(self, message: Message) -> Message:
        """
        Process an incoming planning request.

        Args:
            message: The incoming message containing requirements.

        Returns:
            Message: Response with planning status or specifications.
        """
        await self._set_busy(f"Planning: {message.content[:50]}")

        try:
            # Create specification from requirements
            specs = await self.create_specification(message.content)

            response_content = json.dumps(specs, indent=2)

        except AIClientError as e:
            self.logger.error(f"AI planning failed: {e}")
            response_content = (
                "I encountered an issue while planning. "
                "Please provide more details about the project requirements."
            )
            await self._set_error(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected planning error: {e}")
            response_content = f"Planning error: {str(e)}"
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

    async def create_specification(self, requirements: str) -> dict[str, Any]:
        """
        Create detailed technical specifications from requirements.

        Args:
            requirements: High-level project requirements.

        Returns:
            Dict containing technical specifications.
        """
        await self._set_busy("Creating specifications")

        try:
            prompt = f"""Based on the following project requirements, create a detailed technical specification.

Requirements:
{requirements}

Create a JSON specification with the following structure:
{{
    "project_name": "descriptive project name",
    "description": "brief project description",
    "technologies": ["HTML5", "CSS3", "JavaScript"],
    "file_structure": {{
        "root": ["index.html", "README.md"],
        "css": ["styles.css"],
        "js": ["script.js"],
        "assets/images": []
    }},
    "pages": [
        {{
            "name": "Home",
            "file": "index.html",
            "description": "Main landing page",
            "components": ["header", "hero", "features", "footer"]
        }}
    ],
    "features": [
        {{
            "name": "Responsive Navigation",
            "description": "Mobile-friendly navigation menu",
            "priority": "high"
        }}
    ],
    "design_guidelines": {{
        "color_scheme": "professional blue and white",
        "typography": "system fonts",
        "layout": "clean and modern"
    }},
    "tasks": [
        {{
            "id": "task-1",
            "description": "Create HTML structure",
            "assigned_to": "FrontendAgent",
            "dependencies": [],
            "estimated_complexity": "medium"
        }}
    ]
}}

Return only valid JSON, no additional text or markdown formatting."""

            response = await self.get_ai_response(prompt)

            # Clean up response - remove markdown code blocks if present
            clean_response = self._clean_code_response(response, "json")

            # Parse JSON
            try:
                specs = json.loads(clean_response)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse AI response as JSON: {e}")
                specs = {
                    "requirements": requirements,
                    "technologies": ["HTML5", "CSS3", "JavaScript"],
                    "components": [],
                    "data_models": [],
                    "api_endpoints": [],
                    "ui_pages": [],
                    "raw_response": response[:500],
                    "parse_error": str(e),
                }

            self._project_specs = specs

        except AIClientError as e:
            self.logger.error(f"AI specification generation failed: {e}")
            specs = {
                "requirements": requirements,
                "technologies": ["HTML5", "CSS3", "JavaScript"],
                "components": [],
                "error": str(e),
            }
        except Exception as e:
            self.logger.error(f"Unexpected specification error: {e}")
            specs = {
                "requirements": requirements,
                "technologies": [],
                "error": str(e),
            }

        await self._set_idle()
        return specs

    async def define_file_structure(
        self, specs: dict[str, Any]
    ) -> dict[str, list[str]]:
        """
        Define the project file structure based on specifications.

        Args:
            specs: Technical specifications.

        Returns:
            Dict mapping directories to file lists.
        """
        await self._set_busy("Defining file structure")

        # If specs already contain file_structure, use it
        if "file_structure" in specs:
            self._file_structure = specs["file_structure"]
            await self._set_idle()
            return self._file_structure

        try:
            prompt = f"""Based on these project specifications, define the file structure.

Specifications:
{json.dumps(specs, indent=2)}

Return a JSON object mapping directory paths to lists of files:
{{
    "root": ["index.html", "README.md"],
    "css": ["styles.css", "responsive.css"],
    "js": ["script.js", "utils.js"],
    "assets/images": ["logo.png"]
}}

Return only valid JSON."""

            response = await self.get_ai_response(prompt)

            # Clean and parse
            clean_response = self._clean_code_response(response, "json")

            try:
                structure = json.loads(clean_response)
            except json.JSONDecodeError:
                structure = {
                    "root": ["index.html", "README.md"],
                    "css": ["styles.css"],
                    "js": ["script.js"],
                    "assets/images": [],
                }

            self._file_structure = structure

        except Exception as e:
            self.logger.error(f"Failed to define file structure: {e}")
            structure = {
                "root": ["index.html", "styles.css", "script.js"],
                "assets": [],
            }

        await self._set_idle()
        return structure

    async def create_roadmap(self, specs: dict[str, Any]) -> list[Task]:
        """
        Create an implementation roadmap from specifications.

        Args:
            specs: Technical specifications.

        Returns:
            List of tasks in execution order.
        """
        await self._set_busy("Creating roadmap")

        tasks: list[Task] = []

        # If specs contain tasks, convert them
        if "tasks" in specs:
            for task_data in specs["tasks"]:
                task = Task(
                    id=task_data.get("id", f"task-{len(tasks) + 1}"),
                    description=task_data.get("description", ""),
                    assigned_to=task_data.get("assigned_to"),
                    dependencies=task_data.get("dependencies", []),
                )
                tasks.append(task)
            await self._set_idle()
            return tasks

        try:
            prompt = f"""Based on these specifications, create a task list for implementation.

Specifications:
{json.dumps(specs, indent=2)}

Return a JSON array of tasks:
[
    {{
        "id": "task-1",
        "description": "Set up project structure and create base HTML file",
        "assigned_to": "FrontendAgent",
        "dependencies": [],
        "estimated_complexity": "low"
    }},
    {{
        "id": "task-2",
        "description": "Create CSS styles",
        "assigned_to": "FrontendAgent",
        "dependencies": ["task-1"],
        "estimated_complexity": "medium"
    }}
]

Assign tasks to: FrontendAgent (HTML/CSS/JS), BackendAgent (APIs), Helper (docs)
Return only valid JSON array."""

            response = await self.get_ai_response(prompt)

            # Clean and parse
            clean_response = self._clean_code_response(response, "json")

            try:
                task_list = json.loads(clean_response)
                for task_data in task_list:
                    task = Task(
                        id=task_data.get("id", f"task-{len(tasks) + 1}"),
                        description=task_data.get("description", ""),
                        assigned_to=task_data.get("assigned_to"),
                        dependencies=task_data.get("dependencies", []),
                    )
                    tasks.append(task)
            except json.JSONDecodeError:
                # Create default tasks
                tasks = [
                    Task(
                        id="task-1",
                        description="Create HTML structure",
                        assigned_to="FrontendAgent",
                    ),
                    Task(
                        id="task-2",
                        description="Create CSS styles",
                        assigned_to="FrontendAgent",
                        dependencies=["task-1"],
                    ),
                    Task(
                        id="task-3",
                        description="Add JavaScript functionality",
                        assigned_to="FrontendAgent",
                        dependencies=["task-1"],
                    ),
                    Task(
                        id="task-4",
                        description="Create documentation",
                        assigned_to="Helper",
                        dependencies=["task-1", "task-2", "task-3"],
                    ),
                ]

        except Exception as e:
            self.logger.error(f"Failed to create roadmap: {e}")

        await self._set_idle()
        return tasks

    async def estimate_complexity(self, specs: dict[str, Any]) -> dict[str, Any]:
        """
        Estimate project complexity and time requirements.

        Args:
            specs: Technical specifications.

        Returns:
            Dict with complexity metrics.
        """
        # Count various elements to estimate complexity
        num_pages = len(specs.get("pages", specs.get("ui_pages", [])))
        num_features = len(specs.get("features", []))
        num_tasks = len(specs.get("tasks", []))

        # Calculate complexity score (simple heuristic)
        complexity_score = num_pages * 2 + num_features + num_tasks
        if complexity_score < 10:
            complexity_level = "low"
        elif complexity_score < 25:
            complexity_level = "medium"
        else:
            complexity_level = "high"

        return {
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "estimated_pages": num_pages,
            "estimated_features": num_features,
            "estimated_tasks": num_tasks or num_pages + num_features,
            "estimated_files": len(specs.get("file_structure", {}).get("root", [])) + 5,
        }

    async def create_plan(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """
        Create development plan from requirements.

        This is a convenience method that takes structured requirements
        and returns a structured plan suitable for the FlowController.

        Args:
            requirements: Dictionary of project requirements.

        Returns:
            Dictionary with tasks, file_structure, and estimated_time.
        """
        await self._set_busy("Creating development plan")

        # Convert requirements dict to string for specification
        req_str = json.dumps(requirements, default=str)
        specs = await self.create_specification(req_str)

        # Build tasks list from specs
        tasks = []
        file_structure = []

        # Extract tasks from specs
        if "tasks" in specs:
            for task in specs["tasks"]:
                tasks.append({
                    "id": task.get("id", f"task-{len(tasks) + 1}"),
                    "type": self._get_file_type(task.get("file_path", "")),
                    "file": task.get("file_path", ""),
                    "description": task.get("description", ""),
                    "assigned_to": task.get("assigned_to", "FrontendAgent"),
                })
                if task.get("file_path"):
                    file_structure.append(task.get("file_path"))

        # Extract file structure
        if "file_structure" in specs:
            fs = specs["file_structure"]
            if isinstance(fs, dict):
                for directory, files in fs.items():
                    for f in files:
                        path = f if directory == "root" else f"{directory}/{f}"
                        if path not in file_structure:
                            file_structure.append(path)

        # Create default tasks if none exist
        if not tasks:
            tasks = [
                {
                    "id": "1",
                    "type": "html",
                    "file": "index.html",
                    "description": "Create main HTML structure",
                    "assigned_to": "FrontendAgent",
                },
                {
                    "id": "2",
                    "type": "css",
                    "file": "css/styles.css",
                    "description": "Create CSS styles",
                    "assigned_to": "FrontendAgent",
                },
                {
                    "id": "3",
                    "type": "js",
                    "file": "js/script.js",
                    "description": "Add JavaScript functionality",
                    "assigned_to": "FrontendAgent",
                },
            ]
            file_structure = ["index.html", "css/styles.css", "js/script.js"]

        await self._set_idle()

        return {
            "tasks": tasks,
            "file_structure": file_structure,
            "estimated_time": "2 minutes",
            "specs": specs,
        }

    def _get_file_type(self, file_path: str) -> str:
        """Get file type from file path."""
        if file_path.endswith(".html"):
            return "html"
        elif file_path.endswith(".css"):
            return "css"
        elif file_path.endswith(".js"):
            return "js"
        else:
            return "other"
