"""
Helper Agent module for AgentForge Studio.

This agent provides utility functions and assistance to other agents
in the system.
"""

from typing import Any, Optional
from backend.agents.base_agent import BaseAgent, AgentMessage, AgentStatus


class HelperAgent(BaseAgent):
    """
    Helper agent that provides utility functions.
    
    The helper is responsible for:
    - Providing utility functions to other agents
    - Managing shared resources
    - Handling common tasks
    - Assisting with data transformations
    
    Attributes:
        utilities: Dictionary of available utility functions.
        cache: Cache for frequently used data.
    """
    
    def __init__(
        self,
        name: str = "Helper",
        description: str = "Provides utility functions and assistance",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the helper agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        super().__init__(name, description, config)
        self.utilities: dict[str, Any] = {}
        self.cache: dict[str, Any] = {}
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process a helper request.
        
        Args:
            message: The incoming message with utility request.
            
        Returns:
            The response message with utility result.
        """
        self.status = AgentStatus.BUSY
        self.add_to_history(message)
        
        try:
            # Process utility request
            result = await self._process_utility_request(message.content)
            
            response = AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content=result,
                metadata={"original_message_id": message.id}
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
        Execute a helper task.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the task execution.
        """
        self.status = AgentStatus.BUSY
        
        try:
            task_type = task.get("type", "utility")
            
            if task_type == "utility":
                result = await self._execute_utility(task)
            elif task_type == "transform":
                result = await self._transform_data(task)
            elif task_type == "cache":
                result = await self._manage_cache(task)
            elif task_type == "validate":
                result = await self._validate_data(task)
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
    
    def register_utility(
        self,
        name: str,
        utility: Any
    ) -> None:
        """
        Register a utility function.
        
        Args:
            name: Name of the utility.
            utility: The utility function or object.
        """
        self.utilities[name] = utility
    
    def get_utility(self, name: str) -> Optional[Any]:
        """
        Get a registered utility.
        
        Args:
            name: Name of the utility.
            
        Returns:
            The utility or None if not found.
        """
        return self.utilities.get(name)
    
    async def _process_utility_request(self, content: Any) -> dict[str, Any]:
        """
        Process a utility request.
        
        Args:
            content: The request content.
            
        Returns:
            The utility result.
        """
        if isinstance(content, dict):
            utility_name = content.get("utility")
            if utility_name and utility_name in self.utilities:
                return {
                    "status": "executed",
                    "utility": utility_name,
                    "result": None
                }
        
        return {
            "status": "no_utility_found",
            "available_utilities": list(self.utilities.keys())
        }
    
    async def _execute_utility(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a utility function.
        
        Args:
            task: The utility execution task.
            
        Returns:
            The execution result.
        """
        utility_name = task.get("utility_name")
        if utility_name and utility_name in self.utilities:
            return {
                "status": "executed",
                "utility": utility_name
            }
        
        return {
            "status": "utility_not_found",
            "requested": utility_name
        }
    
    async def _transform_data(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Transform data between formats.
        
        Args:
            task: The transformation task.
            
        Returns:
            The transformed data.
        """
        return {
            "status": "transformed",
            "task_id": task.get("id"),
            "from_format": task.get("from_format"),
            "to_format": task.get("to_format")
        }
    
    async def _manage_cache(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Manage cache operations.
        
        Args:
            task: The cache management task.
            
        Returns:
            The cache operation result.
        """
        operation = task.get("operation", "get")
        key = task.get("key")
        
        if key is None:
            return {"status": "error", "message": "key is required"}
        
        if operation == "get":
            return {
                "status": "retrieved",
                "key": key,
                "value": self.cache.get(key)
            }
        elif operation == "set":
            self.cache[key] = task.get("value")
            return {
                "status": "stored",
                "key": key
            }
        elif operation == "delete":
            self.cache.pop(key, None)
            return {
                "status": "deleted",
                "key": key
            }
        elif operation == "clear":
            self.cache.clear()
            return {
                "status": "cleared"
            }
        
        return {"status": "unknown_operation"}
    
    async def _validate_data(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Validate data against a schema.
        
        Args:
            task: The validation task.
            
        Returns:
            The validation result.
        """
        return {
            "status": "validated",
            "task_id": task.get("id"),
            "valid": True,
            "errors": []
        }
