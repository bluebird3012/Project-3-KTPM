"""Shared WebDriver creation and resilient interaction helpers."""
from __future__ import annotations


def build_browser(headless: bool):
    from selenium import webdriver

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
    return driver


def safe_type(
    browser,
    by: str,
    locator: str,
    value: str,
    timeout: int = 30,
    *,
    clear_first: bool = True,
) -> None:
    """Enter text into an input element, retrying safely on StaleElementReferenceException."""
    from selenium.common.exceptions import ElementNotInteractableException, StaleElementReferenceException
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    def enter_value(driver):
        try:
            element = EC.element_to_be_clickable((by, locator))(driver)
            if not element:
                return False
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
            if clear_first:
                element.clear()
            if value:
                element.send_keys(value)
            return True
        except (StaleElementReferenceException, ElementNotInteractableException):
            return False

    WebDriverWait(browser, timeout, poll_frequency=0.25).until(
        enter_value,
        message=f"Cannot enter value into field ({by}={locator})",
    )


def click_visible(browser, by: str, locator: str, timeout: int, action_name: str) -> None:
    """Click an element via real WebDriver click or ActionChains (never JS click for submit)."""
    from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException
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
                const x = Math.max(0, Math.min(window.innerWidth - 1, rect.left + rect.width / 2));
                const y = Math.max(0, Math.min(window.innerHeight - 1, rect.top + rect.height / 2));
                const top = document.elementFromPoint(x, y);
                const describe = (el) => el ? {
                    tag: el.tagName, id: el.id || '',
                    className: typeof el.className === 'string' ? el.className.slice(0, 120) : '',
                    role: el.getAttribute('role') || ''
                } : null;
                return {
                    target: describe(target),
                    blockedBy: describe(top),
                    covered: !!top && top !== target && !target.contains(top),
                    center: [Math.round(x), Math.round(y)],
                    viewport: [window.innerWidth, window.innerHeight]
                };
                """,
                element,
            )
            return f"{alignment}/{method}: {detail}"
        except Exception as err:
            return f"{alignment}/{method}: diagnostic unavailable ({type(err).__name__}: {err})"

    for alignment in alignments:
        for _ in range(2):
            try:
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
                element.click()
                return
            except StaleElementReferenceException as err:
                last_error = err
                continue
            except ElementClickInterceptedException as err:
                last_error = err
                diagnostics.append(diagnose(element, alignment, "WebElement.click"))
                try:
                    ActionChains(browser).move_to_element(element).click().perform()
                    return
                except (ElementClickInterceptedException, StaleElementReferenceException) as err2:
                    last_error = err2
                    diagnostics.append(diagnose(element, alignment, "ActionChains.click"))
                    break

    raise RuntimeError(
        f"Cannot click {action_name} ({by}={locator}) after {len(alignments)} scroll alignments. "
        f"Diagnostics: {'; '.join(diagnostics)}"
    ) from last_error


def safe_set_checkbox(browser, by: str, locator: str, checked: bool, timeout: int, label: str) -> None:
    """Ensure a checkbox reaches the requested checked state."""
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    element = WebDriverWait(browser, timeout).until(EC.presence_of_element_located((by, locator)))
    if element.is_selected() != checked:
        click_visible(browser, by, locator, timeout, label)
        WebDriverWait(browser, timeout).until(
            lambda d: d.find_element(by, locator).is_selected() == checked,
            message=f"Checkbox {label} ({by}={locator}) did not reach checked={checked}",
        )


def safe_select(
    browser,
    by: str,
    locator: str,
    *,
    value: str | None = None,
    label: str | None = None,
    timeout: int = 30,
) -> None:
    """Select a dropdown option by value or visible text, waiting until enabled."""
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait

    def do_select(driver):
        try:
            el = EC.element_to_be_clickable((by, locator))(driver)
            if not el or not el.is_enabled():
                return False
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", el)
            sel = Select(el)
            if value is not None:
                sel.select_by_value(value)
            elif label is not None:
                sel.select_by_visible_text(label)
            else:
                raise ValueError("Either value or label must be provided")
            return True
        except StaleElementReferenceException:
            return False

    WebDriverWait(browser, timeout, poll_frequency=0.25).until(
        do_select,
        message=f"Cannot select option (value={value!r}, label={label!r}) on ({by}={locator})",
    )
