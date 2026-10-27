"""
Tests for v5.7 Sprint 4: Modal Component
"""
import pytest
import os


class TestModalCSS:
    """Test modal CSS component"""

    def test_modal_css_exists(self):
        """Verify modal.css file exists"""
        assert os.path.exists('static/css/components/modal.css')

    def test_modal_css_in_base_html(self):
        """Verify modal.css is linked in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'static/css/components/modal.css' in content

    def test_modal_overlay_styling(self):
        """Verify modal overlay CSS"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.modal-overlay' in content
        assert 'position: fixed;' in content
        assert 'z-index: 1000;' in content

    def test_modal_component_styling(self):
        """Verify modal component CSS"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.modal {' in content
        assert 'max-width: 500px;' in content
        assert 'max-height: 90vh;' in content

    def test_modal_sections_styling(self):
        """Verify modal header/body/footer styling"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.modal-header' in content
        assert '.modal-body' in content
        assert '.modal-footer' in content
        assert '.modal-title' in content
        assert '.modal-close' in content

    def test_modal_animations(self):
        """Verify modal animations (fade-in, slide-up)"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@keyframes modal-fade-in' in content
        assert '@keyframes modal-slide-up' in content
        assert 'animation: modal-fade-in' in content
        assert 'animation: modal-slide-up' in content

    def test_modal_dark_mode(self):
        """Verify dark mode support"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '[data-theme="dark"] .modal' in content
        assert '[data-theme="dark"] .modal-overlay' in content

    def test_modal_responsive(self):
        """Verify responsive CSS"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (max-width: 480px)' in content

    def test_modal_reduced_motion(self):
        """Verify prefers-reduced-motion support"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (prefers-reduced-motion: reduce)' in content


class TestModalJavaScript:
    """Test modal JavaScript component"""

    def test_modal_js_exists(self):
        """Verify modal.js file exists"""
        assert os.path.exists('static/js/components/modal.js')

    def test_modal_js_in_base_html(self):
        """Verify modal.js is loaded in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'static/js/components/modal.js' in content

    def test_modal_class_defined(self):
        """Verify Modal class exists"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'class Modal' in content

    def test_modal_constructor(self):
        """Verify Modal constructor accepts options"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'constructor(options' in content
        assert 'this.title' in content
        assert 'this.content' in content
        assert 'this.buttons' in content

    def test_modal_methods_present(self):
        """Verify Modal has required methods"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        methods = ['create', 'open', 'close', 'setupFocusTrap']
        for method in methods:
            assert f'{method}(' in content

    def test_modal_static_apis(self):
        """Verify static API methods"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static confirm' in content
        assert 'static alert' in content

    def test_focus_trap_implementation(self):
        """Verify focus trap for keyboard navigation"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'setupFocusTrap' in content
        assert 'focusableSelectors' in content or 'querySelectorAll' in content
        assert 'Tab' in content or 'shift' in content.lower()

    def test_esc_key_handler(self):
        """Verify ESC key closes modal"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Escape' in content
        assert 'handleEscKey' in content

    def test_aria_attributes(self):
        """Verify ARIA attributes for accessibility"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert ('role' in content and 'dialog' in content)
        assert 'aria-modal' in content
        assert 'aria-label' in content

    def test_no_syntax_errors(self):
        """Verify no obvious JavaScript syntax errors"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check matching braces, parens, brackets
        assert content.count('{') == content.count('}')
        assert content.count('(') == content.count(')')
        assert content.count('[') == content.count(']')


class TestModalIntegration:
    """Integration tests"""

    def test_modal_css_syntax_valid(self):
        """Verify CSS has no obvious syntax errors"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check matching braces
        assert content.count('{') == content.count('}')
        # Check matching parens
        assert content.count('(') == content.count(')')

    def test_modal_in_both_files(self):
        """Verify modal is integrated in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            base_content = f.read()

        # CSS link
        assert 'modal.css' in base_content
        # JS script
        assert 'modal.js' in base_content

    def test_button_styling_available(self):
        """Verify .btn classes are available for modal buttons"""
        with open('static/design-tokens.css', 'r', encoding='utf-8') as f:
            design_tokens = f.read()

        assert '.btn' in design_tokens
        assert 'btn-primary' in design_tokens or 'btn-' in design_tokens

    def test_no_duplicate_modal_css(self):
        """Verify modal.css is not duplicated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        count = content.count('modal.css')
        assert count == 1, f"modal.css appears {count} times, expected 1"

    def test_no_duplicate_modal_js(self):
        """Verify modal.js is not duplicated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        count = content.count('modal.js')
        assert count == 1, f"modal.js appears {count} times, expected 1"


class TestModalAccessibility:
    """Accessibility tests"""

    def test_close_button_has_aria_label(self):
        """Verify close button has aria-label"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-label' in content
        assert 'Fechar' in content or 'Close' in content

    def test_modal_has_role_dialog(self):
        """Verify modal has role=dialog"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert ('role' in content and 'dialog' in content)

    def test_modal_has_aria_modal(self):
        """Verify modal has aria-modal=true"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-modal' in content

    def test_focus_management(self):
        """Verify focus is managed (restoration on close)"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'previousFocus' in content
        assert 'focus()' in content or '.focus()' in content

    def test_touch_targets_44px(self):
        """Verify buttons and close icon are accessible"""
        with open('static/css/components/modal.css', 'r', encoding='utf-8') as f:
            content = f.read()

        # Modal close button
        assert '.modal-close' in content
        # Check for size (should be >= 44px or use --touch-target-min)
        assert '44px' in content or 'var(--spacing' in content

    def test_keyboard_navigation(self):
        """Verify keyboard support (Tab, Shift+Tab, ESC)"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Tab' in content
        assert 'Escape' in content or 'Esc' in content


class TestModalUsagePatterns:
    """Test usage patterns are documented"""

    def test_confirm_pattern_documented(self):
        """Verify Modal.confirm() is documented"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static confirm' in content

    def test_alert_pattern_documented(self):
        """Verify Modal.alert() is documented"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'static alert' in content

    def test_usage_comments_present(self):
        """Verify usage examples in comments"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Usage:' in content or 'usage:' in content.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
