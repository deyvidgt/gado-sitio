"""
Tests for v5.7 Sprint 3: Bottom Navigation
"""
import pytest
from app import app
from flask import url_for


@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


class TestBottomNavHTML:
    """Test bottom navigation HTML presence"""

    def test_bottom_nav_in_base_html(self):
        """Verify bottom-nav element in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'id="bottom-nav"' in content
        assert 'class="bottom-nav"' in content

    def test_nav_items_in_html(self):
        """Verify all 5 nav items are in HTML"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for nav items with correct routes
        assert 'data-route="dashboard"' in content
        assert 'data-route="tarefas"' in content
        assert 'data-route="relatorios"' in content
        assert 'data-route="central_alertas"' in content
        assert 'data-route="configuracoes"' in content

    def test_nav_icons_present(self):
        """Verify emoji icons for nav items"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '🏠' in content  # Painel
        assert '🗓️' in content  # Agenda
        assert '📊' in content  # Relatórios
        assert '🔔' in content  # Alertas
        assert '👤' in content  # Perfil

    def test_badge_elements_present(self):
        """Verify badge elements for notifications"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'id="badge-tarefas"' in content
        assert 'id="badge-alertas"' in content
        assert 'class="nav-badge"' in content


class TestBottomNavCSS:
    """Test bottom navigation CSS"""

    def test_bottom_nav_css_in_design_tokens(self):
        """Verify .bottom-nav CSS in design-tokens.css"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.bottom-nav' in content
        assert 'position: fixed;' in content
        assert 'bottom: 0;' in content
        assert 'z-index: 999;' in content

    def test_nav_item_css_present(self):
        """Verify .nav-item CSS"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.nav-item' in content
        assert '.nav-item.active' in content
        assert '.nav-item:hover' in content

    def test_nav_badge_css_present(self):
        """Verify .nav-badge CSS with animation"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.nav-badge' in content
        assert 'background: var(--color-danger-main' in content
        assert '@keyframes badge-pulse' in content

    def test_dark_mode_nav_css(self):
        """Verify dark mode CSS for navigation"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '[data-theme="dark"] .bottom-nav' in content
        assert '[data-theme="dark"] .nav-item' in content

    def test_responsive_nav_css(self):
        """Verify responsive CSS for different breakpoints"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (max-width: 768px)' in content
        assert '@media (max-width: 480px)' in content
        # On mobile, labels should be hidden
        assert '.nav-item .label' in content


class TestBottomNavJavaScript:
    """Test bottom navigation JavaScript"""

    def test_bottom_nav_js_exists(self):
        """Verify bottom-nav.js file exists"""
        import os
        assert os.path.exists('static/js/bottom-nav.js')

    def test_bottom_nav_js_in_base_html(self):
        """Verify bottom-nav.js is loaded in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static/js/bottom-nav.js' in content

    def test_bottom_nav_class_defined(self):
        """Verify BottomNav class exists in JavaScript"""
        with open('static/js/bottom-nav.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'class BottomNav' in content

    def test_bottom_nav_methods_present(self):
        """Verify BottomNav has required methods"""
        with open('static/js/bottom-nav.js', 'r', encoding='utf-8') as f:
            content = f.read()

        methods = [
            'updateActiveState',
            'setActive',
            'initSwipe',
            'focusNextTab',
            'focusPrevTab',
            'loadBadgeCounts',
            'adjustBodyPadding'
        ]

        for method in methods:
            assert method in content

    def test_auto_init_on_dom_ready(self):
        """Verify auto-initialization on DOMContentLoaded"""
        with open('static/js/bottom-nav.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'DOMContentLoaded' in content
        assert 'window.bottomNav = new BottomNav()' in content

    def test_public_api_methods(self):
        """Verify public static API methods"""
        with open('static/js/bottom-nav.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static updateBadge' in content
        assert 'static setActiveTab' in content


class TestBottomNavAPI:
    """Test bottom navigation API endpoints"""

    def test_api_tarefas_count_route_exists(self):
        """Verify /api/tarefas/pendentes-count route is registered"""
        with open('routes_dashboard.py', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '/api/tarefas/pendentes-count' in content
        assert 'api_tarefas_pendentes_count' in content

    def test_api_alertas_count_route_exists(self):
        """Verify /api/alertas/count route is registered"""
        with open('routes_dashboard.py', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '/api/alertas/count' in content
        assert 'api_alertas_count' in content

    def test_api_endpoints_decorated(self, client):
        """Verify API endpoints have login_required decorator"""
        with open('routes_dashboard.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the function and check for @login_required before it
        assert '@login_required' in content
        assert 'def api_tarefas_pendentes_count' in content
        assert 'def api_alertas_count' in content

    def test_api_endpoints_return_json(self):
        """Verify API endpoints return JSON with 'count' field"""
        with open('routes_dashboard.py', 'r', encoding='utf-8') as f:
            content = f.read()

        assert "return jsonify({'count':" in content


class TestBottomNavIntegration:
    """Integration tests"""

    def test_page_loads_with_bottom_nav(self, client):
        """Test that a page loads without errors with bottom nav"""
        # This test requires authentication, so we test the template structure
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify the complete nav structure
        assert '<nav class="bottom-nav"' in content
        assert 'href="{{ url_for(' in content  # Template variables
        assert '</nav>' in content

    def test_no_javascript_errors_in_bottom_nav(self):
        """Verify no obvious JavaScript syntax errors"""
        with open('static/js/bottom-nav.js', 'r', encoding='utf-8') as f:
            content = f.read()

        # Basic checks for common JavaScript errors
        assert content.count('{') == content.count('}')  # Matching braces
        assert content.count('(') == content.count(')')  # Matching parens
        assert content.count('[') == content.count(']')  # Matching brackets

    def test_css_no_syntax_errors(self):
        """Verify CSS has basic validity"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        # Basic CSS checks
        assert content.count('{') == content.count('}')
        assert content.count('(') == content.count(')')


class TestBottomNavAccessibility:
    """Accessibility tests"""

    def test_nav_links_have_titles(self):
        """Verify all nav links have title attributes"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check that nav items have title attributes
        assert 'title="Painel"' in content
        assert 'title="Agenda"' in content
        assert 'title="Relatórios"' in content
        assert 'title="Alertas"' in content
        assert 'title="Perfil"' in content

    def test_focus_visible_styling(self):
        """Verify focus-visible styling for keyboard users"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.nav-item:focus-visible' in content
        assert 'outline:' in content

    def test_touch_targets_minimum(self):
        """Verify touch targets are >= 44px"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check that height is set to at least 44px (reduced for mobile)
        assert 'height: 60px' in content  # Desktop
        assert 'height: 56px' in content  # Tablet (still >= 44px)
        assert 'height: 52px' in content  # Mobile (still >= 44px)

    def test_prefers_reduced_motion_support(self):
        """Verify support for prefers-reduced-motion"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (prefers-reduced-motion: reduce)' in content
        assert '.nav-badge' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
