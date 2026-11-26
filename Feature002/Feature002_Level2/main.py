"""Run the Moodle Create Course Level 2 cases with configurable URLs and locators."""
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
from urllib.parse import parse_qs, quote_plus, urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "moodle_config.json"
TEXT_FIELDS = ("fullname", "shortname", "idnumber")
SPECIAL_OPTIONS = {"category", "startdate", "enddate", "enddate_enabled", "summary"}
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


def read_config(path, cases):
    with path.open(encoding="utf-8-sig") as stream:
        config = json.load(stream)
    base = urlparse(config["base_url"])
    if base.scheme not in {"http", "https"} or not base.netloc or base.query or base.fragment:
        raise ValueError("base_url must be an HTTP(S) URL without a query or fragment")

    routes = config["paths"]
    for name in ("login", "login_area", "create_course", "edit_course", "view_course", "course_search"):
        if not routes[name].startswith("/"):
            raise ValueError(f"paths.{name} must start with /")
    activity_paths = routes["activity_setup"]
    if not isinstance(activity_paths, list) or not activity_paths or not all(path.startswith("/") for path in activity_paths):
        raise ValueError("paths.activity_setup must contain at least one path starting with /")
    routes["edit_course"].format(course_id=1)
    routes["course_search"].format(term="course", page=0)
    if not isinstance(routes["directory_index"], str) or not routes["directory_index"]:
        raise ValueError("paths.directory_index must be a nonempty string")
    for name in ("course_id", "activity_course_id"):
        if not config["query_parameters"][name]:
            raise ValueError(f"query_parameters.{name} cannot be empty")

    names = set(TEXT_FIELDS) | {
        "username", "password", "login_button", "category", "category_selection", "enddate_enabled",
        "section_ancestor", "section_toggle", "choice_trigger", "choice_option", "summary_textarea",
        "summary_frame", "summary_body", "save_and_display", "cancel", "course_heading",
        "all_validation_errors", "search_listing", "search_item",
    }
    names.update(f"{field}_{part}" for field in ("startdate", "enddate")
                 for part in ("year", "month", "day", "hour", "minute"))
    error_names = set()
    for row in cases.values():
        names.update(json.loads(row["form_options_json"]).keys() - SPECIAL_OPTIONS)
        if row["expected_kind"] == "field_error":
            error_names.add(row["expected_target"])

    for section, required in (("locators", names), ("error_locators", error_names)):
        entries = config[section]
        missing = required - entries.keys()
        if missing:
            raise ValueError(f"missing {section}: {', '.join(sorted(missing))}")
        for name, entry in entries.items():
            by, value = entry["by"], entry["value"]
            if not isinstance(by, str) or not by or not isinstance(value, str) or not value:
                raise ValueError(f"{section}.{name} must have nonempty by and value strings")
            entries[name] = (by, value)
    return config


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


def read_validation_errors(browser, general_locator, error_locators):
    # Capture visible fallback messages before resolving configured locators on the form.
    # An error that appears during the poll can then still be matched in the configured pass.
    observed = {}
    for element in browser.find_elements(*general_locator):
        if element.is_displayed() and (message := element.text.strip()):
            observed[element.id] = (element.get_dom_attribute("id"), message)

    errors = {}
    for name, error_locator in error_locators.items():
        for element in browser.find_elements(*error_locator):
            if element.id in observed:
                _, errors[name] = observed.pop(element.id)
            elif element.is_displayed() and (message := element.text.strip()):
                errors[name] = message
    for dom_id, message in observed.values():
        errors[f"unmapped:{dom_id}"] = message
    return errors


def run_selenium(rows, base, config, run_id):
    from selenium import webdriver
    from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait

    username = os.getenv("MOODLE_ADMIN_USERNAME", "admin")
    password = os.getenv("MOODLE_ADMIN_PASSWORD") or getpass.getpass("Moodle password: ")
    directory = ROOT / "results" / run_id
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 20, ignored_exceptions=(StaleElementReferenceException,))
    base_path = urlparse(base).path
    paths = config["paths"]
    query_parameters = config["query_parameters"]
    locators = config["locators"]

    def locator(name, **parameters):
        by, expression = locators[name]
        if parameters:
            expression = expression.format(**parameters)
        return by, expression

    def visible(name):
        return wait.until(EC.visibility_of_element_located(locator(name)), name)

    def present(name):
        return wait.until(EC.presence_of_element_located(locator(name)), name)

    def value(name):
        return present(name).get_property("value")

    def course_settings(course_id):
        driver.get(base + paths["edit_course"].format(course_id=int(course_id)))
        visible("fullname")

    def open_section(control):
        fieldsets = control.find_elements(*locator("section_ancestor"))
        if not fieldsets:
            return
        section_id = fieldsets[0].get_attribute("id")
        toggle = locator("section_toggle", section_id=section_id)
        if driver.find_elements(*toggle):
            wait.until(EC.element_to_be_clickable(toggle)).click()

    def select_value(name, expected):
        control = present(name)
        open_section(control)
        if control.get_dom_attribute("data-region") == "choice-select":
            if control.get_property("value") != expected:
                control_id = control.get_dom_attribute("id")
                trigger = locator("choice_trigger", control_id=control_id)
                option = locator("choice_option", control_id=control_id, option_value=expected)
                wait.until(EC.element_to_be_clickable(trigger), name).click()
                wait.until(EC.element_to_be_clickable(option), f"{name}={expected}").click()
                if name == "format":
                    wait.until(EC.staleness_of(control), "Course format form refresh")
        else:
            Select(visible(name)).select_by_value(expected)
        wait.until(lambda _: value(name) == expected, f"{name}={expected}")

    def date_value(name):
        return date(*(int(value(f"{name}_{part}")) for part in ("year", "month", "day")))

    def select_date(name, expected):
        for part in ("year", "month", "day"):
            select_value(f"{name}_{part}", str(getattr(expected, part)))

    def category_name():
        option = Select(present("category")).first_selected_option
        return option.get_property("textContent").strip()

    def clear_category():
        if value("category"):
            selection = locator("category_selection")
            wait.until(EC.element_to_be_clickable(selection), "Remove Course category").click()
            wait.until(lambda _: not value("category"), "Course category was not cleared")

    def summary_text(text=None):
        target = present("summary_textarea")
        frame = locator("summary_frame", editor_id=target.get_attribute("id"))
        open_section(target)
        wait.until(EC.frame_to_be_available_and_switch_to_it(frame), "TinyMCE course summary editor")
        try:
            editor = wait.until(EC.element_to_be_clickable(locator("summary_body")))
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
            if name not in SPECIAL_OPTIONS:
                select_value(name, expected)
        if "category" in options:
            if not options["category"]:
                clear_category()
            elif category_name() != options["category"]:
                raise CaseMismatch(f"Expected category {options['category']!r}, found {category_name()!r}")
        if "startdate" in options:
            select_date("startdate", date.fromisoformat(options["startdate"]))
        if "enddate_enabled" in options:
            checkbox = visible("enddate_enabled")
            enabled = options["enddate_enabled"]
            if checkbox.is_selected() != enabled:
                checkbox.click()
            wait.until(
                lambda _: all(present(f"enddate_{part}").is_enabled() == enabled
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
                values[name] = present("enddate_enabled").is_selected()
            elif name == "summary":
                values[name] = summary_text()
            else:
                values[name] = value(name)
        return values

    def page_outcome(browser):
        url = urlparse(browser.current_url)
        path = url.path.removeprefix(base_path)
        query = parse_qs(url.query)
        course_id = query.get(query_parameters["course_id"], [None])[0]
        if course_id and path == paths["view_course"]:
            headings = browser.find_elements(*locator("course_heading"))
            if headings and headings[0].is_displayed():
                return {"course_id": course_id, "heading": headings[0].text.strip()}
            # A whitespace-only course name can render an empty heading.
            if headings and not headings[0].get_property("textContent").strip():
                return {"course_id": course_id, "heading": ""}
        if path in paths["activity_setup"]:
            course_id = query.get(query_parameters["activity_course_id"], [course_id])[0]
            if course_id:
                return {"course_id": course_id, "activity_path": url.path}
        errors = read_validation_errors(browser, locator("all_validation_errors"), config["error_locators"])
        if errors:
            return {"errors": errors}
        return False

    def submission_outcome(browser):
        try:
            return page_outcome(browser)
        except WebDriverException as exc:
            # ChromeDriver can report a detached node as an inspector error during navigation.
            if "Node with given id does not belong to the document" in (exc.msg or ""):
                return False
            raise

    def submit(fields, options, cancel=False):
        driver.get(base + paths["create_course"])
        visible("fullname")
        saved_options = configure(options)
        for name, expected in fields.items():
            control = visible(name)
            if expected:
                control.send_keys(expected)
            entered = control.get_property("value")
            if entered != expected:
                raise CaseMismatch(f"{name} before submission: expected {display(expected)}, observed {display(entered)}")
        if cancel:
            before = driver.current_url
            visible("cancel").click()
            wait.until(EC.url_changes(before), "Cancel redirect")
            return {"redirect": urlparse(driver.current_url).path}, saved_options
        visible("save_and_display").click()
        return wait.until(submission_outcome, "Course creation page or inline validation error"), saved_options

    def search_courses(term):
        page = 0
        ids = []
        while True:
            driver.get(base + paths["course_search"].format(term=quote_plus(term), page=page))
            listing = wait.until(EC.visibility_of_element_located(locator("search_listing")),
                                 f"Course search: {term!r}")
            items = listing.find_elements(*locator("search_item"))
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
            if redirect not in (expected, expected + paths["directory_index"]):
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
        driver.get(base + paths["login"])
        visible("username").send_keys(username)
        visible("password").send_keys(password)
        visible("login_button").click()
        wait.until(
            lambda browser: not urlparse(browser.current_url).path.removeprefix(base_path).startswith(paths["login_area"]),
            "Moodle login",
        )
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
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Moodle URLs and locators JSON")
    parser.add_argument("--base-url", help="Override the base_url in the configuration for this run")
    args = parser.parse_args()
    try:
        config = read_config(args.config, cases)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.error(f"{args.config}: {exc}")
    base = (args.base_url or config["base_url"]).rstrip("/")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
    rows = prepare_cases(cases, args.case, run_id)
    if args.dry_run:
        for row in rows:
            print(row["case_id"], display(row["short_name"]), row["expected_kind"],
                  display(row["expected_value"]), row["form_options_json"])
        return 0
    return run_selenium(rows, base, config, run_id)


if __name__ == "__main__":
    raise SystemExit(run())
