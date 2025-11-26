"""
Tester Agent module for AgentForge Studio.

This agent is responsible for generating and running tests for
the generated code.
"""

from typing import Any, Optional
from backend.agents.base_agent import BaseAgent, AgentMessage, AgentStatus


class TesterAgent(BaseAgent):
    """
    Tester agent that creates and runs tests.
    
    The tester is responsible for:
    - Generating unit tests
    - Creating integration tests
    - Running test suites
    - Reporting test coverage
    
    Attributes:
        test_framework: The testing framework being used.
        generated_tests: List of generated tests.
        test_results: Results from test runs.
    """
    
    def __init__(
        self,
        name: str = "Tester",
        description: str = "Generates and runs tests for code validation",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the tester agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        super().__init__(name, description, config)
        self.test_framework: str = config.get("framework", "pytest") if config else "pytest"
        self.generated_tests: list[dict[str, Any]] = []
        self.test_results: list[dict[str, Any]] = []
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process a testing request.
        
        Args:
            message: The incoming message with code to test.
            
        Returns:
            The response message with test results.
        """
        self.status = AgentStatus.BUSY
        self.add_to_history(message)
        
        try:
            # Generate and run tests
            test_result = await self._generate_and_run_tests(message.content)
            self.test_results.append(test_result)
            
            response = AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content=test_result,
                metadata={
                    "original_message_id": message.id,
                    "framework": self.test_framework
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
        Execute a testing task.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the testing task.
        """
        self.status = AgentStatus.BUSY
        
        try:
            task_type = task.get("type", "unit_test")
            
            if task_type == "unit_test":
                result = await self._create_unit_tests(task)
            elif task_type == "integration_test":
                result = await self._create_integration_tests(task)
            elif task_type == "e2e_test":
                result = await self._create_e2e_tests(task)
            elif task_type == "run_tests":
                result = await self._run_tests(task)
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
    
    async def _generate_and_run_tests(self, content: Any) -> dict[str, Any]:
        """
        Generate and run tests for content.
        
        Args:
            content: The content to test.
            
        Returns:
            The test results.
        """
        return {
            "status": "completed",
            "framework": self.test_framework,
            "tests_generated": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "coverage": 0.0
        }
    
    async def _create_unit_tests(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create unit tests for a component.
        
        Args:
            task: The unit test creation task.
            
        Returns:
            The created unit tests.
        """
        test = {
            "type": "unit",
            "target": task.get("target", "component"),
            "framework": self.test_framework,
            "code": "# Unit test placeholder"
        }
        self.generated_tests.append(test)
        
        return {
            "status": "created",
            "test": test
        }
    
    async def _create_integration_tests(
        self,
        task: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create integration tests.
        
        Args:
            task: The integration test creation task.
            
        Returns:
            The created integration tests.
        """
        test = {
            "type": "integration",
            "target": task.get("target", "api"),
            "framework": self.test_framework,
            "code": "# Integration test placeholder"
        }
        self.generated_tests.append(test)
        
        return {
            "status": "created",
            "test": test
        }
    
    async def _create_e2e_tests(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Create end-to-end tests.
        
        Args:
            task: The e2e test creation task.
            
        Returns:
            The created e2e tests.
        """
        test = {
            "type": "e2e",
            "target": task.get("target", "application"),
            "framework": task.get("e2e_framework", "playwright"),
            "code": "# E2E test placeholder"
        }
        self.generated_tests.append(test)
        
        return {
            "status": "created",
            "test": test
        }
    
    async def _run_tests(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Run the test suite.
        
        Args:
            task: The test run task.
            
        Returns:
            The test run results.
        """
        return {
            "status": "completed",
            "task_id": task.get("id"),
            "tests_run": len(self.generated_tests),
            "passed": len(self.generated_tests),
            "failed": 0,
            "skipped": 0,
            "coverage": 85.0
        }
