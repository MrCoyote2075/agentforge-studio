"""
AgentForge Studio - Designer Agent.

The Designer Agent creates color schemes, defines typography and spacing,
and generates CSS variables for consistent styling.
"""

from datetime import datetime
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import Message


class DesignerAgent(BaseAgent):
    """
    Designer Agent that handles visual design tasks.

    The Designer creates color schemes, defines typography, spacing systems,
    and generates CSS variables for consistent styling across projects.

    Attributes:
        color_palettes: Dictionary of generated color palettes.
        design_tokens: Dictionary of design tokens.

    Example:
        >>> designer = DesignerAgent()
        >>> palette = await designer.create_color_scheme("modern", "blue")
    """

    # Predefined color harmonies
    COLOR_HARMONIES = {
        "complementary": "colors opposite on the color wheel",
        "analogous": "colors adjacent on the color wheel",
        "triadic": "three colors equally spaced on the color wheel",
        "split-complementary": "a color and two colors adjacent to its complement",
        "monochromatic": "variations of a single color",
    }

    # Typography scale ratios
    TYPE_SCALES = {
        "minor-second": 1.067,
        "major-second": 1.125,
        "minor-third": 1.200,
        "major-third": 1.250,
        "perfect-fourth": 1.333,
        "augmented-fourth": 1.414,
        "perfect-fifth": 1.500,
        "golden-ratio": 1.618,
    }

    def __init__(
        self,
        name: str = "DesignerAgent",
        model: str = "gemini-pro",
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Designer agent.

        Args:
            name: The agent's name. Defaults to 'DesignerAgent'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._color_palettes: dict[str, dict[str, str]] = {}
        self._design_tokens: dict[str, Any] = {}

    async def process(self, message: Message) -> Message:
        """
        Process a design request.

        Args:
            message: The incoming message with design requirements.

        Returns:
            Message: Response with design output.
        """
        await self._set_busy(f"Designing: {message.content[:50]}")

        try:
            content = message.content.lower()

            if "color" in content or "palette" in content:
                style = "modern"
                primary_color = "blue"
                palette = await self.create_color_scheme(style, primary_color)
                response_content = (
                    f"Color palette created with {len(palette)} colors.\n"
                    f"Primary: {palette.get('primary', 'N/A')}"
                )
            elif "typography" in content or "font" in content:
                typography = await self.create_typography_system()
                font_family = typography.get('font_family', 'system')
                response_content = f"Typography system created: {font_family}"
            elif "spacing" in content:
                spacing = await self.create_spacing_system()
                response_content = f"Spacing system created with {len(spacing)} values."
            elif "css" in content or "variables" in content:
                css_vars = await self.generate_css_variables()
                response_content = f"CSS variables generated ({len(css_vars)} chars)"
            else:
                # General design request
                response = await self.get_ai_response(
                    f"Help with this design request: {message.content}"
                )
                response_content = response

        except Exception as e:
            self.logger.error(f"Design task failed: {e}")
            response_content = f"Design task failed: {str(e)}"
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

    async def create_color_scheme(
        self,
        style: str = "modern",
        primary_color: str = "blue",
        harmony: str = "complementary",
    ) -> dict[str, str]:
        """
        Create a color scheme based on style and primary color.

        Args:
            style: Design style (modern, classic, minimal, vibrant).
            primary_color: Base primary color.
            harmony: Color harmony type.

        Returns:
            dict: Color palette with named colors.
        """
        await self._set_busy(f"Creating {style} color scheme")

        # Default color palette
        palette = {
            "primary": "#3B82F6",
            "primary-light": "#60A5FA",
            "primary-dark": "#2563EB",
            "secondary": "#8B5CF6",
            "secondary-light": "#A78BFA",
            "secondary-dark": "#7C3AED",
            "accent": "#F59E0B",
            "background": "#FFFFFF",
            "surface": "#F3F4F6",
            "text": "#1F2937",
            "text-muted": "#6B7280",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "info": "#3B82F6",
        }

        try:
            prompt = f"""Create a {style} color scheme with {primary_color} as \
the primary color.
Use {harmony} color harmony.

Provide colors in hex format for:
- primary, primary-light, primary-dark
- secondary, secondary-light, secondary-dark
- accent
- background, surface
- text, text-muted
- success, warning, error, info

Return as JSON object with color names as keys and hex values as values.
Only return the JSON, no explanation."""

            response = await self.get_ai_response(prompt)

            # Try to parse JSON from response
            import json
            import re

            # Extract JSON from response
            json_match = re.search(r"\{[^{}]+\}", response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                palette.update(parsed)

        except Exception as e:
            self.logger.warning(f"Could not generate custom palette: {e}")

        self._color_palettes[f"{style}_{primary_color}"] = palette
        self._design_tokens["colors"] = palette

        await self._set_idle()
        return palette

    async def create_typography_system(
        self,
        base_size: int = 16,
        scale: str = "major-third",
        font_family: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a typography system with scaled sizes.

        Args:
            base_size: Base font size in pixels.
            scale: Typography scale ratio name.
            font_family: Optional font family.

        Returns:
            dict: Typography system with sizes and settings.
        """
        await self._set_busy("Creating typography system")

        ratio = self.TYPE_SCALES.get(scale, 1.250)

        # Generate sizes based on scale
        sizes = {
            "xs": round(base_size / (ratio ** 2)),
            "sm": round(base_size / ratio),
            "base": base_size,
            "lg": round(base_size * ratio),
            "xl": round(base_size * (ratio ** 2)),
            "2xl": round(base_size * (ratio ** 3)),
            "3xl": round(base_size * (ratio ** 4)),
            "4xl": round(base_size * (ratio ** 5)),
        }

        # Font families
        default_font = (
            "system-ui, -apple-system, BlinkMacSystemFont, "
            "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
        )
        mono_font = (
            "'SF Mono', SFMono-Regular, ui-monospace, Menlo, Monaco, "
            "'Cascadia Code', 'Source Code Pro', monospace"
        )

        typography = {
            "font_family": font_family or default_font,
            "font_family_mono": mono_font,
            "base_size": base_size,
            "scale": scale,
            "scale_ratio": ratio,
            "sizes": sizes,
            "line_heights": {
                "tight": 1.25,
                "normal": 1.5,
                "relaxed": 1.75,
            },
            "font_weights": {
                "normal": 400,
                "medium": 500,
                "semibold": 600,
                "bold": 700,
            },
            "letter_spacing": {
                "tight": "-0.025em",
                "normal": "0",
                "wide": "0.025em",
            },
        }

        self._design_tokens["typography"] = typography

        await self._set_idle()
        return typography

    async def create_spacing_system(
        self,
        base_unit: int = 4,
    ) -> dict[str, int]:
        """
        Create a spacing system based on a base unit.

        Args:
            base_unit: Base spacing unit in pixels.

        Returns:
            dict: Spacing scale.
        """
        await self._set_busy("Creating spacing system")

        spacing = {
            "0": 0,
            "px": 1,
            "0.5": base_unit // 2,
            "1": base_unit,
            "1.5": base_unit + base_unit // 2,
            "2": base_unit * 2,
            "2.5": base_unit * 2 + base_unit // 2,
            "3": base_unit * 3,
            "4": base_unit * 4,
            "5": base_unit * 5,
            "6": base_unit * 6,
            "8": base_unit * 8,
            "10": base_unit * 10,
            "12": base_unit * 12,
            "16": base_unit * 16,
            "20": base_unit * 20,
            "24": base_unit * 24,
            "32": base_unit * 32,
            "40": base_unit * 40,
            "48": base_unit * 48,
            "64": base_unit * 64,
        }

        self._design_tokens["spacing"] = spacing

        await self._set_idle()
        return spacing

    async def generate_css_variables(
        self,
        prefix: str = "",
    ) -> str:
        """
        Generate CSS custom properties from design tokens.

        Args:
            prefix: Optional prefix for CSS variable names.

        Returns:
            str: CSS custom properties declaration.
        """
        await self._set_busy("Generating CSS variables")

        # Ensure we have design tokens
        if "colors" not in self._design_tokens:
            await self.create_color_scheme()
        if "typography" not in self._design_tokens:
            await self.create_typography_system()
        if "spacing" not in self._design_tokens:
            await self.create_spacing_system()

        css_lines = [":root {"]

        # Color variables
        colors = self._design_tokens.get("colors", {})
        for name, value in colors.items():
            var_name = f"--{prefix}color-{name}" if prefix else f"--color-{name}"
            css_lines.append(f"  {var_name}: {value};")

        css_lines.append("")

        # Typography variables
        typography = self._design_tokens.get("typography", {})
        sizes = typography.get("sizes", {})
        for name, value in sizes.items():
            if prefix:
                var_name = f"--{prefix}font-size-{name}"
            else:
                var_name = f"--font-size-{name}"
            css_lines.append(f"  {var_name}: {value}px;")

        if typography.get("font_family"):
            var_name = f"--{prefix}font-family" if prefix else "--font-family"
            css_lines.append(f"  {var_name}: {typography['font_family']};")

        css_lines.append("")

        # Spacing variables
        spacing = self._design_tokens.get("spacing", {})
        for name, value in spacing.items():
            var_name = f"--{prefix}spacing-{name}" if prefix else f"--spacing-{name}"
            css_lines.append(f"  {var_name}: {value}px;")

        css_lines.append("}")

        css_content = "\n".join(css_lines)

        await self._set_idle()
        return css_content

    async def generate_design_system(
        self,
        project_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a complete design system.

        Args:
            project_info: Optional project information.

        Returns:
            dict: Complete design system with all tokens.
        """
        await self._set_busy("Generating design system")

        style = project_info.get("style", "modern") if project_info else "modern"
        primary = project_info.get("primary_color", "blue") if project_info else "blue"

        # Generate all components
        colors = await self.create_color_scheme(style, primary)
        typography = await self.create_typography_system()
        spacing = await self.create_spacing_system()
        css_variables = await self.generate_css_variables()

        design_system = {
            "colors": colors,
            "typography": typography,
            "spacing": spacing,
            "css_variables": css_variables,
            "breakpoints": {
                "sm": "640px",
                "md": "768px",
                "lg": "1024px",
                "xl": "1280px",
                "2xl": "1536px",
            },
            "shadows": {
                "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
                "base": (
                    "0 1px 3px 0 rgba(0, 0, 0, 0.1), "
                    "0 1px 2px 0 rgba(0, 0, 0, 0.06)"
                ),
                "md": (
                    "0 4px 6px -1px rgba(0, 0, 0, 0.1), "
                    "0 2px 4px -1px rgba(0, 0, 0, 0.06)"
                ),
                "lg": (
                    "0 10px 15px -3px rgba(0, 0, 0, 0.1), "
                    "0 4px 6px -2px rgba(0, 0, 0, 0.05)"
                ),
                "xl": (
                    "0 20px 25px -5px rgba(0, 0, 0, 0.1), "
                    "0 10px 10px -5px rgba(0, 0, 0, 0.04)"
                ),
            },
            "border_radius": {
                "none": "0",
                "sm": "0.125rem",
                "base": "0.25rem",
                "md": "0.375rem",
                "lg": "0.5rem",
                "xl": "0.75rem",
                "2xl": "1rem",
                "full": "9999px",
            },
        }

        await self._set_idle()
        return design_system

    async def get_design_tokens(self) -> dict[str, Any]:
        """Get all design tokens."""
        return self._design_tokens.copy()

    async def get_color_palettes(self) -> dict[str, dict[str, str]]:
        """Get all generated color palettes."""
        return self._color_palettes.copy()

    def clear_tokens(self) -> None:
        """Clear all design tokens."""
        self._design_tokens.clear()
        self._color_palettes.clear()
