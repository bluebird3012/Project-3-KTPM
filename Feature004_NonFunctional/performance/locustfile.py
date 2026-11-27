"""Locust HttpUser workload for NFR-07: Add Quiz creation under concurrent load."""
from __future__ import annotations

import os
from pathlib import Path
import time

from locust import HttpUser, between, task
from locust.exception import StopUser

from core.config import settings
from core.moodle_client import TIMEOUT, login, prepare_add_quiz, quiz_created_response
from core.reporter import append_json, new_quiz_name

CFG = settings()
BASE = CFG["base"]
ADMIN = CFG["username"]
PASSWORD = CFG["password"]
COURSE_ID = CFG["course_id"]
SECTION_ID = CFG["section_id"]
PREFIX = os.environ["NFR_PREFIX"]
MANIFEST = Path(os.environ["NFR_MANIFEST"])


class MoodleQuizCreator(HttpUser):
    host = BASE
    wait_time = between(1, 2)

    def on_start(self):
        self.client.trust_env = False
        try:
            login(self.client, BASE, ADMIN, PASSWORD)
        except Exception as exc:
            append_json(
                MANIFEST,
                {"event": "setup_error", "stage": "login", "error": f"{type(exc).__name__}: {str(exc)[:180]}"},
            )
            raise StopUser()

    @task
    def create_quiz(self):
        quiz_name = new_quiz_name(PREFIX)
        try:
            url, data = prepare_add_quiz(
                self.client,
                BASE,
                quiz_name,
                course_id=COURSE_ID,
                section_id=SECTION_ID,
            )
        except Exception as exc:
            append_json(
                MANIFEST,
                {"event": "setup_error", "stage": "form", "error": f"{type(exc).__name__}: {str(exc)[:180]}"},
            )
            return

        append_json(MANIFEST, {"event": "attempt", "quiz_name": quiz_name})
        start = time.perf_counter()
        ok, status, error = False, 0, ""
        try:
            with self.client.post(
                url,
                data=data,
                timeout=TIMEOUT,
                name="create_quiz",
                catch_response=True,
            ) as resp:
                # Stop clock right after redirect chain completes, before HTML parsing.
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                status = resp.status_code
                ok = quiz_created_response(resp, quiz_name)
                if ok:
                    resp.success()
                else:
                    error = f"quiz_not_confirmed_in_course_view (status={status}, url={resp.url})"
                    resp.failure(error)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            error = f"{type(exc).__name__}: {str(exc)[:180]}"

        append_json(
            MANIFEST,
            {
                "event": "result",
                "quiz_name": quiz_name,
                "http_ok": ok,
                "status": status,
                "response_ms": round(elapsed_ms, 3),
                "error": error,
            },
        )
