"""LEVEL 1 helper - Moodle UI actions used by every test script of Feature 3 (Add Assignment).

Level 1 = data-driven testing: the TEST DATA (assignment name, dates, grades, ... and the
expected results) comes from the CSV files in ./data, but the SITE URL, the page paths and
the ELEMENT LOCATORS are hard-coded in the block below.

Target: Moodle 5.1.8 (mutms/demo Docker) - Course > Add an activity > Assignment.
"""
import html
import os
import re
import time

from selenium import webdriver
from selenium.common.exceptions import (ElementNotInteractableException, NoAlertPresentException,
                                        NoSuchElementException, StaleElementReferenceException,
                                        TimeoutException, UnexpectedAlertPresentException,
                                        WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# ===== SITE AND ELEMENTS (Level 1: hard-coded in the script) =====
SITE = {
    "BASE_URL": "http://127.0.0.1:9502",
    "LOGIN_PAGE": "/login/index.php",
    "LOGOUT_PAGE": "/login/logout.php?sesskey={sesskey}",
    "COURSE_PAGE": "/course/view.php?id={course}",
    "ADD_ASSIGNMENT_PAGE": "/course/modedit.php?add=assign&course={course}&section={section}&return=0",
    "EDIT_ACTIVITY_PAGE": "/course/modedit.php?update={cmid}",
    "DELETE_ACTIVITY_PAGE": "/course/mod.php?delete={cmid}&confirm=1&sesskey={sesskey}",
    "ASSIGNMENT_VIEW_PATH": "/mod/assign/view.php",
    "FORM_PATH": "/course/modedit.php",
    "COURSE_PATH": "/course/view.php",
    "LOGIN_PATH": "/login/index.php",
    "TIMEOUT": "60",
    "PAGE_LOAD_TIMEOUT": "240",
}

L = {
    # login / page
    "login.username": (By.ID, "username"),
    "login.password": (By.ID, "password"),
    "login.button": (By.ID, "loginbtn"),
    "page.body": (By.TAG_NAME, "body"),
    "page.heading": (By.CSS_SELECTOR, "h1, h2"),
    # Add an assignment form
    "form.name": (By.ID, "id_name"),
    "form.expand_all": (By.CSS_SELECTOR, "a.collapseexpand"),
    "form.description_iframe": (By.ID, "id_introeditor_ifr"),
    "form.description_body": (By.ID, "tinymce"),
    "form.description_textarea": (By.ID, "id_introeditor"),
    "date.allow_from": (By.ID, "id_allowsubmissionsfromdate_{part}"),
    "date.due": (By.ID, "id_duedate_{part}"),
    "date.cutoff": (By.ID, "id_cutoffdate_{part}"),
    "date.remind": (By.ID, "id_gradingduedate_{part}"),
    "form.onlinetext": (By.ID, "id_assignsubmission_onlinetext_enabled"),
    "form.file": (By.ID, "id_assignsubmission_file_enabled"),
    "form.wordlimit": (By.ID, "id_assignsubmission_onlinetext_wordlimit"),
    "form.wordlimit_enabled": (By.ID, "id_assignsubmission_onlinetext_wordlimit_enabled"),
    "form.maxfiles": (By.ID, "id_assignsubmission_file_maxfiles"),
    "form.maxsize": (By.ID, "id_assignsubmission_file_maxsizebytes"),
    "form.grade": (By.ID, "id_grade_modgrade_point"),
    "form.gradepass": (By.ID, "id_gradepass"),
    "form.sesskey": (By.CSS_SELECTOR, "input[name='sesskey']"),
    "button.save_return": (By.ID, "id_submitbutton2"),
    "button.save_display": (By.ID, "id_submitbutton"),
    "button.cancel": (By.ID, "id_cancel"),
    # error messages next to the fields
    "error.name": (By.ID, "id_error_name"),
    "error.grade": (By.CSS_SELECTOR, "#id_error_grade, #fgroup_id_error_grade, [id^='id_error_grade_modgrade']"),
    "error.gradepass": (By.ID, "id_error_gradepass"),
    "error.allow_from": (By.CSS_SELECTOR, "#id_error_allowsubmissionsfromdate, #fgroup_id_error_allowsubmissionsfromdate"),
    "error.due": (By.CSS_SELECTOR, "#id_error_duedate, #fgroup_id_error_duedate"),
    "error.cutoff": (By.CSS_SELECTOR, "#id_error_cutoffdate, #fgroup_id_error_cutoffdate"),
    "error.remind": (By.CSS_SELECTOR, "#id_error_gradingduedate, #fgroup_id_error_gradingduedate"),
    "error.wordlimit": (By.CSS_SELECTOR, "#id_error_assignsubmission_onlinetext_wordlimit_group, #fgroup_id_error_assignsubmission_onlinetext_wordlimit_group, #id_error_assignsubmission_onlinetext_wordlimit"),
    "error.any": (By.CSS_SELECTOR, ".invalid-feedback, .error"),
    # course page
    "course.activity": (By.CSS_SELECTOR, "[data-for='cmitem']"),
    "course.activity_name": (By.CSS_SELECTOR, "[data-activityname]"),
    "course.edit_switch": (By.CSS_SELECTOR, "form.editmode-switch-form"),
    "course.add_activity": (By.CSS_SELECTOR, "[data-action='open-chooser'], .section-modchooser-link"),
}
# ===== END OF SITE AND ELEMENTS =====

TIMEOUT = int(SITE.get("TIMEOUT", 60))
PAGE_LOAD_TIMEOUT = int(SITE.get("PAGE_LOAD_TIMEOUT", 240))
DATE_FIELDS = ("allow_from", "due", "cutoff", "remind")
TEXT_FIELDS = ("name", "grade", "gradepass", "wordlimit")
SELECT_FIELDS = ("maxfiles", "maxsize")
CHECKBOX_FIELDS = ("onlinetext", "file")


def loc(key, **fmt):
    """Locator (By, value) of an element; {part}/{field} placeholders are filled from fmt."""
    if key not in L:
        raise KeyError(f"element '{key}' is not defined")
    by, value = L[key]
    return (by, value.format(**fmt)) if fmt else (by, value)


# ------------------------------------------------------------------ driver
def create_driver():
    """Browser: environment variable BROWSER (chrome|firefox|edge). HEADLESS=1 runs without a window."""
    browser = os.environ.get("BROWSER", "chrome").lower()
    headless = os.environ.get("HEADLESS", "0") == "1"
    if browser == "firefox":
        opts = webdriver.FirefoxOptions()
        if headless:
            opts.add_argument("-headless")
        driver = webdriver.Firefox(options=opts)
    elif browser == "edge":
        opts = webdriver.EdgeOptions()
        if headless:
            opts.add_argument("--headless=new")
        driver = webdriver.Edge(options=opts)
    else:
        opts = webdriver.ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1400,1000")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=opts)
    driver.set_window_size(1400, 1000)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def contains_any(haystack, alternatives):
    hay = norm(haystack).lower()
    return any(norm(a).lower() in hay for a in alternatives)


def same_value(expected, actual):
    """Compares two field values; numbers are compared as numbers (40 == 40.00)."""
    try:
        return abs(float(expected) - float(actual)) < 1e-9
    except (TypeError, ValueError):
        return norm(expected).lower() == norm(actual).lower()


class MoodleUI:
    """Small page object for the Moodle pages used by the Add Assignment tests."""

    def __init__(self, driver, accounts, course_id, section="1"):
        self.d = driver
        self.accounts = accounts          # {"teacher": (user, pw), "student": (...), "admin": (...)}
        self.course = str(course_id)
        self.section = str(section or "1")
        self.current_user = None
        self.alerts = []                  # texts of JavaScript alerts seen (XSS checks)

    # ---------------------------------------------------------------- basics
    def url(self, page, **fmt):
        fmt.setdefault("course", self.course)
        fmt.setdefault("section", self.section)
        return SITE["BASE_URL"].rstrip("/") + SITE[page].format(**fmt)

    def accept_alerts(self):
        for _ in range(5):
            try:
                alert = self.d.switch_to.alert
                self.alerts.append(alert.text)
                alert.accept()
            except NoAlertPresentException:
                return

    def go(self, page_or_url, **fmt):
        target = page_or_url if page_or_url.startswith("http") else self.url(page_or_url, **fmt)
        try:
            self.d.get(target)
        except UnexpectedAlertPresentException:
            self.accept_alerts()
        self.accept_alerts()
        self.wait_ready()

    def wait_ready(self, timeout=None):
        try:
            WebDriverWait(self.d, timeout or PAGE_LOAD_TIMEOUT).until(
                lambda d: d.execute_script("return document.readyState") == "complete")
        except UnexpectedAlertPresentException:
            self.accept_alerts()

    def find(self, locator, timeout=None):
        return WebDriverWait(self.d, timeout or TIMEOUT).until(EC.presence_of_element_located(locator))

    def exists(self, locator):
        return len(self.d.find_elements(*locator)) > 0

    def is_displayed(self, locator):
        return any(e.is_displayed() for e in self.d.find_elements(*locator))

    def page_text(self):
        try:
            return self.d.find_element(*loc("page.body")).text
        except (NoSuchElementException, UnexpectedAlertPresentException):
            self.accept_alerts()
            return self.d.find_element(*loc("page.body")).text

    def current_url(self):
        return self.d.current_url

    def on_page(self, path_key):
        return SITE[path_key] in self.current_url()

    def screenshot(self, path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.d.save_screenshot(path)
        except Exception:
            pass

    # ---------------------------------------------------------------- session
    def sesskey(self):
        try:
            return self.d.execute_script("return (window.M && M.cfg && M.cfg.sesskey) || null;")
        except WebDriverException:
            return None

    def logout(self):
        key = self.sesskey()
        if key:
            self.go("LOGOUT_PAGE", sesskey=key)
        else:                     # no Moodle page open: drop the session cookie instead
            self.d.delete_all_cookies()
        self.current_user = None

    def login(self, who):
        """Logs in; retries with a fresh login page because Moodle silently refuses the form when its
        hidden logintoken belongs to the session that was just closed by the logout."""
        user, password = self.accounts[who]
        for attempt in range(3):
            self.go("LOGIN_PAGE")
            if not self.exists(loc("login.username")):      # already logged in as someone
                self.logout()
                self.go("LOGIN_PAGE")
            self.set_text(loc("login.username"), user)
            self.set_text(loc("login.password"), password)
            button = self.d.find_element(*loc("login.button"))
            button.click()
            try:
                WebDriverWait(self.d, PAGE_LOAD_TIMEOUT).until(EC.staleness_of(button))
            except (TimeoutException, WebDriverException):
                pass
            self.wait_ready()
            if not (self.on_page("LOGIN_PATH") and self.exists(loc("login.username"))):
                self.current_user = who
                return
            if attempt == 1:
                self.d.delete_all_cookies()                 # last try: completely new session
        raise AssertionError(f"Login failed for user '{user}'")

    def new_browser(self):
        """Closes the browser and opens a new one (a completely new Moodle session)."""
        try:
            self.d.quit()
        except WebDriverException:
            pass
        self.d = create_driver()
        self.current_user = None

    def ensure_user(self, who):
        """Logs in as `who` ('guest' = not logged in). Switching user uses a new browser: logging in
        right after a logout in the same browser is refused by Moodle (stale logintoken)."""
        if self.current_user == who and who != "guest":
            return
        if self.current_user is not None or who == "guest":
            self.new_browser()
        if who != "guest":
            self.login(who)

    # ---------------------------------------------------------------- course page
    def open_course(self):
        self.go("COURSE_PAGE")

    def course_activities(self):
        """[(cmid, name), ...] of the activities shown on the course page currently open."""
        items = []
        for el in self.d.find_elements(*loc("course.activity")):
            names = el.find_elements(*loc("course.activity_name"))
            name = names[0].get_attribute("data-activityname") if names else ""
            # the attribute is escaped twice by Moodle ("&" -> "&amp;amp;"), so decode it once more
            items.append((el.get_attribute("data-id"), html.unescape(name or "")))
        return items

    def find_activities(self, name, match="exact", reload=True):
        if reload or not self.on_page("COURSE_PATH"):
            self.open_course()
        want = norm(name)
        return [cmid for cmid, have in self.course_activities()
                if norm(have) == want or (match == "startswith" and norm(have).startswith(want))]

    def count_activities(self, name):
        """Number of activities called `name` in the course (reuses the course page if it is open)."""
        return len(self.find_activities(name, reload=not self.on_page("COURSE_PATH")))

    def delete_activity(self, cmid):
        self.go("DELETE_ACTIVITY_PAGE", cmid=cmid, sesskey=self.sesskey())

    def cleanup(self, names):
        """Deletes every activity with one of these names (precondition: no such assignment exists).
        A name ending with '*' deletes every activity whose name starts with it."""
        names = [n for n in names if norm(n)]
        if not names:
            return
        self.open_course()
        doomed = []
        for name in names:
            match = "startswith" if name.endswith("*") else "exact"
            doomed += self.find_activities(name.rstrip("*") if match == "startswith" else name, match, reload=False)
        for cmid in dict.fromkeys(doomed):
            self.delete_activity(cmid)
        if doomed:
            self.open_course()

    # ---------------------------------------------------------------- Add an assignment form
    def open_add_form(self):
        self.go("ADD_ASSIGNMENT_PAGE")
        self.find(loc("form.name"))
        try:        # Moodle resets the form while the editor starts: fill it only afterwards
            self.find(loc("form.description_iframe"))
        except TimeoutException:
            pass
        time.sleep(1)
        self.expand_all()

    def on_form(self):
        return self.on_page("FORM_PATH") and self.exists(loc("form.name"))

    def expand_all(self):
        for link in self.d.find_elements(*loc("form.expand_all")):
            if link.is_displayed() and link.get_attribute("aria-expanded") != "true":
                self.js_click(link)
                break

    def js_click(self, el):
        self.d.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", el)

    def set_text(self, locator, value):
        el = self.find(locator)
        try:
            el.clear()
            if value:
                el.send_keys(value)
        except WebDriverException:          # not interactable / disabled for a moment
            pass
        if (el.get_attribute("value") or "") != value:      # clear() did not work / field not interactable
            self.d.execute_script(
                "arguments[0].value=arguments[1];"
                "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el, value)

    def set_checkbox(self, locator, on):
        el = self.find(locator)
        if el.is_selected() != on:
            try:
                el.click()
            except (ElementNotInteractableException, WebDriverException):
                self.js_click(el)

    def set_select(self, locator, value):
        el = self.find(locator)
        # one JavaScript call instead of 2 WebDriver calls per option (the year list has 151 options)
        options = [tuple(o) for o in self.d.execute_script(
            "return Array.from(arguments[0].options).map(o => [o.value, o.text]);", el)]
        if value in ("@smallest", "@largest"):
            numeric = [v for v, _ in options if v.lstrip("-").isdigit() and int(v) > 0]
            numeric.sort(key=int)
            value = numeric[0] if value == "@smallest" else numeric[-1]
        elif value not in [v for v, _ in options]:
            texts = {t.strip(): v for v, t in options}
            if value in texts:
                value = texts[value]
            else:
                raise AssertionError(f"option '{value}' is not offered by {locator[1]} {[t for _, t in options]}")
        # set by JavaScript (one call; also works while Moodle is still enabling the date selectors)
        self.d.execute_script("arguments[0].value=arguments[1];"
                              "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el, value)
        return value

    def set_date(self, field, value):
        """value: 'YYYY-MM-DD HH:MM' enables the date and sets it, 'off' disables it."""
        key = f"date.{field}"
        self.set_checkbox(loc(key, part="enabled"), value != "off")
        if value == "off":
            return
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2}))?", value.strip())
        if not m:
            raise ValueError(f"bad date '{value}' for {field} (use YYYY-MM-DD HH:MM or off)")
        year, month, day, hour, minute = m.groups()
        parts = {"year": year, "month": month, "day": day, "hour": hour or "0", "minute": minute or "0"}
        for part, val in parts.items():
            self.set_select(loc(key, part=part), str(int(val)))

    def set_description(self, text):
        try:
            frame = self.find(loc("form.description_iframe"))
            self.d.switch_to.frame(frame)
            body = self.find(loc("form.description_body"))
            body.clear()
            body.send_keys(text)
        except (TimeoutException, WebDriverException):
            self.d.switch_to.default_content()     # no TinyMCE: plain textarea
            self.set_text(loc("form.description_textarea"), text)
        finally:
            self.d.switch_to.default_content()

    def _fill_once(self, r, baseline=True):
        """Fills the form from a data row. Columns:
        name, description, allow_from, due, cutoff, remind (YYYY-MM-DD HH:MM | off),
        onlinetext, file (yes|no), wordlimit, maxfiles, maxsize (@smallest|@largest|value),
        grade, gradepass ('@empty' clears the field).
        baseline=True: an empty date cell disables that date and the name is always typed
        (Project 2 baseline: all dates off). baseline=False (2nd attempt): empty cell = unchanged."""
        def val(col):
            return (r.get(col) or "").strip() if col != "name" else (r.get(col) or "")
        if val("description"):
            self.set_description(val("description"))
        for field in DATE_FIELDS:
            v = val(field)
            if v or baseline:
                self.set_date(field, v or "off")
        for field in CHECKBOX_FIELDS:
            if val(field):
                self.set_checkbox(loc(f"form.{field}"), val(field).lower() == "yes")
        if val("wordlimit"):
            self.set_checkbox(loc("form.wordlimit_enabled"), True)
            self.set_text(loc("form.wordlimit"), "" if val("wordlimit") == "@empty" else val("wordlimit"))
        for field in SELECT_FIELDS:
            if val(field):
                self.set_select(loc(f"form.{field}"), val(field))
        for field in ("grade", "gradepass"):
            if val(field):
                self.set_text(loc(f"form.{field}"), "" if val(field) == "@empty" else val(field))
        if baseline or val("name"):       # typed last: Moodle's editor start-up may reset fields typed earlier
            self.set_text(loc("form.name"), val("name"))
            field = self.find(loc("form.name"))
            if (field.get_attribute("value") or "") != val("name"):
                self.d.execute_script("arguments[0].value = arguments[1];", field, val("name"))

    def wanted_values(self, r, baseline=True):
        """The values the form must show after filling row r (for the self-check)."""
        want = {}
        for field in DATE_FIELDS:
            v = (r.get(field) or "").strip()
            if v or baseline:
                v = v or "off"
                if v != "off":
                    y, mo, d, *rest = re.split(r"[- :T]", v)
                    h, mi = (rest + ["0", "0"])[:2]
                    v = f"{int(y)}-{int(mo):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}"
                want[field] = v
        for field in CHECKBOX_FIELDS:
            if (r.get(field) or "").strip():
                want[field] = "yes" if r[field].strip().lower() == "yes" else "no"
        for field in ("wordlimit", "grade", "gradepass", "maxfiles"):
            v = (r.get(field) or "").strip()
            if v:
                want[field] = "" if v == "@empty" else v
        if baseline or r.get("name"):
            want["name"] = r.get("name") or ""
        return want

    def fill_assignment_form(self, r, baseline=True):
        """Fills the form, then checks every field and fills again what Moodle's JavaScript reset
        while the page was still starting (up to 3 times)."""
        self._fill_once(r, baseline)
        want = self.wanted_values(r, baseline)
        for _ in range(3):
            time.sleep(1)
            now = self.current_values(list(want))
            wrong = [k for k, v in want.items() if now[k] != v and not same_value(v, now[k])]
            if not wrong:
                return
            redo = {k: (want[k] if want[k] != "" else "@empty") for k in wrong if k != "name"}
            self._fill_once(redo, baseline=False)
            if "name" in wrong:
                self.set_text(loc("form.name"), want["name"])

    def click_button(self, button):
        """Clicks save_return | save_display | cancel and waits for the next page or a client-side error."""
        old = self.d.find_element(*loc("page.body"))
        target = self.find(loc(f"button.{button}"))
        try:
            target.click()
        except (ElementNotInteractableException, WebDriverException):
            self.js_click(target)
        try:
            WebDriverWait(self.d, PAGE_LOAD_TIMEOUT, ignored_exceptions=[UnexpectedAlertPresentException]).until(
                lambda d: self._reloaded_or_client_error(old))
        except TimeoutException:
            pass
        self.accept_alerts()
        self.wait_ready()

    def _reloaded_or_client_error(self, old_body):
        try:
            old_body.is_enabled()          # still the same page?
        except (StaleElementReferenceException, WebDriverException):
            return True                    # page changed (server answered)
        return bool(self.visible_errors())  # client-side validation stopped the submit

    def field_error(self, field):
        key = f"error.{field}"
        if key not in L:
            raise KeyError(f"no error element defined for field '{field}'")
        for el in self.d.find_elements(*loc(key)):
            if el.is_displayed() and norm(el.text):
                return norm(el.text)
        return ""

    def visible_errors(self):
        try:
            return [norm(e.text) for e in self.d.find_elements(*loc("error.any")) if e.is_displayed() and norm(e.text)]
        except (StaleElementReferenceException, WebDriverException):
            return []

    def heading_texts(self):
        return [norm(h.text) for h in self.d.find_elements(*loc("page.heading")) if norm(h.text)]

    # ---------------------------------------------------------------- saved settings
    def current_values(self, keys):
        """{key: value} of the form fields as they are now in the browser."""
        values = {}
        for key in keys:
            if key in DATE_FIELDS:
                part = lambda p: self.find(loc(f"date.{key}", part=p))
                if not part("enabled").is_selected():
                    values[key] = "off"
                else:
                    y, mo, d, h, mi = (part(p).get_attribute("value") for p in ("year", "month", "day", "hour", "minute"))
                    values[key] = f"{y}-{int(mo):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}"
            elif key in CHECKBOX_FIELDS:
                values[key] = "yes" if self.find(loc(f"form.{key}")).is_selected() else "no"
            else:
                values[key] = self.find(loc(f"form.{key}")).get_attribute("value") or ""
        return values

    def read_settings(self, cmid, keys):
        """Opens the edit form of an activity and returns {key: value} as shown in the form."""
        self.go("EDIT_ACTIVITY_PAGE", cmid=cmid)
        self.find(loc("form.name"))
        return self.current_values(keys)
