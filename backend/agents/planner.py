"""
Planner Agent module for AgentForge Studio.

This agent is responsible for analyzing requirements and creating
detailed implementation plans for the website.
"""

from typing import Any, Optional
from backend.agents.base_agent import BaseAgent, AgentMessage, AgentStatus


class PlannerAgent(BaseAgent):
    """
    Planner agent that creates implementation plans.
    
    The planner is responsible for:
    - Analyzing user requirements
    - Breaking down requirements into actionable tasks
    - Creating project structure and architecture plans
    - Defining dependencies between tasks
    
    Attributes:
        current_plan: The current plan being developed.
        requirements: List of analyzed requirements.
    """
    
    def __init__(
        self,
        name: str = "Planner",
        description: str = "Analyzes requirements and creates implementation plans",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the planner agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        super().__init__(name, description, config)
        self.current_plan: dict[str, Any] = {}
        self.requirements: list[dict[str, Any]] = []
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process a planning request.
        
        Args:
            message: The incoming message containing requirements.
            
        Returns:
            The response message with the plan.
        """
        self.status = AgentStatus.BUSY
        self.add_to_history(message)
        
        try:
            # Analyze requirements from message
            requirements = await self._extract_requirements(message.content)
            self.requirements.extend(requirements)
            
            # Create plan
            plan = await self._create_plan(requirements)
            self.current_plan = plan
            
            response = AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content=plan,
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
        Execute a planning task.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the planning task.
        """
        self.status = AgentStatus.BUSY
        
        try:
            task_type = task.get("type", "analyze")
            
            if task_type == "analyze":
                result = await self._analyze_requirements(task)
            elif task_type == "plan":
                result = await self._generate_plan(task)
            elif task_type == "architecture":
                result = await self._design_architecture(task)
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
    
    async def _extract_requirements(self, content: Any) -> list[dict[str, Any]]:
        """
        Extract requirements from message content.
        
        Args:
            content: The message content.
            
        Returns:
            List of extracted requirements.
        """
        if isinstance(content, dict):
            return content.get("requirements", [])
        return []
    
    async def _create_plan(
        self,
        requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Create an implementation plan from requirements.
        
        Args:
            requirements: List of requirements.
            
        Returns:
            The implementation plan.
        """
        return {
            "status": "planned",
            "requirements_count": len(requirements),
            "phases": [
                {"name": "Design", "tasks": []},
                {"name": "Frontend Development", "tasks": []},
                {"name": "Backend Development", "tasks": []},
                {"name": "Testing", "tasks": []},
                {"name": "Deployment", "tasks": []}
            ]
        }
    
    async def _analyze_requirements(
        self,
        task: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze requirements from a task.
        
        Args:
            task: The analysis task.
            
        Returns:
            The analysis result.
        """
        return {
            "status": "analyzed",
            "task_id": task.get("id"),
            "requirements": []
        }
    
    async def _generate_plan(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a detailed plan from a task.
        
        Args:
            task: The planning task.
            
        Returns:
            The generated plan.
        """
        return {
            "status": "planned",
            "task_id": task.get("id"),
            "plan": self.current_plan
        }
    
    async def _design_architecture(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Design the system architecture.
        
        Args:
            task: The architecture task.
            
        Returns:
            The architecture design.
        """
        return {
            "status": "designed",
            "task_id": task.get("id"),
            "architecture": {
                "frontend": {"framework": "React/Vue/Angular"},
                "backend": {"framework": "FastAPI"},
                "database": {"type": "PostgreSQL/MongoDB"},
                "deployment": {"platform": "Docker/Kubernetes"}
            }
        }
