"""
AgentForge Studio - WebSocket Handler.

This module implements WebSocket support for real-time
communication between clients and the agent system.
"""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

websocket_router = APIRouter(tags=["websocket"])


class WebSocketConnection:
    """
    Represents a WebSocket connection.

    Attributes:
        id: Unique connection identifier.
        websocket: The WebSocket instance.
        project_id: Associated project ID if any.
        connected_at: Connection timestamp.
    """

    def __init__(
        self,
        websocket: WebSocket,
        project_id: str | None = None,
    ) -> None:
        """
        Initialize a WebSocket connection.

        Args:
            websocket: The WebSocket instance.
            project_id: Optional associated project ID.
        """
        self.id = str(uuid4())
        self.websocket = websocket
        self.project_id = project_id
        self.connected_at = datetime.utcnow()

    async def send_json(self, data: dict[str, Any]) -> None:
        """
        Send JSON data to the client.

        Args:
            data: Dictionary to send as JSON.
        """
        await self.websocket.send_json(data)

    async def send_text(self, message: str) -> None:
        """
        Send text data to the client.

        Args:
            message: Text message to send.
        """
        await self.websocket.send_text(message)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.

    The WebSocketManager handles multiple client connections,
    message broadcasting, and subscription to specific projects.

    Attributes:
        connections: Dictionary of active connections.
        project_subscriptions: Mapping of projects to connections.

    Example:
        >>> manager = WebSocketManager()
        >>> await manager.connect(websocket, "project-123")
        >>> await manager.broadcast_to_project("project-123", {"type": "update"})
    """

    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self._connections: dict[str, WebSocketConnection] = {}
        self._project_subscriptions: dict[str, set[str]] = {}
        self._message_handlers: dict[str, Callable] = {}
        self.logger = logging.getLogger("websocket_manager")

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    async def connect(
        self,
        websocket: WebSocket,
        project_id: str | None = None,
    ) -> WebSocketConnection:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket to accept.
            project_id: Optional project to subscribe to.

        Returns:
            WebSocketConnection: The new connection instance.
        """
        await websocket.accept()

        connection = WebSocketConnection(websocket, project_id)
        self._connections[connection.id] = connection

        if project_id:
            if project_id not in self._project_subscriptions:
                self._project_subscriptions[project_id] = set()
            self._project_subscriptions[project_id].add(connection.id)

        self.logger.info(
            f"Client connected: {connection.id}"
            f"{f' (project: {project_id})' if project_id else ''}"
        )

        # Send welcome message
        await connection.send_json({
            "type": "connected",
            "connection_id": connection.id,
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return connection

    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect a WebSocket connection.

        Args:
            connection_id: ID of the connection to disconnect.
        """
        if connection_id not in self._connections:
            return

        connection = self._connections[connection_id]

        # Remove from project subscriptions
        if connection.project_id:
            if connection.project_id in self._project_subscriptions:
                self._project_subscriptions[connection.project_id].discard(
                    connection_id
                )
                if not self._project_subscriptions[connection.project_id]:
                    del self._project_subscriptions[connection.project_id]

        del self._connections[connection_id]
        self.logger.info(f"Client disconnected: {connection_id}")

    async def subscribe_to_project(
        self,
        connection_id: str,
        project_id: str,
    ) -> bool:
        """
        Subscribe a connection to a project's updates.

        Args:
            connection_id: The connection ID.
            project_id: The project ID to subscribe to.

        Returns:
            bool: True if subscription was successful.
        """
        if connection_id not in self._connections:
            return False

        connection = self._connections[connection_id]

        # Remove from previous project if any
        if connection.project_id and connection.project_id != project_id:
            await self.unsubscribe_from_project(connection_id, connection.project_id)

        connection.project_id = project_id

        if project_id not in self._project_subscriptions:
            self._project_subscriptions[project_id] = set()
        self._project_subscriptions[project_id].add(connection_id)

        self.logger.info(f"Connection {connection_id} subscribed to {project_id}")
        return True

    async def unsubscribe_from_project(
        self,
        connection_id: str,
        project_id: str,
    ) -> bool:
        """
        Unsubscribe a connection from a project.

        Args:
            connection_id: The connection ID.
            project_id: The project ID to unsubscribe from.

        Returns:
            bool: True if unsubscription was successful.
        """
        if project_id not in self._project_subscriptions:
            return False

        self._project_subscriptions[project_id].discard(connection_id)

        if connection_id in self._connections:
            connection = self._connections[connection_id]
            if connection.project_id == project_id:
                connection.project_id = None

        return True

    async def broadcast(self, message: dict[str, Any]) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message to broadcast.

        Returns:
            int: Number of clients that received the message.
        """
        sent_count = 0
        disconnected = []

        for connection_id, connection in self._connections.items():
            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                self.logger.error(f"Failed to send to {connection_id}: {e}")
                disconnected.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)

        return sent_count

    async def broadcast_to_project(
        self,
        project_id: str,
        message: dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all clients subscribed to a project.

        Args:
            project_id: The project ID.
            message: Message to broadcast.

        Returns:
            int: Number of clients that received the message.
        """
        if project_id not in self._project_subscriptions:
            return 0

        sent_count = 0
        disconnected = []

        for connection_id in self._project_subscriptions[project_id]:
            if connection_id not in self._connections:
                continue

            connection = self._connections[connection_id]
            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                self.logger.error(f"Failed to send to {connection_id}: {e}")
                disconnected.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)

        return sent_count

    async def send_to_connection(
        self,
        connection_id: str,
        message: dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: The target connection ID.
            message: Message to send.

        Returns:
            bool: True if message was sent successfully.
        """
        if connection_id not in self._connections:
            return False

        connection = self._connections[connection_id]
        try:
            await connection.send_json(message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False

    def register_handler(
        self,
        message_type: str,
        handler: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> Callable:
        """
        Register a handler for a message type.

        Can be used as a decorator or called directly.

        Args:
            message_type: Type of message to handle.
            handler: Async function to handle the message (optional if used as decorator).

        Returns:
            Decorator function if handler is None, otherwise the handler.
        """
        def decorator(func: Callable) -> Callable:
            self._message_handlers[message_type] = func
            return func

        if handler is not None:
            self._message_handlers[message_type] = handler
            return handler

        return decorator

    async def handle_message(
        self,
        connection_id: str,
        message: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Handle an incoming message from a client.

        Args:
            connection_id: The connection that sent the message.
            message: The message content.

        Returns:
            Optional response to send back.
        """
        message_type = message.get("type")

        if not message_type:
            return {"type": "error", "message": "Missing message type"}

        if message_type in self._message_handlers:
            try:
                return await self._message_handlers[message_type](
                    connection_id,
                    message,
                )
            except Exception as e:
                self.logger.error(f"Error handling {message_type}: {e}")
                return {"type": "error", "message": str(e)}

        return {"type": "error", "message": f"Unknown message type: {message_type}"}


# Global WebSocket manager instance
ws_manager = WebSocketManager()


@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Main WebSocket endpoint for real-time communication.

    Args:
        websocket: The WebSocket connection.
    """
    connection = await ws_manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await connection.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            # Handle the message
            response = await ws_manager.handle_message(connection.id, message)

            if response:
                await connection.send_json(response)

    except WebSocketDisconnect:
        await ws_manager.disconnect(connection.id)


@websocket_router.websocket("/ws/project/{project_id}")
async def project_websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
) -> None:
    """
    WebSocket endpoint for project-specific updates.

    Args:
        websocket: The WebSocket connection.
        project_id: The project to subscribe to.
    """
    connection = await ws_manager.connect(websocket, project_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await connection.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            response = await ws_manager.handle_message(connection.id, message)

            if response:
                await connection.send_json(response)

    except WebSocketDisconnect:
        await ws_manager.disconnect(connection.id)


# Register default message handlers
@ws_manager.register_handler("ping")
async def handle_ping(connection_id: str, message: dict[str, Any]) -> dict[str, Any]:
    """Handle ping messages."""
    return {"type": "pong", "timestamp": datetime.utcnow().isoformat()}


@ws_manager.register_handler("subscribe")
async def handle_subscribe(
    connection_id: str,
    message: dict[str, Any],
) -> dict[str, Any]:
    """Handle project subscription requests."""
    project_id = message.get("project_id")
    if not project_id:
        return {"type": "error", "message": "Missing project_id"}

    success = await ws_manager.subscribe_to_project(connection_id, project_id)
    return {
        "type": "subscribed" if success else "error",
        "project_id": project_id,
    }


@ws_manager.register_handler("chat")
async def handle_chat(
    connection_id: str,
    message: dict[str, Any],
) -> dict[str, Any]:
    """Handle chat messages through WebSocket."""
    content = message.get("content", "")
    project_id = message.get("project_id")

    # TODO: Forward to Intermediator agent
    # For now, echo back
    return {
        "type": "chat_response",
        "content": f"Received: {content}",
        "project_id": project_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
