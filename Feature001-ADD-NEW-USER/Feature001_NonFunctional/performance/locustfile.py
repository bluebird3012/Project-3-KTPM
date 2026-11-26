"""One local Locust process; the runner supplies a run-specific manifest."""
import os
import time
from pathlib import Path
from locust import HttpUser, task, between
from locust.exception import StopUser
from core.config import settings
from core.moodle_client import login, prepare, success, TIMEOUT
from core.reporter import new_name, append_json

BASE, ADMIN, PASSWORD, _ = settings()
PREFIX = os.environ['NFR_PREFIX']
MANIFEST = Path(os.environ['NFR_MANIFEST'])

class MoodleAdmin(HttpUser):
    host = BASE
    wait_time = between(1, 2)

    def on_start(self):
        self.client.trust_env = False
        try:
            login(self.client, BASE, ADMIN, PASSWORD)
        except Exception as exc:
            append_json(MANIFEST, {'event':'setup_error', 'stage':'login', 'error':type(exc).__name__})
            raise StopUser()

    @task
    def create_user(self):
        name = new_name(PREFIX)
        try:
            url, data = prepare(self.client, BASE, name)
        except Exception as exc:
            append_json(MANIFEST, {'event':'setup_error', 'stage':'form', 'error':type(exc).__name__})
            return
        append_json(MANIFEST, {'event':'attempt', 'username':name})
        start = time.perf_counter()
        ok, status, error = False, 0, ''
        try:
            with self.client.post(url, data=data, timeout=TIMEOUT, name='create_user', catch_response=True) as r:
                # Include the redirect chain; stop clock before parsing HTML.
                elapsed = (time.perf_counter()-start)*1000
                status = r.status_code
                ok = success(r)
                if ok:
                    r.success()
                else:
                    error = 'success alert not observed'
                    r.failure(error)
        except Exception as exc:
            elapsed = (time.perf_counter()-start)*1000
            error = type(exc).__name__
        append_json(MANIFEST, {'event':'result','username':name,'http_ok':ok,'status':status,
                               'response_ms':round(elapsed,3),'error':error})
