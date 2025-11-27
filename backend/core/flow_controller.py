"""
AgentForge Studio - Flow Controller.

This module controls the end-to-end website generation flow,
coordinating between the Intermediator, Planner, Frontend Agent,
and Reviewer to generate complete websites.
"""

import logging
from enum import Enum
from typing import TYPE_CHECKING, Any

from backend.core.memory.memory_manager import MemoryManager
from backend.core.orchestrator import Orchestrator
from backend.core.workspace_manager import WorkspaceManager

if TYPE_CHECKING:
    from backend.api.websocket import WebSocketManager


class FlowStage(str, Enum):
    """Stages of the website generation flow."""

    GATHERING_REQUIREMENTS = "gathering_requirements"
    REQUIREMENTS_CONFIRMED = "requirements_confirmed"
    PLANNING = "planning"
    DEVELOPMENT = "development"
    REVIEW = "review"
    COMPLETE = "complete"
    FAILED = "failed"


class FlowController:
    """
    Controls the end-to-end website generation flow.

    The FlowController manages the progression from user chat through
    requirements gathering, planning, development, and review to
    deliver a complete generated website.

    Attributes:
        orchestrator: The Orchestrator instance.
        memory_manager: The MemoryManager instance.
        workspace_manager: The WorkspaceManager instance.
        current_stage: Dictionary mapping project_id to current stage.
        requirements: Dictionary mapping project_id to gathered requirements.

    Example:
        >>> controller = FlowController(orchestrator, memory_manager)
        >>> result = await controller.process_user_message("proj-1", "Hello")
    """

    def __init__(
        self,
        orchestrator: Orchestrator | None = None,
        memory_manager: MemoryManager | None = None,
        workspace_manager: WorkspaceManager | None = None,
    ) -> None:
        """
        Initialize the FlowController.

        Args:
            orchestrator: Optional Orchestrator instance.
            memory_manager: Optional MemoryManager instance.
            workspace_manager: Optional WorkspaceManager instance.
        """
        self.orchestrator = orchestrator or Orchestrator()
        self.memory_manager = memory_manager or MemoryManager()
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.current_stage: dict[str, FlowStage] = {}
        self.requirements: dict[str, dict[str, Any]] = {}
        self.plans: dict[str, dict[str, Any]] = {}
        self.generated_files: dict[str, list[dict[str, Any]]] = {}
        self.logger = logging.getLogger("flow_controller")

    def get_stage(self, project_id: str) -> FlowStage:
        """
        Get the current stage for a project.

        Args:
            project_id: The project identifier.

        Returns:
            Current FlowStage for the project.
        """
        return self.current_stage.get(project_id, FlowStage.GATHERING_REQUIREMENTS)

    def _get_ws_manager(self) -> "WebSocketManager | None":
        """Get the WebSocket manager, importing it lazily to avoid circular imports."""
        try:
            from backend.api.websocket import ws_manager
            return ws_manager
        except ImportError:
            return None

    async def _emit_stage_changed(
        self, project_id: str, stage: FlowStage
    ) -> None:
        """Emit stage_changed event via WebSocket."""
        ws_manager = self._get_ws_manager()
        if ws_manager:
            await ws_manager.broadcast_to_project(
                project_id,
                {
                    "type": "stage_changed",
                    "stage": stage.value,
                    "project_id": project_id,
                },
            )

    async def _emit_agent_working(
        self, project_id: str, agent: str, task: str
    ) -> None:
        """Emit agent_working event via WebSocket."""
        ws_manager = self._get_ws_manager()
        if ws_manager:
            await ws_manager.broadcast_to_project(
                project_id,
                {
                    "type": "agent_working",
                    "agent": agent,
                    "task": task,
                    "project_id": project_id,
                },
            )

    async def _emit_file_generated(
        self, project_id: str, path: str
    ) -> None:
        """Emit file_generated event via WebSocket."""
        ws_manager = self._get_ws_manager()
        if ws_manager:
            await ws_manager.broadcast_to_project(
                project_id,
                {
                    "type": "file_generated",
                    "path": path,
                    "project_id": project_id,
                },
            )

    async def _emit_preview_ready(self, project_id: str) -> None:
        """Emit preview_ready event via WebSocket."""
        ws_manager = self._get_ws_manager()
        if ws_manager:
            await ws_manager.broadcast_to_project(
                project_id,
                {
                    "type": "preview_ready",
                    "url": f"/preview/{project_id}",
                    "project_id": project_id,
                },
            )

    async def _emit_complete(
        self, project_id: str, files: list[dict[str, Any]]
    ) -> None:
        """Emit complete event via WebSocket."""
        ws_manager = self._get_ws_manager()
        if ws_manager:
            await ws_manager.broadcast_to_project(
                project_id,
                {
                    "type": "complete",
                    "files": [f.get("path", "") for f in files],
                    "download_ready": True,
                    "project_id": project_id,
                },
            )

    async def process_user_message(
        self, project_id: str, message: str, intermediator: Any = None
    ) -> dict[str, Any]:
        """
        Process user message and advance flow as needed.

        Args:
            project_id: The project identifier.
            message: The user's message.
            intermediator: Optional Intermediator agent instance.

        Returns:
            Dictionary with response, stage, files_generated, preview_ready.
        """
        current_stage = self.get_stage(project_id)

        # If we're in gathering requirements stage, process through intermediator
        if current_stage == FlowStage.GATHERING_REQUIREMENTS:
            # Use the intermediator to chat
            if intermediator:
                chat_result = await intermediator.chat(message, project_id)

                # Check if the intermediator detected requirements completion
                if isinstance(chat_result, dict):
                    response = chat_result.get("response", "")
                    if chat_result.get("requirements_complete", False):
                        # Store requirements and advance flow
                        self.requirements[project_id] = chat_result.get(
                            "requirements", {}
                        )
                        confirmed_stage = FlowStage.REQUIREMENTS_CONFIRMED
                        self.current_stage[project_id] = confirmed_stage
                        await self._emit_stage_changed(project_id, confirmed_stage)

                        # Automatically start planning
                        return await self._start_full_flow(
                            project_id, response, intermediator
                        )
                else:
                    response = chat_result

                # Check if this message is a confirmation
                if self._is_confirmation(message):
                    # Try to extract requirements from conversation
                    requirements = await self._extract_requirements_from_conversation(
                        project_id, intermediator
                    )
                    if requirements:
                        self.requirements[project_id] = requirements
                        confirmed_stage = FlowStage.REQUIREMENTS_CONFIRMED
                        self.current_stage[project_id] = confirmed_stage
                        await self._emit_stage_changed(project_id, confirmed_stage)

                        # Automatically start planning
                        return await self._start_full_flow(
                            project_id,
                            "Great! I have all the information I need. "
                            "Let me start planning your website...",
                            intermediator,
                        )

                return {
                    "response": response,
                    "stage": current_stage.value,
                    "files_generated": False,
                    "preview_ready": False,
                }
            else:
                return {
                    "response": "No intermediator available.",
                    "stage": current_stage.value,
                    "files_generated": False,
                    "preview_ready": False,
                }

        # If already past requirements gathering, just respond
        stage_msg = "Your website is being generated. Current stage: "
        return {
            "response": stage_msg + current_stage.value,
            "stage": current_stage.value,
            "files_generated": project_id in self.generated_files,
            "preview_ready": current_stage == FlowStage.COMPLETE,
        }

    async def _start_full_flow(
        self, project_id: str, initial_response: str, intermediator: Any = None
    ) -> dict[str, Any]:
        """
        Start the full website generation flow.

        Args:
            project_id: The project identifier.
            initial_response: The initial response to user.
            intermediator: Optional Intermediator agent instance.

        Returns:
            Dictionary with flow result.
        """
        try:
            # Start planning
            plan = await self.trigger_planning(
                project_id, self.requirements.get(project_id, {})
            )

            if not plan or "error" in plan:
                err_msg = (
                    initial_response
                    + "\n\nHowever, I encountered an issue during planning."
                )
                return {
                    "response": err_msg,
                    "stage": FlowStage.FAILED.value,
                    "files_generated": False,
                    "preview_ready": False,
                    "error": plan.get("error") if plan else "Planning failed",
                }

            # Start development
            files = await self.trigger_development(project_id, plan)

            if not files:
                gen_msg = initial_response + "\n\nI'm generating your website now..."
                return {
                    "response": gen_msg,
                    "stage": FlowStage.DEVELOPMENT.value,
                    "files_generated": False,
                    "preview_ready": False,
                }

            # Trigger review
            await self.trigger_review(project_id, files)

            # Save files to workspace
            await self.save_files_to_workspace(project_id, files)

            # Emit completion events
            await self._emit_preview_ready(project_id)
            await self._emit_complete(project_id, files)

            file_list = [f.get("path", "") for f in files]
            return {
                "response": (
                    f"{initial_response}\n\n"
                    f"Your website has been generated! Files created:\n"
                    f"- {chr(10).join('• ' + f for f in file_list)}\n\n"
                    f"You can preview your website and download it as a ZIP file."
                ),
                "stage": FlowStage.COMPLETE.value,
                "files_generated": True,
                "preview_ready": True,
                "files": file_list,
            }

        except Exception as e:
            self.logger.error(f"Error in full flow: {e}")
            self.current_stage[project_id] = FlowStage.FAILED
            err_msg = f"I encountered an error while generating your website: {e}"
            return {
                "response": err_msg,
                "stage": FlowStage.FAILED.value,
                "files_generated": False,
                "preview_ready": False,
                "error": str(e),
            }

    def _is_confirmation(self, message: str) -> bool:
        """
        Check if the message is a confirmation to proceed.

        Args:
            message: The user's message.

        Returns:
            True if the message is a confirmation.
        """
        confirmation_phrases = [
            "yes",
            "yep",
            "yeah",
            "sure",
            "ok",
            "okay",
            "go ahead",
            "proceed",
            "let's do it",
            "lets do it",
            "sounds good",
            "perfect",
            "great",
            "looks good",
            "that's right",
            "thats right",
            "correct",
            "confirmed",
            "confirm",
            "start",
            "begin",
            "build it",
            "create it",
            "make it",
            "generate",
        ]
        message_lower = message.lower().strip()
        return any(phrase in message_lower for phrase in confirmation_phrases)

    async def _extract_requirements_from_conversation(
        self, project_id: str, intermediator: Any
    ) -> dict[str, Any] | None:
        """
        Extract requirements from the conversation history.

        Args:
            project_id: The project identifier.
            intermediator: The Intermediator agent instance.

        Returns:
            Extracted requirements dictionary or None.
        """
        if not intermediator:
            return None

        # Get conversation history
        history = intermediator.conversation_history
        if not history:
            return None

        # Build a summary of the conversation for extraction
        conversation_text = "\n".join(
            f"{msg.role}: {msg.content}" for msg in history
        )

        try:
            # Use the intermediator to translate requirements
            requirements = await intermediator.translate_requirements(conversation_text)
            return requirements
        except Exception as e:
            self.logger.error(f"Failed to extract requirements: {e}")
            return None

    async def check_requirements_complete(
        self, project_id: str, conversation: list
    ) -> bool:
        """
        Check if we have enough info to start planning.

        Args:
            project_id: The project identifier.
            conversation: List of conversation messages.

        Returns:
            True if requirements are complete.
        """
        # Simple heuristic: at least 3 exchanges and user confirmed
        if len(conversation) < 4:
            return False

        # Check for confirmation keywords in recent messages
        for msg in conversation[-2:]:
            if hasattr(msg, "role") and msg.role == "user":
                if self._is_confirmation(msg.content):
                    return True

        return False

    async def trigger_planning(
        self, project_id: str, requirements: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Start the Planner agent.

        Args:
            project_id: The project identifier.
            requirements: The gathered requirements.

        Returns:
            Development plan dictionary.
        """
        self.current_stage[project_id] = FlowStage.PLANNING
        await self._emit_stage_changed(project_id, FlowStage.PLANNING)
        await self._emit_agent_working(
            project_id, "Planner", "Creating development plan..."
        )

        try:
            # Get the planner agent from orchestrator if available
            planner = self.orchestrator._agents.get("Planner")

            if planner:
                # Use the planner's create_specification method
                import json
                specs = await planner.create_specification(
                    json.dumps(requirements, default=str)
                )
                plan = await self._convert_specs_to_plan(specs)
            else:
                # Create a default plan based on requirements
                plan = self._create_default_plan(requirements)

            self.plans[project_id] = plan
            return plan

        except Exception as e:
            self.logger.error(f"Planning failed: {e}")
            return {"error": str(e)}

    def _create_default_plan(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """
        Create a default development plan.

        Args:
            requirements: The project requirements.

        Returns:
            Default plan dictionary.
        """
        website_type = requirements.get("website_type", "website")
        # Note: pages and features are available for future enhancements
        _ = requirements.get("pages", ["Home"])
        _ = requirements.get("features", [])

        tasks = [
            {
                "id": "1",
                "type": "html",
                "file": "index.html",
                "description": f"Create main HTML structure for {website_type}",
            },
            {
                "id": "2",
                "type": "css",
                "file": "css/styles.css",
                "description": "Create CSS styles for the website",
            },
            {
                "id": "3",
                "type": "js",
                "file": "js/script.js",
                "description": "Add JavaScript functionality",
            },
        ]

        return {
            "tasks": tasks,
            "file_structure": ["index.html", "css/styles.css", "js/script.js"],
            "estimated_time": "2 minutes",
            "requirements": requirements,
        }

    async def _convert_specs_to_plan(
        self, specs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Convert planner specifications to a development plan.

        Args:
            specs: The planner specifications.

        Returns:
            Development plan dictionary.
        """
        tasks = []
        file_structure = []

        # Extract tasks from specs
        if "tasks" in specs:
            for i, task in enumerate(specs["tasks"]):
                tasks.append({
                    "id": str(i + 1),
                    "type": self._get_file_type(task.get("file_path", "")),
                    "file": task.get("file_path", f"file_{i}.txt"),
                    "description": task.get("description", ""),
                })
                if task.get("file_path"):
                    file_structure.append(task.get("file_path"))

        # Extract file structure from specs
        if "file_structure" in specs:
            fs = specs["file_structure"]
            if isinstance(fs, dict):
                for directory, files in fs.items():
                    for f in files:
                        path = f if directory == "root" else f"{directory}/{f}"
                        if path not in file_structure:
                            file_structure.append(path)
            elif isinstance(fs, list):
                file_structure.extend(fs)

        # Create default tasks if none exist
        if not tasks:
            tasks = [
                {
                    "id": "1", "type": "html", "file": "index.html",
                    "description": "Create HTML"
                },
                {
                    "id": "2", "type": "css", "file": "css/styles.css",
                    "description": "Create CSS"
                },
                {
                    "id": "3", "type": "js", "file": "js/script.js",
                    "description": "Create JS"
                },
            ]
            file_structure = ["index.html", "css/styles.css", "js/script.js"]

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

    async def trigger_development(
        self, project_id: str, plan: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Start Frontend/Backend agents, return generated files.

        Args:
            project_id: The project identifier.
            plan: The development plan.

        Returns:
            List of generated file dictionaries.
        """
        self.current_stage[project_id] = FlowStage.DEVELOPMENT
        await self._emit_stage_changed(project_id, FlowStage.DEVELOPMENT)

        files = []
        requirements = self.requirements.get(project_id, {})

        # Get the frontend agent from orchestrator
        frontend_agent = self.orchestrator._agents.get("FrontendAgent")

        if frontend_agent:
            await self._emit_agent_working(
                project_id, "FrontendAgent", "Generating website files..."
            )

            # Use the frontend agent to generate files
            files = await self._generate_website_with_agent(
                frontend_agent, plan, requirements
            )
        else:
            # Generate default files
            files = await self._generate_default_files(plan, requirements)

        # Emit file generated events
        for f in files:
            await self._emit_file_generated(project_id, f.get("path", ""))

        self.generated_files[project_id] = files
        return files

    async def _generate_website_with_agent(
        self, frontend_agent: Any, plan: dict[str, Any], requirements: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Generate website files using the frontend agent.

        Args:
            frontend_agent: The FrontendAgent instance.
            plan: The development plan.
            requirements: The project requirements.

        Returns:
            List of generated files.
        """
        files = []

        # Combine specs and requirements for context
        specs = plan.get("specs", {})
        specs.update(requirements)

        # Generate HTML
        try:
            html = await frontend_agent.generate_html(specs)
            files.append({
                "path": "index.html",
                "content": html,
                "type": "html",
            })
        except Exception as e:
            self.logger.error(f"HTML generation failed: {e}")

        # Generate CSS
        try:
            css = await frontend_agent.generate_css(specs)
            files.append({
                "path": "css/styles.css",
                "content": css,
                "type": "css",
            })
        except Exception as e:
            self.logger.error(f"CSS generation failed: {e}")

        # Generate JavaScript
        try:
            js = await frontend_agent.generate_javascript(specs)
            files.append({
                "path": "js/script.js",
                "content": js,
                "type": "js",
            })
        except Exception as e:
            self.logger.error(f"JavaScript generation failed: {e}")

        return files

    async def _generate_default_files(
        self, plan: dict[str, Any], requirements: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Generate default website files without an agent.

        Args:
            plan: The development plan.
            requirements: The project requirements.

        Returns:
            List of generated files.
        """
        website_type = requirements.get("website_type", "Website")
        title = requirements.get("title", website_type)
        description = requirements.get("description", f"A {website_type}")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <title>{title}</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <header role="banner">
        <nav role="navigation" aria-label="Main navigation">
            <div class="logo">{title}</div>
            <ul class="nav-links">
                <li><a href="#home">Home</a></li>
                <li><a href="#about">About</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
        </nav>
    </header>
    <main role="main">
        <section id="home" class="hero">
            <h1>Welcome to {title}</h1>
            <p>{description}</p>
            <a href="#about" class="cta-button">Learn More</a>
        </section>
        <section id="about" class="about">
            <h2>About Us</h2>
            <p>This is the about section of the website.</p>
        </section>
        <section id="contact" class="contact">
            <h2>Contact Us</h2>
            <p>Get in touch with us.</p>
        </section>
    </main>
    <footer role="contentinfo">
        <p>&copy; 2024 {title}. All rights reserved.</p>
    </footer>
    <script src="js/script.js" defer></script>
</body>
</html>"""

        css_content = """/* Generated Styles */
:root {
    --primary-color: #3498db;
    --secondary-color: #2c3e50;
    --text-color: #333;
    --bg-color: #fff;
    --spacing-unit: 1rem;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--bg-color);
}

header {
    background-color: var(--secondary-color);
    padding: var(--spacing-unit);
    position: fixed;
    width: 100%;
    top: 0;
    z-index: 1000;
}

nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    max-width: 1200px;
    margin: 0 auto;
}

.logo {
    color: #fff;
    font-size: 1.5rem;
    font-weight: bold;
}

.nav-links {
    display: flex;
    list-style: none;
    gap: var(--spacing-unit);
}

.nav-links a {
    color: #fff;
    text-decoration: none;
    padding: 0.5rem 1rem;
    transition: opacity 0.3s ease;
}

.nav-links a:hover {
    opacity: 0.8;
}

main {
    padding-top: 80px;
}

section {
    padding: calc(var(--spacing-unit) * 4) var(--spacing-unit);
    max-width: 1200px;
    margin: 0 auto;
}

.hero {
    text-align: center;
    min-height: 80vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.hero h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
    color: var(--secondary-color);
}

.hero p {
    font-size: 1.25rem;
    margin-bottom: 2rem;
    max-width: 600px;
}

.cta-button {
    display: inline-block;
    background-color: var(--primary-color);
    color: #fff;
    padding: 1rem 2rem;
    border-radius: 5px;
    text-decoration: none;
    font-weight: bold;
    transition: background-color 0.3s ease;
}

.cta-button:hover {
    background-color: #2980b9;
}

.about, .contact {
    text-align: center;
}

h2 {
    font-size: 2rem;
    margin-bottom: 1rem;
    color: var(--secondary-color);
}

footer {
    background-color: var(--secondary-color);
    color: #fff;
    text-align: center;
    padding: var(--spacing-unit);
    margin-top: calc(var(--spacing-unit) * 4);
}

@media (max-width: 768px) {
    .nav-links {
        flex-direction: column;
        gap: 0.5rem;
    }

    .hero h1 {
        font-size: 2rem;
    }
}
"""

        js_content = """// Generated JavaScript
document.addEventListener('DOMContentLoaded', () => {
    console.log('Website loaded successfully');

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add active class to nav links on scroll
    const sections = document.querySelectorAll('section');
    const navLinks = document.querySelectorAll('.nav-links a');

    window.addEventListener('scroll', () => {
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (scrollY >= sectionTop - 100) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + current) {
                link.classList.add('active');
            }
        });
    });
});
"""

        return [
            {"path": "index.html", "content": html_content, "type": "html"},
            {"path": "css/styles.css", "content": css_content, "type": "css"},
            {"path": "js/script.js", "content": js_content, "type": "js"},
        ]

    async def trigger_review(
        self, project_id: str, files: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Have Reviewer check the code.

        Args:
            project_id: The project identifier.
            files: List of generated files.

        Returns:
            Review results dictionary.
        """
        self.current_stage[project_id] = FlowStage.REVIEW
        await self._emit_stage_changed(project_id, FlowStage.REVIEW)
        await self._emit_agent_working(
            project_id, "Reviewer", "Reviewing generated code..."
        )

        # Get the reviewer agent from orchestrator
        reviewer = self.orchestrator._agents.get("Reviewer")

        review_results = {"status": "reviewed", "findings": []}

        if reviewer:
            for f in files:
                try:
                    findings = await reviewer.review_code(
                        f.get("content", ""),
                        f.get("path", ""),
                        f.get("type"),
                    )
                    review_results["findings"].extend(
                        [
                            {
                                "file": f.get("path"),
                                "severity": finding.severity,
                                "message": finding.message,
                            }
                            for finding in findings
                        ]
                    )
                except Exception as e:
                    self.logger.error(f"Review failed for {f.get('path')}: {e}")

        self.current_stage[project_id] = FlowStage.COMPLETE
        return review_results

    async def save_files_to_workspace(
        self, project_id: str, files: list[dict[str, Any]]
    ) -> None:
        """
        Save generated files to workspace folder.

        Args:
            project_id: The project identifier.
            files: List of files to save.
        """
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")

            if path and content:
                try:
                    await self.workspace_manager.write_file(
                        project_id, path, content
                    )
                    self.logger.info(f"Saved file: {path}")
                except Exception as e:
                    self.logger.error(f"Failed to save file {path}: {e}")

    def get_generated_files(self, project_id: str) -> list[dict[str, Any]]:
        """
        Get the generated files for a project.

        Args:
            project_id: The project identifier.

        Returns:
            List of generated file dictionaries.
        """
        return self.generated_files.get(project_id, [])

    def get_plan(self, project_id: str) -> dict[str, Any] | None:
        """
        Get the development plan for a project.

        Args:
            project_id: The project identifier.

        Returns:
            Plan dictionary or None.
        """
        return self.plans.get(project_id)

    def get_requirements(self, project_id: str) -> dict[str, Any] | None:
        """
        Get the requirements for a project.

        Args:
            project_id: The project identifier.

        Returns:
            Requirements dictionary or None.
        """
        return self.requirements.get(project_id)
