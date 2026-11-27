"""Level 1 hardcoded Moodle URLs, paths, and UI locators for Feature 004 (Add Quiz).

Verified directly against live Moodle 5.1.9 DOM (`tools/live_add_quiz_dom.html`)
and cross-referenced with Project #2 Katalon recordings (`tools/extracted_locators_f004.json`).
Note: Level 2 will externalize all items in this module to `config/testing_items.csv`.
"""
from __future__ import annotations

from core.config import get_course_id, get_section_id

# Paths
HOME_PATH = "/"
LOGIN_PATH = "/login/index.php"
LOGIN_PREFIX = "/login"
COURSE_VIEW_PATH_TEMPLATE = "/course/view.php?id={course_id}"
ADD_QUIZ_PATH_TEMPLATE = "/course/modedit.php?add=quiz&type&course={course_id}&sectionid={section_id}&return=0&beforemod=0"
EDIT_QUIZ_PATH_TEMPLATE = "/course/modedit.php?update={cmid}&return=1"


def course_view_path() -> str:
    return COURSE_VIEW_PATH_TEMPLATE.format(course_id=get_course_id())


def add_quiz_path() -> str:
    return ADD_QUIZ_PATH_TEMPLATE.format(course_id=get_course_id(), section_id=get_section_id())


def edit_quiz_path(cmid: str) -> str:
    return EDIT_QUIZ_PATH_TEMPLATE.format(cmid=cmid)


# Login page
LOGIN_LINK = "a[href*='/login/index.php']"
LOGIN_USERNAME_ID = "username"
LOGIN_PASSWORD_ID = "password"
LOGIN_BUTTON_ID = "loginbtn"
LOGIN_ERROR_SELECTOR = "#loginerrormessage, .loginerrors, .alert-danger"

# Add / Edit Quiz form - core controls
MFORM_NAME_INPUT = "form.mform input[name='name']"
NAME_INPUT_ID = "id_name"
EXPAND_ALL_LINK = "form.mform a.collapseexpand"
SHOW_MORE_LINKS = "form.mform a.moreless-toggler:not(.moreless-less)"

# General / Description (TinyMCE)
INTRO_EDITOR_IFRAME = "iframe[id^='id_introeditor'][id$='_ifr']"
INTRO_EDITOR_BODY = "body[contenteditable='true']"
INTRO_EDITOR_BODY_READ = "body"
SHOW_DESCRIPTION_CHECKBOX = "form.mform input[type='checkbox'][name='showdescription']"

# Timing
TIMEOPEN_ENABLED = "form.mform [name='timeopen[enabled]']"
TIMEOPEN_YEAR = "form.mform [name='timeopen[year]']"
TIMEOPEN_MONTH = "form.mform [name='timeopen[month]']"
TIMEOPEN_DAY = "form.mform [name='timeopen[day]']"
TIMEOPEN_HOUR = "form.mform [name='timeopen[hour]']"
TIMEOPEN_MINUTE = "form.mform [name='timeopen[minute]']"

TIMECLOSE_ENABLED = "form.mform [name='timeclose[enabled]']"
TIMECLOSE_YEAR = "form.mform [name='timeclose[year]']"
TIMECLOSE_MONTH = "form.mform [name='timeclose[month]']"
TIMECLOSE_DAY = "form.mform [name='timeclose[day]']"
TIMECLOSE_HOUR = "form.mform [name='timeclose[hour]']"
TIMECLOSE_MINUTE = "form.mform [name='timeclose[minute]']"

TIMELIMIT_ENABLED = "form.mform [name='timelimit[enabled]']"
TIMELIMIT_NUMBER = "form.mform [name='timelimit[number]']"
TIMELIMIT_TIMEUNIT = "form.mform [name='timelimit[timeunit]']"

OVERDUEHANDLING_SELECT = "form.mform select[name='overduehandling']"

GRACEPERIOD_ENABLED = "form.mform [name='graceperiod[enabled]']"
GRACEPERIOD_NUMBER = "form.mform [name='graceperiod[number]']"
GRACEPERIOD_TIMEUNIT = "form.mform [name='graceperiod[timeunit]']"

# Grade & Appearance
GRADECAT_SELECT = "form.mform select[name='gradecat']"
GRADEPASS_INPUT = "form.mform input[name='gradepass']"
ATTEMPTS_SELECT = "form.mform select[name='attempts']"
GRADEMETHOD_SELECT = "form.mform select[name='grademethod']"
DECIMALPOINTS_SELECT = "form.mform select[name='decimalpoints']"

# Overall feedback
FEEDBACK_BOUNDARY_0 = "form.mform input[name='feedbackboundaries[0]']"
FEEDBACK_BOUNDARY_1 = "form.mform input[name='feedbackboundaries[1]']"
# Live Moodle 5.1.9 DOM renders name='boundary_add_fields' (id='id_boundary_add_fields'),
# whereas legacy Katalon recorded name='addfeedbacks'. Support exact live button selector.
ADD_FEEDBACK_FIELDS_BTN = "input[name='boundary_add_fields'], button[name='boundary_add_fields'], input[name='addfeedbacks'], button[name='addfeedbacks']"

# Submit / Cancel actions
SUBMIT_RETURN_BTN = "input[name='submitbutton2'], button[name='submitbutton2']"
SUBMIT_DISPLAY_BTN = "input[name='submitbutton'], button[name='submitbutton']"
CANCEL_BTN = "input[name='cancel'], button[name='cancel']"

# Validation error containers (verified against live_add_quiz_dom.html)
ERROR_SELECTORS = {
    "name_error": "#id_error_name",
    "timeclose_error": "#id_error_timeclose, [id^='id_error_timeclose_']",
    "graceperiod_error": "#id_error_graceperiod, [id^='id_error_graceperiod_']",
    "gradepass_error": "#id_error_gradepass",
    "feedbackboundary_0_error": "#id_error_feedbackboundaries_0, [id='id_error_feedbackboundaries[0]'], #id_error_feedbackboundaries",
    "feedbackboundary_1_error": "#id_error_feedbackboundaries_1, [id='id_error_feedbackboundaries[1]'], #id_error_feedbackboundaries1",
}

# Field map for reopen-edit verification
FIELD_CSS_MAP = {
    "name": MFORM_NAME_INPUT,
    "showdescription": SHOW_DESCRIPTION_CHECKBOX,
    "timeopen[enabled]": TIMEOPEN_ENABLED,
    "timeopen[year]": TIMEOPEN_YEAR,
    "timeopen[month]": TIMEOPEN_MONTH,
    "timeopen[day]": TIMEOPEN_DAY,
    "timeopen[hour]": TIMEOPEN_HOUR,
    "timeopen[minute]": TIMEOPEN_MINUTE,
    "timeclose[enabled]": TIMECLOSE_ENABLED,
    "timeclose[year]": TIMECLOSE_YEAR,
    "timeclose[month]": TIMECLOSE_MONTH,
    "timeclose[day]": TIMECLOSE_DAY,
    "timeclose[hour]": TIMECLOSE_HOUR,
    "timeclose[minute]": TIMECLOSE_MINUTE,
    "timelimit[enabled]": TIMELIMIT_ENABLED,
    "timelimit[number]": TIMELIMIT_NUMBER,
    "timelimit[timeunit]": TIMELIMIT_TIMEUNIT,
    "overduehandling": OVERDUEHANDLING_SELECT,
    "graceperiod[enabled]": GRACEPERIOD_ENABLED,
    "graceperiod[number]": GRACEPERIOD_NUMBER,
    "graceperiod[timeunit]": GRACEPERIOD_TIMEUNIT,
    "gradecat": GRADECAT_SELECT,
    "gradepass": GRADEPASS_INPUT,
    "attempts": ATTEMPTS_SELECT,
    "grademethod": GRADEMETHOD_SELECT,
    "decimalpoints": DECIMALPOINTS_SELECT,
    "feedbackboundaries[0]": FEEDBACK_BOUNDARY_0,
    "feedbackboundaries[1]": FEEDBACK_BOUNDARY_1,
}

# Destination pages
COURSE_PAGE_BODY = "body[id^='page-course-view-'], body#page-course-section"
QUIZ_VIEW_BODY = "body#page-mod-quiz-view"
QUIZ_VIEW_H1 = "h1"
QUIZ_LINK_HREF_TOKEN = "/mod/quiz/view.php"
