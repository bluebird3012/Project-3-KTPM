from pathlib import Path
from urllib.parse import urlsplit
import os
import re
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def local_url(raw):
    u = urlsplit(raw.rstrip('/'))
    if (u.scheme not in ('http', 'https') or u.hostname not in ('localhost', '127.0.0.1', '::1')
            or u.username or u.password or u.query or u.fragment):
        raise ValueError('Only a local Moodle HTTP(S) site is supported.')
    return raw.rstrip('/')


def settings():
    base = local_url(os.getenv('MOODLE_BASE_URL', 'http://127.0.0.1:9502'))
    user, password = os.getenv('MOODLE_ADMIN_USERNAME', 'admin'), os.getenv('MOODLE_ADMIN_PASSWORD', '')
    container = os.getenv('MOODLE_WEB_CONTAINER', '')
    if not password or password == 'REPLACE_ME':
        raise ValueError('Set MOODLE_ADMIN_PASSWORD in .env.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', container):
        raise ValueError('Set MOODLE_WEB_CONTAINER to the actual local Docker webserver container name/ID.')
    return base, user, password, container
