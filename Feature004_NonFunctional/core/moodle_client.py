"""HTTP client for Moodle login & Add Quiz form submission (used by Locust & preflight)."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup
import requests

TIMEOUT = 60
LOGIN_PATH = "/login/index.php"


def add_quiz_path(course_id: int = 2, section_id: int = 2) -> str:
    return f"/course/modedit.php?add=quiz&type&course={course_id}&sectionid={section_id}&return=0&beforemod=0"


def soup(response) -> BeautifulSoup:
    return BeautifulSoup(response.text, "html.parser")


def checked_url(base: str, action: str) -> str:
    target = urljoin(base + "/", action)
    a, b = urlsplit(target), urlsplit(base)
    if (a.scheme, a.netloc) != (b.scheme, b.netloc):
        raise ValueError("Form action points outside the configured local Moodle origin")
    return target


def form_values(form) -> list[tuple[str, str]]:
    """Extract successful HTML controls, preserving repeated names & hidden QuickForm fields."""
    values: list[tuple[str, str]] = []
    for el in form.select("input[name],select[name],textarea[name],button[name]"):
        if el.has_attr("disabled") or el.find_parent("fieldset", disabled=True):
            continue
        name = el["name"]
        kind = el.get("type", "").lower()
        if el.name == "select":
            options = el.select("option[selected]:not([disabled])")
            if not options and not el.has_attr("multiple"):
                first = el.select_one("option:not([disabled])")
                options = [first] if first else []
            values.extend((name, o.get("value", o.get_text())) for o in options)
        elif el.name == "textarea":
            values.append((name, el.get_text()))
        elif el.name == "button" or kind in ("submit", "button", "reset", "file", "image"):
            continue
        elif kind in ("checkbox", "radio"):
            if el.has_attr("checked"):
                values.append((name, el.get("value", "on")))
        else:
            values.append((name, el.get("value", "")))
    return values


def override(values: list[tuple[str, str]], **changes) -> list[tuple[str, str]]:
    return [(k, v) for k, v in values if k not in changes] + [
        (k, v) for k, v in changes.items() if v is not None
    ]


def request_kwargs(client, label: str) -> dict:
    return {"timeout": TIMEOUT, **({"name": label} if hasattr(client, "request_name") else {})}


def extract_sesskey(response) -> str | None:
    page = soup(response)
    el = page.select_one('input[name="sesskey"]')
    if el and el.get("value"):
        return el["value"]
    m = re.search(r'["\']sesskey["\']\s*:\s*["\']([^"\']+)', response.text)
    if m:
        return m.group(1)
    for link in page.select('a[href*="/login/logout.php"]'):
        val = parse_qs(urlsplit(link["href"]).query).get("sesskey")
        if val:
            return val[0]
    return None


def login(client, base: str, username: str, password: str):
    url = base + LOGIN_PATH
    r = client.get(url, **request_kwargs(client, "login_get"))
    r.raise_for_status()
    form = soup(r).select_one('form:has(input[name="logintoken"]):has(input[name="username"])')
    if form is None:
        raise RuntimeError("Login form/logintoken not found")
    values = override(form_values(form), username=username, password=password)
    # Do not follow the 303 redirect into the heavy /my/ dashboard; Moodle sets the
    # authenticated MoodleSession cookie directly on the 303 response.
    r = client.post(
        checked_url(base, urljoin(r.url, form.get("action", r.url))),
        data=values,
        allow_redirects=False,
        **request_kwargs(client, "login_post"),
    )
    if r.status_code in (301, 302, 303, 307, 308):
        loc = r.headers.get("Location", "")
        if "testsession=" in loc or "/login/index.php" not in urlsplit(loc).path:
            return r
        raise RuntimeError(f"Login redirected back to login page: {loc}")
    r.raise_for_status()
    if soup(r).select_one('input[name="logintoken"], #loginerrormessage, .loginerrors'):
        raise RuntimeError("Login failed or additional step required")
    return r


def add_quiz_form(response):
    return soup(response).select_one(
        'form.mform:has(input[name="name"]):has(input[name="sesskey"]):has(input[name="modulename"][value="quiz"])'
    )


def prepare_add_quiz(client, base: str, quiz_name: str, *, course_id: int = 2, section_id: int = 2):
    r = client.get(
        base + add_quiz_path(course_id, section_id),
        **request_kwargs(client, "add_quiz_form_get"),
    )
    r.raise_for_status()
    form = add_quiz_form(r)
    if form is None:
        raise RuntimeError("Add a new Quiz form not found")
    values = form_values(form)
    val_map = dict(values)
    if not val_map.get("sesskey") or not val_map.get("_qf__mod_quiz_mod_form"):
        raise RuntimeError("Missing Moodle sesskey or _qf__mod_quiz_mod_form marker")
    submit_btn = form.select_one('[name="submitbutton2"]')
    if submit_btn is None:
        raise RuntimeError("Save and return to course button (submitbutton2) not found")
    values = override(
        values,
        name=quiz_name,
        submitbutton2=submit_btn.get("value", "Save and return to course"),
    )
    action_url = checked_url(base, urljoin(r.url, form.get("action", r.url)))
    return action_url, values


def quiz_created_response(response, quiz_name: str) -> bool:
    if response.status_code != 200:
        return False
    path = urlsplit(response.url).path
    if "/course/view.php" not in path:
        return False
    return quiz_name in response.text


def session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    return s
