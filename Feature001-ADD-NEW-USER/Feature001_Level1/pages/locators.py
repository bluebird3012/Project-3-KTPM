"""Level 1 testing items: page paths and Selenium locators."""
from __future__ import annotations



CREATE_USER_PATH = "/user/editadvanced.php?id=-1"

# Fixed locators are INTENTIONAL in Level 1.
FIELD_IDS = {
    "username": "id_username",
    "first_name": "id_firstname",
    "last_name": "id_lastname",
    "email": "id_email",
    "new_password": "id_newpassword",
}
PASSWORD_TOGGLE = '[data-passwordunmaskid="id_newpassword"] a[data-passwordunmask="edit"]'
SUCCESS_SELECTOR = 'div.alert-success[role="alert"]'


VERIFICATION_LOCATORS = {
    'success_message': "css=div.alert-success[role='alert']",
    'password_error': 'id=id_error_newpassword',
    'username_error': 'id=id_error_username',
    'email_error': 'id=id_error_email',
    'system_error': 'css=p.errormessage',
    'first_name_error': 'id=id_error_firstname',
    'last_name_error': 'id=id_error_lastname',
    'new_password': 'id=id_newpassword',
    'first_name': 'id=id_firstname',
    'last_name': 'id=id_lastname',
    'email': 'id=id_email',
}


def locator_tuple(locator: str):
    """Convert source Katalon locator format to Selenium tuple."""
    from selenium.webdriver.common.by import By
    if locator.startswith("id="):
        return (By.ID, locator[3:])
    if locator.startswith("css="):
        return (By.CSS_SELECTOR, locator[4:])
    if locator.startswith("xpath="):
        return (By.XPATH, locator[6:])
    raise ValueError(f"Unsupported locator format: {locator!r}")


def resolve_target(target: str) -> str:
    """Resolve a semantic CSV target to the original Katalon locator."""
    return VERIFICATION_LOCATORS[target]

LOGIN_PATH = "/login/index.php"
LOGIN_LINK = 'a[href*="/login/index.php"]'
LOGIN_USERNAME_ID = "username"
LOGIN_PASSWORD_ID = "password"
LOGIN_BUTTON_ID = "loginbtn"
LOGIN_ERROR_SELECTOR = "#loginerrormessage, .loginerrors, .alert-danger"
AUTH_ID = "id_auth"
SUBMIT_ID = "id_submitbutton"

# Additional text fields and collapsible sections recorded in F02_TEXT.
TEXT_FIELD_IDS = {
    "city": "id_city",
    "image_alt": "id_imagealt",
    "first_name_phonetic": "id_firstnamephonetic",
    "last_name_phonetic": "id_lastnamephonetic",
    "middle_name": "id_middlename",
    "alternate_name": "id_alternatename",
    "id_number": "id_idnumber",
    "institution": "id_institution",
    "department": "id_department",
    "address": "id_address",
    "phone": "id_phone1",
    "mobile_phone": "id_phone2",
}
SECTION_TOGGLES = {
    "additional_names": 'a[aria-controls="id_moodle_additional_namescontainer"]',
    "optional": 'a[aria-controls="id_moodle_optionalcontainer"]',
}
VERIFICATION_LOCATORS.update({
    field: f"id={element_id}" for field, element_id in TEXT_FIELD_IDS.items()
})

# F03–F11 testing items. CSVs contain only logical names and data.
VERIFICATION_LOCATORS.update({
    'description_error': 'id=id_error_description_editor',
    'suspended_error': 'id=id_error_suspended',
    'picture_file': 'css=#id_imagefile_fieldset .fp-file',
    'picture_thumbnail': 'css=#id_imagefile_fieldset .fp-file img[src*="preview=thumb"], #id_imagefile_fieldset .fp-file img[src*="preview=tinyicon"]',
    'create_button': 'id=id_submitbutton',
    'add_user_link': "xpath=//a[contains(@href,'/user/editadvanced.php') and contains(normalize-space(.),'Add a new user')]",
})
RICH_FRAME = 'id_description_editor_ifr'
RICH_BODY = 'body#tinymce'
RICH_BOLD = 'body#tinymce strong'
FLAG_IDS = {
    'suspended': 'id_suspended', 'generate_password': 'id_createpassword',
    'force_password_change': 'id_preference_auth_forcepasswordchange',
    'delete_picture': 'id_deletepicture',
}
SELECT_IDS = {'email_display':'id_maildisplay', 'country':'id_country', 'timezone':'id_timezone', 'language':'id_lang'}
INTERESTS_TOGGLE = 'a[aria-controls="id_moodle_interestscontainer"]'
TAG_INPUT = '#fitem_id_interests input[placeholder="Enter tags..."]'
TAG_SELECTED = '#id_interests option:checked'
PICTURE_ADD = '#id_imagefile_fieldset .fp-btn-add a'
PICTURE_FILES = '#id_imagefile_fieldset .fp-file'
PICTURE_THUMBNAIL = VERIFICATION_LOCATORS['picture_thumbnail'][4:]
PICTURE_FILE_ICONS = '#id_imagefile_fieldset .fp-file img'
PICTURE_UNLIMITED = "//*[contains(normalize-space(text()),'Maximum file size: Unlimited')]"
PICTURE_SECTION = 'a[aria-controls="id_moodle_picturecontainer"]'
PICKER_REPOSITORY = "//*[self::a or self::button][normalize-space(.)='Upload a file' or .//*[normalize-space(.)='Upload a file']]"
PICKER_UPLOAD_INPUT = '.file-picker input[type="file"], .fp-upload-form input[type="file"]'
PICKER_UPLOAD_BUTTON = '.file-picker .fp-upload-btn, .fp-upload-form .fp-upload-btn'
PICKER_UPLOAD_TEXT = "//button[normalize-space(.)='Upload this file']"
PICKER_ERROR = '.fp-error, .fp-msg-error, .file-picker .alert-danger, .moodle-dialogue .alert-danger, .moodle-dialogue .fp-msg .fp-msg-text, .moodle-dialogue [role=alert], .modal [role=alert], .modal .alert-danger'
PICKER_DIALOG = '.moodle-dialogue, .modal.show, [role=alertdialog]'
PICKER_DIALOG_TITLE = '.moodle-dialogue-hd, .modal-title, [data-region=title]'
PICKER_DIALOG_BODY = '.moodle-dialogue-bd, .modal-body, [data-region=body]'
PICKER_CLOSE = '.moodle-dialogue-base .moodle-dialogue .closebutton, .moodle-dialogue-base .moodle-dialogue button.btn-close, .moodle-dialogue-base .moodle-dialogue [data-action="hide"]'
CANCEL_ID = 'id_cancel'
USER_MENU = '.usermenu .dropdown-toggle, #user-menu-toggle'
DENIAL_ERROR = '.alert-danger, .errormessage, #notice'

PICKER_OK = "//button[normalize-space(.)='OK' or normalize-space(.)='Ok']"
