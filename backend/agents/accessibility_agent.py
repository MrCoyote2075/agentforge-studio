"""
AgentForge Studio - Accessibility Agent.

The Accessibility Agent performs WCAG compliance audits, adds ARIA labels,
and checks color contrast for accessibility compliance.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import Message


class WCAGLevel(str, Enum):
    """WCAG compliance levels."""

    A = "A"
    AA = "AA"
    AAA = "AAA"


class AccessibilityIssue:
    """Represents an accessibility issue."""

    def __init__(
        self,
        rule: str,
        severity: str,
        description: str,
        wcag_criterion: str | None = None,
        element: str | None = None,
        line_number: int | None = None,
        recommendation: str | None = None,
    ) -> None:
        """
        Initialize an accessibility issue.

        Args:
            rule: The accessibility rule violated.
            severity: Severity level (critical, serious, moderate, minor).
            description: Description of the issue.
            wcag_criterion: WCAG success criterion reference.
            element: The HTML element with the issue.
            line_number: Optional line number.
            recommendation: Optional fix recommendation.
        """
        self.rule = rule
        self.severity = severity
        self.description = description
        self.wcag_criterion = wcag_criterion
        self.element = element
        self.line_number = line_number
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rule": self.rule,
            "severity": self.severity,
            "description": self.description,
            "wcag_criterion": self.wcag_criterion,
            "element": self.element,
            "line_number": self.line_number,
            "recommendation": self.recommendation,
        }


class AccessibilityAgent(BaseAgent):
    """
    Accessibility Agent that checks WCAG compliance.

    The Accessibility Agent performs WCAG compliance audits, adds ARIA labels,
    checks color contrast, and suggests accessibility improvements.

    Attributes:
        issues: List of accessibility issues found.
        audit_history: History of accessibility audits.

    Example:
        >>> a11y = AccessibilityAgent()
        >>> issues = await a11y.audit_html(html_code)
    """

    # Common accessibility rules to check
    ACCESSIBILITY_RULES = {
        "img-alt": {
            "description": "Images must have alt attributes",
            "wcag": "1.1.1",
            "severity": "critical",
        },
        "button-name": {
            "description": "Buttons must have accessible names",
            "wcag": "4.1.2",
            "severity": "critical",
        },
        "link-name": {
            "description": "Links must have accessible names",
            "wcag": "2.4.4",
            "severity": "critical",
        },
        "form-label": {
            "description": "Form inputs must have labels",
            "wcag": "1.3.1",
            "severity": "critical",
        },
        "heading-order": {
            "description": "Heading levels should not be skipped",
            "wcag": "1.3.1",
            "severity": "moderate",
        },
        "html-lang": {
            "description": "HTML should have a lang attribute",
            "wcag": "3.1.1",
            "severity": "serious",
        },
        "meta-viewport": {
            "description": "Viewport should not disable zoom",
            "wcag": "1.4.4",
            "severity": "serious",
        },
    }

    def __init__(
        self,
        name: str = "AccessibilityAgent",
        model: str = "gemini-pro",
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Accessibility agent.

        Args:
            name: The agent's name. Defaults to 'AccessibilityAgent'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._issues: list[AccessibilityIssue] = []
        self._audit_history: list[dict[str, Any]] = []

    async def process(self, message: Message) -> Message:
        """
        Process an accessibility check request.

        Args:
            message: The incoming message with HTML to check.

        Returns:
            Message: Response with accessibility findings.
        """
        await self._set_busy(f"Accessibility check: {message.content[:50]}")

        try:
            # Perform accessibility audit
            issues = await self.audit_html(message.content)

            critical_count = sum(1 for i in issues if i.severity == "critical")
            serious_count = sum(1 for i in issues if i.severity == "serious")

            if issues:
                response_content = (
                    f"Accessibility audit complete. Found {len(issues)} issues:\n"
                    f"- Critical: {critical_count}\n"
                    f"- Serious: {serious_count}\n"
                    f"- Other: {len(issues) - critical_count - serious_count}"
                )
            else:
                response_content = "Accessibility audit complete. No issues found."

        except Exception as e:
            self.logger.error(f"Accessibility audit failed: {e}")
            response_content = f"Accessibility audit failed: {str(e)}"
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

    async def audit_html(
        self,
        html: str,
        level: WCAGLevel = WCAGLevel.AA,
    ) -> list[AccessibilityIssue]:
        """
        Perform a WCAG compliance audit on HTML.

        Args:
            html: The HTML code to audit.
            level: WCAG compliance level to check against.

        Returns:
            list: List of accessibility issues found.
        """
        await self._set_busy(f"Auditing for WCAG {level.value}")

        issues: list[AccessibilityIssue] = []

        # Check for images without alt
        issues.extend(self._check_img_alt(html))

        # Check for buttons without accessible names
        issues.extend(self._check_button_names(html))

        # Check for links without accessible names
        issues.extend(self._check_link_names(html))

        # Check for form inputs without labels
        issues.extend(self._check_form_labels(html))

        # Check for html lang attribute
        issues.extend(self._check_html_lang(html))

        # Check for heading order
        issues.extend(self._check_heading_order(html))

        # Check for viewport meta tag issues
        issues.extend(self._check_viewport(html))

        # Store issues and update history
        self._issues.extend(issues)
        self._audit_history.append({
            "level": level.value,
            "timestamp": datetime.utcnow().isoformat(),
            "issues_count": len(issues),
        })

        await self._set_idle()
        return issues

    def _check_img_alt(self, html: str) -> list[AccessibilityIssue]:
        """Check for images missing alt attributes."""
        issues = []
        lines = html.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Find img tags
            img_matches = re.finditer(r"<img[^>]*>", line, re.IGNORECASE)
            for match in img_matches:
                img_tag = match.group()
                # Check if alt attribute exists
                if "alt=" not in img_tag.lower():
                    issues.append(
                        AccessibilityIssue(
                            rule="img-alt",
                            severity="critical",
                            description="Image missing alt attribute",
                            wcag_criterion="1.1.1",
                            element=img_tag[:100],
                            line_number=line_num,
                            recommendation=(
                                "Add an alt attribute describing the image content. "
                                "Use alt='' for decorative images."
                            ),
                        )
                    )

        return issues

    def _check_button_names(self, html: str) -> list[AccessibilityIssue]:
        """Check for buttons without accessible names."""
        issues = []
        lines = html.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Find empty buttons
            button_matches = re.finditer(
                r"<button[^>]*>\s*</button>", line, re.IGNORECASE
            )
            for match in button_matches:
                button_tag = match.group()
                if "aria-label" not in button_tag.lower():
                    issues.append(
                        AccessibilityIssue(
                            rule="button-name",
                            severity="critical",
                            description="Button has no accessible name",
                            wcag_criterion="4.1.2",
                            element=button_tag[:100],
                            line_number=line_num,
                            recommendation=(
                                "Add visible text content or aria-label to the button."
                            ),
                        )
                    )

        return issues

    def _check_link_names(self, html: str) -> list[AccessibilityIssue]:
        """Check for links without accessible names."""
        issues = []
        lines = html.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Find empty links or links with only images
            link_matches = re.finditer(r"<a[^>]*>\s*</a>", line, re.IGNORECASE)
            for match in link_matches:
                link_tag = match.group()
                if "aria-label" not in link_tag.lower():
                    issues.append(
                        AccessibilityIssue(
                            rule="link-name",
                            severity="critical",
                            description="Link has no accessible name",
                            wcag_criterion="2.4.4",
                            element=link_tag[:100],
                            line_number=line_num,
                            recommendation=(
                                "Add visible text content or aria-label to the link."
                            ),
                        )
                    )

        return issues

    def _check_form_labels(self, html: str) -> list[AccessibilityIssue]:
        """Check for form inputs without labels."""
        issues = []

        # Find all input elements with IDs
        inputs = re.findall(r'<input[^>]*id=["\']([^"\']+)["\'][^>]*>', html)

        for input_id in inputs:
            # Check if there's a corresponding label
            label_pattern = f'<label[^>]*for=["\']?{re.escape(input_id)}["\']?'
            if not re.search(label_pattern, html, re.IGNORECASE):
                # Also check for aria-label or aria-labelledby
                input_pattern = f'<input[^>]*id=["\']?{re.escape(input_id)}["\']?[^>]*>'
                input_match = re.search(input_pattern, html)
                if input_match:
                    input_tag = input_match.group()
                    if (
                        "aria-label" not in input_tag.lower()
                        and "aria-labelledby" not in input_tag.lower()
                    ):
                        issues.append(
                            AccessibilityIssue(
                                rule="form-label",
                                severity="critical",
                                description=f"Input '{input_id}' missing label",
                                wcag_criterion="1.3.1",
                                element=input_tag[:100],
                                recommendation=(
                                    "Add a <label for='id'> element or "
                                    "aria-label attribute."
                                ),
                            )
                        )

        return issues

    def _check_html_lang(self, html: str) -> list[AccessibilityIssue]:
        """Check for html lang attribute."""
        issues = []

        # Find html tag
        html_match = re.search(r"<html[^>]*>", html, re.IGNORECASE)
        if html_match:
            html_tag = html_match.group()
            if "lang=" not in html_tag.lower():
                issues.append(
                    AccessibilityIssue(
                        rule="html-lang",
                        severity="serious",
                        description="HTML element missing lang attribute",
                        wcag_criterion="3.1.1",
                        element=html_tag[:100],
                        recommendation=(
                            "Add lang attribute to <html> element. "
                            "Example: <html lang='en'>"
                        ),
                    )
                )

        return issues

    def _check_heading_order(self, html: str) -> list[AccessibilityIssue]:
        """Check for proper heading order (h1-h6)."""
        issues = []

        # Find all heading tags
        headings = re.findall(r"<h([1-6])[^>]*>", html, re.IGNORECASE)

        if headings:
            prev_level = 0
            for heading_level in headings:
                level = int(heading_level)
                if prev_level > 0 and level > prev_level + 1:
                    issues.append(
                        AccessibilityIssue(
                            rule="heading-order",
                            severity="moderate",
                            description=(
                                f"Heading level skipped: h{prev_level} to h{level}"
                            ),
                            wcag_criterion="1.3.1",
                            recommendation=(
                                f"Use h{prev_level + 1} instead of h{level} "
                                "to maintain proper heading hierarchy."
                            ),
                        )
                    )
                prev_level = level

        return issues

    def _check_viewport(self, html: str) -> list[AccessibilityIssue]:
        """Check for viewport meta tag issues."""
        issues = []

        # Find viewport meta tag
        viewport_match = re.search(
            r'<meta[^>]*name=["\']?viewport["\']?[^>]*>', html, re.IGNORECASE
        )

        if viewport_match:
            viewport_tag = viewport_match.group()
            if "user-scalable=no" in viewport_tag.lower():
                issues.append(
                    AccessibilityIssue(
                        rule="meta-viewport",
                        severity="serious",
                        description="Viewport disables user zoom (user-scalable=no)",
                        wcag_criterion="1.4.4",
                        element=viewport_tag[:100],
                        recommendation=(
                            "Remove user-scalable=no to allow users to zoom the page."
                        ),
                    )
                )
            if "maximum-scale=1" in viewport_tag.lower():
                issues.append(
                    AccessibilityIssue(
                        rule="meta-viewport",
                        severity="serious",
                        description="Viewport restricts zoom (maximum-scale=1)",
                        wcag_criterion="1.4.4",
                        element=viewport_tag[:100],
                        recommendation=(
                            "Remove maximum-scale=1 to allow users to zoom the page."
                        ),
                    )
                )

        return issues

    async def add_aria_labels(
        self,
        html: str,
    ) -> str:
        """
        Add ARIA labels to improve accessibility.

        Args:
            html: The HTML code to enhance.

        Returns:
            str: HTML with ARIA labels added.
        """
        await self._set_busy("Adding ARIA labels")

        enhanced = html

        # Add aria-label to images without alt
        enhanced = re.sub(
            r'<img(?![^>]*alt=)([^>]*)>',
            r'<img alt="" aria-hidden="true"\1>',
            enhanced,
        )

        # Add role="navigation" to nav elements without role
        enhanced = re.sub(
            r'<nav(?![^>]*role=)([^>]*)>',
            r'<nav role="navigation"\1>',
            enhanced,
        )

        # Add role="main" to main elements without role
        enhanced = re.sub(
            r'<main(?![^>]*role=)([^>]*)>',
            r'<main role="main"\1>',
            enhanced,
        )

        await self._set_idle()
        return enhanced

    async def check_color_contrast(
        self,
        foreground: str,
        background: str,
    ) -> dict[str, Any]:
        """
        Check color contrast ratio.

        Args:
            foreground: Foreground color (hex).
            background: Background color (hex).

        Returns:
            dict: Contrast check results.
        """
        await self._set_busy("Checking color contrast")

        def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
            """Convert hex color to RGB."""
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        def luminance(r: int, g: int, b: int) -> float:
            """Calculate relative luminance."""

            def adjust(c: int) -> float:
                c = c / 255
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

            return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

        try:
            fg_rgb = hex_to_rgb(foreground)
            bg_rgb = hex_to_rgb(background)

            fg_lum = luminance(*fg_rgb)
            bg_lum = luminance(*bg_rgb)

            lighter = max(fg_lum, bg_lum)
            darker = min(fg_lum, bg_lum)
            ratio = (lighter + 0.05) / (darker + 0.05)

            result = {
                "foreground": foreground,
                "background": background,
                "ratio": round(ratio, 2),
                "passes_aa_normal": ratio >= 4.5,
                "passes_aa_large": ratio >= 3,
                "passes_aaa_normal": ratio >= 7,
                "passes_aaa_large": ratio >= 4.5,
            }

        except Exception as e:
            self.logger.error(f"Color contrast check failed: {e}")
            result = {
                "error": str(e),
                "foreground": foreground,
                "background": background,
            }

        await self._set_idle()
        return result

    async def get_accessibility_report(self) -> dict[str, Any]:
        """Generate an accessibility report."""
        critical = sum(1 for i in self._issues if i.severity == "critical")
        serious = sum(1 for i in self._issues if i.severity == "serious")

        return {
            "total_audits": len(self._audit_history),
            "total_issues": len(self._issues),
            "by_severity": {
                "critical": critical,
                "serious": serious,
                "moderate": sum(1 for i in self._issues if i.severity == "moderate"),
                "minor": sum(1 for i in self._issues if i.severity == "minor"),
            },
            "issues": [i.to_dict() for i in self._issues[-20:]],  # Last 20 issues
        }

    async def get_issues(self) -> list[dict[str, Any]]:
        """Get all accessibility issues."""
        return [i.to_dict() for i in self._issues]

    def clear_issues(self) -> None:
        """Clear all accessibility issues."""
        self._issues.clear()
        self._audit_history.clear()
