"""
Intermediator Agent module for AgentForge Studio.

This agent handles communication between different agents and manages
message translation and routing.
"""

from typing import Any, Optional
from backend.agents.base_agent import BaseAgent, AgentMessage, AgentStatus


class IntermediatorAgent(BaseAgent):
    """
    Intermediator agent that facilitates communication between agents.
    
    The intermediator is responsible for:
    - Translating messages between agents
    - Managing communication protocols
    - Resolving conflicts between agent outputs
    - Ensuring message consistency
    
    Attributes:
        message_queue: Queue of pending messages.
        translation_rules: Rules for message translation.
    """
    
    def __init__(
        self,
        name: str = "Intermediator",
        description: str = "Facilitates communication between agents",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the intermediator agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        super().__init__(name, description, config)
        self.message_queue: list[AgentMessage] = []
        self.translation_rules: dict[str, Any] = {}
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process and potentially translate an incoming message.
        
        Args:
            message: The incoming message to process.
            
        Returns:
            The translated/processed response message.
        """
        self.status = AgentStatus.BUSY
        self.add_to_history(message)
        
        try:
            # Translate message if needed
            translated_content = await self._translate_message(message)
            
            response = AgentMessage(
                sender=self.name,
                recipient=message.recipient,
                content=translated_content,
                metadata={
                    "original_message_id": message.id,
                    "translated": True
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
        Execute an intermediation task.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the task execution.
        """
        self.status = AgentStatus.BUSY
        
        try:
            task_type = task.get("type", "route")
            
            if task_type == "route":
                result = await self._route_message(task)
            elif task_type == "translate":
                result = await self._translate_task(task)
            elif task_type == "resolve":
                result = await self._resolve_conflict(task)
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
    
    def add_translation_rule(
        self,
        source_agent: str,
        target_agent: str,
        rule: dict[str, Any]
    ) -> None:
        """
        Add a translation rule between two agents.
        
        Args:
            source_agent: The source agent name.
            target_agent: The target agent name.
            rule: The translation rule definition.
        """
        key = f"{source_agent}->{target_agent}"
        self.translation_rules[key] = rule
    
    async def _translate_message(self, message: AgentMessage) -> Any:
        """
        Translate message content based on rules.
        
        Args:
            message: The message to translate.
            
        Returns:
            The translated content.
        """
        key = f"{message.sender}->{message.recipient}"
        if key in self.translation_rules:
            # Apply translation rules
            return {
                "original": message.content,
                "translated": True,
                "rule_applied": key
            }
        return message.content
    
    async def _route_message(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Route a message to appropriate recipients.
        
        Args:
            task: The routing task.
            
        Returns:
            The routing result.
        """
        return {
            "status": "routed",
            "task_id": task.get("id")
        }
    
    async def _translate_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a translation task.
        
        Args:
            task: The translation task.
            
        Returns:
            The translation result.
        """
        return {
            "status": "translated",
            "task_id": task.get("id")
        }
    
    async def _resolve_conflict(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve conflicts between agent outputs.
        
        Args:
            task: The conflict resolution task.
            
        Returns:
            The resolution result.
        """
        return {
            "status": "resolved",
            "task_id": task.get("id")
        }
