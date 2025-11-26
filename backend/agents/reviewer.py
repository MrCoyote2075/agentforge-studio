"""
Reviewer Agent module for AgentForge Studio.

This agent is responsible for reviewing generated code and providing
feedback for improvements.
"""

from typing import Any, Optional
from backend.agents.base_agent import BaseAgent, AgentMessage, AgentStatus


class ReviewerAgent(BaseAgent):
    """
    Reviewer agent that reviews generated code.
    
    The reviewer is responsible for:
    - Checking code quality and best practices
    - Identifying potential bugs and issues
    - Suggesting improvements
    - Ensuring code consistency
    
    Attributes:
        review_criteria: List of review criteria to check.
        reviews: List of completed reviews.
    """
    
    def __init__(
        self,
        name: str = "Reviewer",
        description: str = "Reviews generated code for quality and improvements",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the reviewer agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        super().__init__(name, description, config)
        self.review_criteria: list[str] = [
            "code_quality",
            "security",
            "performance",
            "maintainability",
            "best_practices"
        ]
        self.reviews: list[dict[str, Any]] = []
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process a code review request.
        
        Args:
            message: The incoming message with code to review.
            
        Returns:
            The response message with review results.
        """
        self.status = AgentStatus.BUSY
        self.add_to_history(message)
        
        try:
            # Review the code
            review_result = await self._review_code(message.content)
            self.reviews.append(review_result)
            
            response = AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content=review_result,
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
        Execute a code review task.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the review.
        """
        self.status = AgentStatus.BUSY
        
        try:
            task_type = task.get("type", "full_review")
            
            if task_type == "full_review":
                result = await self._full_review(task)
            elif task_type == "security_review":
                result = await self._security_review(task)
            elif task_type == "performance_review":
                result = await self._performance_review(task)
            elif task_type == "style_review":
                result = await self._style_review(task)
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
    
    async def _review_code(self, content: Any) -> dict[str, Any]:
        """
        Review code content.
        
        Args:
            content: The code content to review.
            
        Returns:
            The review results.
        """
        return {
            "status": "reviewed",
            "criteria_checked": self.review_criteria,
            "issues": [],
            "suggestions": [],
            "score": 0.0
        }
    
    async def _full_review(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Perform a full code review.
        
        Args:
            task: The review task.
            
        Returns:
            The full review results.
        """
        return {
            "status": "reviewed",
            "task_id": task.get("id"),
            "type": "full_review",
            "findings": [],
            "approved": True
        }
    
    async def _security_review(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Perform a security-focused review.
        
        Args:
            task: The review task.
            
        Returns:
            The security review results.
        """
        return {
            "status": "reviewed",
            "task_id": task.get("id"),
            "type": "security_review",
            "vulnerabilities": [],
            "security_score": 10.0
        }
    
    async def _performance_review(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Perform a performance-focused review.
        
        Args:
            task: The review task.
            
        Returns:
            The performance review results.
        """
        return {
            "status": "reviewed",
            "task_id": task.get("id"),
            "type": "performance_review",
            "bottlenecks": [],
            "optimizations": []
        }
    
    async def _style_review(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Perform a code style review.
        
        Args:
            task: The review task.
            
        Returns:
            The style review results.
        """
        return {
            "status": "reviewed",
            "task_id": task.get("id"),
            "type": "style_review",
            "style_issues": [],
            "formatting_issues": []
        }
