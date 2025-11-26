"""
AgentForge Studio - Optimizer Agent.

The Optimizer Agent minifies HTML/CSS/JS code, suggests performance
improvements, and optimizes code for production deployment.
"""

import re
from datetime import datetime
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import Message


class OptimizerAgent(BaseAgent):
    """
    Optimizer Agent that handles code optimization tasks.

    The Optimizer minifies HTML, CSS, and JavaScript, identifies performance
    bottlenecks, and suggests optimizations for production deployment.

    Attributes:
        optimization_history: History of optimizations performed.
        stats: Optimization statistics.

    Example:
        >>> optimizer = OptimizerAgent()
        >>> minified = await optimizer.minify_css(css_code)
    """

    def __init__(
        self,
        name: str = "OptimizerAgent",
        model: str = "gemini-pro",
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Optimizer agent.

        Args:
            name: The agent's name. Defaults to 'OptimizerAgent'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._optimization_history: list[dict[str, Any]] = []
        self._stats: dict[str, Any] = {
            "total_files": 0,
            "total_original_size": 0,
            "total_optimized_size": 0,
        }

    async def process(self, message: Message) -> Message:
        """
        Process an optimization request.

        Args:
            message: The incoming message with code to optimize.

        Returns:
            Message: Response with optimization results.
        """
        await self._set_busy(f"Optimizing: {message.content[:50]}")

        try:
            content_lower = message.content.lower()
            code = message.metadata.get("code", "") if message.metadata else ""

            if "minify" in content_lower:
                if "css" in content_lower:
                    result = await self.minify_css(code or message.content)
                    response_content = f"CSS minified: {len(result)} chars"
                elif "html" in content_lower:
                    result = await self.minify_html(code or message.content)
                    response_content = f"HTML minified: {len(result)} chars"
                elif "js" in content_lower or "javascript" in content_lower:
                    result = await self.minify_javascript(code or message.content)
                    response_content = f"JavaScript minified: {len(result)} chars"
                else:
                    response_content = (
                        "Please specify what to minify: css, html, or javascript"
                    )
            elif "performance" in content_lower or "suggest" in content_lower:
                suggestions = await self.suggest_improvements(
                    code or message.content, "auto"
                )
                response_content = f"Performance suggestions: {suggestions[:500]}"
            else:
                # General optimization request
                response = await self.get_ai_response(
                    f"Help with this optimization request: {message.content}"
                )
                response_content = response

        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            response_content = f"Optimization failed: {str(e)}"
            await self._set_error(str(e))

        await self._set_idle()

        return Message(
            from_agent=self.name,
            to_agent=message.from_agent,
            content=response_content,
            message_type="response",
            timestamp=datetime.utcnow(),
        )

    async def send_message(
        self,
        to_agent: str,
        content: str,
        message_type: str = "request",
    ) -> bool:
        """
        Send a message to another agent.

        Args:
            to_agent: Target agent name.
            content: Message content.
            message_type: Type of message.

        Returns:
            bool: True if sent successfully.
        """
        if not self._message_bus:
            self.logger.warning("No message bus configured")
            return False

        await self._log_activity("Sending message", f"To: {to_agent}")
        return True

    async def receive_message(self, message: Message) -> None:
        """
        Handle a received message.

        Args:
            message: The received message.
        """
        await self._log_activity(
            "Received message",
            f"From: {message.from_agent}",
        )

    async def minify_html(self, html: str) -> str:
        """
        Minify HTML code.

        Args:
            html: The HTML code to minify.

        Returns:
            str: Minified HTML.
        """
        await self._set_busy("Minifying HTML")

        original_size = len(html)

        # Remove HTML comments (but not conditional comments)
        minified = re.sub(r"<!--(?!\[if).*?-->", "", html, flags=re.DOTALL)

        # Remove whitespace between tags
        minified = re.sub(r">\s+<", "><", minified)

        # Remove leading/trailing whitespace on lines
        lines = [line.strip() for line in minified.split("\n")]
        minified = "".join(lines)

        # Remove multiple spaces
        minified = re.sub(r"\s{2,}", " ", minified)

        # Track statistics
        optimized_size = len(minified)
        self._record_optimization("html", original_size, optimized_size)

        await self._set_idle()
        return minified

    async def minify_css(self, css: str) -> str:
        """
        Minify CSS code.

        Args:
            css: The CSS code to minify.

        Returns:
            str: Minified CSS.
        """
        await self._set_busy("Minifying CSS")

        original_size = len(css)

        # Remove comments
        minified = re.sub(r"/\*[\s\S]*?\*/", "", css)

        # Remove whitespace around special characters
        minified = re.sub(r"\s*([{}:;,>+~])\s*", r"\1", minified)

        # Remove whitespace at start/end of lines
        lines = [line.strip() for line in minified.split("\n")]
        minified = "".join(lines)

        # Remove last semicolon before closing brace
        minified = re.sub(r";\}", "}", minified)

        # Remove newlines
        minified = minified.replace("\n", "")

        # Remove multiple spaces
        minified = re.sub(r"\s{2,}", " ", minified)

        # Track statistics
        optimized_size = len(minified)
        self._record_optimization("css", original_size, optimized_size)

        await self._set_idle()
        return minified

    async def minify_javascript(self, js: str) -> str:
        """
        Minify JavaScript code.

        Note: This is a basic minification. For production, use a proper
        minifier like Terser.

        Args:
            js: The JavaScript code to minify.

        Returns:
            str: Minified JavaScript.
        """
        await self._set_busy("Minifying JavaScript")

        original_size = len(js)

        # Remove single-line comments (but not URLs)
        minified = re.sub(r"(?<!:)//.*$", "", js, flags=re.MULTILINE)

        # Remove multi-line comments
        minified = re.sub(r"/\*[\s\S]*?\*/", "", minified)

        # Remove leading/trailing whitespace on lines
        lines = [line.strip() for line in minified.split("\n") if line.strip()]
        minified = " ".join(lines)

        # Remove multiple spaces
        minified = re.sub(r"\s{2,}", " ", minified)

        # Track statistics
        optimized_size = len(minified)
        self._record_optimization("javascript", original_size, optimized_size)

        await self._set_idle()
        return minified

    async def suggest_improvements(
        self,
        code: str,
        language: str = "auto",
    ) -> str:
        """
        Suggest performance improvements for code.

        Args:
            code: The code to analyze.
            language: Programming language or 'auto' to detect.

        Returns:
            str: Performance improvement suggestions.
        """
        await self._set_busy("Analyzing for improvements")

        prompt = f"""Analyze this code for performance improvements:

```{language}
{code[:3000]}
```

Provide specific, actionable suggestions for:
1. Code efficiency improvements
2. Memory usage optimization
3. Load time optimization
4. Best practices for production

Be concise and practical. Focus on the most impactful improvements."""

        try:
            response = await self.get_ai_response(prompt)
            await self._set_idle()
            return response
        except Exception as e:
            self.logger.error(f"Improvement analysis failed: {e}")
            await self._set_idle()
            return self._get_generic_suggestions(language)

    def _get_generic_suggestions(self, language: str) -> str:
        """Get generic performance suggestions."""
        return """Performance Improvement Suggestions:

1. **Code Efficiency**
   - Minimize DOM manipulations
   - Use efficient selectors
   - Avoid unnecessary loops

2. **Memory Usage**
   - Remove unused variables
   - Clear event listeners when not needed
   - Avoid memory leaks in closures

3. **Load Time**
   - Minify CSS and JavaScript
   - Optimize images
   - Use lazy loading for heavy resources

4. **Best Practices**
   - Use caching where appropriate
   - Implement code splitting
   - Enable compression (gzip/brotli)
"""

    async def optimize_for_production(
        self,
        files: dict[str, str],
    ) -> dict[str, str]:
        """
        Optimize a set of files for production.

        Args:
            files: Dictionary mapping file paths to content.

        Returns:
            dict: Optimized files.
        """
        await self._set_busy("Optimizing for production")

        optimized: dict[str, str] = {}

        for file_path, content in files.items():
            ext = file_path.split(".")[-1].lower() if "." in file_path else ""

            if ext == "html" or ext == "htm":
                optimized[file_path] = await self.minify_html(content)
            elif ext == "css":
                optimized[file_path] = await self.minify_css(content)
            elif ext == "js":
                optimized[file_path] = await self.minify_javascript(content)
            else:
                optimized[file_path] = content

        await self._set_idle()
        return optimized

    async def analyze_bundle_size(
        self,
        files: dict[str, str],
    ) -> dict[str, Any]:
        """
        Analyze the bundle size of project files.

        Args:
            files: Dictionary mapping file paths to content.

        Returns:
            dict: Bundle analysis results.
        """
        await self._set_busy("Analyzing bundle size")

        analysis = {
            "total_size": 0,
            "by_type": {},
            "files": [],
            "recommendations": [],
        }

        for file_path, content in files.items():
            size = len(content)
            ext = file_path.split(".")[-1].lower() if "." in file_path else "other"

            analysis["total_size"] += size
            analysis["by_type"][ext] = analysis["by_type"].get(ext, 0) + size
            analysis["files"].append({
                "path": file_path,
                "size": size,
                "type": ext,
            })

        # Sort files by size
        analysis["files"].sort(key=lambda x: x["size"], reverse=True)

        # Generate recommendations
        total_kb = analysis["total_size"] / 1024

        if total_kb > 500:
            analysis["recommendations"].append(
                "Consider code splitting to reduce initial bundle size"
            )
        if analysis["by_type"].get("js", 0) > 100 * 1024:
            analysis["recommendations"].append(
                "JavaScript bundle is large. Consider tree shaking."
            )
        if analysis["by_type"].get("css", 0) > 50 * 1024:
            analysis["recommendations"].append(
                "CSS is large. Consider using CSS modules or purging unused styles."
            )

        await self._set_idle()
        return analysis

    async def generate_optimization_report(self) -> dict[str, Any]:
        """
        Generate a report of all optimizations performed.

        Returns:
            dict: Optimization report.
        """
        total_savings = (
            self._stats["total_original_size"] - self._stats["total_optimized_size"]
        )
        savings_percent = 0
        if self._stats["total_original_size"] > 0:
            savings_percent = (
                total_savings / self._stats["total_original_size"]
            ) * 100

        return {
            "total_files_optimized": self._stats["total_files"],
            "total_original_size": self._stats["total_original_size"],
            "total_optimized_size": self._stats["total_optimized_size"],
            "total_savings_bytes": total_savings,
            "savings_percentage": round(savings_percent, 2),
            "history": self._optimization_history[-10:],  # Last 10 optimizations
        }

    def _record_optimization(
        self,
        file_type: str,
        original_size: int,
        optimized_size: int,
    ) -> None:
        """Record an optimization for statistics."""
        self._stats["total_files"] += 1
        self._stats["total_original_size"] += original_size
        self._stats["total_optimized_size"] += optimized_size

        self._optimization_history.append({
            "type": file_type,
            "original_size": original_size,
            "optimized_size": optimized_size,
            "savings": original_size - optimized_size,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def get_stats(self) -> dict[str, Any]:
        """Get optimization statistics."""
        return self._stats.copy()

    def clear_stats(self) -> None:
        """Clear optimization statistics."""
        self._stats = {
            "total_files": 0,
            "total_original_size": 0,
            "total_optimized_size": 0,
        }
        self._optimization_history.clear()
