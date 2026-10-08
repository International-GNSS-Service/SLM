"""
Playwright browser smoke tests for the core editor workflows.
"""

import re

import pytest
from django.urls import reverse
from playwright.sync_api import expect

from slm.defines import SiteFileUploadStatus, SiteLogStatus
from slm.models import SiteFileUpload
from tests.conftest import PASSWORD, make_updated
from tests.resources import JPLM_JPG


def goto(page, name, *args):
    page.goto(reverse(name, args=args))
    page.wait_for_load_state("networkidle")


def test_login_logout(page, editor):
    goto(page, "slm:home")
    # anonymous users are bounced to the login form
    expect(page).to_have_url(re.compile(r"/accounts/login/"))

    page.fill("input[name=login]", editor.email)
    page.fill("input[name=password]", "wrong")
    page.locator("form [type=submit]").first.click()
    expect(page.locator("form")).to_contain_text(
        re.compile("not correct|incorrect", re.I)
    )

    page.fill("input[name=password]", PASSWORD)
    page.locator("form [type=submit]").first.click()
    page.wait_for_load_state("networkidle")
    expect(page).not_to_have_url(re.compile(r"/accounts/login/"))
    expect(page.locator("nav")).to_contain_text(editor.last_name)

    goto(page, "account_logout")
    page.locator("form [type=submit]").first.click()
    page.wait_for_load_state("networkidle")
    goto(page, "slm:home")
    expect(page).to_have_url(re.compile(r"/accounts/login/"))


@pytest.mark.xfail(
    strict=True,
    reason='BUG: the login page throws "Cannot read properties of undefined '
    "(reading 'trigger')\" from a Bootstrap tooltip/popover initialised "
    "without a valid config.",
)
def test_login_page_has_no_errors(page, console_errors):
    errors = console_errors(page)
    goto(page, "account_login")
    assert not errors, errors


def test_station_list_and_search(
    logged_in_page, editor, published_site, proposed_site, console_errors
):
    page = logged_in_page(editor)
    errors = console_errors(page)
    goto(page, "slm:home")
    stations = page.locator("#slm-station-list")
    expect(stations).to_contain_text(published_site.name)
    expect(stations).to_contain_text(proposed_site.name)

    page.fill("#station-search", "AAA6")
    expect(stations).not_to_contain_text(proposed_site.name)
    expect(stations).to_contain_text(published_site.name)

    stations.get_by_text(published_site.name).first.click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(rf"/edit/{published_site.name}"))
    assert not errors, errors


def test_edit_section_and_save(logged_in_page, editor, published_site, console_errors):
    page = logged_in_page(editor)
    errors = console_errors(page)
    goto(page, "slm:edit", published_site.name, "identification")

    form = page.locator("#site-identification")
    unpublished = form.locator(".alert.slm-form-unpublished")
    expect(unpublished).to_be_hidden()

    # NOTE: published_diff() ignores changes to/from empty values, so edit a
    # field that already has a published value or the banner never shows
    form.locator("[name=site_name]").fill("Frogtown North")
    with page.expect_response(
        lambda r: "/api/edit/siteidentification/" in r.url
    ) as resp:
        form.locator("button[name=save]").click()
    assert resp.value.ok, resp.value.text()
    expect(unpublished).to_be_visible()

    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.UPDATED
    assert published_site.siteidentification_set.head().site_name == "Frogtown North"
    assert not errors, errors


def test_upload_image(logged_in_page, editor, published_site, console_errors):
    page = logged_in_page(editor)
    errors = console_errors(page)
    goto(page, "slm:upload", published_site.name)

    with page.expect_response(
        lambda r: f"/api/edit/files/{published_site.name}" in r.url
        and r.request.method == "POST"
    ) as resp:
        page.locator("input.dz-hidden-input").set_input_files(str(JPLM_JPG))
    assert resp.value.ok, resp.value.text()

    upload = SiteFileUpload.objects.get(site=published_site, name=JPLM_JPG.name)
    assert upload.status == SiteFileUploadStatus.UNPUBLISHED
    # a single upload redirects to that file's detail page
    page.wait_for_url(re.compile(rf"/upload/{published_site.name}/{upload.pk}$"))
    expect(page.locator("body")).to_contain_text(JPLM_JPG.name)
    assert not errors, errors


def test_moderator_publish(
    logged_in_page, editor, moderator, published_site, console_errors
):
    make_updated(published_site, editor)
    page = logged_in_page(moderator)
    errors = console_errors(page)
    goto(page, "slm:review", published_site.name)

    page.once("dialog", lambda dialog: dialog.accept())
    with page.expect_response(
        lambda r: "/api/edit/stations/" in r.url
        and r.request.method in {"PATCH", "PUT", "POST"}
    ) as resp:
        page.locator("button[name=publish]").first.click()
    assert resp.value.ok, resp.value.text()

    published_site.refresh_from_db()
    assert published_site.status == SiteLogStatus.PUBLISHED
    assert not errors, errors


def test_download_site_log(logged_in_page, editor, published_site, console_errors):
    page = logged_in_page(editor)
    errors = console_errors(page)
    goto(page, "slm:download", published_site.name)
    link = page.locator(
        f'a[href^="/api/edit/download/{published_site.name}.log"]'
    ).first
    with page.expect_download() as download:
        link.click()
    assert download.value.suggested_filename.startswith(published_site.name.lower())
    assert published_site.name in open(download.value.path()).read().upper()
    assert not errors, errors


def test_map_page(logged_in_page, editor, published_site, console_errors):
    page = logged_in_page(editor)
    errors = console_errors(page)
    goto(page, "slm_map:map")
    # no MapBox key is configured in tests - the page should say so cleanly
    expect(page.locator("body")).to_contain_text("MapBox")
    assert not errors, errors


@pytest.mark.parametrize(
    "name,station",
    [
        ("slm:home", False),
        ("slm:about", False),
        ("slm:help", False),
        ("slm:alerts", False),
        ("slm:profile", False),
        ("slm:user_activity", False),
        ("slm:new_site", False),
        ("slm:edit", True),
        ("slm:alerts", True),
        ("slm:upload", True),
        ("slm:download", True),
        ("slm:review", True),
        ("slm:log", True),
    ],
)
def test_pages_have_no_errors(
    logged_in_page, editor, published_site, console_errors, name, station
):
    page = logged_in_page(editor)
    errors = console_errors(page)
    goto(page, name, *([published_site.name] if station else []))
    assert not errors, errors
