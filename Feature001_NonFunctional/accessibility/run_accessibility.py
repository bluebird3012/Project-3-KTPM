"""NFR-02: automated accessibility checks of local Moodle Add New User."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import time
import traceback
from urllib.parse import urlsplit
import uuid

from core.config import ROOT, local_url
from .axe_asset import VERSION, load_asset
from .evaluation import SCAN_TAGS, evaluate_scan, evaluate_keyboard, evaluate_validation, overall

FORM_FIELDS = ("id_username", "id_firstname", "id_lastname", "id_email")
KEYBOARD_TARGETS = (*FORM_FIELDS, "id_submitbutton", "id_cancel")
SECTION_IDS = ("id_moodle_picturecontainer", "id_moodle_additional_namescontainer",
               "id_moodle_interestscontainer", "id_moodle_optionalcontainer")
SCENARIOS = ("ACC-01", "ACC-02", "ACC-03", "ACC-04", "ACC-05")


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def redact(data, secrets):
    if isinstance(data, str):
        for secret in secrets:
            if secret:
                data = data.replace(secret, "[REDACTED]")
        return re.sub(r"(?i)(sesskey=)[^&\s\"'<>]+", r"\1[REDACTED]", data)
    if isinstance(data, list):
        return [redact(item, secrets) for item in data]
    if isinstance(data, dict):
        return {key: redact(value, secrets) for key, value in data.items()}
    return data


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})


def start_browser(args):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    options = webdriver.ChromeOptions()
    if not args.headed:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-dev-shm-usage")
    if args.browser_binary:
        options.binary_location = args.browser_binary
    service = Service(executable_path=args.driver) if args.driver else Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(args.timeout)
    driver.set_script_timeout(max(90, args.timeout))
    driver.set_window_size(1440, 1000)
    return driver


def wait_for_form(driver, base, timeout):
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.visibility_of_element_located((By.ID, "id_username")))
    wait.until(EC.presence_of_element_located((By.ID, "id_submitbutton")))
    if not same_origin(driver.current_url, base) or not urlsplit(driver.current_url).path.endswith("/user/editadvanced.php"):
        raise RuntimeError("Unexpected page instead of Add New User")
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    # The editor and Moodle JS may initialise asynchronously after load.
    time.sleep(1)


def same_origin(url, base):
    def origin(value):
        u = urlsplit(value)
        return u.scheme, u.hostname, u.port or (443 if u.scheme == "https" else 80)
    return origin(url) == origin(base)


def login(driver, base, username, password, timeout):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    driver.get(base + "/login/index.php")
    if not same_origin(driver.current_url, base):
        raise RuntimeError("Moodle login redirected outside configured local site")
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "loginbtn").click()
    wait.until(lambda d: not urlsplit(d.current_url).path.endswith("/login/index.php"))
    open_form(driver, base, timeout)


def open_form(driver, base, timeout):
    driver.get(base + "/user/editadvanced.php?id=-1")
    wait_for_form(driver, base, timeout)


# Scroll rather than changing CSS/DOM or forcing a JavaScript click.
SCROLL_TO_ELEMENT = """
    arguments[0].scrollIntoView({behavior:'instant', block:arguments[1], inline:'nearest'});
"""
CLICK_GEOMETRY = """
    const el = arguments[0], r = el.getClientRects()[0];
    const viewport = [window.innerWidth, window.innerHeight];
    if (!r) return {ready:false, viewport:viewport, reason:'no client rect'};
    // Match WebDriver's in-view center: center of the first client rectangle
    // clipped to the viewport. Hit-testing also detects overlays/nested clips.
    const left = Math.max(0, Math.min(r.left, r.right));
    const right = Math.min(viewport[0], Math.max(r.left, r.right));
    const top = Math.max(0, Math.min(r.top, r.bottom));
    const bottom = Math.min(viewport[1], Math.max(r.top, r.bottom));
    const rect = [r.left, r.top, r.width, r.height].map(Math.round);
    if (right <= left || bottom <= top)
        return {ready:false, viewport:viewport, rect:rect, reason:'outside viewport'};
    const x = Math.floor((left + right)/2), y = Math.floor((top + bottom)/2);
    const hit = document.elementFromPoint(x, y);
    return {ready:!!hit && (hit === el || el.contains(hit)),
            viewport:viewport, rect:rect, point:[x,y],
            hit:hit ? {tag:hit.tagName, id:hit.id} : null};
"""


def _click_until_ready(driver, locator, timeout, retryable, before_click=None):
    """Bounded explicit wait, reacquiring candidates and using native clicks.

    Separate from Selenium imports so retry/guard semantics can be unit-tested
    even on machines without a browser or Selenium installed.
    """
    deadline = time.monotonic() + timeout
    attempt = 0
    last = "no displayed/enabled matching element"
    # Center first. If a fixed element covers it, try other alignments.
    alignments = ("center", "center", "center", "end", "end", "start", "start")
    while True:
        try:
            for element in driver.find_elements(*locator):
                if not element.is_displayed() or not element.is_enabled():
                    continue
                alignment = alignments[attempt % len(alignments)]
                driver.execute_script(SCROLL_TO_ELEMENT, element, alignment)
                geometry = driver.execute_script(CLICK_GEOMETRY, element)
                last = f"alignment={alignment}, geometry={geometry}"
                if not geometry.get("ready"):
                    continue
                if before_click is not None:
                    before_click()
                # A real WebDriver click. Never call element.click() via JS.
                element.click()
                return
        except retryable as exc:
            last = f"{type(exc).__name__}: {(str(exc).splitlines() or [''])[0]} | {last}"
        attempt += 1
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(f"Click timeout for {locator}: {last}")
        time.sleep(min(0.2, remaining))


def click_when_ready(driver, locator, timeout, before_click=None):
    from selenium.common.exceptions import (
        ElementClickInterceptedException, ElementNotInteractableException,
        StaleElementReferenceException,
    )
    return _click_until_ready(
        driver, locator, timeout,
        (ElementClickInterceptedException, ElementNotInteractableException,
         StaleElementReferenceException),
        before_click,
    )


def expand_sections(driver, timeout):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    wait = WebDriverWait(driver, timeout)
    details = []
    for section in SECTION_IDS:
        target = wait.until(EC.presence_of_element_located((By.ID, section)))
        if not target.is_displayed():
            click_when_ready(driver, (By.CSS_SELECTOR, f'[aria-controls="{section}"]'), timeout)
        wait.until(EC.visibility_of_element_located((By.ID, section)))
        details.append(section)
    time.sleep(0.5)
    driver.execute_script("window.scrollTo({top:0, left:0, behavior:'instant'})")
    return details


def inject_axe(driver, source):
    """Inject in top document and reachable visible same-origin child frames."""
    from selenium.webdriver.common.by import By
    warnings = []
    def inject(path, depth):
        driver.execute_script(source)
        version = driver.execute_script("return window.axe && window.axe.version")
        if version != VERSION:
            raise RuntimeError(f"Expected axe-core {VERSION}, got {version}")
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for i, frame in enumerate(frames):
            label = f"{path}/{frame.get_attribute('id') or i}"
            if not frame.is_displayed():
                continue
            if depth >= 5:
                warnings.append(f"Frame depth limit: {label}")
                continue
            switched = False
            try:
                # Don't inject JS into an external frame.
                same = driver.execute_script("try { return !!arguments[0].contentDocument; } catch(e) { return false; }", frame)
                if not same:
                    warnings.append(f"Inaccessible/cross-origin frame: {label}")
                    continue
                driver.switch_to.frame(frame)
                switched = True
                inject(label, depth + 1)
            except Exception as e:
                warnings.append(f"Frame injection failed: {label} ({type(e).__name__})")
            finally:
                if switched:
                    driver.switch_to.parent_frame()
    driver.switch_to.default_content()
    inject("top", 0)
    return warnings


def run_axe(driver, source):
    warnings = inject_axe(driver, source)
    result = driver.execute_async_script("""
        const tags = arguments[0], done = arguments[arguments.length-1];
        window.axe.run(document, {runOnly:{type:'tag',values:tags},
          resultTypes:['violations','incomplete','passes','inapplicable']})
          .then(r => done({ok:true, result:r}))
          .catch(e => done({ok:false, error:String(e)}));
    """, list(SCAN_TAGS))
    if not result or not result.get("ok"):
        raise RuntimeError(f"axe.run failed: {result.get('error') if result else 'no result'}")
    raw = result["result"]
    if raw.get("testEngine", {}).get("version") != VERSION:
        raise RuntimeError("Unexpected axe result engine version")
    evaluation = evaluate_scan(raw, warnings)
    # Retain rule IDs and rule-level evidence but omit raw element HTML and
    # arbitrary DOM data (which can contain Moodle session tokens).
    details = {"engine": raw["testEngine"], "tags": list(SCAN_TAGS),
               "rules": {bucket: [{"id": r["id"], "impact": r.get("impact"),
                                   "tags": r.get("tags", []), "node_count": len(r.get("nodes", []))}
                                  for r in raw[bucket]] for bucket in ("violations", "incomplete", "passes", "inapplicable")},
               **evaluation}
    return details


def trigger_validation(driver, base, timeout):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    # Keep all required identity fields empty. Do not create a user.
    for field in FORM_FIELDS:
        el = driver.find_element(By.ID, field)
        if el.get_attribute("value"):
            el.clear()
        if el.get_attribute("value"):
            raise RuntimeError(f"Cannot guarantee blank required field: {field}")
    def ensure_blank():
        # Re-check all identity inputs immediately before each actual click
        # attempt: scrolling/focus/autofill must not turn this into a valid POST.
        for field in FORM_FIELDS:
            el = driver.find_element(By.ID, field)
            if el.get_attribute("value") != "":
                raise RuntimeError(f"Cannot guarantee blank required field: {field}")

    click_when_ready(driver, (By.ID, "id_submitbutton"), timeout, before_click=ensure_blank)
    try:
        WebDriverWait(driver, timeout).until(lambda d: any(x["message"] for x in validation_items(d)))
    except TimeoutException:
        raise RuntimeError("No visible or native validation error was observed after empty form submission") from None
    wait_for_form(driver, base, timeout)
    # Only audit the error state if the error still exists on the form.
    evidence = validation_items(driver)
    if not any(item["message"] for item in evidence):
        raise RuntimeError("Validation error disappeared before audit")
    return evidence


def validation_items(driver):
    return driver.execute_script("""
      const ids=arguments[0];
      function visible(e) { if(!e) return false; const s=getComputedStyle(e);
          return !!e.getClientRects().length && s.visibility!=='hidden' && s.display!=='none'; }
      return ids.map(id=>{
        const el=document.getElementById(id);
        if(!el) return {field:id,message:'',native:false,associated:false,missing:true};
        const refs=(el.getAttribute('aria-describedby')||'').split(/\\s+/)
          .concat((el.getAttribute('aria-errormessage')||'').split(/\\s+/)).filter(Boolean);
        const error=document.getElementById(id.replace(/^id_/, 'id_error_'));
        const dom=visible(error) ? error.innerText.trim() : '';
        const native=!!(!dom && document.activeElement===el && el.validity && !el.validity.valid && el.validationMessage);
        return {field:id, message:dom || (native?el.validationMessage:''), native:native,
                associated:!!(dom && refs.includes(error.id)), refs:refs,
                aria_invalid:el.getAttribute('aria-invalid'), required:el.required,
                error_id:error?error.id:null};
      });
    """, list(FORM_FIELDS))


def focus_identity(driver):
    return driver.execute_script("""
      let doc=document, parts=[], id='', tag='', blocked=false;
      for(let depth=0;depth<6;depth++){
        let el=doc.activeElement; if(!el)break;
        id=el.id||''; tag=el.tagName.toLowerCase();
        const indexes=[]; for(let p=el;p&&p.parentElement;p=p.parentElement){
          indexes.push(Array.prototype.indexOf.call(p.parentElement.children,p)); }
        parts.push(tag+'#'+id+'@'+indexes.reverse().join('.'));
        if(tag!=='iframe'&&tag!=='frame')break;
        try {if(!el.contentDocument){blocked=true;break;}doc=el.contentDocument;}
        catch(e){blocked=true;break;}
      }
      return {id:id, tag:tag, identity:parts.join(' > '), blocked:blocked};
    """)


def keyboard_check(driver, limit, timeout=30):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    for target in KEYBOARD_TARGETS:
        element = driver.find_element(By.ID, target)
        if not element.is_displayed() or not element.is_enabled():
            raise RuntimeError(f"Required keyboard target not visible/enabled: {target}")
    # Seed focus on username only; subsequent movement is actual keyboard Tab.
    click_when_ready(driver, (By.ID, KEYBOARD_TARGETS[0]), timeout)
    first = focus_identity(driver)
    if first["id"] != KEYBOARD_TARGETS[0]:
        raise RuntimeError("Could not establish starting focus on username")
    trace = [{"step": 0, **first}]
    reached = [KEYBOARD_TARGETS[0]]
    cycle = False
    steps = 0
    for steps in range(1, limit + 1):
        ActionChains(driver).send_keys(Keys.TAB).perform()
        active = focus_identity(driver)
        trace.append({"step": steps, **active})
        if active["id"] in KEYBOARD_TARGETS and active["id"] not in reached:
            reached.append(active["id"])
        if set(reached) == set(KEYBOARD_TARGETS):
            break
        # A return to the exact seed indicates a cycle through the available order.
        if active["identity"] == first["identity"] and steps > 1:
            cycle = True
            break
    summary = evaluate_keyboard(KEYBOARD_TARGETS, reached, steps, limit, cycle)
    if any(t["blocked"] for t in trace) and summary["status"] == "FAIL":
        summary["status"] = "INCONCLUSIVE"
    return {**summary, "trace": trace}


def screenshot(driver, path):
    try:
        if driver.save_screenshot(str(path)):
            return path.name
    except Exception:
        pass
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headed", action="store_true", help="Show Chrome")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-tabs", type=int, default=180)
    parser.add_argument("--axe-js", type=Path, help="Use a trusted local official axe.min.js 4.10.3")
    parser.add_argument("--browser-binary")
    parser.add_argument("--driver")
    args = parser.parse_args(argv)
    if not 5 <= args.timeout <= 180 or not 30 <= args.max_tabs <= 300:
        parser.error("timeout must be 5–180; max-tabs must be 30–300")
    started = utcnow()
    token = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12]
    out = ROOT / "results" / "accessibility" / token
    out.mkdir(parents=True)
    info = {"nfr": "NFR-02", "type": "Accessibility Testing", "run_id": token,
            "started_at": started, "complete": False, "axe_expected_version": VERSION,
            "runner_revision": "2-scroll-click-fix",
            "scope": "whole Add New User page, including page chrome; visible same-origin frames",
            "tags": list(SCAN_TAGS), "platform": platform.platform(), "python": platform.python_version(),
            "viewport_requested": [1440, 1000], "headless": not args.headed,
            "timeout": args.timeout, "max_tabs": args.max_tabs,
            "criteria": "zero serious/critical WCAG violations; zero WCAG name/label/contrast/key rule violations; "
                        "five downstream core targets reachable by Tab from username; observed validation errors associated or native; "
                        "blocking incomplete results or frame coverage failures are inconclusive if no definite failure"}
    write_json(out / "run_info.json", info)
    rows, findings, secrets = [], [], []
    driver = None
    safe_form = False
    base = ""
    def record(sid, detail):
        detail = redact(detail, secrets)
        shot = ""
        if safe_form and driver is not None:
            try:
                if same_origin(driver.current_url, base) and urlsplit(driver.current_url).path.endswith("/user/editadvanced.php"):
                    shot = screenshot(driver, out / f"{sid}.png")
            except Exception:
                pass
        row = {"scenario_id": sid, "status": detail["status"], "screenshot": shot,
               "detail_file": f"{sid}.json", "reason": detail.get("reason", ""),
               **detail.get("node_counts", {}),
               "rule_counts": detail.get("rule_counts", {}),
               "frame_warnings": detail.get("frame_warnings", []),
               "keyboard_steps": detail.get("steps", ""), "missing_targets": detail.get("missing", []),
               "observed_errors": detail.get("observed_count", ""), "unassociated": detail.get("unassociated", [])}
        write_json(out / row["detail_file"], detail)
        rows.append(row)
        findings.extend({"scenario_id": sid, **f} for f in detail.get("findings", []))
        if "node_counts" in detail:
            metrics = (f" | blocking violations={row.get('blocking_violations', 0)}"
                       f" | incomplete={row.get('incomplete_nodes', 0)}")
        else:
            metrics = " | axe counts=N/A"
        # Preserve the complete reason in the JSON/CSV, but avoid repeating
        # Selenium's long stack trace for dependent scenarios in the terminal.
        reason_line = row["reason"].splitlines()[0] if row["reason"] else ""
        print(f"{sid}: {row['status']}{metrics} {reason_line}", flush=True)
    def check(sid, func):
        try:
            record(sid, func())
        except Exception as exc:
            # Never save login page/credentials or raw page source.
            record(sid, {"status": "INCONCLUSIVE", "reason": f"{type(exc).__name__}: {exc}",
                         "traceback": traceback.format_exc()})
    try:
        base = local_url(os.getenv("MOODLE_BASE_URL", "http://127.0.0.1:9502"))
        username = os.getenv("MOODLE_ADMIN_USERNAME", "admin")
        password = os.getenv("MOODLE_ADMIN_PASSWORD", "")
        if not password or password == "REPLACE_ME":
            raise ValueError("Set MOODLE_ADMIN_PASSWORD in .env")
        secrets.append(password)
        info["base_url"] = base
        source, digest, source_kind = load_asset(args.axe_js)
        info.update(axe_sha256=digest, axe_source=source_kind)
        # Asset download/cache happens before any authenticated browsing.
        driver = start_browser(args)
        info["browser_version"] = driver.capabilities.get("browserVersion", "")
        import selenium
        info["selenium_version"] = selenium.__version__
        login(driver, base, username, password, args.timeout)
        safe_form = True
        secrets.extend(driver.execute_script("return Array.from(document.querySelectorAll('input[name=sesskey]')).map(x=>x.value)") or [])
        info["viewport_actual"] = driver.execute_script("return [innerWidth,innerHeight]")
        check("ACC-01", lambda: run_axe(driver, source))
        def expanded():
            open_form(driver, base, args.timeout)
            sections = expand_sections(driver, args.timeout)
            return {**run_axe(driver, source), "expanded_sections": sections}
        check("ACC-02", expanded)
        validation = None
        try:
            open_form(driver, base, args.timeout)
            validation = trigger_validation(driver, base, args.timeout)
        except Exception as exc:
            reason = f"Validation setup failed: {type(exc).__name__}: {exc}"
            record("ACC-03", {"status": "INCONCLUSIVE", "reason": reason})
            record("ACC-05", {"status": "INCONCLUSIVE", "reason": reason})
        else:
            check("ACC-03", lambda: run_axe(driver, source))
            check("ACC-05", lambda: evaluate_validation(validation))
        def keyboard():
            open_form(driver, base, args.timeout)
            return keyboard_check(driver, args.max_tabs, args.timeout)
        check("ACC-04", keyboard)
        info["complete"] = True
    except Exception as exc:
        info["setup_error"] = redact(f"{type(exc).__name__}: {exc}", secrets)
        print(f"Setup/run error: {info['setup_error']}")
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        # Missing scenarios are not successes. Preserve an explicit row.
        for sid in SCENARIOS:
            if not any(row["scenario_id"] == sid for row in rows):
                rows.append({"scenario_id": sid, "status": "INCONCLUSIVE", "reason": "Not executed"})
        rows.sort(key=lambda row: row["scenario_id"])
        write_csv(out / "summary.csv", rows,
                  ["scenario_id", "status", "blocking_violations", "blocking_incomplete", "violations_nodes",
                   "violations_wcag", "violations_best_practice", "wcag_critical", "wcag_serious", "wcag_moderate",
                   "wcag_minor", "incomplete_nodes", "rule_counts", "frame_warnings", "keyboard_steps",
                   "missing_targets", "observed_errors", "unassociated", "screenshot", "detail_file", "reason"])
        write_csv(out / "findings.csv", findings, ["scenario_id", "bucket", "rule_id", "impact", "wcag", "blocking",
                  "target", "tags", "help", "help_url", "failure_summary"])
        info["verdict"] = overall([r["status"] for r in rows], len(SCENARIOS))
        info["ended_at"] = utcnow()
        info["counts"] = {s: sum(r["status"] == s for r in rows) for s in ("PASS", "FAIL", "INCONCLUSIVE")}
        write_json(out / "run_info.json", info)
        print(f"Results: {out}\nVerdict: {info['verdict']}")
    return 0 if info["verdict"] == "PASS" else 1 if info["verdict"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
