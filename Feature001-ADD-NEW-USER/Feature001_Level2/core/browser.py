"""Shared WebDriver creation and interaction helpers."""
from __future__ import annotations


def build_browser(headless: bool):
    from selenium import webdriver
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1440,1000")
    if headless:
        options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


def safe_type(browser, by: str, locator: str, value: str, timeout: int = 15) -> None:
    """Enter a value using a fresh element on each retry if the DOM changes.

    Clear again before retrying so a partial input cannot be appended twice.
    Do not verify exact value here: maxlength and other input restrictions are
    intentionally exercised by the data-driven test cases.
    """
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    def enter_value(driver):
        try:
            element = EC.element_to_be_clickable((by, locator))(driver)
            if not element:
                return False
            element.clear()
            if value:
                element.send_keys(value)
            return True
        except StaleElementReferenceException:
            return False

    WebDriverWait(browser, timeout, poll_frequency=0.25).until(
        enter_value, message=f"Cannot enter value into field ({by}={locator})"
    )


def click_visible(browser, by: str, locator: str, timeout: int, action_name: str) -> None:
    """Try a real WebDriver click and ActionChains, with blocker diagnostics.

    The Moodle Add New User form is tall. A sticky/floating element may cover
    the requested click point even when the button is present and enabled.
    This helper never uses JavaScript to *activate* the button: JavaScript is
    only used for scrolling and inspecting the element under the click point.
    """
    from selenium.common.exceptions import ElementClickInterceptedException
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    alignments = ("center", "start", "end")
    last_error = None
    diagnostics: list[str] = []

    def diagnose(element, alignment: str, method: str) -> str:
        try:
            detail = browser.execute_script(
                """
                const target = arguments[0];
                const rect = target.getBoundingClientRect();
                const x = Math.max(0, Math.min(window.innerWidth - 1,
                    rect.left + rect.width / 2));
                const y = Math.max(0, Math.min(window.innerHeight - 1,
                    rect.top + rect.height / 2));
                const top = document.elementFromPoint(x, y);
                const describe = (el) => el ? {
                    tag: el.tagName,
                    id: el.id || '',
                    className: typeof el.className === 'string'
                        ? el.className.slice(0, 160) : '',
                    role: el.getAttribute('role') || ''
                } : null;
                const covered = !!top && top !== target && !target.contains(top);
                return {
                    target: describe(target),
                    blockedBy: describe(top),
                    covered: covered,
                    center: [Math.round(x), Math.round(y)],
                    targetRect: [Math.round(rect.left), Math.round(rect.top),
                        Math.round(rect.width), Math.round(rect.height)],
                    viewport: [window.innerWidth, window.innerHeight]
                };
                """,
                element,
            )
            return f"{alignment}/{method}: {detail}"
        except Exception as error:
            return f"{alignment}/{method}: diagnostic unavailable: {type(error).__name__}: {error}"

    for alignment in alignments:
        element = WebDriverWait(browser, timeout).until(
            EC.presence_of_element_located((by, locator))
        )
        browser.execute_script(
            "arguments[0].scrollIntoView({block: arguments[1], inline: 'nearest'});",
            element,
            alignment,
        )
        element = WebDriverWait(browser, timeout).until(
            EC.element_to_be_clickable((by, locator))
        )

        # First try WebDriver's standard click. If Chrome reports that the
        # click point is blocked, try a real pointer action on the same target.
        try:
            element.click()
            return
        except ElementClickInterceptedException as error:
            last_error = error
            message = diagnose(element, alignment, "WebElement.click")
            print(f"[CLICK DEBUG] {action_name}: {message}")
            diagnostics.append(message)

        try:
            ActionChains(browser).move_to_element(element).click().perform()
            print(f"[CLICK DEBUG] {action_name}: ActionChains click succeeded "
                  f"after intercepted WebElement.click ({alignment}).")
            return
        except ElementClickInterceptedException as error:
            last_error = error
            message = diagnose(element, alignment, "ActionChains.click")
            print(f"[CLICK DEBUG] {action_name}: {message}")
            diagnostics.append(message)

    raise RuntimeError(
        f"Cannot click {action_name} ({by}={locator}) after "
        f"{len(alignments)} scroll alignments and ActionChains attempts. "
        f"Blocker diagnostics: {'; '.join(diagnostics)}"
    ) from last_error
