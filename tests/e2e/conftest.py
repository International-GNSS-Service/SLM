"""
Browser tests run against ``live_server``, which serves requests from another
thread on its own connection - it cannot see data inside the per-module
transaction the rest of the suite uses. So here ``seed`` is rebuilt for every
test on a transactional database.

Run only these with ``just test -m e2e`` or skip them with ``-m "not e2e"``.
Chromium must be installed first: ``just install-browsers``.
"""

import os
from importlib.util import find_spec

import pytest
from django.urls import reverse

from tests.conftest import PASSWORD, build_seed

# pytest-playwright is not installable on every python version we support
if find_spec("playwright") is None:
    collect_ignore_glob = ["test_*.py"]

# Playwright's sync API runs an event loop in the main thread, which trips
# Django's async-unsafe guard when tests touch the ORM.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


def pytest_collection_modifyitems(items):
    for item in items:
        if "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(autouse=True)
def _restore_serialized_snapshot(django_db_setup):
    """See ``django_db_setup`` in tests/conftest.py."""
    from django.db import connections

    for alias, contents in django_db_setup.items():
        connections[alias]._test_serialized_contents = contents


@pytest.fixture
def seed(browser_context_args):
    # browser_context_args pulls in transactional_db with serialized rollback
    return build_seed()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {**browser_type_launch_args, "headless": True}


@pytest.fixture
def browser_context_args(
    browser_context_args, live_server, transactional_db, django_db_serialized_rollback
):
    # Depending on the db fixtures here means:
    #   1) browser contexts close *before* the database is flushed - otherwise
    #      open pages can hold locks that deadlock the flush.
    #   2) every browser test restores the data loaded by data migrations,
    #      which the transactional flush otherwise wipes.
    return {
        **browser_context_args,
        "base_url": live_server.url,
        "ignore_https_errors": True,
    }


@pytest.fixture
def logged_in_page(browser, browser_context_args):
    """Factory: ``logged_in_page(user)`` returns a page with an active session.

    The login goes through the real allauth form once, the storage state is
    captured, and the page handed to the test is from a fresh context built
    from that state.
    """
    contexts = []

    def make(user):
        login_ctx = browser.new_context(**browser_context_args)
        contexts.append(login_ctx)
        page = login_ctx.new_page()
        page.goto(reverse("account_login"))
        page.fill("input[name=login]", user.email)
        page.fill("input[name=password]", PASSWORD)
        page.locator("form [type=submit]").first.click()
        page.wait_for_load_state("networkidle")
        state = login_ctx.storage_state()

        ctx = browser.new_context(**browser_context_args, storage_state=state)
        contexts.append(ctx)
        return ctx.new_page()

    yield make
    for ctx in contexts:
        ctx.close()


@pytest.fixture
def console_errors(live_server):
    """Attach to a page to collect JS errors and 4xx/5xx responses.

    Only responses from the live server are checked so third party CDN
    hiccups do not cause failures. Usage::

        errors = console_errors(page)
        ...
        assert not errors
    """

    def attach(page):
        errors = []
        page.on(
            "console",
            lambda msg: errors.append(f"console: {msg.text}")
            if msg.type == "error"
            else None,
        )
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
        page.on(
            "response",
            lambda resp: errors.append(f"{resp.status}: {resp.url}")
            if resp.status >= 400 and resp.url.startswith(live_server.url)
            else None,
        )
        return errors

    return attach
