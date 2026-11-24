"""Compatibility entry point for the original F01_CORE command."""
import sys

from core.config import BASE_URL, DATA_FILE, load_local_env, protected_local_url
from core.data_loader import Case, read_cases, resolve_data
from core.browser import build_browser, safe_type, click_visible
from core.reporter import output_results, safe_screenshot
from pages.login_page import login_redirect_complete, prepare_admin_session
from pages.add_user_page import input_field
from pages.locators import CREATE_USER_PATH, FIELD_IDS, PASSWORD_TOGGLE, SUCCESS_SELECTOR, locator_tuple
from test_groups.test_core_fields import matching_text, verify_pre_submit, verify_expected, run_case
from main import main

if __name__ == "__main__":
    sys.exit(main(default_groups=["F01_CORE"]))
