"""Level 2 logical testing-item registry; all URLs, paths, and locators come from config/testing_items.csv.

Zero embedded Moodle URLs, paths, or CSS/ID/XPath locators exist in this module.
"""
from __future__ import annotations

from core.config import get_course_id, get_section_id
from core.testing_items import STRATEGIES, item, item_template, value

# Logical path/token keys
HOME_PATH = value("HOME_PATH", "path")
LOGIN_PATH = value("LOGIN_PATH", "path")
LOGIN_PREFIX = value("LOGIN_PREFIX", "path")
COURSE_VIEW_PATH_TEMPLATE = value("COURSE_VIEW_PATH_TEMPLATE", "path")
ADD_QUIZ_PATH_TEMPLATE = value("ADD_QUIZ_PATH_TEMPLATE", "path")
EDIT_QUIZ_PATH_TEMPLATE = value("EDIT_QUIZ_PATH_TEMPLATE", "path")
QUIZ_LINK_HREF_TOKEN = value("QUIZ_LINK_HREF_TOKEN", "token")
QUIZ_INSTANCE_CLASS_TOKEN = value("QUIZ_INSTANCE_CLASS_TOKEN", "token")

# Mapping from CSV/logical field names to externalized testing_items.csv keys
FIELD_ITEM_KEYS = {
    "name": "FIELD.name",
    "showdescription": "FIELD.showdescription",
    "timeopen[enabled]": "FIELD.timeopen_enabled",
    "timeopen[year]": "FIELD.timeopen_year",
    "timeopen[month]": "FIELD.timeopen_month",
    "timeopen[day]": "FIELD.timeopen_day",
    "timeopen[hour]": "FIELD.timeopen_hour",
    "timeopen[minute]": "FIELD.timeopen_minute",
    "timeclose[enabled]": "FIELD.timeclose_enabled",
    "timeclose[year]": "FIELD.timeclose_year",
    "timeclose[month]": "FIELD.timeclose_month",
    "timeclose[day]": "FIELD.timeclose_day",
    "timeclose[hour]": "FIELD.timeclose_hour",
    "timeclose[minute]": "FIELD.timeclose_minute",
    "timelimit[enabled]": "FIELD.timelimit_enabled",
    "timelimit[number]": "FIELD.timelimit_number",
    "timelimit[timeunit]": "FIELD.timelimit_timeunit",
    "overduehandling": "FIELD.overduehandling",
    "graceperiod[enabled]": "FIELD.graceperiod_enabled",
    "graceperiod[number]": "FIELD.graceperiod_number",
    "graceperiod[timeunit]": "FIELD.graceperiod_timeunit",
    "gradecat": "FIELD.gradecat",
    "gradepass": "FIELD.gradepass",
    "attempts": "FIELD.attempts",
    "grademethod": "FIELD.grademethod",
    "decimalpoints": "FIELD.decimalpoints",
    "feedbackboundaries[0]": "FIELD.feedbackboundaries_0",
    "feedbackboundaries[1]": "FIELD.feedbackboundaries_1",
}

ERROR_ITEM_KEYS = {
    "name_error": "VERIFICATION.name_error",
    "timeclose_error": "VERIFICATION.timeclose_error",
    "graceperiod_error": "VERIFICATION.graceperiod_error",
    "gradepass_error": "VERIFICATION.gradepass_error",
    "feedbackboundary_0_error": "VERIFICATION.feedbackboundary_0_error",
    "feedbackboundary_1_error": "VERIFICATION.feedbackboundary_1_error",
}

REQUIRED_LOCATOR_ITEMS = (
    "LOGIN_LINK",
    "LOGIN_USERNAME_INPUT",
    "LOGIN_PASSWORD_INPUT",
    "LOGIN_BUTTON",
    "LOGIN_ERROR_ALERT",
    "EXPAND_ALL_LINK",
    "SHOW_MORE_LINKS",
    "INTRO_EDITOR_IFRAME",
    "INTRO_EDITOR_BODY",
    "INTRO_EDITOR_BODY_READ",
    "ADD_FEEDBACK_FIELDS_BUTTON",
    "SUBMIT_RETURN_BUTTON",
    "SUBMIT_DISPLAY_BUTTON",
    "CANCEL_BUTTON",
    "VERIFICATION.course_page_body",
    "VERIFICATION.quiz_view_body",
    "VERIFICATION.quiz_link_xpath",
    "VERIFICATION.quiz_view_h1_xpath",
    "VERIFICATION.visible_text_xpath",
    *FIELD_ITEM_KEYS.values(),
    *ERROR_ITEM_KEYS.values(),
)

# Eagerly validate every required logical item at import time (fail fast, no fallback)
for _key in REQUIRED_LOCATOR_ITEMS:
    value(_key, *STRATEGIES.keys())


def course_view_path() -> str:
    return COURSE_VIEW_PATH_TEMPLATE.format(course_id=get_course_id())


def add_quiz_path() -> str:
    return ADD_QUIZ_PATH_TEMPLATE.format(course_id=get_course_id(), section_id=get_section_id())


def edit_quiz_path(cmid: str) -> str:
    return EDIT_QUIZ_PATH_TEMPLATE.format(cmid=cmid)


def field_locator(field_key: str) -> tuple[str, str]:
    return item(FIELD_ITEM_KEYS[field_key])


def error_locator(target_key: str) -> tuple[str, str]:
    return item(ERROR_ITEM_KEYS[target_key])
