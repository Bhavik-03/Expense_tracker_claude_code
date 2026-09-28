"""
Tests for Step 6b: Analytics Coming Soon Page.

Based on .claude/specs/06b-analytics-coming-soon.md — NOT derived from
reading the implementation. Covers:
  - GET /analytics auth guard (redirect to /login when logged out)
  - GET /analytics returns 200 when logged in and renders expected content
  - Analytics navbar link visibility (hidden when logged out, shown when
    logged in) and active-state marking (active class + aria-current on
    /analytics, neither on other pages such as /profile)
  - No hardcoded hex colour values in templates/analytics.html source
"""

import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Matches a hex colour literal like #abc or #aabbcc (word boundary either side).
HEX_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def find_analytics_nav_link(html):
    """Return the full <a ...href="/analytics"...> tag from `html`, or None."""
    match = re.search(r'<a\b[^>]*href="/analytics"[^>]*>', html)
    return match.group(0) if match else None


class TestAnalyticsAuthGuard:
    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get("/analytics", follow_redirects=False)
        assert response.status_code == 302, "Unauthenticated /analytics must redirect"
        assert "/login" in response.headers["Location"], "Must redirect to /login"

    def test_logout_then_analytics_redirects_to_login(self, auth_client):
        auth_client.get("/logout")
        response = auth_client.get("/analytics", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


class TestAnalyticsRoute:
    def test_logged_in_returns_200(self, auth_client):
        response = auth_client.get("/analytics")
        assert response.status_code == 200, "Logged-in /analytics must return 200"

    def test_page_shows_heading(self, auth_client):
        response = auth_client.get("/analytics")
        assert b"Advanced Analytics" in response.data, "Expected the 'Advanced Analytics' heading"

    def test_page_shows_coming_soon_badge(self, auth_client):
        response = auth_client.get("/analytics")
        html = response.data.decode("utf-8")
        assert re.search(r"coming soon", html, re.IGNORECASE), "Expected a 'Coming soon' badge"

    def test_page_shows_description(self, auth_client):
        response = auth_client.get("/analytics")
        # Collapse whitespace as a browser would, so template line-wrapping doesn't matter
        text = " ".join(response.data.decode("utf-8").split())
        assert (
            "We're working on powerful insights and visualizations to help you "
            "understand your spending patterns better." in text
        ), "Expected the analytics description text"

    def test_page_shows_crafting_note(self, auth_client):
        response = auth_client.get("/analytics")
        assert b"We're crafting something special" in response.data, "Expected the crafting-something-special note"


class TestAnalyticsNavLinkVisibility:
    def test_logged_out_landing_page_has_no_analytics_link(self, client):
        response = client.get("/")
        html = response.data.decode("utf-8")
        assert find_analytics_nav_link(html) is None, "Logged-out landing page must not show an Analytics link"

    def test_logged_out_login_page_has_no_analytics_link(self, client):
        response = client.get("/login")
        html = response.data.decode("utf-8")
        assert find_analytics_nav_link(html) is None, "Logged-out login page must not show an Analytics link"

    def test_logged_in_landing_page_has_analytics_link(self, auth_client):
        response = auth_client.get("/")
        html = response.data.decode("utf-8")
        link = find_analytics_nav_link(html)
        assert link is not None, "Logged-in nav must show an Analytics link"

    def test_logged_in_profile_page_has_analytics_link(self, auth_client):
        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        link = find_analytics_nav_link(html)
        assert link is not None, "Logged-in nav must show an Analytics link on /profile too"


class TestAnalyticsNavLinkActiveState:
    def test_on_analytics_page_link_is_active(self, auth_client):
        response = auth_client.get("/analytics")
        html = response.data.decode("utf-8")
        link = find_analytics_nav_link(html)
        assert link is not None, "Analytics link must be present on /analytics"
        assert "active" in link, "Analytics link must have the 'active' class on /analytics"
        assert 'aria-current="page"' in link, "Analytics link must have aria-current=page on /analytics"

    def test_on_profile_page_link_is_not_active(self, auth_client):
        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        link = find_analytics_nav_link(html)
        assert link is not None, "Analytics link must be present on /profile"
        assert "active" not in link, "Analytics link must not have the 'active' class on /profile"
        assert "aria-current" not in link, "Analytics link must not have aria-current on /profile"

    def test_on_landing_page_link_is_not_active(self, auth_client):
        response = auth_client.get("/")
        html = response.data.decode("utf-8")
        link = find_analytics_nav_link(html)
        assert link is not None, "Analytics link must be present on /"
        assert "active" not in link, "Analytics link must not have the 'active' class on /"
        assert "aria-current" not in link, "Analytics link must not have aria-current on /"


class TestAnalyticsTemplateNoHardcodedColors:
    def test_no_hex_colors_in_analytics_template_source(self):
        template_path = TEMPLATES_DIR / "analytics.html"
        assert template_path.exists(), "templates/analytics.html must exist"
        source = template_path.read_text(encoding="utf-8")
        matches = HEX_COLOR_RE.findall(source)
        assert not matches, f"analytics.html must not hardcode hex colours, found: {matches}"
