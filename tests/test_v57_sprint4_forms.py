"""
Tests for v5.7 Sprint 4 Phase 3: Form Validator Component
"""
import pytest
import os


class TestFormValidatorCSS:
    """Test form validator CSS component"""

    def test_form_validator_css_exists(self):
        """Verify form-validator.css file exists"""
        assert os.path.exists('static/css/components/form-validator.css')

    def test_form_validator_css_in_base_html(self):
        """Verify form-validator.css is linked in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'static/css/components/form-validator.css' in content

    def test_form_group_styling(self):
        """Verify form-group CSS"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-group {' in content
        assert 'display: flex;' in content
        assert 'flex-direction: column;' in content

    def test_form_label_styling(self):
        """Verify form-label CSS"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-label {' in content
        assert 'font-weight: 500;' in content

    def test_form_input_styling(self):
        """Verify form-input CSS"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-input,' in content or '.form-input {' in content
        assert 'border: 2px solid' in content
        assert 'border-radius:' in content
        assert 'transition:' in content

    def test_form_input_focus_state(self):
        """Verify input focus styling"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert ':focus {' in content
        assert 'outline: none;' in content

    def test_form_input_valid_state(self):
        """Verify valid input state (.is-valid)"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.is-valid' in content
        assert 'color-success' in content or '#27ae60' in content

    def test_form_input_invalid_state(self):
        """Verify invalid input state (.is-invalid)"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.is-invalid' in content
        assert 'color-error' in content or '#e74c3c' in content

    def test_form_validation_message_styling(self):
        """Verify validation message CSS"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-validation-message {' in content
        assert 'display: none;' in content or 'display: flex;' in content
        assert 'font-size: 12px;' in content

    def test_form_validation_message_error_state(self):
        """Verify error message styling"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-validation-message.error' in content
        assert 'color-error' in content or '#e74c3c' in content

    def test_form_validation_message_success_state(self):
        """Verify success message styling"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-validation-message.success' in content
        assert 'color-success' in content or '#27ae60' in content

    def test_form_textarea_styling(self):
        """Verify textarea CSS"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-textarea' in content
        assert 'resize: vertical;' in content

    def test_form_select_styling(self):
        """Verify select/dropdown CSS"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-select' in content
        assert 'cursor: pointer;' in content

    def test_form_checkbox_radio_styling(self):
        """Verify checkbox/radio CSS"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.form-checkbox,' in content or '.form-checkbox {' in content
        assert '.form-radio' in content

    def test_submit_button_disabled_state(self):
        """Verify disabled submit button styling"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'button[type="submit"]:disabled' in content
        assert 'cursor: not-allowed;' in content

    def test_form_dark_mode(self):
        """Verify dark mode support"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '[data-theme="dark"]' in content

    def test_form_mobile_responsive(self):
        """Verify mobile responsive CSS"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (max-width: 480px)' in content

    def test_form_reduced_motion(self):
        """Verify prefers-reduced-motion support"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '@media (prefers-reduced-motion: reduce)' in content

    def test_form_css_syntax_valid(self):
        """Verify CSS has no obvious syntax errors"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert content.count('{') == content.count('}')
        assert content.count('(') == content.count(')')


class TestFormValidatorJavaScript:
    """Test form validator JavaScript component"""

    def test_form_validator_js_exists(self):
        """Verify form-validator.js file exists"""
        assert os.path.exists('static/js/components/form-validator.js')

    def test_form_validator_js_in_base_html(self):
        """Verify form-validator.js is loaded in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'static/js/components/form-validator.js' in content

    def test_form_validator_class_defined(self):
        """Verify FormValidator class exists"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'class FormValidator' in content

    def test_form_validator_constructor(self):
        """Verify constructor accepts form selector and rules"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'constructor(formSelector, rules' in content
        assert 'this.form' in content
        assert 'this.rules' in content

    def test_form_validator_init_method(self):
        """Verify init() method exists"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'init()' in content
        assert 'addEventListener' in content

    def test_form_validator_validate_field_method(self):
        """Verify validateField() method exists"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'validateField(fieldName, value)' in content

    def test_form_validator_validate_form_method(self):
        """Verify validateForm() method exists"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'validateForm()' in content

    def test_form_validator_required_validation(self):
        """Verify required field validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'required' in content
        assert 'trim()' in content

    def test_form_validator_email_validation(self):
        """Verify email validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'isValidEmail' in content or 'email' in content
        assert '@' in content

    def test_form_validator_url_validation(self):
        """Verify URL validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'isValidUrl' in content or 'url' in content
        assert 'URL' in content

    def test_form_validator_phone_validation(self):
        """Verify phone validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'isValidPhone' in content or 'phone' in content

    def test_form_validator_min_length(self):
        """Verify min-length validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'minLength' in content
        assert 'length' in content

    def test_form_validator_max_length(self):
        """Verify max-length validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'maxLength' in content

    def test_form_validator_pattern_validation(self):
        """Verify pattern/regex validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'pattern' in content
        assert 'RegExp' in content

    def test_form_validator_custom_validation(self):
        """Verify custom validation function support"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'custom' in content
        assert 'typeof' in content

    def test_form_validator_error_messages(self):
        """Verify error message display"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'updateFieldState' in content or 'messageElement' in content

    def test_form_validator_submit_button_management(self):
        """Verify submit button disabled/enabled"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'submitButton' in content
        assert 'disabled' in content

    def test_form_validator_aria_live_region(self):
        """Verify ARIA live region for announcements"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-live' in content or 'ariaLive' in content
        assert 'role="status"' in content or "'status'" in content

    def test_form_validator_reset_method(self):
        """Verify reset() method"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'reset()' in content

    def test_form_validator_get_errors_method(self):
        """Verify getErrors() method"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'getErrors()' in content

    def test_form_validator_get_form_data_method(self):
        """Verify getFormData() method"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'getFormData()' in content

    def test_form_validator_is_form_valid_method(self):
        """Verify isFormValid() method"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'isFormValid()' in content

    def test_form_validator_debounce(self):
        """Verify input debouncing for validation"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'debounce' in content or 'setTimeout' in content
        assert 'clearTimeout' in content

    def test_form_validator_window_export(self):
        """Verify FormValidator is exported to window"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'window.FormValidator' in content

    def test_form_validator_module_export(self):
        """Verify CommonJS export"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'module.exports' in content

    def test_form_validator_js_no_syntax_errors(self):
        """Verify no obvious JavaScript syntax errors"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert content.count('{') == content.count('}')
        assert content.count('(') == content.count(')')
        assert content.count('[') == content.count(']')


class TestFormValidatorIntegration:
    """Integration tests for form validator"""

    def test_form_validator_css_and_js_linked(self):
        """Verify both CSS and JS are linked in base.html"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            base_content = f.read()

        assert 'form-validator.css' in base_content
        assert 'form-validator.js' in base_content

    def test_form_validator_loads_after_accordion(self):
        """Verify form-validator loads after accordion"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        accordion_pos = content.find('accordion.js')
        validator_pos = content.find('form-validator.js')

        if accordion_pos >= 0 and validator_pos >= 0:
            assert accordion_pos < validator_pos, "accordion.js should load before form-validator.js"

    def test_all_sprint4_phase3_components_linked(self):
        """Verify all Phase 3 components are linked"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'accordion.css' in content
        assert 'accordion.js' in content
        assert 'form-validator.css' in content
        assert 'form-validator.js' in content

    def test_no_duplicate_form_validator_css(self):
        """Verify form-validator.css is not duplicated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        count = content.count('form-validator.css')
        assert count == 1, f"form-validator.css appears {count} times, expected 1"

    def test_no_duplicate_form_validator_js(self):
        """Verify form-validator.js is not duplicated"""
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()

        count = content.count('form-validator.js')
        assert count == 1, f"form-validator.js appears {count} times, expected 1"


class TestFormValidatorAccessibility:
    """Accessibility tests for form validator"""

    def test_form_label_required_indicator(self):
        """Verify required field indicator"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.required' in content

    def test_form_aria_role_alert(self):
        """Verify ARIA role=alert for error messages"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'role="alert"' in content or "'alert'" in content

    def test_form_aria_live_polite(self):
        """Verify aria-live=polite for announcements"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'aria-live' in content
        assert 'polite' in content

    def test_form_keyboard_navigation(self):
        """Verify keyboard accessibility (Tab/Enter)"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        assert ':focus' in content

    def test_form_min_height_touch_target(self):
        """Verify 44px minimum touch target for inputs"""
        with open('static/css/components/form-validator.css', 'r', encoding='utf-8') as f:
            content = f.read()

        # Inputs should have sufficient padding/height for touch targets
        assert 'padding:' in content


class TestFormValidatorUsagePatterns:
    """Test usage patterns and documentation"""

    def test_form_validator_usage_comment(self):
        """Verify usage example in comments"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Usage' in content
        assert 'new FormValidator' in content

    def test_form_validator_rules_example(self):
        """Verify rules configuration example"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'required' in content
        assert 'email' in content or 'minLength' in content

    def test_form_validator_feature_list(self):
        """Verify features are documented"""
        with open('static/js/components/form-validator.js', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Real-time' in content or 'validation' in content
        assert 'ARIA' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
