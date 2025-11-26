"""
AgentForge Studio - Analytics Agent.

The Analytics Agent generates analytics code, SEO meta tags,
and sitemap files for web projects.
"""

from datetime import datetime
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import Message


class AnalyticsAgent(BaseAgent):
    """
    Analytics Agent that handles analytics and SEO tasks.

    The Analytics Agent generates tracking code, SEO meta tags, sitemaps,
    and other analytics-related content for web projects.

    Attributes:
        generated_code: Dictionary of generated analytics code.
        seo_tags: Dictionary of generated SEO tags.

    Example:
        >>> analytics = AnalyticsAgent()
        >>> tracking_code = await analytics.generate_google_analytics("GA-XXXXX")
    """

    def __init__(
        self,
        name: str = "AnalyticsAgent",
        model: str = "gemini-pro",
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Analytics agent.

        Args:
            name: The agent's name. Defaults to 'AnalyticsAgent'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._generated_code: dict[str, str] = {}
        self._seo_tags: dict[str, str] = {}

    async def process(self, message: Message) -> Message:
        """
        Process an analytics/SEO request.

        Args:
            message: The incoming message with request details.

        Returns:
            Message: Response with generated content.
        """
        await self._set_busy(f"Processing: {message.content[:50]}")

        try:
            content_lower = message.content.lower()

            if "analytics" in content_lower or "tracking" in content_lower:
                tracking_id = (
                    message.metadata.get("tracking_id", "GA-XXXXXXX")
                    if message.metadata
                    else "GA-XXXXXXX"
                )
                code = await self.generate_google_analytics(tracking_id)
                response_content = f"Analytics code generated ({len(code)} chars)"
            elif "seo" in content_lower or "meta" in content_lower:
                page_info = message.metadata if message.metadata else {}
                tags = await self.generate_seo_tags(page_info)
                response_content = f"SEO tags generated ({len(tags)} chars)"
            elif "sitemap" in content_lower:
                pages = (
                    message.metadata.get("pages", []) if message.metadata else []
                )
                sitemap = await self.generate_sitemap(
                    "https://example.com", pages
                )
                response_content = f"Sitemap generated ({len(sitemap)} chars)"
            else:
                # General analytics request
                response = await self.get_ai_response(
                    f"Help with this analytics/SEO request: {message.content}"
                )
                response_content = response

        except Exception as e:
            self.logger.error(f"Analytics task failed: {e}")
            response_content = f"Analytics task failed: {str(e)}"
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

    async def generate_google_analytics(
        self,
        tracking_id: str,
        enable_ecommerce: bool = False,
    ) -> str:
        """
        Generate Google Analytics tracking code.

        Args:
            tracking_id: Google Analytics tracking ID.
            enable_ecommerce: Whether to enable ecommerce tracking.

        Returns:
            str: Google Analytics script code.
        """
        await self._set_busy("Generating Google Analytics code")

        # GA4 script
        ga_code = f"""<!-- Google Analytics (GA4) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={tracking_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{tracking_id}');
</script>"""

        if enable_ecommerce:
            ga_code += """
<script>
  // Enhanced Ecommerce tracking helper functions
  function trackProductView(product) {
    gtag('event', 'view_item', {
      currency: product.currency || 'USD',
      value: product.price,
      items: [{
        item_id: product.id,
        item_name: product.name,
        price: product.price,
        quantity: 1
      }]
    });
  }

  function trackAddToCart(product) {
    gtag('event', 'add_to_cart', {
      currency: product.currency || 'USD',
      value: product.price,
      items: [{
        item_id: product.id,
        item_name: product.name,
        price: product.price,
        quantity: product.quantity || 1
      }]
    });
  }

  function trackPurchase(transaction) {
    gtag('event', 'purchase', {
      transaction_id: transaction.id,
      value: transaction.total,
      currency: transaction.currency || 'USD',
      items: transaction.items
    });
  }
</script>"""

        self._generated_code["google_analytics"] = ga_code

        await self._set_idle()
        return ga_code

    async def generate_seo_tags(
        self,
        page_info: dict[str, Any],
    ) -> str:
        """
        Generate SEO meta tags for a page.

        Args:
            page_info: Dictionary with page information.

        Returns:
            str: HTML meta tags for SEO.
        """
        await self._set_busy("Generating SEO tags")

        title = page_info.get("title", "Page Title")
        description = page_info.get("description", "Page description")
        keywords = page_info.get("keywords", [])
        image = page_info.get("image", "")
        url = page_info.get("url", "")
        site_name = page_info.get("site_name", "")
        author = page_info.get("author", "")
        twitter_handle = page_info.get("twitter_handle", "")

        tags = []

        # Basic meta tags
        tags.append(f'<title>{title}</title>')
        tags.append(f'<meta name="description" content="{description}">')

        if keywords:
            if isinstance(keywords, list):
                keyword_str = ", ".join(keywords)
            else:
                keyword_str = keywords
            tags.append(f'<meta name="keywords" content="{keyword_str}">')

        if author:
            tags.append(f'<meta name="author" content="{author}">')

        # Open Graph tags
        tags.append("")
        tags.append("<!-- Open Graph / Facebook -->")
        tags.append('<meta property="og:type" content="website">')
        tags.append(f'<meta property="og:title" content="{title}">')
        tags.append(f'<meta property="og:description" content="{description}">')

        if url:
            tags.append(f'<meta property="og:url" content="{url}">')
        if image:
            tags.append(f'<meta property="og:image" content="{image}">')
        if site_name:
            tags.append(f'<meta property="og:site_name" content="{site_name}">')

        # Twitter Card tags
        tags.append("")
        tags.append("<!-- Twitter -->")
        tags.append('<meta name="twitter:card" content="summary_large_image">')
        tags.append(f'<meta name="twitter:title" content="{title}">')
        tags.append(f'<meta name="twitter:description" content="{description}">')

        if twitter_handle:
            tags.append(f'<meta name="twitter:site" content="{twitter_handle}">')
        if image:
            tags.append(f'<meta name="twitter:image" content="{image}">')

        # Canonical URL
        if url:
            tags.append("")
            tags.append("<!-- Canonical -->")
            tags.append(f'<link rel="canonical" href="{url}">')

        seo_output = "\n".join(tags)
        self._seo_tags[url or "default"] = seo_output

        await self._set_idle()
        return seo_output

    async def generate_sitemap(
        self,
        base_url: str,
        pages: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Generate an XML sitemap.

        Args:
            base_url: The base URL of the website.
            pages: List of page dictionaries with 'path', 'priority', 'changefreq'.

        Returns:
            str: XML sitemap content.
        """
        await self._set_busy("Generating sitemap")

        # Default pages if none provided
        if not pages:
            pages = [
                {"path": "/", "priority": "1.0", "changefreq": "daily"},
                {"path": "/about", "priority": "0.8", "changefreq": "monthly"},
                {"path": "/contact", "priority": "0.8", "changefreq": "monthly"},
            ]

        sitemap_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]

        today = datetime.utcnow().strftime("%Y-%m-%d")

        for page in pages:
            path = page.get("path", "/")
            priority = page.get("priority", "0.5")
            changefreq = page.get("changefreq", "monthly")
            lastmod = page.get("lastmod", today)

            # Ensure base_url doesn't end with / and path starts with /
            clean_base = base_url.rstrip("/")
            clean_path = path if path.startswith("/") else f"/{path}"
            full_url = f"{clean_base}{clean_path}"

            sitemap_lines.append("  <url>")
            sitemap_lines.append(f"    <loc>{full_url}</loc>")
            sitemap_lines.append(f"    <lastmod>{lastmod}</lastmod>")
            sitemap_lines.append(f"    <changefreq>{changefreq}</changefreq>")
            sitemap_lines.append(f"    <priority>{priority}</priority>")
            sitemap_lines.append("  </url>")

        sitemap_lines.append("</urlset>")

        sitemap = "\n".join(sitemap_lines)
        self._generated_code["sitemap"] = sitemap

        await self._set_idle()
        return sitemap

    async def generate_robots_txt(
        self,
        base_url: str,
        disallow_paths: list[str] | None = None,
    ) -> str:
        """
        Generate a robots.txt file.

        Args:
            base_url: The base URL of the website.
            disallow_paths: List of paths to disallow.

        Returns:
            str: robots.txt content.
        """
        await self._set_busy("Generating robots.txt")

        lines = [
            "# robots.txt",
            "User-agent: *",
        ]

        if disallow_paths:
            for path in disallow_paths:
                lines.append(f"Disallow: {path}")
        else:
            lines.append("Allow: /")

        lines.append("")
        lines.append(f"Sitemap: {base_url.rstrip('/')}/sitemap.xml")

        robots_txt = "\n".join(lines)
        self._generated_code["robots_txt"] = robots_txt

        await self._set_idle()
        return robots_txt

    async def generate_structured_data(
        self,
        data_type: str,
        data: dict[str, Any],
    ) -> str:
        """
        Generate structured data (JSON-LD).

        Args:
            data_type: Type of structured data (Organization, Product, etc.).
            data: Data for the structured data.

        Returns:
            str: JSON-LD script tag.
        """
        await self._set_busy(f"Generating {data_type} structured data")

        import json

        schema = {
            "@context": "https://schema.org",
            "@type": data_type,
        }

        # Add data based on type
        if data_type == "Organization":
            schema.update({
                "name": data.get("name", ""),
                "url": data.get("url", ""),
                "logo": data.get("logo", ""),
                "description": data.get("description", ""),
            })
            if data.get("social_profiles"):
                schema["sameAs"] = data["social_profiles"]

        elif data_type == "Product":
            schema.update({
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "image": data.get("image", ""),
                "sku": data.get("sku", ""),
                "offers": {
                    "@type": "Offer",
                    "price": data.get("price", 0),
                    "priceCurrency": data.get("currency", "USD"),
                    "availability": "https://schema.org/InStock",
                },
            })

        elif data_type == "Article":
            schema.update({
                "headline": data.get("headline", ""),
                "description": data.get("description", ""),
                "image": data.get("image", ""),
                "author": {
                    "@type": "Person",
                    "name": data.get("author", ""),
                },
                "datePublished": data.get("published_date", ""),
                "dateModified": data.get("modified_date", ""),
            })

        elif data_type == "WebSite":
            schema.update({
                "name": data.get("name", ""),
                "url": data.get("url", ""),
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": data.get("search_url", "{url}?q={search_term_string}"),
                    "query-input": "required name=search_term_string",
                },
            })

        else:
            # Generic: add all data
            schema.update(data)

        json_ld = f"""<script type="application/ld+json">
{json.dumps(schema, indent=2)}
</script>"""

        self._generated_code[f"structured_data_{data_type.lower()}"] = json_ld

        await self._set_idle()
        return json_ld

    async def generate_analytics_dashboard_config(
        self,
        metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate configuration for an analytics dashboard.

        Args:
            metrics: List of metrics to track.

        Returns:
            dict: Dashboard configuration.
        """
        await self._set_busy("Generating dashboard config")

        default_metrics = [
            "pageviews",
            "unique_visitors",
            "bounce_rate",
            "avg_session_duration",
            "pages_per_session",
        ]

        config = {
            "metrics": metrics or default_metrics,
            "widgets": [
                {
                    "type": "line_chart",
                    "title": "Page Views Over Time",
                    "metric": "pageviews",
                    "period": "last_30_days",
                },
                {
                    "type": "number",
                    "title": "Total Visitors",
                    "metric": "unique_visitors",
                },
                {
                    "type": "gauge",
                    "title": "Bounce Rate",
                    "metric": "bounce_rate",
                    "target": 40,
                },
                {
                    "type": "bar_chart",
                    "title": "Top Pages",
                    "metric": "pageviews_by_page",
                    "limit": 10,
                },
                {
                    "type": "pie_chart",
                    "title": "Traffic Sources",
                    "metric": "traffic_sources",
                },
            ],
            "refresh_interval": 300,  # 5 minutes
        }

        await self._set_idle()
        return config

    async def get_generated_code(self) -> dict[str, str]:
        """Get all generated analytics code."""
        return self._generated_code.copy()

    async def get_seo_tags(self) -> dict[str, str]:
        """Get all generated SEO tags."""
        return self._seo_tags.copy()

    def clear_generated(self) -> None:
        """Clear all generated content."""
        self._generated_code.clear()
        self._seo_tags.clear()
