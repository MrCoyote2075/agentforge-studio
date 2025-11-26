"""
Orchestrator Agent module for AgentForge Studio.

This agent coordinates all other agents and manages the overall workflow
of the website building process.
"""

from typing import Any, Optional
from backend.agents.base_agent import BaseAgent, AgentMessage, AgentStatus


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that coordinates all other agents.
    
    The orchestrator is responsible for:
    - Breaking down user requirements into tasks
    - Assigning tasks to appropriate agents
    - Managing the workflow and dependencies
    - Aggregating results from all agents
    
    Attributes:
        workflow: The current workflow being executed.
        agents: Dictionary of registered agents.
    """
    
    def __init__(
        self,
        name: str = "Orchestrator",
        description: str = "Coordinates all agents and manages workflow",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the orchestrator agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        super().__init__(name, description, config)
        self.workflow: dict[str, Any] = {}
        self.agents: dict[str, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: The agent to register.
        """
        self.agents[agent.name] = agent
    
    def unregister_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Unregister an agent from the orchestrator.
        
        Args:
            agent_name: Name of the agent to unregister.
            
        Returns:
            The unregistered agent or None if not found.
        """
        return self.agents.pop(agent_name, None)
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process an incoming message and coordinate response.
        
        Args:
            message: The incoming message to process.
            
        Returns:
            The response message from the orchestrator.
        """
        self.status = AgentStatus.BUSY
        self.add_to_history(message)
        
        try:
            # Analyze the message and determine workflow
            result = await self._analyze_and_route(message)
            
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
        Execute a task by coordinating with appropriate agents.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the task execution.
        """
        self.status = AgentStatus.BUSY
        
        try:
            task_type = task.get("type", "unknown")
            
            # Create workflow based on task
            self.workflow = await self._create_workflow(task)
            
            # Execute workflow
            results = await self._execute_workflow()
            
            self.status = AgentStatus.COMPLETED
            return {
                "status": "success",
                "task_type": task_type,
                "results": results
            }
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _analyze_and_route(self, message: AgentMessage) -> dict[str, Any]:
        """
        Analyze message content and route to appropriate agents.
        
        Args:
            message: The message to analyze.
            
        Returns:
            The aggregated results from routing.
        """
        # Placeholder for routing logic
        return {
            "analyzed": True,
            "message_id": message.id,
            "routed_to": list(self.agents.keys())
        }
    
    async def _create_workflow(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create a workflow based on the task.
        
        Args:
            task: The task to create workflow for.
            
        Returns:
            The created workflow definition.
        """
        return {
            "task_id": task.get("id"),
            "steps": [],
            "status": "created"
        }
    
    async def _execute_workflow(self) -> dict[str, Any]:
        """
        Execute the current workflow.
        
        Returns:
            The results of workflow execution.
        """
        return {
            "workflow_id": self.workflow.get("task_id"),
            "steps_completed": 0,
            "status": "completed"
        }
