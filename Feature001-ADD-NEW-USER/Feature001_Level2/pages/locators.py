"""Level 2 logical testing-item names and compatibility views (values from CSV)."""
from core.testing_items import item, value, encoded_locator, locator_tuple, STRATEGIES

CREATE_USER_PATH = value('CREATE_USER_PATH', "path")
LOGIN_PATH = value('LOGIN_PATH', "path")
HOME_PATH = value('HOME_PATH', "path")
LOGIN_PREFIX = value('LOGIN_PREFIX', "path")
THEME_IMAGE_PATH = value('THEME_IMAGE_PATH', "path")
PIX_FILE_PATH = value('PIX_FILE_PATH', "path")
THEME_FILE_PATH = value('THEME_FILE_PATH', "path")
DRAFT_FILE_TOKEN = value('DRAFT_FILE_TOKEN', "token")
THEME_FILE_QUERY_PREFIX = value('THEME_FILE_QUERY_PREFIX', "token")
RICH_FRAME_SUFFIX = value('RICH_FRAME_SUFFIX', "token")
PASSWORD_TOGGLE = value('PASSWORD_TOGGLE', *STRATEGIES)
SUCCESS_SELECTOR = value('SUCCESS_SELECTOR', *STRATEGIES)
LOGIN_LINK = value('LOGIN_LINK', *STRATEGIES)
LOGIN_ERROR_SELECTOR = value('LOGIN_ERROR_SELECTOR', *STRATEGIES)
RICH_BODY = value('RICH_BODY', *STRATEGIES)
RICH_BOLD = value('RICH_BOLD', *STRATEGIES)
INTERESTS_TOGGLE = value('INTERESTS_TOGGLE', *STRATEGIES)
TAG_INPUT = value('TAG_INPUT', *STRATEGIES)
TAG_SELECTED = value('TAG_SELECTED', *STRATEGIES)
PICTURE_ADD = value('PICTURE_ADD', *STRATEGIES)
PICTURE_FILES = value('PICTURE_FILES', *STRATEGIES)
PICTURE_THUMBNAIL = value('PICTURE_THUMBNAIL', *STRATEGIES)
PICTURE_FILE_ICONS = value('PICTURE_FILE_ICONS', *STRATEGIES)
PICTURE_SECTION = value('PICTURE_SECTION', *STRATEGIES)
PICKER_UPLOAD_INPUT = value('PICKER_UPLOAD_INPUT', *STRATEGIES)
PICKER_UPLOAD_BUTTON = value('PICKER_UPLOAD_BUTTON', *STRATEGIES)
PICKER_ERROR = value('PICKER_ERROR', *STRATEGIES)
PICKER_DIALOG = value('PICKER_DIALOG', *STRATEGIES)
PICKER_DIALOG_TITLE = value('PICKER_DIALOG_TITLE', *STRATEGIES)
PICKER_DIALOG_BODY = value('PICKER_DIALOG_BODY', *STRATEGIES)
PICKER_CLOSE = value('PICKER_CLOSE', *STRATEGIES)
USER_MENU = value('USER_MENU', *STRATEGIES)
DENIAL_ERROR = value('DENIAL_ERROR', *STRATEGIES)
LOGIN_USERNAME_ID = value('LOGIN_USERNAME_ID', *STRATEGIES)
LOGIN_PASSWORD_ID = value('LOGIN_PASSWORD_ID', *STRATEGIES)
LOGIN_BUTTON_ID = value('LOGIN_BUTTON_ID', *STRATEGIES)
AUTH_ID = value('AUTH_ID', *STRATEGIES)
SUBMIT_ID = value('SUBMIT_ID', *STRATEGIES)
RICH_FRAME = value('RICH_FRAME', *STRATEGIES)
CANCEL_ID = value('CANCEL_ID', *STRATEGIES)
PICTURE_UNLIMITED = value('PICTURE_UNLIMITED', *STRATEGIES)
PICKER_REPOSITORY = value('PICKER_REPOSITORY', *STRATEGIES)
PICKER_UPLOAD_TEXT = value('PICKER_UPLOAD_TEXT', *STRATEGIES)
PICKER_OK = value('PICKER_OK', *STRATEGIES)

FIELD_IDS = {key: value(f"FIELD_IDS.{key}", *STRATEGIES) for key in ('username', 'first_name', 'last_name', 'email', 'new_password')}

TEXT_FIELD_IDS = {key: value(f"TEXT_FIELD_IDS.{key}", *STRATEGIES) for key in ('city', 'image_alt', 'first_name_phonetic', 'last_name_phonetic', 'middle_name', 'alternate_name', 'id_number', 'institution', 'department', 'address', 'phone', 'mobile_phone')}

SECTION_TOGGLES = {key: value(f"SECTION_TOGGLES.{key}", *STRATEGIES) for key in ('additional_names', 'optional')}

FLAG_IDS = {key: value(f"FLAG_IDS.{key}", *STRATEGIES) for key in ('suspended', 'generate_password', 'force_password_change', 'delete_picture')}

SELECT_IDS = {key: value(f"SELECT_IDS.{key}", *STRATEGIES) for key in ('email_display', 'country', 'timezone', 'language')}

# Verification targets reuse input locators where applicable.
VERIFY_KEYS = {
    'success_message': 'VERIFICATION.success_message',
    'password_error': 'VERIFICATION.password_error',
    'username_error': 'VERIFICATION.username_error',
    'email_error': 'VERIFICATION.email_error',
    'system_error': 'VERIFICATION.system_error',
    'first_name_error': 'VERIFICATION.first_name_error',
    'last_name_error': 'VERIFICATION.last_name_error',
    'new_password': 'FIELD_IDS.new_password',
    'first_name': 'FIELD_IDS.first_name',
    'last_name': 'FIELD_IDS.last_name',
    'email': 'FIELD_IDS.email',
    'city': 'TEXT_FIELD_IDS.city',
    'image_alt': 'TEXT_FIELD_IDS.image_alt',
    'first_name_phonetic': 'TEXT_FIELD_IDS.first_name_phonetic',
    'last_name_phonetic': 'TEXT_FIELD_IDS.last_name_phonetic',
    'middle_name': 'TEXT_FIELD_IDS.middle_name',
    'alternate_name': 'TEXT_FIELD_IDS.alternate_name',
    'id_number': 'TEXT_FIELD_IDS.id_number',
    'institution': 'TEXT_FIELD_IDS.institution',
    'department': 'TEXT_FIELD_IDS.department',
    'address': 'TEXT_FIELD_IDS.address',
    'phone': 'TEXT_FIELD_IDS.phone',
    'mobile_phone': 'TEXT_FIELD_IDS.mobile_phone',
    'description_error': 'VERIFICATION.description_error',
    'suspended_error': 'VERIFICATION.suspended_error',
    'picture_file': 'PICTURE_FILES',
    'picture_thumbnail': 'PICTURE_THUMBNAIL',
    'create_button': 'SUBMIT_ID',
    'add_user_link': 'VERIFICATION.add_user_link',
}
VERIFICATION_LOCATORS = {target: encoded_locator(key) for target, key in VERIFY_KEYS.items()}


def resolve_target(target):
    return encoded_locator(VERIFY_KEYS[target])
