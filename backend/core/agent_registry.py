"""
AgentForge Studio - Agent Registry.

This module implements a registry for tracking agent status and capabilities,
enabling efficient task assignment and health monitoring.
"""

import asyncio
import logging
import threading
from datetime import datetime, timedelta

from backend.models.messages import AgentInfo, AgentStatusType


class AgentRegistry:
    """
    Registry for tracking agent status and capabilities.

    This class provides a centralized registry for managing agent information,
    including:
    - Agent registration and unregistration
    - Status tracking (IDLE, BUSY, WAITING, ERROR, OFFLINE)
    - Capability tracking (what file types agents can handle)
    - Health check mechanism
    - Agent discovery by capability

    Example:
        >>> registry = AgentRegistry()
        >>> registry.register("frontend_agent", capabilities=["html", "css", "js"])
        >>> available = registry.get_available_agents("html")
        >>> registry.update_status("frontend_agent", AgentStatusType.BUSY)
    """

    def __init__(
        self,
        heartbeat_timeout: float = 30.0,
        health_check_interval: float = 10.0,
    ) -> None:
        """
        Initialize the agent registry.

        Args:
            heartbeat_timeout: Time in seconds before marking agent as offline.
            health_check_interval: Interval for health check background task.
        """
        self._agents: dict[str, AgentInfo] = {}
        self._capabilities: dict[str, set[str]] = {}  # capability -> set of agents
        self._heartbeat_timeout = heartbeat_timeout
        self._health_check_interval = health_check_interval
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()
        self._running = False
        self._health_check_task: asyncio.Task | None = None
        self.logger = logging.getLogger("agent_registry")

    def register(
        self,
        name: str,
        capabilities: list[str] | None = None,
        status: AgentStatusType = AgentStatusType.IDLE,
    ) -> AgentInfo:
        """
        Register an agent.

        Args:
            name: Agent name.
            capabilities: List of capabilities (file types, task types).
            status: Initial agent status.

        Returns:
            AgentInfo: The registered agent information.
        """
        with self._lock:
            agent = AgentInfo(
                name=name,
                status=status,
                capabilities=capabilities or [],
                registered_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
            )

            self._agents[name] = agent

            # Index capabilities for fast lookup
            for capability in agent.capabilities:
                if capability not in self._capabilities:
                    self._capabilities[capability] = set()
                self._capabilities[capability].add(name)

            self.logger.info(
                f"Registered agent '{name}' with capabilities: {capabilities}"
            )
            return agent

    def unregister(self, name: str) -> bool:
        """
        Unregister an agent.

        Args:
            name: Agent name.

        Returns:
            bool: True if agent was unregistered, False if not found.
        """
        with self._lock:
            agent = self._agents.get(name)
            if not agent:
                return False

            # Remove from capability index
            for capability in agent.capabilities:
                if capability in self._capabilities:
                    self._capabilities[capability].discard(name)
                    if not self._capabilities[capability]:
                        del self._capabilities[capability]

            del self._agents[name]
            self.logger.info(f"Unregistered agent '{name}'")
            return True

    def get_agent(self, name: str) -> AgentInfo | None:
        """
        Get agent information.

        Args:
            name: Agent name.

        Returns:
            AgentInfo: Agent information or None if not found.
        """
        with self._lock:
            return self._agents.get(name)

    def get_all_agents(self) -> list[AgentInfo]:
        """
        Get all registered agents.

        Returns:
            List of all registered agents.
        """
        with self._lock:
            return list(self._agents.values())

    def update_status(
        self,
        name: str,
        status: AgentStatusType,
        current_task_id: str | None = None,
    ) -> bool:
        """
        Update agent status.

        Args:
            name: Agent name.
            status: New status.
            current_task_id: Optional current task ID.

        Returns:
            bool: True if status was updated, False if agent not found.
        """
        with self._lock:
            agent = self._agents.get(name)
            if not agent:
                return False

            old_status = agent.status
            agent.status = status
            agent.current_task_id = current_task_id
            agent.last_heartbeat = datetime.utcnow()

            if old_status != status:
                self.logger.debug(
                    f"Agent '{name}' status changed: {old_status} -> {status}"
                )

            return True

    def heartbeat(self, name: str) -> bool:
        """
        Record a heartbeat from an agent.

        Args:
            name: Agent name.

        Returns:
            bool: True if heartbeat was recorded, False if agent not found.
        """
        with self._lock:
            agent = self._agents.get(name)
            if not agent:
                return False

            agent.last_heartbeat = datetime.utcnow()

            # Bring back online if was offline
            if agent.status == AgentStatusType.OFFLINE:
                agent.status = AgentStatusType.IDLE
                self.logger.info(f"Agent '{name}' is back online")

            return True

    def get_available_agents(
        self,
        capability: str | None = None,
    ) -> list[AgentInfo]:
        """
        Get available (idle or waiting) agents.

        Args:
            capability: Optional capability to filter by.

        Returns:
            List of available agents.
        """
        with self._lock:
            self._check_offline_agents()

            if capability:
                agent_names = self._capabilities.get(capability, set())
                agents = [
                    self._agents[name]
                    for name in agent_names
                    if name in self._agents
                ]
            else:
                agents = list(self._agents.values())

            return [
                a for a in agents
                if a.status in (AgentStatusType.IDLE, AgentStatusType.WAITING)
            ]

    def get_agents_by_status(self, status: AgentStatusType) -> list[AgentInfo]:
        """
        Get agents by status.

        Args:
            status: Status to filter by.

        Returns:
            List of agents with the specified status.
        """
        with self._lock:
            self._check_offline_agents()
            return [a for a in self._agents.values() if a.status == status]

    def get_agents_by_capability(self, capability: str) -> list[AgentInfo]:
        """
        Get agents by capability.

        Args:
            capability: Capability to filter by.

        Returns:
            List of agents with the specified capability.
        """
        with self._lock:
            agent_names = self._capabilities.get(capability, set())
            return [
                self._agents[name]
                for name in agent_names
                if name in self._agents
            ]

    def add_capability(self, name: str, capability: str) -> bool:
        """
        Add a capability to an agent.

        Args:
            name: Agent name.
            capability: Capability to add.

        Returns:
            bool: True if capability was added, False if agent not found.
        """
        with self._lock:
            agent = self._agents.get(name)
            if not agent:
                return False

            if capability not in agent.capabilities:
                agent.capabilities.append(capability)

            if capability not in self._capabilities:
                self._capabilities[capability] = set()
            self._capabilities[capability].add(name)

            return True

    def remove_capability(self, name: str, capability: str) -> bool:
        """
        Remove a capability from an agent.

        Args:
            name: Agent name.
            capability: Capability to remove.

        Returns:
            bool: True if capability was removed, False otherwise.
        """
        with self._lock:
            agent = self._agents.get(name)
            if not agent:
                return False

            if capability in agent.capabilities:
                agent.capabilities.remove(capability)

            if capability in self._capabilities:
                self._capabilities[capability].discard(name)
                if not self._capabilities[capability]:
                    del self._capabilities[capability]

            return True

    def get_all_capabilities(self) -> list[str]:
        """
        Get all registered capabilities.

        Returns:
            List of all capability names.
        """
        with self._lock:
            return list(self._capabilities.keys())

    def get_agent_count(self) -> int:
        """
        Get the number of registered agents.

        Returns:
            int: Number of agents.
        """
        with self._lock:
            return len(self._agents)

    def is_healthy(self, name: str) -> bool:
        """
        Check if an agent is healthy.

        An agent is considered healthy if it has sent a heartbeat
        within the timeout period and is not in ERROR status.

        Args:
            name: Agent name.

        Returns:
            bool: True if agent is healthy, False otherwise.
        """
        with self._lock:
            agent = self._agents.get(name)
            if not agent:
                return False

            if agent.status == AgentStatusType.ERROR:
                return False

            if agent.status == AgentStatusType.OFFLINE:
                return False

            elapsed = (datetime.utcnow() - agent.last_heartbeat).total_seconds()
            return elapsed <= self._heartbeat_timeout

    async def start_health_check(self) -> None:
        """
        Start the background health check task.

        This periodically checks for agents that have missed heartbeats
        and marks them as offline.
        """
        if not self._running:
            self._running = True
            self._health_check_task = asyncio.create_task(
                self._health_check_loop()
            )
            self.logger.info("Health check started")

    async def stop_health_check(self) -> None:
        """Stop the background health check task."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Health check stopped")

    async def _health_check_loop(self) -> None:
        """Background task to check agent health."""
        while self._running:
            try:
                await asyncio.sleep(self._health_check_interval)
                self._check_offline_agents()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check: {e}")

    def _check_offline_agents(self) -> int:
        """
        Check for agents that have missed heartbeats.

        Returns:
            int: Number of agents marked as offline.
        """
        count = 0
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self._heartbeat_timeout)

        for agent in self._agents.values():
            if (
                agent.status != AgentStatusType.OFFLINE
                and agent.last_heartbeat < cutoff
            ):
                agent.status = AgentStatusType.OFFLINE
                agent.current_task_id = None
                count += 1
                self.logger.warning(f"Agent '{agent.name}' marked as offline")

        return count

    def clear(self) -> None:
        """Clear all registered agents."""
        with self._lock:
            self._agents.clear()
            self._capabilities.clear()
            self.logger.info("Registry cleared")
