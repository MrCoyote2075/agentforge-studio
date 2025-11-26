"""
Frontend Agent module for AgentForge Studio.

This agent is responsible for generating frontend code including
HTML, CSS, JavaScript, and frontend framework components.
"""

from typing import Any, Optional
from backend.agents.base_agent import BaseAgent, AgentMessage, AgentStatus


class FrontendAgent(BaseAgent):
    """
    Frontend agent that generates frontend code.
    
    The frontend agent is responsible for:
    - Generating HTML/CSS/JavaScript code
    - Creating React/Vue/Angular components
    - Implementing responsive designs
    - Managing frontend assets and styling
    
    Attributes:
        framework: The frontend framework being used.
        generated_components: List of generated components.
    """
    
    def __init__(
        self,
        name: str = "FrontendAgent",
        description: str = "Generates frontend code and components",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the frontend agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        super().__init__(name, description, config)
        self.framework: str = config.get("framework", "react") if config else "react"
        self.generated_components: list[dict[str, Any]] = []
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process a frontend generation request.
        
        Args:
            message: The incoming message with frontend requirements.
            
        Returns:
            The response message with generated code.
        """
        self.status = AgentStatus.BUSY
        self.add_to_history(message)
        
        try:
            # Generate frontend code based on message
            generated_code = await self._generate_frontend(message.content)
            
            response = AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content=generated_code,
                metadata={
                    "original_message_id": message.id,
                    "framework": self.framework
                }
            )
            
            self.status = AgentStatus.COMPLETED
            return response
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content={"error": str(e)},
                metadata={"original_message_id": message.id}
            )
    
    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a frontend development task.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the task execution.
        """
        self.status = AgentStatus.BUSY
        
        try:
            task_type = task.get("type", "component")
            
            if task_type == "component":
                result = await self._create_component(task)
            elif task_type == "page":
                result = await self._create_page(task)
            elif task_type == "style":
                result = await self._create_styles(task)
            elif task_type == "layout":
                result = await self._create_layout(task)
            else:
                result = {"status": "unknown_task_type"}
            
            self.status = AgentStatus.COMPLETED
            return result
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _generate_frontend(self, content: Any) -> dict[str, Any]:
        """
        Generate frontend code from content specifications.
        
        Args:
            content: The content specifications.
            
        Returns:
            The generated frontend code.
        """
        return {
            "status": "generated",
            "framework": self.framework,
            "files": [],
            "components": []
        }
    
    async def _create_component(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create a frontend component.
        
        Args:
            task: The component creation task.
            
        Returns:
            The created component details.
        """
        component_name = task.get("name", "Component")
        component = {
            "name": component_name,
            "type": "component",
            "framework": self.framework,
            "code": f"// {component_name} component placeholder"
        }
        self.generated_components.append(component)
        
        return {
            "status": "created",
            "component": component
        }
    
    async def _create_page(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create a frontend page.
        
        Args:
            task: The page creation task.
            
        Returns:
            The created page details.
        """
        return {
            "status": "created",
            "page": {
                "name": task.get("name", "Page"),
                "route": task.get("route", "/"),
                "framework": self.framework
            }
        }
    
    async def _create_styles(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create styles for a component or page.
        
        Args:
            task: The style creation task.
            
        Returns:
            The created styles.
        """
        return {
            "status": "created",
            "styles": {
                "type": task.get("style_type", "css"),
                "content": "/* Styles placeholder */"
            }
        }
    
    async def _create_layout(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create a layout component.
        
        Args:
            task: The layout creation task.
            
        Returns:
            The created layout details.
        """
        return {
            "status": "created",
            "layout": {
                "name": task.get("name", "Layout"),
                "type": task.get("layout_type", "grid"),
                "framework": self.framework
            }
        }
