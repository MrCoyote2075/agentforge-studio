"""
WebSocket module for AgentForge Studio.

This module provides WebSocket handlers for real-time communication
with clients.
"""

import json
from typing import Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


websocket_router = APIRouter(tags=["websocket"])


@dataclass
class WebSocketConnection:
    """
    Represents a WebSocket connection.
    
    Attributes:
        websocket: The WebSocket instance.
        client_id: Unique client identifier.
        connected_at: When the connection was established.
        subscriptions: List of subscribed topics.
    """
    websocket: WebSocket
    client_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    subscriptions: list[str] = field(default_factory=list)


class WebSocketManager:
    """
    Manager for WebSocket connections.
    
    Handles connection management, broadcasting, and topic-based
    subscriptions.
    
    Attributes:
        connections: Dictionary of client_id to WebSocketConnection.
        topic_subscriptions: Dictionary of topic to list of client_ids.
    """
    
    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self._connections: dict[str, WebSocketConnection] = {}
        self._topic_subscriptions: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        client_id: str
    ) -> WebSocketConnection:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket instance.
            client_id: The client identifier.
            
        Returns:
            The WebSocketConnection instance.
        """
        await websocket.accept()
        
        connection = WebSocketConnection(
            websocket=websocket,
            client_id=client_id
        )
        
        async with self._lock:
            self._connections[client_id] = connection
        
        return connection
    
    async def disconnect(self, client_id: str) -> None:
        """
        Disconnect a client.
        
        Args:
            client_id: The client identifier.
        """
        async with self._lock:
            if client_id in self._connections:
                connection = self._connections[client_id]
                
                # Remove from all subscriptions
                for topic in connection.subscriptions:
                    if topic in self._topic_subscriptions:
                        self._topic_subscriptions[topic].discard(client_id)
                
                del self._connections[client_id]
    
    async def subscribe(self, client_id: str, topic: str) -> bool:
        """
        Subscribe a client to a topic.
        
        Args:
            client_id: The client identifier.
            topic: The topic to subscribe to.
            
        Returns:
            True if subscribed successfully.
        """
        async with self._lock:
            if client_id not in self._connections:
                return False
            
            connection = self._connections[client_id]
            if topic not in connection.subscriptions:
                connection.subscriptions.append(topic)
            
            if topic not in self._topic_subscriptions:
                self._topic_subscriptions[topic] = set()
            self._topic_subscriptions[topic].add(client_id)
            
            return True
    
    async def unsubscribe(self, client_id: str, topic: str) -> bool:
        """
        Unsubscribe a client from a topic.
        
        Args:
            client_id: The client identifier.
            topic: The topic to unsubscribe from.
            
        Returns:
            True if unsubscribed successfully.
        """
        async with self._lock:
            if client_id not in self._connections:
                return False
            
            connection = self._connections[client_id]
            if topic in connection.subscriptions:
                connection.subscriptions.remove(topic)
            
            if topic in self._topic_subscriptions:
                self._topic_subscriptions[topic].discard(client_id)
            
            return True
    
    async def send_to_client(
        self,
        client_id: str,
        message: dict[str, Any]
    ) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            client_id: The client identifier.
            message: The message to send.
            
        Returns:
            True if sent successfully.
        """
        connection = self._connections.get(client_id)
        if not connection:
            return False
        
        try:
            await connection.websocket.send_json(message)
            return True
        except Exception:
            return False
    
    async def broadcast(
        self,
        message: dict[str, Any],
        exclude: Optional[list[str]] = None
    ) -> int:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message to broadcast.
            exclude: List of client_ids to exclude.
            
        Returns:
            Number of clients message was sent to.
        """
        exclude = exclude or []
        count = 0
        
        for client_id, connection in self._connections.items():
            if client_id not in exclude:
                try:
                    await connection.websocket.send_json(message)
                    count += 1
                except Exception:
                    pass
        
        return count
    
    async def broadcast_to_topic(
        self,
        topic: str,
        message: dict[str, Any],
        exclude: Optional[list[str]] = None
    ) -> int:
        """
        Broadcast a message to all subscribers of a topic.
        
        Args:
            topic: The topic to broadcast to.
            message: The message to broadcast.
            exclude: List of client_ids to exclude.
            
        Returns:
            Number of clients message was sent to.
        """
        exclude = exclude or []
        count = 0
        
        subscribers = self._topic_subscriptions.get(topic, set())
        
        for client_id in subscribers:
            if client_id not in exclude:
                connection = self._connections.get(client_id)
                if connection:
                    try:
                        await connection.websocket.send_json(message)
                        count += 1
                    except Exception:
                        pass
        
        return count
    
    def get_connection_count(self) -> int:
        """
        Get the number of active connections.
        
        Returns:
            Number of connections.
        """
        return len(self._connections)
    
    def get_topic_subscriber_count(self, topic: str) -> int:
        """
        Get the number of subscribers for a topic.
        
        Args:
            topic: The topic name.
            
        Returns:
            Number of subscribers.
        """
        return len(self._topic_subscriptions.get(topic, set()))


# Global WebSocket manager instance
ws_manager = WebSocketManager()


@websocket_router.websocket("/connect/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
    """
    WebSocket connection endpoint.
    
    Args:
        websocket: The WebSocket instance.
        client_id: The client identifier.
    """
    await ws_manager.connect(websocket, client_id)
    
    # Send welcome message
    await ws_manager.send_to_client(client_id, {
        "type": "connected",
        "client_id": client_id,
        "message": "Connected to AgentForge Studio"
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(client_id, message)
            except json.JSONDecodeError:
                await ws_manager.send_to_client(client_id, {
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)


async def handle_websocket_message(
    client_id: str,
    message: dict[str, Any]
) -> None:
    """
    Handle incoming WebSocket messages.
    
    Args:
        client_id: The client identifier.
        message: The received message.
    """
    message_type = message.get("type", "")
    
    if message_type == "subscribe":
        topic = message.get("topic")
        if topic:
            await ws_manager.subscribe(client_id, topic)
            await ws_manager.send_to_client(client_id, {
                "type": "subscribed",
                "topic": topic
            })
    
    elif message_type == "unsubscribe":
        topic = message.get("topic")
        if topic:
            await ws_manager.unsubscribe(client_id, topic)
            await ws_manager.send_to_client(client_id, {
                "type": "unsubscribed",
                "topic": topic
            })
    
    elif message_type == "ping":
        await ws_manager.send_to_client(client_id, {
            "type": "pong"
        })
    
    else:
        await ws_manager.send_to_client(client_id, {
            "type": "echo",
            "data": message
        })
