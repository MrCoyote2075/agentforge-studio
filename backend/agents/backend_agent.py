"""
Backend Agent module for AgentForge Studio.

This agent is responsible for generating backend code including
API endpoints, database models, and server-side logic.
"""

from typing import Any, Optional
from backend.agents.base_agent import BaseAgent, AgentMessage, AgentStatus


class BackendAgent(BaseAgent):
    """
    Backend agent that generates backend code.
    
    The backend agent is responsible for:
    - Creating API endpoints
    - Designing database models
    - Implementing business logic
    - Managing server configuration
    
    Attributes:
        framework: The backend framework being used.
        database_type: The type of database.
        generated_endpoints: List of generated endpoints.
    """
    
    def __init__(
        self,
        name: str = "BackendAgent",
        description: str = "Generates backend code and API endpoints",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the backend agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        super().__init__(name, description, config)
        self.framework: str = config.get("framework", "fastapi") if config else "fastapi"
        self.database_type: str = config.get("database", "postgresql") if config else "postgresql"
        self.generated_endpoints: list[dict[str, Any]] = []
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process a backend generation request.
        
        Args:
            message: The incoming message with backend requirements.
            
        Returns:
            The response message with generated code.
        """
        self.status = AgentStatus.BUSY
        self.add_to_history(message)
        
        try:
            # Generate backend code based on message
            generated_code = await self._generate_backend(message.content)
            
            response = AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content=generated_code,
                metadata={
                    "original_message_id": message.id,
                    "framework": self.framework,
                    "database": self.database_type
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
        Execute a backend development task.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the task execution.
        """
        self.status = AgentStatus.BUSY
        
        try:
            task_type = task.get("type", "endpoint")
            
            if task_type == "endpoint":
                result = await self._create_endpoint(task)
            elif task_type == "model":
                result = await self._create_model(task)
            elif task_type == "service":
                result = await self._create_service(task)
            elif task_type == "middleware":
                result = await self._create_middleware(task)
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
    
    async def _generate_backend(self, content: Any) -> dict[str, Any]:
        """
        Generate backend code from content specifications.
        
        Args:
            content: The content specifications.
            
        Returns:
            The generated backend code.
        """
        return {
            "status": "generated",
            "framework": self.framework,
            "database": self.database_type,
            "files": [],
            "endpoints": []
        }
    
    async def _create_endpoint(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create an API endpoint.
        
        Args:
            task: The endpoint creation task.
            
        Returns:
            The created endpoint details.
        """
        endpoint = {
            "path": task.get("path", "/api/resource"),
            "method": task.get("method", "GET"),
            "framework": self.framework,
            "code": "# Endpoint placeholder"
        }
        self.generated_endpoints.append(endpoint)
        
        return {
            "status": "created",
            "endpoint": endpoint
        }
    
    async def _create_model(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create a database model.
        
        Args:
            task: The model creation task.
            
        Returns:
            The created model details.
        """
        return {
            "status": "created",
            "model": {
                "name": task.get("name", "Model"),
                "database": self.database_type,
                "fields": task.get("fields", [])
            }
        }
    
    async def _create_service(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create a service layer component.
        
        Args:
            task: The service creation task.
            
        Returns:
            The created service details.
        """
        return {
            "status": "created",
            "service": {
                "name": task.get("name", "Service"),
                "methods": task.get("methods", [])
            }
        }
    
    async def _create_middleware(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create a middleware component.
        
        Args:
            task: The middleware creation task.
            
        Returns:
            The created middleware details.
        """
        return {
            "status": "created",
            "middleware": {
                "name": task.get("name", "Middleware"),
                "type": task.get("middleware_type", "auth")
            }
        }
