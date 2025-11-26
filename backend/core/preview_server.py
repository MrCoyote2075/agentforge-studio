"""
AgentForge Studio - Preview Server.

This module provides an HTTP server for live preview of generated
websites with auto-refresh capability.
"""

import asyncio
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.core.config import get_settings


class PreviewServer:
    """
    HTTP server for live website preview.

    The PreviewServer serves generated project files over HTTP,
    allowing users to preview their websites in a browser with
    automatic refresh when files change.

    Attributes:
        host: Server host address.
        port: Server port number.
        project_id: Currently previewing project.

    Example:
        >>> server = PreviewServer()
        >>> await server.start("my-project")
        >>> # Preview available at http://localhost:8080
        >>> await server.stop()
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        """
        Initialize the preview server.

        Args:
            host: Optional host address.
            port: Optional port number.
        """
        settings = get_settings()
        self._host = host or settings.api_host
        self._port = port or settings.preview_port
        self._workspace_path = settings.workspace_path
        self._project_id: Optional[str] = None
        self._server: Optional[asyncio.Server] = None
        self._running = False
        self._watchers: Dict[str, asyncio.Task] = {}
        self._on_change_callbacks: list[Callable[[str], None]] = []
        self.logger = logging.getLogger("preview_server")

    @property
    def host(self) -> str:
        """Get the server host."""
        return self._host

    @property
    def port(self) -> int:
        """Get the server port."""
        return self._port

    @property
    def project_id(self) -> Optional[str]:
        """Get the currently previewing project."""
        return self._project_id

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running

    def get_url(self) -> str:
        """
        Get the preview URL.

        Returns:
            str: Full URL to access the preview.
        """
        return f"http://{self._host}:{self._port}"

    async def start(self, project_id: str) -> str:
        """
        Start the preview server for a project.

        Args:
            project_id: Project to preview.

        Returns:
            str: URL to access the preview.

        Raises:
            RuntimeError: If server is already running.
        """
        if self._running:
            if self._project_id == project_id:
                return self.get_url()
            await self.stop()

        self._project_id = project_id
        project_path = self._workspace_path / project_id

        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_id}' not found")

        # Create the HTTP server
        self._server = await asyncio.start_server(
            self._handle_request,
            self._host,
            self._port,
        )

        self._running = True
        self.logger.info(f"Preview server started at {self.get_url()}")
        self.logger.info(f"Serving project: {project_id}")

        return self.get_url()

    async def stop(self) -> None:
        """Stop the preview server."""
        if not self._running:
            return

        # Stop file watchers
        for task in self._watchers.values():
            task.cancel()
        self._watchers.clear()

        # Close the server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        self._running = False
        self._project_id = None
        self.logger.info("Preview server stopped")

    async def _handle_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Handle an incoming HTTP request.

        Args:
            reader: Stream reader for the request.
            writer: Stream writer for the response.
        """
        try:
            # Read the request line
            request_line = await reader.readline()
            if not request_line:
                return

            request = request_line.decode("utf-8").strip()
            parts = request.split(" ")

            if len(parts) < 2:
                await self._send_error(writer, 400, "Bad Request")
                return

            method, path = parts[0], parts[1]

            if method != "GET":
                await self._send_error(writer, 405, "Method Not Allowed")
                return

            # Consume headers
            while True:
                line = await reader.readline()
                if line == b"\r\n" or not line:
                    break

            # Serve the file
            await self._serve_file(writer, path)

        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            await self._send_error(writer, 500, "Internal Server Error")

        finally:
            writer.close()
            await writer.wait_closed()

    async def _serve_file(
        self,
        writer: asyncio.StreamWriter,
        path: str,
    ) -> None:
        """
        Serve a file from the project directory.

        Args:
            writer: Stream writer for the response.
            path: Requested path.
        """
        if not self._project_id:
            await self._send_error(writer, 503, "No project loaded")
            return

        # Normalize the path
        if path == "/":
            path = "/index.html"

        # Security: prevent directory traversal
        clean_path = os.path.normpath(path).lstrip("/")
        if ".." in clean_path:
            await self._send_error(writer, 403, "Forbidden")
            return

        file_path = self._workspace_path / self._project_id / clean_path

        if not file_path.exists():
            await self._send_error(writer, 404, "Not Found")
            return

        if file_path.is_dir():
            # Try index.html in directory
            file_path = file_path / "index.html"
            if not file_path.exists():
                await self._send_error(writer, 404, "Not Found")
                return

        # Read and serve the file
        content_type = self._get_content_type(file_path)

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # Inject auto-refresh script for HTML files
            if content_type == "text/html":
                content = self._inject_refresh_script(content)

            await self._send_response(writer, 200, content, content_type)

        except Exception as e:
            self.logger.error(f"Error reading file: {e}")
            await self._send_error(writer, 500, "Internal Server Error")

    def _get_content_type(self, file_path: Path) -> str:
        """
        Get the MIME type for a file.

        Args:
            file_path: Path to the file.

        Returns:
            str: MIME type.
        """
        content_type, _ = mimetypes.guess_type(str(file_path))
        return content_type or "application/octet-stream"

    def _inject_refresh_script(self, content: bytes) -> bytes:
        """
        Inject auto-refresh JavaScript into HTML content.

        Args:
            content: Original HTML content.

        Returns:
            bytes: Modified HTML with refresh script.
        """
        refresh_script = b"""
<script>
// Auto-refresh when files change
(function() {
    let lastCheck = Date.now();
    setInterval(async () => {
        try {
            const response = await fetch('/__refresh_check?t=' + lastCheck);
            const data = await response.json();
            if (data.refresh) {
                location.reload();
            }
            lastCheck = Date.now();
        } catch (e) {}
    }, 2000);
})();
</script>
"""
        # Insert before </body> or at the end
        if b"</body>" in content:
            content = content.replace(b"</body>", refresh_script + b"</body>")
        else:
            content = content + refresh_script

        return content

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        content: bytes,
        content_type: str,
    ) -> None:
        """
        Send an HTTP response.

        Args:
            writer: Stream writer.
            status_code: HTTP status code.
            content: Response body.
            content_type: Content-Type header value.
        """
        status_text = {
            200: "OK",
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }.get(status_code, "Unknown")

        response = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(content)}\r\n"
        response += "Connection: close\r\n"
        response += "Access-Control-Allow-Origin: *\r\n"
        response += "\r\n"

        writer.write(response.encode("utf-8"))
        writer.write(content)
        await writer.drain()

    async def _send_error(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None:
        """
        Send an error response.

        Args:
            writer: Stream writer.
            status_code: HTTP status code.
            message: Error message.
        """
        content = f"<html><body><h1>{status_code} {message}</h1></body></html>"
        await self._send_response(
            writer,
            status_code,
            content.encode("utf-8"),
            "text/html",
        )

    async def watch_for_changes(self, callback: Callable[[str], None]) -> None:
        """
        Start watching for file changes.

        Args:
            callback: Function to call when files change.
        """
        self._on_change_callbacks.append(callback)

        if self._project_id and "main" not in self._watchers:
            self._watchers["main"] = asyncio.create_task(
                self._file_watcher_task()
            )

    async def _file_watcher_task(self) -> None:
        """Background task to watch for file changes."""
        if not self._project_id:
            return

        project_path = self._workspace_path / self._project_id
        last_modified: Dict[str, float] = {}

        while self._running:
            try:
                # Check for modified files
                for path in project_path.rglob("*"):
                    if path.is_file():
                        mtime = path.stat().st_mtime
                        str_path = str(path)
                        if str_path in last_modified:
                            if mtime > last_modified[str_path]:
                                # File was modified
                                for callback in self._on_change_callbacks:
                                    callback(str_path)
                        last_modified[str_path] = mtime

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in file watcher: {e}")
                await asyncio.sleep(5)

    async def switch_project(self, project_id: str) -> str:
        """
        Switch to previewing a different project.

        Args:
            project_id: New project to preview.

        Returns:
            str: Preview URL.
        """
        if self._running:
            await self.stop()
        return await self.start(project_id)
