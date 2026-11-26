from urllib.parse import urljoin, urlsplit
import re
import secrets
import requests
from bs4 import BeautifulSoup

TIMEOUT = 15
CREATE = '/user/editadvanced.php?id=-1'
LOGIN = '/login/index.php'


def soup(response):
    return BeautifulSoup(response.text, 'html.parser')


def checked_url(base, action):
    target = urljoin(base + '/', action)
    a, b = urlsplit(target), urlsplit(base)
    if (a.scheme, a.netloc) != (b.scheme, b.netloc):
        raise ValueError('Form action points outside the configured Moodle origin')
    return target


def form_values(form):
    """Successful HTML controls; retain repeated names and hidden QuickForm fields."""
    values = []
    for el in form.select('input[name],select[name],textarea[name],button[name]'):
        if el.has_attr('disabled') or el.find_parent('fieldset', disabled=True):
            continue
        name, kind = el['name'], el.get('type', '').lower()
        if el.name == 'select':
            options = el.select('option[selected]:not([disabled])')
            if not options and not el.has_attr('multiple'):
                first = el.select_one('option:not([disabled])')
                options = [first] if first else []
            values.extend((name, o.get('value', o.get_text())) for o in options)
        elif el.name == 'textarea':
            values.append((name, el.get_text()))
        elif el.name == 'button' or kind in ('submit', 'button', 'reset', 'file', 'image'):
            continue
        elif kind in ('checkbox', 'radio'):
            if el.has_attr('checked'):
                values.append((name, el.get('value', 'on')))
        else:
            values.append((name, el.get('value', '')))
    return values


def override(values, **changes):
    return [(k,v) for k,v in values if k not in changes] + [(k,v) for k,v in changes.items() if v is not None]


def request_kwargs(client, label):
    # Locust HttpSession exposes request_name; regular requests.Session does not.
    return {'timeout': TIMEOUT, **({'name': label} if hasattr(client, 'request_name') else {})}


def login(client, base, username, password):
    url = base + LOGIN
    r = client.get(url, **request_kwargs(client, 'login_get'))
    r.raise_for_status()
    f = soup(r).select_one('form:has(input[name="logintoken"]):has(input[name="username"])')
    if f is None:
        raise RuntimeError('Login form/token not found')
    values = override(form_values(f), username=username, password=password)
    r = client.post(checked_url(base, urljoin(r.url, f.get('action', r.url))), data=values,
                    **request_kwargs(client, 'login_post'))
    r.raise_for_status()
    if soup(r).select_one('input[name="logintoken"], #loginerrormessage, .loginerrors'):
        raise RuntimeError('Login failed or additional login step required')
    if not sesskey(r):
        home = client.get(base + '/', **request_kwargs(client, 'login_home'))
        home.raise_for_status()
        if not sesskey(home) or soup(home).select_one('input[name="logintoken"]'):
            raise RuntimeError('Authenticated session not confirmed')
    return r


def sesskey(r):
    page = soup(r)
    el = page.select_one('input[name="sesskey"]')
    if el and el.get('value'):
        return el['value']
    found = re.search(r'["\']sesskey["\']\s*:\s*["\']([^"\']+)', r.text)
    if found:
        return found.group(1)
    from urllib.parse import parse_qs
    for el in page.select('a[href*="/login/logout.php"]'):
        val = parse_qs(urlsplit(el['href']).query).get('sesskey')
        if val:
            return val[0]
    return None


def create_form(r):
    return soup(r).select_one('form:has(input[name="username"]):has(input[name="firstname"]):has(input[name="sesskey"])')


def prepare(client, base, name):
    r = client.get(base + CREATE, **request_kwargs(client, 'create_form_get'))
    r.raise_for_status()
    f = create_form(r)
    if f is None:
        raise RuntimeError('Add New User form not found')
    values = form_values(f)
    if not dict(values).get('sesskey') or not any(k.startswith('_qf__') for k,v in values):
        raise RuntimeError('Missing Moodle sesskey or QuickForm marker')
    button = f.select_one('[name="submitbutton"]')
    if button is None:
        raise RuntimeError('Submit control not found')
    # A unique synthetic account; no mail sent. .invalid is reserved for tests.
    values = override(values, id='-1', auth='manual', username=name, firstname='NFR', lastname='Test',
                      email=name+'@example.invalid', newpassword='NfR!7a'+secrets.token_hex(10),
                      createpassword=None, submitbutton=button.get('value', 'Create user'))
    return checked_url(base, urljoin(r.url, f.get('action', r.url))), values


def success(r):
    return r.status_code == 200 and any('Changes saved' in el.get_text(' ', strip=True)
           for el in soup(r).select('.alert-success[role="alert"], .alert-success'))


def denial(r):
    page = soup(r)
    return (r.status_code in (401,403) or bool(page.select_one('input[name="logintoken"], .alert-danger, .errormessage, #notice')))


def session():
    s = requests.Session()
    s.trust_env = False
    return s
