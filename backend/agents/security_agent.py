"""
AgentForge Studio - Security Agent.

The Security Agent reviews code for security vulnerabilities,
checks for XSS, validates input handling, and identifies hardcoded secrets.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import Message


class SecuritySeverity(str, Enum):
    """Severity levels for security findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityCategory(str, Enum):
    """Categories of security issues."""

    XSS = "xss"
    INJECTION = "injection"
    HARDCODED_SECRET = "hardcoded_secret"
    INPUT_VALIDATION = "input_validation"
    INSECURE_CRYPTO = "insecure_crypto"
    SENSITIVE_DATA = "sensitive_data"
    MISCONFIGURATION = "misconfiguration"
    OTHER = "other"


class SecurityFinding:
    """Represents a security vulnerability finding."""

    def __init__(
        self,
        category: SecurityCategory,
        severity: SecuritySeverity,
        description: str,
        line_number: int | None = None,
        code_snippet: str | None = None,
        recommendation: str | None = None,
    ) -> None:
        """
        Initialize a security finding.

        Args:
            category: The category of the security issue.
            severity: The severity level.
            description: Description of the issue.
            line_number: Optional line number.
            code_snippet: Optional code snippet.
            recommendation: Optional fix recommendation.
        """
        self.category = category
        self.severity = severity
        self.description = description
        self.line_number = line_number
        self.code_snippet = code_snippet
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
        }


class SecurityAgent(BaseAgent):
    """
    Security Agent that reviews code for vulnerabilities.

    The Security Agent analyzes code for XSS vulnerabilities, SQL injection,
    hardcoded secrets, and other security issues. It provides recommendations
    for secure coding practices.

    Attributes:
        findings: List of security findings.
        audit_history: History of security audits.

    Example:
        >>> security = SecurityAgent()
        >>> findings = await security.review_code(code, "script.js")
    """

    # Patterns for detecting potential secrets
    SECRET_PATTERNS = [
        (r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']', "API key"),
        (r'password\s*[=:]\s*["\'][^"\']+["\']', "Password"),
        (r'secret\s*[=:]\s*["\'][^"\']+["\']', "Secret"),
        (r'token\s*[=:]\s*["\'][^"\']+["\']', "Token"),
        (r'private[_-]?key\s*[=:]\s*["\'][^"\']+["\']', "Private key"),
        (r'aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*["\'][^"\']+["\']', "AWS key"),
        (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub token"),
    ]

    # Patterns for detecting XSS vulnerabilities
    XSS_PATTERNS = [
        (r'innerHTML\s*=', "innerHTML assignment"),
        (r'document\.write\s*\(', "document.write"),
        (r'eval\s*\(', "eval usage"),
        (r'v-html\s*=', "Vue v-html directive"),
        (r'dangerouslySetInnerHTML', "React dangerouslySetInnerHTML"),
    ]

    def __init__(
        self,
        name: str = "SecurityAgent",
        model: str = "gemini-pro",
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Security agent.

        Args:
            name: The agent's name. Defaults to 'SecurityAgent'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._findings: list[SecurityFinding] = []
        self._audit_history: list[dict[str, Any]] = []

    async def process(self, message: Message) -> Message:
        """
        Process a security review request.

        Args:
            message: The incoming message with code to review.

        Returns:
            Message: Response with security findings.
        """
        await self._set_busy(f"Security review: {message.content[:50]}")

        try:
            # Perform security review
            file_path = (
                message.metadata.get("file_path", "unknown")
                if message.metadata
                else "unknown"
            )
            findings = await self.review_code(message.content, file_path)

            if findings:
                critical_count = sum(
                    1 for f in findings if f.severity == SecuritySeverity.CRITICAL
                )
                high_count = sum(
                    1 for f in findings if f.severity == SecuritySeverity.HIGH
                )
                response_content = (
                    f"Security review complete. Found {len(findings)} issues:\n"
                    f"- Critical: {critical_count}\n"
                    f"- High: {high_count}\n"
                    f"- Other: {len(findings) - critical_count - high_count}"
                )
            else:
                response_content = "Security review complete. No issues found."

        except Exception as e:
            self.logger.error(f"Security review failed: {e}")
            response_content = f"Security review failed: {str(e)}"
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

    async def review_code(
        self,
        code: str,
        file_path: str,
    ) -> list[SecurityFinding]:
        """
        Review code for security vulnerabilities.

        Args:
            code: The code to review.
            file_path: Path of the file being reviewed.

        Returns:
            list: List of security findings.
        """
        await self._set_busy(f"Reviewing {file_path}")

        findings: list[SecurityFinding] = []

        # Check for hardcoded secrets
        secret_findings = await self.check_secrets(code, file_path)
        findings.extend(secret_findings)

        # Check for XSS vulnerabilities
        xss_findings = await self.check_xss(code, file_path)
        findings.extend(xss_findings)

        # Check for input validation issues
        validation_findings = await self.check_input_validation(code, file_path)
        findings.extend(validation_findings)

        # Store findings and update history
        self._findings.extend(findings)
        self._audit_history.append({
            "file_path": file_path,
            "timestamp": datetime.utcnow().isoformat(),
            "findings_count": len(findings),
        })

        await self._set_idle()
        return findings

    async def check_secrets(
        self,
        code: str,
        file_path: str,
    ) -> list[SecurityFinding]:
        """
        Check code for hardcoded secrets.

        Args:
            code: The code to check.
            file_path: Path of the file.

        Returns:
            list: List of secret-related findings.
        """
        findings: list[SecurityFinding] = []
        lines = code.split("\n")

        for pattern, secret_type in self.SECRET_PATTERNS:
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith("//") or stripped.startswith("#"):
                        continue

                    findings.append(
                        SecurityFinding(
                            category=SecurityCategory.HARDCODED_SECRET,
                            severity=SecuritySeverity.CRITICAL,
                            description=f"Possible hardcoded {secret_type} detected",
                            line_number=line_num,
                            code_snippet=line.strip()[:100],
                            recommendation=(
                                f"Move the {secret_type} to environment variables "
                                "and use a secrets management solution."
                            ),
                        )
                    )

        return findings

    async def check_xss(
        self,
        code: str,
        file_path: str,
    ) -> list[SecurityFinding]:
        """
        Check code for XSS vulnerabilities.

        Args:
            code: The code to check.
            file_path: Path of the file.

        Returns:
            list: List of XSS-related findings.
        """
        findings: list[SecurityFinding] = []
        lines = code.split("\n")

        for pattern, issue_type in self.XSS_PATTERNS:
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(
                        SecurityFinding(
                            category=SecurityCategory.XSS,
                            severity=SecuritySeverity.HIGH,
                            description=f"Potential XSS vulnerability: {issue_type}",
                            line_number=line_num,
                            code_snippet=line.strip()[:100],
                            recommendation=(
                                "Use safe alternatives like textContent, "
                                "or properly sanitize HTML before rendering."
                            ),
                        )
                    )

        return findings

    async def check_input_validation(
        self,
        code: str,
        file_path: str,
    ) -> list[SecurityFinding]:
        """
        Check code for input validation issues.

        Args:
            code: The code to check.
            file_path: Path of the file.

        Returns:
            list: List of validation-related findings.
        """
        findings: list[SecurityFinding] = []
        lines = code.split("\n")

        # Patterns that suggest missing input validation
        risk_patterns = [
            (r'request\.body\[', "Direct request body access"),
            (r'req\.params\.', "Direct request params access"),
            (r'\$_GET\[', "Direct $_GET access (PHP)"),
            (r'\$_POST\[', "Direct $_POST access (PHP)"),
        ]

        for pattern, issue_type in risk_patterns:
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(
                        SecurityFinding(
                            category=SecurityCategory.INPUT_VALIDATION,
                            severity=SecuritySeverity.MEDIUM,
                            description=(
                                f"Potential missing input validation: {issue_type}"
                            ),
                            line_number=line_num,
                            code_snippet=line.strip()[:100],
                            recommendation=(
                                "Validate and sanitize all user inputs before use. "
                                "Use a validation library."
                            ),
                        )
                    )

        return findings

    async def audit_project(
        self,
        files: dict[str, str],
    ) -> dict[str, Any]:
        """
        Perform a full security audit on a project.

        Args:
            files: Dictionary mapping file paths to their content.

        Returns:
            dict: Audit results with findings and summary.
        """
        await self._set_busy("Performing security audit")

        all_findings: list[SecurityFinding] = []
        file_results: dict[str, int] = {}

        for file_path, code in files.items():
            findings = await self.review_code(code, file_path)
            all_findings.extend(findings)
            file_results[file_path] = len(findings)

        # Generate summary
        summary = {
            "total_files": len(files),
            "files_with_issues": sum(1 for c in file_results.values() if c > 0),
            "total_findings": len(all_findings),
            "by_severity": {},
            "by_category": {},
        }

        for finding in all_findings:
            sev = finding.severity.value
            cat = finding.category.value
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

        await self._set_idle()

        return {
            "summary": summary,
            "findings": [f.to_dict() for f in all_findings],
            "file_results": file_results,
        }

    async def get_security_recommendations(
        self,
        code: str,
        language: str = "javascript",
    ) -> str:
        """
        Get AI-powered security recommendations for code.

        Args:
            code: The code to analyze.
            language: Programming language.

        Returns:
            str: Security recommendations.
        """
        await self._set_busy("Generating security recommendations")

        prompt = f"""Analyze this {language} code for security issues \
and provide recommendations:

```{language}
{code[:3000]}
```

Provide:
1. Security vulnerabilities found
2. Potential attack vectors
3. Specific recommendations to fix each issue
4. General security best practices for this code

Be concise and actionable."""

        try:
            response = await self.get_ai_response(prompt)
            await self._set_idle()
            return response
        except Exception as e:
            self.logger.error(f"Security recommendations failed: {e}")
            await self._set_idle()
            return "Unable to generate security recommendations."

    async def get_findings(self) -> list[dict[str, Any]]:
        """Get all security findings."""
        return [f.to_dict() for f in self._findings]

    async def get_audit_summary(self) -> dict[str, Any]:
        """Get summary of all security audits."""
        critical = sum(
            1 for f in self._findings if f.severity == SecuritySeverity.CRITICAL
        )
        high = sum(1 for f in self._findings if f.severity == SecuritySeverity.HIGH)

        return {
            "total_audits": len(self._audit_history),
            "total_findings": len(self._findings),
            "critical": critical,
            "high": high,
            "other": len(self._findings) - critical - high,
        }

    def clear_findings(self) -> None:
        """Clear all security findings."""
        self._findings.clear()
        self._audit_history.clear()
