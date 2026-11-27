"""Runner for NFR-08 Accessibility Testing (Selenium + axe-core) on Add a new Quiz."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from accessibility.axe_asset import AXE_VERSION, ensure_axe_script
from accessibility.evaluation import (
    PROPOSED_CRITERIA,
    evaluate_aria_error_result,
    evaluate_axe_result,
    evaluate_keyboard_result,
    overall_verdict,
)
from core.config import ROOT, settings
from core.moodle_client import add_quiz_path
from core.reporter import new_run, now, write_csv, write_json

SUMMARY_FIELDS = [
    "scenario_id",
    "name",
    "kind",
    "verdict",
    "violation_rules",
    "violation_nodes",
    "critical_nodes",
    "serious_nodes",
    "moderate_nodes",
    "minor_nodes",
    "key_label_nodes",
    "color_contrast_nodes",
    "passes_rules",
    "incomplete_rules",
    "detail",
]

VIOLATION_FIELDS = ["scenario_id", "rule_id", "impact", "node_count", "help", "help_url", "sample_target"]

KEYBOARD_TARGETS = [
    "id_name",
    "id_showdescription",
    "id_timeopen_enabled",
    "id_timeclose_enabled",
    "id_timelimit_enabled",
    "id_overduehandling",
    "id_gradepass",
    "id_attempts",
    "id_decimalpoints",
    "id_feedbackboundaries_0",
    "id_boundary_add_fields",
    "id_submitbutton2",
    "id_submitbutton",
    "id_cancel",
]


def build_driver(headless: bool = True):
    options = webdriver.ChromeOptions()
    options.page_load_strategy = "eager"
    options.add_argument("--window-size=1440,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=en-US")
    if headless:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(180)
    driver.set_script_timeout(120)
    return driver


def login_selenium(driver, base: str, username: str, password: str, timeout: int = 90) -> None:
    wait = WebDriverWait(driver, timeout)
    driver.get(base + "/login/index.php")
    u_el = wait.until(EC.element_to_be_clickable((By.ID, "username")))
    u_el.clear()
    u_el.send_keys(username)
    p_el = wait.until(EC.element_to_be_clickable((By.ID, "password")))
    p_el.clear()
    p_el.send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "loginbtn"))).click()
    wait.until(lambda d: urlsplit(d.current_url).path.rstrip("/") != "/login/index.php")


def open_add_quiz(driver, base: str, course_id: int, section_id: int, timeout: int = 90) -> None:
    driver.get(base + add_quiz_path(course_id, section_id))
    WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.ID, "id_name")))
    # Brief settle for Bootstrap/Moodle JS bindings
    time.sleep(1.0)


def expand_all(driver, timeout: int = 90) -> None:
    def try_expand(d):
        links = d.find_elements(By.CSS_SELECTOR, "form.mform a.collapseexpand")
        if not links:
            return True
        link = links[0]
        if not link.is_displayed() or link.get_attribute("aria-expanded") == "true":
            return True
        try:
            d.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
            link.click()
        except Exception:
            return False
        return d.find_element(By.CSS_SELECTOR, "form.mform a.collapseexpand").get_attribute("aria-expanded") == "true"

    WebDriverWait(driver, timeout, poll_frequency=0.5).until(try_expand)
    time.sleep(0.5)


def safe_click_id(driver, element_id: str, timeout: int = 90) -> None:
    wait = WebDriverWait(driver, timeout)
    last_err = None
    for block in ("center", "end", "start"):
        el = wait.until(EC.presence_of_element_located((By.ID, element_id)))
        driver.execute_script(
            "arguments[0].scrollIntoView({block: arguments[1], inline: 'nearest'});",
            el,
            block,
        )
        time.sleep(0.35)
        el = wait.until(EC.element_to_be_clickable((By.ID, element_id)))
        try:
            el.click()
            return
        except ElementClickInterceptedException as err:
            last_err = err
            try:
                ActionChains(driver).move_to_element(el).click().perform()
                return
            except ElementClickInterceptedException as err2:
                last_err = err2
    raise last_err  # type: ignore[misc]


def trigger_validation_errors(driver, timeout: int = 90) -> None:
    """Trigger simultaneous validation errors: empty Name + Close < Open + Grade to pass = 10.1."""
    wait = WebDriverWait(driver, timeout)
    expand_all(driver, timeout)

    # Clear Name (empty)
    name_el = wait.until(EC.element_to_be_clickable((By.ID, "id_name")))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", name_el)
    name_el.clear()

    # Open: 2027-12-01 10:00
    open_cb = wait.until(EC.presence_of_element_located((By.ID, "id_timeopen_enabled")))
    if not open_cb.is_selected():
        safe_click_id(driver, "id_timeopen_enabled", timeout)
    for part, val in [("year", "2027"), ("month", "12"), ("day", "1"), ("hour", "10"), ("minute", "0")]:
        sel = wait.until(EC.element_to_be_clickable((By.ID, f"id_timeopen_{part}")))
        Select(sel).select_by_value(val)

    # Close: 2027-12-01 09:59 (< Open)
    close_cb = wait.until(EC.presence_of_element_located((By.ID, "id_timeclose_enabled")))
    if not close_cb.is_selected():
        safe_click_id(driver, "id_timeclose_enabled", timeout)
    for part, val in [("year", "2027"), ("month", "12"), ("day", "1"), ("hour", "9"), ("minute", "59")]:
        sel = wait.until(EC.element_to_be_clickable((By.ID, f"id_timeclose_{part}")))
        Select(sel).select_by_value(val)

    # Grade to pass: 10.1 (> max 10)
    gp = wait.until(EC.element_to_be_clickable((By.ID, "id_gradepass")))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", gp)
    gp.clear()
    gp.send_keys("10.1")

    # Submit via Save and return to course
    safe_click_id(driver, "id_submitbutton2", timeout)

    # Wait for client-side or server-side validation error(s) to populate
    def has_errors(d):
        found = 0
        for sel_css in ("#id_error_name", "#id_error_timeclose", "#id_error_gradepass"):
            for el in d.find_elements(By.CSS_SELECTOR, sel_css):
                try:
                    if (el.text or "").strip():
                        found += 1
                        break
                except StaleElementReferenceException:
                    continue
        return found >= 1

    wait.until(has_errors)
    time.sleep(0.5)


def trigger_server_validation_errors(driver, timeout: int = 90) -> None:
    """Fill a valid name so Moodle POSTs to server and renders server-side Close<Open + Gradepass>10 errors."""
    wait = WebDriverWait(driver, timeout)
    name_el = wait.until(EC.element_to_be_clickable((By.ID, "id_name")))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", name_el)
    name_el.clear()
    name_el.send_keys("nfr8_acc_validation_probe")

    safe_click_id(driver, "id_submitbutton2", timeout)

    def both_server_errors(d):
        try:
            ok_close = any((e.text or "").strip() for e in d.find_elements(By.CSS_SELECTOR, "#id_error_timeclose"))
            ok_gp = any((e.text or "").strip() for e in d.find_elements(By.CSS_SELECTOR, "#id_error_gradepass"))
            return ok_close and ok_gp
        except StaleElementReferenceException:
            return False

    wait.until(both_server_errors)
    expand_all(driver, timeout)
    time.sleep(0.5)


def run_axe(driver, axe_js: str) -> dict:
    driver.execute_script(axe_js)
    result = driver.execute_async_script(
        """
        const done = arguments[arguments.length - 1];
        axe.run(document, {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] }
        }).then(res => done(res)).catch(err => done({ error: String(err) }));
        """
    )
    if "error" in result:
        raise RuntimeError(f"axe.run failed: {result['error']}")
    return result


def run_keyboard_audit(driver, max_tabs: int = 450) -> tuple[list[dict], set[str], bool]:
    """Traverse expanded form with real TAB key starting from id_name."""
    start_el = driver.find_element(By.ID, "id_name")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'}); window.__nfr8PrevEl = null;", start_el)
    start_el.click()

    trace: list[dict] = []
    reached: set[str] = set()
    trap_detected = False
    same_el_streak = 0
    target_set = set(KEYBOARD_TARGETS)

    for step in range(max_tabs):
        info = driver.execute_script(
            """
            const el = document.activeElement;
            const sameAsPrev = (window.__nfr8PrevEl !== null && el === window.__nfr8PrevEl);
            window.__nfr8PrevEl = el;
            if (!el) return {tag: '', id: '', name: '', type: '', visible: false, outline: '', same_dom_node: false};
            const st = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return {
                tag: el.tagName.toLowerCase(),
                id: el.id || '',
                name: el.getAttribute('name') || '',
                type: el.getAttribute('type') || '',
                visible: rect.width > 0 && rect.height > 0 && st.visibility !== 'hidden',
                outline: st.outlineStyle + ' ' + st.outlineWidth + ' / boxShadow=' + (st.boxShadow !== 'none'),
                same_dom_node: sameAsPrev
            };
            """
        )
        if info["id"]:
            reached.add(info["id"])
        trace.append({"step": step, **{k: v for k, v in info.items() if k != "same_dom_node"}})

        if step > 0 and info["same_dom_node"] and info["tag"] != "body":
            same_el_streak += 1
            if same_el_streak >= 3:
                trap_detected = True
                break
        else:
            same_el_streak = 0

        if target_set <= reached:
            break

        try:
            active = driver.switch_to.active_element
            active.send_keys(Keys.TAB)
        except Exception:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.TAB)

    return trace, reached, trap_detected


def inspect_error_association(driver, field_id: str, error_id: str) -> dict:
    return driver.execute_script(
        """
        const field = document.getElementById(arguments[0]);
        const err = document.getElementById(arguments[1]);
        const errText = err ? (err.textContent || '').trim() : '';
        const ariaInvalid = field ? (field.getAttribute('aria-invalid') || '') : '';
        const describedBy = field ? (field.getAttribute('aria-describedby') || '') : '';
        const errRole = err ? (err.getAttribute('role') || '') : '';
        const ariaLive = err ? (err.getAttribute('aria-live') || '') : '';
        const linkedById = describedBy.split(/\\s+/).includes(arguments[1]);
        const associated = Boolean(errText) && (
            (ariaInvalid === 'true' && linkedById) ||
            linkedById ||
            errRole === 'alert' ||
            ariaLive === 'assertive' ||
            ariaLive === 'polite'
        );
        return {
            field: arguments[0],
            error_id: arguments[1],
            error_text: errText,
            aria_invalid: ariaInvalid,
            aria_describedby: describedBy,
            error_role: errRole,
            aria_live: ariaLive,
            linked_by_describedby: linkedById,
            associated: associated
        };
        """,
        field_id,
        error_id,
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="NFR-08 Accessibility Testing (Add Quiz)")
    parser.add_argument("--smoke", action="store_true", help="Run smoke subset (ACC-01 and ACC-04)")
    parser.add_argument("--headed", action="store_true", help="Run Chrome visibly instead of headless")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args(argv)

    cfg = settings()
    axe_js, axe_sha = ensure_axe_script()

    scenarios = []
    with (ROOT / "accessibility" / "scenarios.csv").open(encoding="utf-8-sig", newline="") as f:
        scenarios = list(csv.DictReader(f))
    if args.smoke:
        scenarios = [s for s in scenarios if s["scenario_id"] in {"ACC-01", "ACC-04"}]

    directory, info = new_run(
        "accessibility",
        cfg["base"],
        extra={
            "nfr_id": "NFR-08",
            "smoke": args.smoke,
            "course_id": cfg["course_id"],
            "section_id": cfg["section_id"],
            "axe_version": AXE_VERSION,
            "axe_sha256": axe_sha,
            "criteria": PROPOSED_CRITERIA,
        },
    )
    ss_dir = directory / "screenshots"
    ss_dir.mkdir(exist_ok=True)

    driver = build_driver(headless=not args.headed)
    summary_rows: list[dict] = []
    all_violations: list[dict] = []

    try:
        print("Logging into local Moodle for NFR-08 Accessibility Testing...", flush=True)
        login_selenium(driver, cfg["base"], cfg["username"], cfg["password"], args.timeout)

        for sc in scenarios:
            sid = sc["scenario_id"]
            sname = sc["name"]
            print(f"Running {sid}: {sname} ...", flush=True)

            if sid == "ACC-01":
                open_add_quiz(driver, cfg["base"], cfg["course_id"], cfg["section_id"], args.timeout)
                axe_res = run_axe(driver, axe_js)
                write_json(directory / f"{sid}_axe.json", axe_res)
                driver.save_screenshot(str(ss_dir / f"{sid}.png"))
                srow, vrows = evaluate_axe_result(sid, sname, axe_res)
                summary_rows.append(srow)
                all_violations.extend(vrows)

            elif sid == "ACC-02":
                open_add_quiz(driver, cfg["base"], cfg["course_id"], cfg["section_id"], args.timeout)
                expand_all(driver, args.timeout)
                axe_res = run_axe(driver, axe_js)
                write_json(directory / f"{sid}_axe.json", axe_res)
                driver.save_screenshot(str(ss_dir / f"{sid}.png"))
                srow, vrows = evaluate_axe_result(sid, sname, axe_res)
                summary_rows.append(srow)
                all_violations.extend(vrows)

            elif sid == "ACC-03":
                open_add_quiz(driver, cfg["base"], cfg["course_id"], cfg["section_id"], args.timeout)
                trigger_validation_errors(driver, args.timeout)
                # Also trigger server-side validation so Close<Open + Gradepass>10 errors are rendered in DOM
                # First capture client-side empty-name error screenshot, then verify server-side error state
                driver.save_screenshot(str(ss_dir / f"{sid}_client_name.png"))
                trigger_server_validation_errors(driver, args.timeout)
                # Clear name again and blur/submit? No, keep server-side errors visible and run axe-core
                axe_res = run_axe(driver, axe_js)
                write_json(directory / f"{sid}_axe.json", axe_res)
                driver.save_screenshot(str(ss_dir / f"{sid}.png"))
                srow, vrows = evaluate_axe_result(sid, sname, axe_res)
                summary_rows.append(srow)
                all_violations.extend(vrows)

            elif sid == "ACC-04":
                open_add_quiz(driver, cfg["base"], cfg["course_id"], cfg["section_id"], args.timeout)
                expand_all(driver, args.timeout)
                trace, reached, trap = run_keyboard_audit(driver)
                write_csv(
                    directory / "keyboard_tab.csv",
                    trace,
                    ["step", "tag", "id", "name", "type", "visible", "outline"],
                )
                driver.save_screenshot(str(ss_dir / f"{sid}.png"))
                srow = evaluate_keyboard_result(sid, sname, KEYBOARD_TARGETS, reached, trap, len(trace))
                summary_rows.append(srow)

            elif sid == "ACC-05":
                # Part A: client-side empty Name error
                open_add_quiz(driver, cfg["base"], cfg["course_id"], cfg["section_id"], args.timeout)
                trigger_validation_errors(driver, args.timeout)
                name_assoc = inspect_error_association(driver, "id_name", "id_error_name")

                # Part B: server-side Close < Open and Grade to pass > 10 errors
                trigger_server_validation_errors(driver, args.timeout)
                close_assoc = inspect_error_association(driver, "id_timeclose_enabled", "id_error_timeclose")
                gp_assoc = inspect_error_association(driver, "id_gradepass", "id_error_gradepass")
                checks = [name_assoc, close_assoc, gp_assoc]
                write_csv(
                    directory / "error_association.csv",
                    checks,
                    [
                        "field",
                        "error_id",
                        "error_text",
                        "aria_invalid",
                        "aria_describedby",
                        "error_role",
                        "aria_live",
                        "linked_by_describedby",
                        "associated",
                    ],
                )
                driver.save_screenshot(str(ss_dir / f"{sid}.png"))
                srow = evaluate_aria_error_result(sid, sname, checks)
                summary_rows.append(srow)

            print(f"  -> {sid}: {summary_rows[-1]['verdict']} | {summary_rows[-1]['detail']}", flush=True)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    write_csv(directory / "summary.csv", summary_rows, SUMMARY_FIELDS)
    write_csv(directory / "violations.csv", all_violations, VIOLATION_FIELDS)
    verdict = overall_verdict(summary_rows)
    info.update(
        complete=True,
        finished_at=now(),
        verdict=verdict,
        scenarios_run=len(summary_rows),
        passed_scenarios=sum(r["verdict"] == "PASS" for r in summary_rows),
        failed_scenarios=sum(r["verdict"] == "FAIL" for r in summary_rows),
    )
    write_json(directory / "run_info.json", info)
    print(f"\nNFR-08 Results: {directory}\nOverall Verdict: {verdict}" + (" (smoke)" if args.smoke else ""), flush=True)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
