"""Check accessible validation feedback on the Moodle Create Course form."""
import argparse
import getpass
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from Feature002_Level2.main import DEFAULT_CONFIG, read_cases, read_config

ROOT = Path(__file__).resolve().parent
REQUIREMENT = "NFR-002-A11Y-01"
SCENARIOS = {"TC-002-002": "fullname", "TC-002-003": "shortname"}
COLUMNS = {"fullname": "full_name", "shortname": "short_name"}


def read_feedback(browser, field_locator, error_locator):
    fields = browser.find_elements(*field_locator)
    messages = browser.find_elements(*error_locator)
    field = fields[0] if fields else None
    error = messages[0] if messages else None
    return {
        "field_id": field.get_dom_attribute("id") if field else None,
        "message_id": error.get_dom_attribute("id") if error else None,
        "message_visible": bool(error and error.is_displayed()),
        "message": error.text.strip() if error else "",
        "aria_invalid": field.get_dom_attribute("aria-invalid") if field else None,
        "aria_describedby": field.get_dom_attribute("aria-describedby") if field else None,
        "aria_errormessage": field.get_dom_attribute("aria-errormessage") if field else None,
    }


def checks_for(observed, initial_invalid, expected):
    error_id = observed["message_id"]
    described_by = (observed["aria_describedby"] or "").split()
    error_messages = (observed["aria_errormessage"] or "").split()
    return {
        "visible_expected_message": observed["message_visible"] and observed["message"] == expected,
        "field_marked_invalid_after_submission": initial_invalid != "true" and observed["aria_invalid"] == "true",
        "message_linked_to_field": bool(error_id and (error_id in described_by or error_id in error_messages)),
    }


def run_browser(cases, config, base):
    from selenium import webdriver
    from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    locator = config["locators"]
    paths = config["paths"]
    base_path = urlparse(base).path
    username = os.getenv("MOODLE_ADMIN_USERNAME", "admin")
    password = os.getenv("MOODLE_ADMIN_PASSWORD") or getpass.getpass("Moodle password: ")
    now = datetime.now().astimezone()
    run_id = now.strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
    output = ROOT / "results" / run_id

    with webdriver.Chrome() as driver:
        wait = WebDriverWait(driver, 10, ignored_exceptions=(StaleElementReferenceException,))

        def visible(key):
            return wait.until(EC.visibility_of_element_located(locator[key]), key)

        driver.get(base + paths["login"])
        visible("username").send_keys(username)
        visible("password").send_keys(password)
        visible("login_button").click()
        wait.until(
            lambda browser: not urlparse(browser.current_url).path.removeprefix(base_path).startswith(paths["login_area"]),
            "Moodle login",
        )
        output.mkdir(parents=True)
        report = {
            "requirement_id": REQUIREMENT,
            "run_at": now.isoformat(timespec="seconds"),
            "base_url": base,
            "browser": driver.capabilities.get("browserName"),
            "browser_version": driver.capabilities.get("browserVersion"),
            "scenarios": [],
        }
        for case_id, field in SCENARIOS.items():
            row = cases[case_id]
            expected = row["expected_value"]
            error_locator = config["error_locators"][row["expected_target"]]
            result = {"case_id": case_id, "field": field, "expected_message": expected}
            observed = {}
            checks = {}

            def matching_feedback(browser):
                nonlocal observed, checks
                observed = read_feedback(browser, locator[field], error_locator)
                checks = checks_for(observed, initial_invalid, expected)
                return all(checks.values())

            try:
                driver.get(base + paths["create_course"])
                for name, column in COLUMNS.items():
                    control = visible(name)
                    control.clear()
                    if row[column]:
                        control.send_keys(row[column])
                initial_invalid = visible(field).get_dom_attribute("aria-invalid")
                result["aria_invalid_before_submission"] = initial_invalid
                visible("save_and_display").click()
                try:
                    wait.until(matching_feedback, "Visible and associated validation message")
                except TimeoutException:
                    # The last observation contains the checks that did not meet the requirement.
                    pass
                result.update(status="PASS" if checks and all(checks.values()) else "FAIL",
                              checks=checks, observed=observed)
                errors = driver.find_elements(*error_locator)
                if errors and errors[0].is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'})", errors[0])
            except WebDriverException as exc:
                if "status" not in result:
                    result.update(status="ERROR", detail=str(exc).splitlines()[0])
                else:
                    result["evidence_error"] = str(exc).splitlines()[0]
            result["url"] = driver.current_url
            screenshot = output / f"{case_id}.png"
            try:
                if driver.save_screenshot(str(screenshot)):
                    result["screenshot"] = screenshot.name
            except WebDriverException as exc:
                result["evidence_error"] = str(exc).splitlines()[0]
            report["scenarios"].append(result)
            print(case_id, result["status"], result.get("checks", result.get("detail", "")), flush=True)

    scenario_statuses = {item["status"] for item in report["scenarios"]}
    report["status"] = next(status for status in ("FAIL", "ERROR", "PASS") if status in scenario_statuses)
    report_path = output / "results.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    return int(report["status"] != "PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--base-url")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cases = read_cases()
    config = read_config(args.config, cases)
    for case_id, field in SCENARIOS.items():
        row = cases[case_id]
        if row["expected_kind"] != "field_error" or row[COLUMNS[field]]:
            parser.error(f"{case_id} must leave {field} empty and expect a field error")
        if args.dry_run:
            print(REQUIREMENT, case_id, field, repr(row["expected_value"]))
    if args.dry_run:
        return 0
    return run_browser(cases, config, (args.base_url or config["base_url"]).rstrip("/"))


if __name__ == "__main__":
    raise SystemExit(main())
