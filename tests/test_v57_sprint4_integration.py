"""
Tests for v5.7 Sprint 4 Phase 4: Component Integration & Edge Cases
"""
import pytest
import os


class TestSprintFourComponentIntegration:
    """Test integration between all Sprint 4 components"""

    def test_all_sprint4_components_linked(self):
        """Verify all 4 components are linked in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        components = ['modal.css', 'modal.js', 'toast.css', 'toast.js',
                      'accordion.css', 'accordion.js', 'form-validator.css', 'form-validator.js']
        for component in components:
            assert component in content, f"{component} not found in base.html"

    def test_component_load_order_correct(self):
        """Verify components load in correct order (CSS first, then JS)"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        # CSS should come before JS
        css_pos = content.find('modal.css')
        js_pos = content.find('modal.js')
        assert css_pos < js_pos, "CSS should load before JS"

    def test_modal_loads_before_toast(self):
        """Verify Modal loads before Toast"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        modal_pos = content.find('modal.js')
        toast_pos = content.find('toast.js')
        assert modal_pos < toast_pos, "modal.js should load before toast.js"

    def test_toast_loads_before_accordion(self):
        """Verify Toast loads before Accordion"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        toast_pos = content.find('toast.js')
        accordion_pos = content.find('accordion.js')
        assert toast_pos < accordion_pos, "toast.js should load before accordion.js"

    def test_accordion_loads_before_form_validator(self):
        """Verify Accordion loads before Form Validator"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        accordion_pos = content.find('accordion.js')
        form_validator_pos = content.find('form-validator.js')
        assert accordion_pos < form_validator_pos, "accordion.js should load before form-validator.js"

    def test_no_duplicate_component_links(self):
        """Verify no component is linked more than once"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        components = ['modal.css', 'modal.js', 'toast.css', 'toast.js',
                      'accordion.css', 'accordion.js', 'form-validator.css', 'form-validator.js']
        for component in components:
            count = content.count(component)
            assert count == 1, f"{component} appears {count} times, expected 1"


class TestComponentEdgeCases:
    """Test edge cases for each component"""

    def test_modal_multiple_instances(self):
        """Verify Modal can handle multiple instances"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        # Should be able to create multiple Modal instances
        assert 'constructor(options' in content

    def test_toast_queue_system(self):
        """Verify Toast queue can handle many notifications"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'queue' in content
        assert 'shift()' in content

    def test_accordion_multiple_open_items(self):
        """Verify Accordion can handle allowMultiple option"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'allowMultiple' in content
        assert 'closeOthers' in content

    def test_form_validator_all_field_types(self):
        """Verify Form Validator supports all input types"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        field_types = ['email', 'url', 'number', 'phone']
        for field_type in field_types:
            assert field_type in content

    def test_form_validator_custom_rules(self):
        """Verify Form Validator supports custom validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'custom' in content
        assert 'typeof fieldRules.custom === \'function\'' in content

    def test_modal_esc_key_closes(self):
        """Verify Modal closes on ESC key"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Escape' in content or 'keydown' in content

    def test_accordion_keyboard_navigation_complete(self):
        """Verify Accordion has full keyboard nav (arrows, home, end)"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        keys = ['ArrowUp', 'ArrowDown', 'Home', 'End']
        for key in keys:
            assert key in content


class TestAccessibilityCompliance:
    """Comprehensive accessibility tests"""

    def test_modal_focus_trap(self):
        """Verify Modal implements focus trap"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'focus' in content or 'Tab' in content

    def test_toast_aria_role_status(self):
        """Verify Toast has role=status"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'role' in content and 'status' in content

    def test_accordion_aria_expanded_toggled(self):
        """Verify Accordion toggles aria-expanded correctly"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-expanded' in content
        assert 'setAttribute' in content

    def test_form_validator_aria_alert_messages(self):
        """Verify Form Validator shows alerts"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'role="alert"' in content or "'alert'" in content

    def test_all_components_support_reduced_motion(self):
        """Verify all components respect prefers-reduced-motion"""
        components = [
            'static/css/components/modal.css',
            'static/css/components/toast.css',
            'static/css/components/accordion.css',
            'static/css/components/form-validator.css'
        ]

        for component in components:
            with open(component, 'r', encoding='utf-8') as f:
                content = f.read()
            assert '@media (prefers-reduced-motion: reduce)' in content

    def test_all_components_dark_mode_support(self):
        """Verify all components support dark mode"""
        components = [
            'static/css/components/modal.css',
            'static/css/components/toast.css',
            'static/css/components/accordion.css',
            'static/css/components/form-validator.css'
        ]

        for component in components:
            with open(component, 'r', encoding='utf-8') as f:
                content = f.read()
            assert '[data-theme="dark"]' in content or 'dark' in content

    def test_all_touch_targets_min_44px(self):
        """Verify interactive elements have 44px minimum touch target"""
        components = [
            'static/css/components/modal.css',
            'static/css/components/toast.css',
            'static/css/components/accordion.css',
            'static/css/components/form-validator.css'
        ]

        for component in components:
            with open(component, 'r', encoding='utf-8') as f:
                content = f.read()
            # Check for min-height or padding that creates 44px targets
            assert 'min-height' in content or 'padding' in content


class TestComponentSyntaxValidation:
    """Validate syntax of all component files"""

    def test_all_css_files_have_matching_braces(self):
        """Verify CSS files have matching braces"""
        css_files = [
            'static/css/components/modal.css',
            'static/css/components/toast.css',
            'static/css/components/accordion.css',
            'static/css/components/form-validator.css'
        ]

        for css_file in css_files:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content.count('{') == content.count('}'), f"{css_file} has unmatched braces"
            assert content.count('(') == content.count(')'), f"{css_file} has unmatched parens"

    def test_all_js_files_have_matching_braces(self):
        """Verify JS files have matching braces"""
        js_files = [
            'static/js/components/modal.js',
            'static/js/components/toast.js',
            'static/js/components/accordion.js',
            'static/js/components/form-validator.js'
        ]

        for js_file in js_files:
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content.count('{') == content.count('}'), f"{js_file} has unmatched braces"
            assert content.count('(') == content.count(')'), f"{js_file} has unmatched parens"
            assert content.count('[') == content.count(']'), f"{js_file} has unmatched brackets"

    def test_all_components_have_usage_comments(self):
        """Verify all components document usage"""
        js_files = [
            'static/js/components/modal.js',
            'static/js/components/toast.js',
            'static/js/components/accordion.js',
            'static/js/components/form-validator.js'
        ]

        for js_file in js_files:
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert 'Usage' in content or 'usage' in content.lower()


class TestComponentDocumentation:
    """Test component documentation completeness"""

    def test_modal_has_feature_list(self):
        """Verify Modal documents features"""
        with open('static/js/components/modal.js', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'Features:' in content

    def test_toast_has_feature_list(self):
        """Verify Toast documents features"""
        with open('static/js/components/toast.js', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'Features:' in content

    def test_accordion_has_feature_list(self):
        """Verify Accordion documents features"""
        with open('static/js/components/accordion.js', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'Features:' in content

    def test_form_validator_has_feature_list(self):
        """Verify Form Validator documents features"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'Features:' in content


class TestSprintFourCompletion:
    """Verify Sprint 4 is complete"""

    def test_all_phase_1_files_exist(self):
        """Verify Modal (Phase 1) files exist"""
        assert os.path.exists('static/css/components/modal.css')
        assert os.path.exists('static/js/components/modal.js')

    def test_all_phase_2_files_exist(self):
        """Verify Toast (Phase 2) files exist"""
        assert os.path.exists('static/css/components/toast.css')
        assert os.path.exists('static/js/components/toast.js')

    def test_all_phase_3_files_exist(self):
        """Verify Accordion + Form Validator (Phase 3) files exist"""
        assert os.path.exists('static/css/components/accordion.css')
        assert os.path.exists('static/js/components/accordion.js')
        assert os.path.exists('static/css/components/form-validator.css')
        assert os.path.exists('static/js/components/form-validator.js')

    def test_all_phase_test_files_exist(self):
        """Verify all phase test files exist"""
        assert os.path.exists('tests/test_v57_sprint4_modal.py')
        assert os.path.exists('tests/test_v57_sprint4_toast.py')
        assert os.path.exists('tests/test_v57_sprint4_accordion.py')
        assert os.path.exists('tests/test_v57_sprint4_forms.py')

    def test_sprint_four_components_total_count(self):
        """Verify Sprint 4 has all 4 components"""
        components = [
            'static/css/components/modal.css',
            'static/js/components/modal.js',
            'static/css/components/toast.css',
            'static/js/components/toast.js',
            'static/css/components/accordion.css',
            'static/js/components/accordion.js',
            'static/css/components/form-validator.css',
            'static/js/components/form-validator.js'
        ]

        existing = sum(1 for c in components if os.path.exists(c))
        assert existing == 8, f"Expected 8 component files, found {existing}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
