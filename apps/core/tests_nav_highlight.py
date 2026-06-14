"""Smoke tests for sidebar nav active-state JS helpers (via static file checks)."""
from django.test import SimpleTestCase
from pathlib import Path


class NavHighlightAssetsTest(SimpleTestCase):
    def test_app_js_defines_highlight_function(self):
        js = (Path(__file__).resolve().parents[2] / "static" / "js" / "app.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("function highlightActiveNav", js)
        self.assertIn("function scoreNavMatch", js)
        self.assertIn("highlightActiveNav();", js)

    def test_base_template_sidebar_structure(self):
        base = (Path(__file__).resolve().parents[2] / "templates" / "base.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('class="nav-menu"', base)
        self.assertIn('class="nav-footer"', base)
        self.assertNotIn('class="nav-item active"', base)

    def test_sidebar_css_uses_scrollable_menu(self):
        css = (Path(__file__).resolve().parents[2] / "static" / "css" / "styles.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".nav-menu", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn(".nav-item.active", css)
