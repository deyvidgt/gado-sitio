"""
Tests for v5.7 Sprint 4 Phase 3: Accordion Component
"""
import pytest
import os


class TestAccordionCSS:
    """Test accordion CSS component"""

    def test_accordion_css_exists(self):
        """Verify accordion.css file exists"""
        assert os.path.exists('static/css/components/accordion.css')

    def test_accordion_css_in_base_html(self):
        """Verify accordion.css is linked in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'static/css/components/accordion.css' in content

    def test_accordion_base_styling(self):
        """Verify base accordion CSS"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.accordion {' in content
        assert 'border:' in content or 'border-radius:' in content
        assert 'overflow: hidden;' in content
        assert '.accordion-item' in content

    def test_accordion_header_styling(self):
        """Verify accordion header CSS"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.accordion-header {' in content
        assert 'display: flex;' in content
        assert 'align-items: center;' in content
        assert 'cursor: pointer;' in content or 'c‍ursor: pointer;' in content
        assert 'min-height: 44px;' in content

    def test_accordion_body_animation(self):
        """Verify accordion body animation"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.accordion-body {' in content
        assert 'max-height: 0;' in content
        assert 'overflow: hidden;' in content
        assert 'transition:' in content

    def test_accordion_expanded_state(self):
        """Verify expanded state changes max-height"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '[aria-expanded="true"]' in content
        assert 'max-height: 2000px;' in content

    def test_accordion_icon_rotation(self):
        """Verify icon rotates on expand"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.accordion-icon {' in content
        assert 'transition:' in content
        assert 'transform: rotate(180deg);' in content

    def test_accordion_dark_mode(self):
        """Verify dark mode support"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '[data-theme="dark"]' in content

    def test_accordion_mobile_responsive(self):
        """Verify mobile responsive CSS"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (max-width: 480px)' in content

    def test_accordion_reduced_motion(self):
        """Verify prefers-reduced-motion support"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (prefers-reduced-motion: reduce)' in content

    def test_accordion_css_syntax_valid(self):
        """Verify CSS has no obvious syntax errors"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check matching braces
        assert content.count('{') == content.count('}')
        # Check matching parens
        assert content.count('(') == content.count(')')


class TestAccordionJavaScript:
    """Test accordion JavaScript component"""

    def test_accordion_js_exists(self):
        """Verify accordion.js file exists"""
        assert os.path.exists('static/js/components/accordion.js')

    def test_accordion_js_in_base_html(self):
        """Verify accordion.js is loaded in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'static/js/components/accordion.js' in content

    def test_accordion_class_defined(self):
        """Verify Accordion class exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'class Accordion' in content

    def test_accordion_constructor(self):
        """Verify constructor accepts selector and options"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'constructor(selector, options' in content
        assert 'this.container' in content
        assert 'this.headers' in content

    def test_accordion_init_method(self):
        """Verify init() method exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'init()' in content
        assert 'querySelectorAll' in content

    def test_accordion_toggle_method(self):
        """Verify toggle() method exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'toggle(header)' in content
        assert 'aria-expanded' in content

    def test_accordion_open_method(self):
        """Verify open() method exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'open(header)' in content
        assert 'setAttribute' in content

    def test_accordion_close_method(self):
        """Verify close() method exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'close(header)' in content

    def test_accordion_keyboard_handler(self):
        """Verify keyboard navigation exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'handleKeydown(e, header)' in content
        assert 'e.key === \'Enter\'' in content or 'e.key == \'Enter\'' in content
        assert 'e.key === \' \'' in content or 'e.key == \' \'' in content

    def test_accordion_arrow_key_navigation(self):
        """Verify arrow key navigation"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'ArrowUp' in content
        assert 'ArrowDown' in content
        assert 'Home' in content
        assert 'End' in content

    def test_accordion_open_all_method(self):
        """Verify openAll() method exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'openAll()' in content
        assert 'allowMultiple' in content

    def test_accordion_close_all_method(self):
        """Verify closeAll() method exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'closeAll()' in content

    def test_accordion_destroy_method(self):
        """Verify destroy() method exists"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'destroy()' in content
        assert 'removeEventListener' in content

    def test_accordion_aria_expanded(self):
        """Verify aria-expanded attribute usage"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-expanded' in content
        assert 'true' in content
        assert 'false' in content

    def test_accordion_aria_controls(self):
        """Verify aria-controls attribute usage"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-controls' in content

    def test_accordion_single_open_option(self):
        """Verify allowMultiple option"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'allowMultiple' in content
        assert 'closeOthers' in content

    def test_accordion_max_height_animation(self):
        """Verify max-height animation trigger"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'maxHeight' in content or 'max-height' in content
        assert 'scrollHeight' in content

    def test_accordion_auto_init(self):
        """Verify auto-initialization on DOM ready"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'DOMContentLoaded' in content
        assert 'data-accordion' in content

    def test_accordion_window_export(self):
        """Verify Accordion is exported to window"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'window.Accordion' in content

    def test_accordion_module_export(self):
        """Verify CommonJS export for use in other modules"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'module.exports' in content

    def test_accordion_js_no_syntax_errors(self):
        """Verify no obvious JavaScript syntax errors"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check matching braces, parens, brackets
        assert content.count('{') == content.count('}')
        assert content.count('(') == content.count(')')
        assert content.count('[') == content.count(']')


class TestAccordionIntegration:
    """Integration tests for accordion component"""

    def test_accordion_css_and_js_linked(self):
        """Verify both CSS and JS are linked in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            base_content = f.read()

        assert 'accordion.css' in base_content
        assert 'accordion.js' in base_content

    def test_accordion_after_modal_and_toast(self):
        """Verify accordion loads after modal and toast"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        modal_pos = content.find('modal.js')
        toast_pos = content.find('toast.js')
        accordion_pos = content.find('accordion.js')

        assert modal_pos < accordion_pos, "modal.js should load before accordion.js"
        assert toast_pos < accordion_pos, "toast.js should load before accordion.js"

    def test_no_duplicate_accordion_css(self):
        """Verify accordion.css is not duplicated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        count = content.count('accordion.css')
        assert count == 1, f"accordion.css appears {count} times, expected 1"

    def test_no_duplicate_accordion_js(self):
        """Verify accordion.js is not duplicated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        count = content.count('accordion.js')
        assert count == 1, f"accordion.js appears {count} times, expected 1"


class TestAccordionAccessibility:
    """Accessibility tests for accordion component"""

    def test_accordion_aria_expanded_attribute(self):
        """Verify aria-expanded is used"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-expanded' in content

    def test_accordion_aria_controls_attribute(self):
        """Verify aria-controls is used"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-controls' in content

    def test_accordion_keyboard_support(self):
        """Verify keyboard support (Enter/Space)"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Enter' in content
        assert 'Space' in content or "' '" in content

    def test_accordion_focus_management(self):
        """Verify focus management with arrow keys"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'focus()' in content
        assert 'ArrowUp' in content or 'ArrowDown' in content

    def test_accordion_min_height_touch_target(self):
        """Verify 44px minimum touch target"""
        with open('static/css/components/accordion.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'min-height: 44px;' in content


class TestAccordionUsagePatterns:
    """Test usage patterns and documentation"""

    def test_accordion_usage_comment(self):
        """Verify usage example in comments"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Usage' in content
        assert 'new Accordion' in content

    def test_accordion_html_example(self):
        """Verify HTML structure example"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'accordion' in content
        assert 'accordion-header' in content
        assert 'accordion-body' in content

    def test_accordion_feature_list(self):
        """Verify features are documented"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Expandable' in content or 'expandable' in content
        assert 'collapsible' in content or 'Collapsible' in content
        assert 'ARIA' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
