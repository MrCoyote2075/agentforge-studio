"""
Tests for the new agents (Phase 8).

These tests verify that the new agents work correctly,
using mocks to avoid actual AI API calls during testing.
"""

import pytest

from backend.agents.accessibility_agent import (
    AccessibilityAgent,
    AccessibilityIssue,
)
from backend.agents.analytics_agent import AnalyticsAgent
from backend.agents.base_agent import AgentState
from backend.agents.designer_agent import DesignerAgent
from backend.agents.error_handler import (
    ErrorAction,
    ErrorAnalysis,
    ErrorCategory,
    ErrorHandlerAgent,
)
from backend.agents.optimizer_agent import OptimizerAgent
from backend.agents.security_agent import (
    SecurityAgent,
    SecurityCategory,
    SecurityFinding,
    SecuritySeverity,
)


class TestErrorHandlerAgent:
    """Tests for the ErrorHandlerAgent."""

    def test_initialization(self):
        """Test that ErrorHandlerAgent initializes correctly."""
        handler = ErrorHandlerAgent()
        assert handler.name == "ErrorHandler"
        assert handler.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_analyze_error_syntax(self):
        """Test analyzing syntax errors."""
        handler = ErrorHandlerAgent()
        analysis = await handler.analyze_error("SyntaxError: unexpected token")
        assert analysis.category == ErrorCategory.SYNTAX

    @pytest.mark.asyncio
    async def test_analyze_error_api(self):
        """Test analyzing API errors."""
        handler = ErrorHandlerAgent()
        analysis = await handler.analyze_error("API rate limit exceeded")
        assert analysis.category == ErrorCategory.API

    @pytest.mark.asyncio
    async def test_analyze_error_timeout(self):
        """Test analyzing timeout errors."""
        handler = ErrorHandlerAgent()
        analysis = await handler.analyze_error("Request timeout after 30s")
        assert analysis.category == ErrorCategory.TIMEOUT

    @pytest.mark.asyncio
    async def test_analyze_error_network(self):
        """Test analyzing network errors."""
        handler = ErrorHandlerAgent()
        analysis = await handler.analyze_error("Connection refused")
        assert analysis.category == ErrorCategory.NETWORK

    @pytest.mark.asyncio
    async def test_get_error_stats(self):
        """Test getting error statistics."""
        handler = ErrorHandlerAgent()
        await handler.analyze_error("SyntaxError: test")
        await handler.analyze_error("API error: test")
        stats = await handler.get_error_stats()
        assert stats["total_errors"] == 2

    def test_clear_history(self):
        """Test clearing error history."""
        handler = ErrorHandlerAgent()
        handler._error_history = [
            ErrorAnalysis("test", ErrorCategory.SYNTAX, ErrorAction.FIX)
        ]
        handler.clear_history()
        assert len(handler._error_history) == 0


class TestSecurityAgent:
    """Tests for the SecurityAgent."""

    def test_initialization(self):
        """Test that SecurityAgent initializes correctly."""
        security = SecurityAgent()
        assert security.name == "SecurityAgent"
        assert security.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_check_secrets_detects_api_key(self):
        """Test detecting hardcoded API keys."""
        security = SecurityAgent()
        code = 'const apiKey = "sk-1234567890abcdef";'
        findings = await security.check_secrets(code, "test.js")
        assert len(findings) > 0
        assert any(f.category == SecurityCategory.HARDCODED_SECRET for f in findings)

    @pytest.mark.asyncio
    async def test_check_secrets_ignores_comments(self):
        """Test that secrets in comments are skipped."""
        security = SecurityAgent()
        code = '// const apiKey = "sk-1234567890abcdef";'
        findings = await security.check_secrets(code, "test.js")
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_check_xss_detects_innerhtml(self):
        """Test detecting innerHTML usage."""
        security = SecurityAgent()
        code = 'element.innerHTML = userInput;'
        findings = await security.check_xss(code, "test.js")
        assert len(findings) > 0
        assert any(f.category == SecurityCategory.XSS for f in findings)

    @pytest.mark.asyncio
    async def test_check_xss_detects_eval(self):
        """Test detecting eval usage."""
        security = SecurityAgent()
        code = 'eval(userCode);'
        findings = await security.check_xss(code, "test.js")
        assert len(findings) > 0

    @pytest.mark.asyncio
    async def test_review_code_combines_checks(self):
        """Test that review_code runs all checks."""
        security = SecurityAgent()
        code = '''
        const apiKey = "sk-secret123";
        element.innerHTML = data;
        '''
        findings = await security.review_code(code, "test.js")
        categories = [f.category for f in findings]
        assert SecurityCategory.HARDCODED_SECRET in categories
        assert SecurityCategory.XSS in categories

    def test_clear_findings(self):
        """Test clearing security findings."""
        security = SecurityAgent()
        security._findings = [
            SecurityFinding(
                SecurityCategory.XSS, SecuritySeverity.HIGH, "test"
            )
        ]
        security.clear_findings()
        assert len(security._findings) == 0


class TestDesignerAgent:
    """Tests for the DesignerAgent."""

    def test_initialization(self):
        """Test that DesignerAgent initializes correctly."""
        designer = DesignerAgent()
        assert designer.name == "DesignerAgent"
        assert designer.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_create_color_scheme(self):
        """Test creating a color scheme."""
        designer = DesignerAgent()
        palette = await designer.create_color_scheme()
        assert "primary" in palette
        assert "secondary" in palette
        assert "background" in palette
        assert "text" in palette

    @pytest.mark.asyncio
    async def test_create_typography_system(self):
        """Test creating a typography system."""
        designer = DesignerAgent()
        typography = await designer.create_typography_system()
        assert "font_family" in typography
        assert "sizes" in typography
        assert "line_heights" in typography

    @pytest.mark.asyncio
    async def test_create_spacing_system(self):
        """Test creating a spacing system."""
        designer = DesignerAgent()
        spacing = await designer.create_spacing_system()
        assert "1" in spacing
        assert "2" in spacing
        assert "4" in spacing

    @pytest.mark.asyncio
    async def test_generate_css_variables(self):
        """Test generating CSS variables."""
        designer = DesignerAgent()
        css = await designer.generate_css_variables()
        assert ":root" in css
        assert "--color-primary" in css
        assert "--font-size-base" in css
        assert "--spacing-" in css

    @pytest.mark.asyncio
    async def test_generate_design_system(self):
        """Test generating complete design system."""
        designer = DesignerAgent()
        system = await designer.generate_design_system()
        assert "colors" in system
        assert "typography" in system
        assert "spacing" in system
        assert "breakpoints" in system

    def test_clear_tokens(self):
        """Test clearing design tokens."""
        designer = DesignerAgent()
        designer._design_tokens = {"colors": {}}
        designer.clear_tokens()
        assert len(designer._design_tokens) == 0


class TestOptimizerAgent:
    """Tests for the OptimizerAgent."""

    def test_initialization(self):
        """Test that OptimizerAgent initializes correctly."""
        optimizer = OptimizerAgent()
        assert optimizer.name == "OptimizerAgent"
        assert optimizer.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_minify_html(self):
        """Test HTML minification."""
        optimizer = OptimizerAgent()
        html = """
        <html>
            <body>
                <!-- This is a comment -->
                <div>   Content   </div>
            </body>
        </html>
        """
        minified = await optimizer.minify_html(html)
        assert "<!--" not in minified
        assert len(minified) < len(html)

    @pytest.mark.asyncio
    async def test_minify_css(self):
        """Test CSS minification."""
        optimizer = OptimizerAgent()
        css = """
        body {
            color: black;
            /* This is a comment */
            background: white;
        }
        """
        minified = await optimizer.minify_css(css)
        assert "/*" not in minified
        assert len(minified) < len(css)

    @pytest.mark.asyncio
    async def test_minify_javascript(self):
        """Test JavaScript minification."""
        optimizer = OptimizerAgent()
        js = """
        // Single line comment
        function test() {
            /* Multi-line
               comment */
            return true;
        }
        """
        minified = await optimizer.minify_javascript(js)
        assert "/*" not in minified
        assert len(minified) < len(js)

    @pytest.mark.asyncio
    async def test_generate_optimization_report(self):
        """Test generating optimization report."""
        optimizer = OptimizerAgent()
        await optimizer.minify_css("body { color: black; }")
        report = await optimizer.generate_optimization_report()
        assert "total_files_optimized" in report
        assert "total_savings_bytes" in report

    def test_clear_stats(self):
        """Test clearing optimization stats."""
        optimizer = OptimizerAgent()
        optimizer._stats["total_files"] = 10
        optimizer.clear_stats()
        assert optimizer._stats["total_files"] == 0


class TestAccessibilityAgent:
    """Tests for the AccessibilityAgent."""

    def test_initialization(self):
        """Test that AccessibilityAgent initializes correctly."""
        a11y = AccessibilityAgent()
        assert a11y.name == "AccessibilityAgent"
        assert a11y.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_audit_html_img_alt(self):
        """Test detecting images without alt."""
        a11y = AccessibilityAgent()
        html = '<img src="photo.jpg">'
        issues = await a11y.audit_html(html)
        assert len(issues) > 0
        assert any(i.rule == "img-alt" for i in issues)

    @pytest.mark.asyncio
    async def test_audit_html_lang(self):
        """Test detecting missing lang attribute."""
        a11y = AccessibilityAgent()
        html = "<html><body>Content</body></html>"
        issues = await a11y.audit_html(html)
        assert any(i.rule == "html-lang" for i in issues)

    @pytest.mark.asyncio
    async def test_audit_html_valid(self):
        """Test valid HTML passes audit."""
        a11y = AccessibilityAgent()
        html = '<html lang="en"><body><img src="photo.jpg" alt="Photo"></body></html>'
        issues = await a11y.audit_html(html)
        # Should have no img-alt issues
        assert not any(i.rule == "img-alt" for i in issues)

    @pytest.mark.asyncio
    async def test_check_color_contrast(self):
        """Test color contrast checking."""
        a11y = AccessibilityAgent()
        result = await a11y.check_color_contrast("#000000", "#FFFFFF")
        assert result["ratio"] >= 21.0
        assert result["passes_aa_normal"] is True

    @pytest.mark.asyncio
    async def test_check_color_contrast_fail(self):
        """Test failing color contrast."""
        a11y = AccessibilityAgent()
        result = await a11y.check_color_contrast("#777777", "#888888")
        assert result["passes_aa_normal"] is False

    @pytest.mark.asyncio
    async def test_add_aria_labels(self):
        """Test adding ARIA labels."""
        a11y = AccessibilityAgent()
        html = '<img src="photo.jpg"><nav>Menu</nav>'
        enhanced = await a11y.add_aria_labels(html)
        assert 'role="navigation"' in enhanced

    def test_clear_issues(self):
        """Test clearing accessibility issues."""
        a11y = AccessibilityAgent()
        a11y._issues = [
            AccessibilityIssue("img-alt", "critical", "Missing alt")
        ]
        a11y.clear_issues()
        assert len(a11y._issues) == 0


class TestAnalyticsAgent:
    """Tests for the AnalyticsAgent."""

    def test_initialization(self):
        """Test that AnalyticsAgent initializes correctly."""
        analytics = AnalyticsAgent()
        assert analytics.name == "AnalyticsAgent"
        assert analytics.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_generate_google_analytics(self):
        """Test generating Google Analytics code."""
        analytics = AnalyticsAgent()
        code = await analytics.generate_google_analytics("GA-12345")
        assert "GA-12345" in code
        assert "gtag" in code
        assert "dataLayer" in code

    @pytest.mark.asyncio
    async def test_generate_google_analytics_ecommerce(self):
        """Test generating GA with ecommerce."""
        analytics = AnalyticsAgent()
        code = await analytics.generate_google_analytics(
            "GA-12345", enable_ecommerce=True
        )
        assert "trackProductView" in code
        assert "trackAddToCart" in code

    @pytest.mark.asyncio
    async def test_generate_seo_tags(self):
        """Test generating SEO meta tags."""
        analytics = AnalyticsAgent()
        tags = await analytics.generate_seo_tags({
            "title": "Test Page",
            "description": "Test description",
        })
        assert "<title>Test Page</title>" in tags
        assert 'meta name="description"' in tags
        assert "og:title" in tags
        assert "twitter:title" in tags

    @pytest.mark.asyncio
    async def test_generate_sitemap(self):
        """Test generating XML sitemap."""
        analytics = AnalyticsAgent()
        sitemap = await analytics.generate_sitemap("https://example.com")
        assert '<?xml version="1.0"' in sitemap
        assert "<urlset" in sitemap
        assert "<loc>https://example.com/</loc>" in sitemap

    @pytest.mark.asyncio
    async def test_generate_robots_txt(self):
        """Test generating robots.txt."""
        analytics = AnalyticsAgent()
        robots = await analytics.generate_robots_txt(
            "https://example.com",
            disallow_paths=["/admin", "/private"]
        )
        assert "User-agent: *" in robots
        assert "Disallow: /admin" in robots
        assert "Sitemap: https://example.com/sitemap.xml" in robots

    @pytest.mark.asyncio
    async def test_generate_structured_data_organization(self):
        """Test generating Organization structured data."""
        analytics = AnalyticsAgent()
        data = await analytics.generate_structured_data("Organization", {
            "name": "Test Company",
            "url": "https://example.com",
        })
        assert "application/ld+json" in data
        assert '"@type": "Organization"' in data
        assert "Test Company" in data

    @pytest.mark.asyncio
    async def test_generate_structured_data_product(self):
        """Test generating Product structured data."""
        analytics = AnalyticsAgent()
        data = await analytics.generate_structured_data("Product", {
            "name": "Test Product",
            "price": 29.99,
        })
        assert '"@type": "Product"' in data
        assert "Test Product" in data

    def test_clear_generated(self):
        """Test clearing generated content."""
        analytics = AnalyticsAgent()
        analytics._generated_code = {"test": "code"}
        analytics._seo_tags = {"test": "tags"}
        analytics.clear_generated()
        assert len(analytics._generated_code) == 0
        assert len(analytics._seo_tags) == 0


class TestAgentPrompts:
    """Tests that all new agents load their prompts correctly."""

    def test_error_handler_has_prompt(self):
        """Test ErrorHandlerAgent has system prompt."""
        handler = ErrorHandlerAgent()
        assert handler.system_prompt is not None
        assert "Error Handler" in handler.system_prompt

    def test_security_agent_has_prompt(self):
        """Test SecurityAgent has system prompt."""
        security = SecurityAgent()
        assert security.system_prompt is not None
        assert "Security" in security.system_prompt

    def test_designer_agent_has_prompt(self):
        """Test DesignerAgent has system prompt."""
        designer = DesignerAgent()
        assert designer.system_prompt is not None
        assert "Designer" in designer.system_prompt

    def test_optimizer_agent_has_prompt(self):
        """Test OptimizerAgent has system prompt."""
        optimizer = OptimizerAgent()
        assert optimizer.system_prompt is not None
        assert "Optimizer" in optimizer.system_prompt

    def test_accessibility_agent_has_prompt(self):
        """Test AccessibilityAgent has system prompt."""
        a11y = AccessibilityAgent()
        assert a11y.system_prompt is not None
        assert "Accessibility" in a11y.system_prompt

    def test_analytics_agent_has_prompt(self):
        """Test AnalyticsAgent has system prompt."""
        analytics = AnalyticsAgent()
        assert analytics.system_prompt is not None
        assert "Analytics" in analytics.system_prompt
