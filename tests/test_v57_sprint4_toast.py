"""
Tests for v5.7 Sprint 4: Toast Notifications Component
"""
import pytest
import os


class TestToastCSS:
    """Test toast CSS component"""

    def test_toast_css_exists(self):
        """Verify toast.css file exists"""
        assert os.path.exists('static/css/components/toast.css')

    def test_toast_css_in_base_html(self):
        """Verify toast.css is linked in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'static/css/components/toast.css' in content

    def test_toast_base_styling(self):
        """Verify base toast CSS"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.toast {' in content
        assert 'position: fixed;' in content
        assert 'z-index: 2000;' in content
        assert '.toast.visible' in content

    def test_toast_types_styling(self):
        """Verify styling for all 4 toast types"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        types = ['success', 'error', 'warning', 'info']
        for toast_type in types:
            assert f'.toast-{toast_type}' in content
            assert toast_type in content

    def test_toast_animations(self):
        """Verify toast animations (slide-in, fade-out)"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'transition:' in content
        assert 'transform:' in content
        assert 'opacity:' in content

    def test_toast_dark_mode(self):
        """Verify dark mode support"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '[data-theme="dark"]' in content

    def test_toast_mobile_responsive(self):
        """Verify mobile responsive CSS"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (max-width: 768px)' in content

    def test_toast_reduced_motion(self):
        """Verify prefers-reduced-motion support"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (prefers-reduced-motion: reduce)' in content

    def test_toast_positioning(self):
        """Verify toast is positioned at bottom-right"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'bottom:' in content
        assert 'right:' in content or 'left:' in content

    def test_toast_accessibility_aria(self):
        """Verify ARIA attributes support"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        # Comments or reference to aria-live
        assert 'aria-live' in content or 'live region' in content.lower()


class TestToastJavaScript:
    """Test toast JavaScript component"""

    def test_toast_js_exists(self):
        """Verify toast.js file exists"""
        assert os.path.exists('static/js/components/toast.js')

    def test_toast_js_in_base_html(self):
        """Verify toast.js is loaded in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'static/js/components/toast.js' in content

    def test_toast_class_defined(self):
        """Verify Toast class exists"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'class Toast' in content

    def test_toast_static_show_method(self):
        """Verify static show() method"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static show' in content

    def test_toast_convenience_methods(self):
        """Verify static convenience methods (success, error, warning, info)"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        methods = ['success', 'error', 'warning', 'info']
        for method in methods:
            assert f'static {method}' in content

    def test_toast_queue_system(self):
        """Verify queue property and system"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'queue' in content
        assert 'shift()' in content or 'shift' in content

    def test_toast_auto_dismiss(self):
        """Verify auto-dismiss functionality"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'duration' in content
        assert 'setTimeout' in content
        assert 'dismiss' in content

    def test_toast_constructor(self):
        """Verify Toast constructor"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'constructor(message' in content
        assert 'this.message' in content
        assert 'this.type' in content
        assert 'this.duration' in content

    def test_toast_create_method(self):
        """Verify create() method for DOM creation"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'create()' in content
        assert 'createElement' in content
        assert 'className' in content

    def test_toast_dismiss_method(self):
        """Verify dismiss() method"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'dismiss()' in content
        assert 'remove()' in content

    def test_toast_aria_attributes(self):
        """Verify ARIA attributes for accessibility"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'role="status"' in content or "'status'" in content
        assert 'aria-live' in content
        assert 'aria-atomic' in content

    def test_toast_clear_all_static_method(self):
        """Verify static clearAll() method"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static clearAll' in content or 'clearAll()' in content

    def test_toast_no_syntax_errors(self):
        """Verify no obvious JavaScript syntax errors"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check matching braces, parens, brackets
        assert content.count('{') == content.count('}')
        assert content.count('(') == content.count(')')
        assert content.count('[') == content.count(']')


class TestToastIntegration:
    """Integration tests"""

    def test_toast_css_syntax_valid(self):
        """Verify CSS has no obvious syntax errors"""
        with open('static/css/components/toast.css', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check matching braces
        assert content.count('{') == content.count('}')
        # Check matching parens
        assert content.count('(') == content.count(')')

    def test_toast_in_base_html(self):
        """Verify toast is integrated in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            base_content = f.read()

        # CSS link
        assert 'toast.css' in base_content
        # JS script
        assert 'toast.js' in base_content

    def test_toast_and_modal_both_integrated(self):
        """Verify both modal and toast are integrated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'modal.css' in content
        assert 'modal.js' in content
        assert 'toast.css' in content
        assert 'toast.js' in content

    def test_no_duplicate_toast_css(self):
        """Verify toast.css is not duplicated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        count = content.count('toast.css')
        assert count == 1, f"toast.css appears {count} times, expected 1"

    def test_no_duplicate_toast_js(self):
        """Verify toast.js is not duplicated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        count = content.count('toast.js')
        assert count == 1, f"toast.js appears {count} times, expected 1"

    def test_script_loading_order(self):
        """Verify toast.js is loaded after modal.js"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        modal_pos = content.find('modal.js')
        toast_pos = content.find('toast.js')
        assert modal_pos < toast_pos, "modal.js should load before toast.js"


class TestToastAccessibility:
    """Accessibility tests"""

    def test_toast_has_role_status(self):
        """Verify toast has role=status"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'role' in content and 'status' in content

    def test_toast_has_aria_live(self):
        """Verify toast has aria-live attribute"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-live' in content

    def test_toast_has_aria_atomic(self):
        """Verify toast has aria-atomic attribute"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-atomic' in content

    def test_toast_color_not_only_indicator(self):
        """Verify toast uses color + content (not just color)"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        # Messages are included, not just colors
        assert 'textContent' in content or 'innerHTML' in content


class TestToastUsagePatterns:
    """Test usage patterns"""

    def test_success_method_documented(self):
        """Verify Toast.success() is available"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static success' in content

    def test_error_method_documented(self):
        """Verify Toast.error() is available"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static error' in content

    def test_warning_method_documented(self):
        """Verify Toast.warning() is available"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static warning' in content

    def test_info_method_documented(self):
        """Verify Toast.info() is available"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static info' in content

    def test_usage_examples_in_comments(self):
        """Verify usage examples in comments"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Usage:' in content or 'usage:' in content.lower()
        assert 'Toast.' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
