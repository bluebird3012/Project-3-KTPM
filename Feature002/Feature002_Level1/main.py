"""Run the Moodle Create Course cases in create_course_cases.csv."""
import argparse
import csv
import getpass
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from random import Random
from string import ascii_uppercase
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
TEXT_FIELDS = ("fullname", "shortname", "idnumber")
DUPLICATE_MESSAGES = {
    "shortname": "Short name is already used for another course",
    "idnumber": "ID number is already used for another course",
}


class CaseMismatch(Exception):
    """The Moodle UI showed a value different from the expected one."""


class FixtureUnavailable(Exception):
    """The test's required course state could not be established."""


def read_cases():
    with (ROOT / "create_course_cases.csv").open(encoding="utf-8-sig", newline="") as stream:
        cases = {}
        for row in csv.DictReader(stream):
            case = row["case_id"]
            if case in cases:
                raise ValueError(f"Duplicate case ID in CSV: {case}")
            cases[case] = row
    return cases


def prepare_cases(cases, selected, run_id):
    for case, row in cases.items():
        if selected and case not in selected:
            continue
        row = row.copy()
        row["options"] = json.loads(row["form_options_json"])
        row["fixture"] = json.loads(row["fixture_fields_json"])
        if row["short_name_policy"] == "unique":
            row["short_name"] += "_" + run_id
        yield row


def display(value):
    if len(value) > 72:
        return f"{value[:32]!r}... [length={len(value)}]"
    return repr(value)


def collision(outcome, field):
    message = outcome.get("errors", {}).get(f"id_error_{field}", "")
    return message.startswith(DUPLICATE_MESSAGES[field])


def alternate_values(original, policy, run_id):
    random = Random(run_id)
    if policy == "same_length":
        # Preserve either a single repeated letter or the leading letter plus a repeated suffix.
        prefix = original[0] if len(set(original)) > 1 else ""
        for letter in random.sample(ascii_uppercase, len(ascii_uppercase)):
            candidate = prefix + letter * (len(original) - len(prefix))
            if candidate != original:
                yield candidate
    elif policy == "replace_digits":
        digits = re.search(r"[0-9]{4}", original)
        if not digits:
            raise ValueError(f"No four-digit part in {original!r}")
        for number in random.sample(range(10000), 26):
            candidate = original[:digits.start()] + f"{number:04d}" + original[digits.end():]
            if candidate != original:
                yield candidate


def run_selenium(rows, base, run_id):
    from selenium import webdriver
    from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait

    username = os.getenv("MOODLE_ADMIN_USERNAME", "admin")
    password = os.getenv("MOODLE_ADMIN_PASSWORD") or getpass.getpass("Moodle password: ")
    directory = ROOT / "results" / run_id
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 20, ignored_exceptions=(StaleElementReferenceException,))
    base_path = urlparse(base).path
    create_url = base + "/course/edit.php?category=0"

    def visible(identifier):
        return wait.until(EC.visibility_of_element_located((By.ID, identifier)), identifier)

    def present(identifier):
        return wait.until(EC.presence_of_element_located((By.ID, identifier)), identifier)

    def value(name):
        return present("id_" + name).get_property("value")

    def course_settings(course_id):
        driver.get(base + "/course/edit.php?id=" + str(int(course_id)))
        visible("id_fullname")

    def open_section(control):
        fieldsets = control.find_elements(By.XPATH, "./ancestor::fieldset[starts-with(@id, 'id_')][1]")
        if not fieldsets:
            return
        section_id = fieldsets[0].get_attribute("id")
        toggle = (By.CSS_SELECTOR, f'[aria-controls="{section_id}container"][aria-expanded="false"]')
        if driver.find_elements(*toggle):
            wait.until(EC.element_to_be_clickable(toggle)).click()

    def select_value(name, expected):
        identifier = "id_" + name
        control = present(identifier)
        open_section(control)
        if control.get_dom_attribute("data-region") == "choice-select":
            if control.get_property("value") != expected:
                wrapper = f"#fitem_{identifier}"
                trigger = (By.CSS_SELECTOR, wrapper + ' [data-for="dropdowndialog_button"]')
                option = (By.CSS_SELECTOR, wrapper + f' [role="option"][data-value="{expected}"]')
                wait.until(EC.element_to_be_clickable(trigger), name).click()
                wait.until(EC.element_to_be_clickable(option), f"{name}={expected}").click()
                if name == "format":
                    wait.until(EC.staleness_of(control), "Course format form refresh")
        else:
            Select(visible(identifier)).select_by_value(expected)
        wait.until(lambda _: value(name) == expected, f"{name}={expected}")

    def date_value(name):
        return date(*(int(value(f"{name}_{part}")) for part in ("year", "month", "day")))

    def select_date(name, expected):
        for part in ("year", "month", "day"):
            select_value(f"{name}_{part}", str(getattr(expected, part)))

    def category_name():
        option = Select(present("id_category")).first_selected_option
        return option.get_property("textContent").strip()

    def clear_category():
        if value("category"):
            selection = (By.CSS_SELECTOR, '#fitem_id_category .form-autocomplete-selection [role="option"]')
            wait.until(EC.element_to_be_clickable(selection), "Remove Course category").click()
            wait.until(lambda _: not value("category"), "Course category was not cleared")

    def summary_text(text=None):
        target = wait.until(EC.presence_of_element_located((By.NAME, "summary_editor[text]")))
        frame = (By.ID, target.get_attribute("id") + "_ifr")
        open_section(target)
        wait.until(EC.frame_to_be_available_and_switch_to_it(frame), "TinyMCE course summary editor")
        try:
            editor = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'body[contenteditable="true"]')))
            if text is not None:
                editor.click()
                editor.send_keys(Keys.CONTROL, "a")
                editor.send_keys(text)
            return editor.get_property("textContent").strip()
        finally:
            driver.switch_to.default_content()

    def configure(options):
        saved_options = options.copy()
        for name, expected in options.items():
            if name not in {"category", "startdate", "enddate", "enddate_enabled", "summary"}:
                select_value(name, expected)
        if "category" in options:
            if not options["category"]:
                clear_category()
            elif category_name() != options["category"]:
                raise CaseMismatch(f"Expected category {options['category']!r}, found {category_name()!r}")
        if "startdate" in options:
            select_date("startdate", date.fromisoformat(options["startdate"]))
        if "enddate_enabled" in options:
            checkbox = visible("id_enddate_enabled")
            enabled = options["enddate_enabled"]
            if checkbox.is_selected() != enabled:
                checkbox.click()
            wait.until(
                lambda _: all(present(f"id_enddate_{part}").is_enabled() == enabled
                              for part in ("year", "month", "day", "hour", "minute")),
                f"Course end date controls enabled={enabled}",
            )
        if "enddate" in options:
            specification = options["enddate"]
            if specification == "same_start":
                end = date_value("startdate")
                select_date("enddate", end)
                for part in ("hour", "minute"):
                    select_value(f"enddate_{part}", value(f"startdate_{part}"))
            elif specification == "after_start":
                start = date_value("startdate")
                end = date_value("enddate")
                if end <= start:
                    end = start + timedelta(days=1)
                    select_date("enddate", end)
            else:
                end = date.fromisoformat(specification)
                select_date("enddate", end)
            saved_options["enddate"] = end.isoformat()
        if "summary" in options:
            entered = summary_text(options["summary"])
            if entered != options["summary"]:
                raise CaseMismatch(f"Course summary before submission: expected {options['summary']!r}, observed {entered!r}")
        return saved_options

    def read_options(options):
        values = {}
        for name in options:
            if name == "category":
                values[name] = category_name()
            elif name in {"startdate", "enddate"}:
                values[name] = date_value(name).isoformat()
            elif name == "enddate_enabled":
                values[name] = present("id_enddate_enabled").is_selected()
            elif name == "summary":
                values[name] = summary_text()
            else:
                values[name] = value(name)
        return values

    def page_outcome(browser):
        url = urlparse(browser.current_url)
        course_id = parse_qs(url.query).get("id", [None])[0]
        if course_id and url.path.endswith("/course/view.php"):
            headings = browser.find_elements(By.CSS_SELECTOR, "#page-header h1")
            if headings and headings[0].is_displayed():
                return {"course_id": course_id, "heading": headings[0].text.strip()}
            # A whitespace-only course name can render an empty heading.
            if headings and not headings[0].get_property("textContent").strip():
                return {"course_id": course_id, "heading": ""}
        if url.path.endswith(("/course/mod.php", "/course/modedit.php")):
            course_id = parse_qs(url.query).get("course", [course_id])[0]
            if course_id:
                return {"course_id": course_id, "activity_path": url.path}
        errors = {}
        for error in browser.find_elements(By.CSS_SELECTOR, "[id^=id_error_]"):
            if error.is_displayed() and error.text.strip():
                errors[error.get_attribute("id")] = error.text.strip()
        if errors:
            return {"errors": errors}
        return False

    def submit(fields, options, cancel=False):
        driver.get(create_url)
        visible("id_fullname")
        saved_options = configure(options)
        for name, expected in fields.items():
            control = visible("id_" + name)
            if expected:
                control.send_keys(expected)
            entered = control.get_property("value")
            if entered != expected:
                raise CaseMismatch(f"{name} before submission: expected {display(expected)}, observed {display(entered)}")
        if cancel:
            before = driver.current_url
            visible("id_cancel").click()
            wait.until(EC.url_changes(before), "Cancel redirect")
            return {"redirect": urlparse(driver.current_url).path}, saved_options
        visible("id_saveanddisplay").click()
        return wait.until(page_outcome, "Course creation page or inline validation error"), saved_options

    def search_courses(term):
        page = 0
        ids = []
        while True:
            query = urlencode({"search": term, "perpage": 100, "page": page})
            driver.get(base + "/course/management.php?" + query)
            listing = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-category="search"]')),
                                 f"Course search: {term!r}")
            items = listing.find_elements(By.CSS_SELECTOR, "li.listitem-course[data-id]")
            ids.extend(item.get_attribute("data-id") for item in items)
            page += 1
            if page >= int(listing.get_attribute("data-totalpages")):
                return ids

    def ensure_fixture(fixture):
        if not fixture:
            return
        for course_id in search_courses(fixture["fullname"]):
            course_settings(course_id)
            if all(value(name) == expected for name, expected in fixture.items()):
                return
        outcome, _ = submit(fixture, {})
        if "course_id" not in outcome:
            raise FixtureUnavailable(f"Could not prepare the exact duplicate fixture: {outcome}")
        course_settings(outcome["course_id"])
        observed = {name: value(name) for name in fixture}
        if observed != fixture:
            raise FixtureUnavailable(f"Fixture values differ after saving: {observed!r}")

    def execute_case(row):
        ensure_fixture(row["fixture"])
        fields = dict(zip(TEXT_FIELDS, (row["full_name"], row["short_name"], row["id_number"])))
        kind = row["expected_kind"]
        expected = row["expected_value"]
        actual, saved_options = submit(fields, row["options"], cancel=kind == "cancel")
        if kind == "field_error":
            return actual.get("errors", {}).get(row["expected_target"]) == expected, actual
        if kind == "cancel":
            redirect = actual["redirect"].removeprefix(base_path)
            if redirect not in (expected, expected + "index.php"):
                return False, actual
            for course_id in search_courses(fields["shortname"]):
                course_settings(course_id)
                if value("shortname") == fields["shortname"]:
                    actual["unexpected_course_id"] = course_id
                    return False, actual
            actual["course_found"] = False
            return True, actual
        for name, policy in (("shortname", row["short_name_policy"]), ("idnumber", row["id_number_policy"])):
            if policy not in {"same_length", "replace_digits"} or not collision(actual, name):
                continue
            original = fields[name]
            for candidate in alternate_values(original, policy, run_id):
                fields[name] = candidate
                actual, saved_options = submit(fields, row["options"])
                if not collision(actual, name):
                    break
            if collision(actual, name):
                raise FixtureUnavailable(f"No unused {name} found with the required data pattern")
            if name == "shortname":
                row["short_name"] = fields[name]
            actual["input_adjustment"] = {"field": name, "from_csv": original, "submitted": fields[name]}
        if "course_id" not in actual:
            short_error = actual.get("errors", {}).get("id_error_shortname", "")
            if row["short_name_policy"] == "fixed_unique" and collision(actual, "shortname"):
                raise FixtureUnavailable(f"Required unused short name is already in use: {short_error}")
            return False, actual
        course_settings(actual["course_id"])
        actual["saved_fields"] = {name: value(name) for name in fields}
        actual["saved_options"] = read_options(saved_options)
        heading_matches = actual.get("heading") == expected.strip()
        if row["options"].get("format") == "singleactivity" and "activity_path" in actual:
            heading_matches = True  # This format redirects to activity setup, so check the title in Settings.
        expected_fields = {**fields, "fullname": expected}
        matches = (heading_matches and actual["saved_fields"] == expected_fields
                   and actual["saved_options"] == saved_options)
        return matches, actual

    failed = False
    try:
        driver.get(base + "/login/index.php")
        visible("username").send_keys(username)
        visible("password").send_keys(password)
        visible("loginbtn").click()
        wait.until(lambda browser: "/login/" not in urlparse(browser.current_url).path, "Moodle login")
        directory.mkdir(parents=True)
        with (directory / "results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["case_id", "short_name", "expected", "actual", "status", "url"])
            for row in rows:
                expected = row["expected_value"]
                if row["options"]:
                    expected += f" | form options={row['form_options_json']}"
                try:
                    matches, actual = execute_case(row)
                    status = "PASS" if matches else "FAIL"
                except CaseMismatch as exc:
                    status, actual = "FAIL", str(exc)
                except FixtureUnavailable as exc:
                    status, actual = "BLOCKED", str(exc)
                except Exception as exc:
                    status, actual = "ERROR", f"{type(exc).__name__}: {str(exc).partition(chr(10))[0]}"
                writer.writerow([row["case_id"], row["short_name"], expected, str(actual), status, driver.current_url])
                stream.flush()
                print(row["case_id"], status, display(str(actual)), flush=True)
                if status != "PASS":
                    failed = True
                    try:
                        driver.save_screenshot(str(directory / (row["case_id"] + ".png")))
                    except WebDriverException as exc:
                        print(f"Screenshot unavailable: {exc.msg}", flush=True)
    finally:
        driver.quit()
    print(directory)
    return int(failed)


def run():
    cases = read_cases()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(cases), action="append")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:9501")
    args = parser.parse_args()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
    rows = prepare_cases(cases, args.case, run_id)
    if args.dry_run:
        for row in rows:
            print(row["case_id"], display(row["short_name"]), row["expected_kind"],
                  display(row["expected_value"]), row["form_options_json"])
        return 0
    return run_selenium(rows, args.base_url.rstrip("/"), run_id)


if __name__ == "__main__":
    raise SystemExit(run())
