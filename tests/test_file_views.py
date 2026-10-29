"""
Tests for the glob backed file system listings in slm.file_views.

The glob pattern is deployment configuration, never request data. These tests
pin down the trust boundary: every listed or served file must live under the
non-wildcard root of the configured pattern, even when symlinks point elsewhere.
"""

import json
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.test import RequestFactory

from slm.file_views.config import FileSystemDirectory, Listing
from slm.file_views.views import FileSystemView, fnmatch_to_regex


@pytest.fixture
def tree(tmp_path):
    """
    tmp_path/
        secret.txt             <- outside the served root
        pub/
            a.txt
            b.log
            inside_link.txt    -> pub/a.txt
            escape.txt         -> ../secret.txt
            sub/
                c.txt
    """
    root = tmp_path / "pub"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("a")
    (root / "b.log").write_text("bb")
    (root / "sub" / "c.txt").write_text("c")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    (root / "inside_link.txt").symlink_to(root / "a.txt")
    (root / "escape.txt").symlink_to(outside)
    return root


@pytest.mark.parametrize(
    "pattern, root",
    [
        ("/data/pub/**/*.txt", "/data/pub"),
        ("/data/pub/*", "/data/pub"),
        ("/data/pub/file[0-9].txt", "/data/pub"),
        ("/data/pub/file?.txt", "/data/pub"),
        ("/data/pub", "/data/pub"),
        ("/data/pub/", "/data/pub"),
        ("*.txt", "."),
    ],
)
def test_glob_root(pattern, root):
    assert Listing.glob_root(pattern) == Path(root)


def test_from_glob_none_yields_nothing():
    assert list(Listing.from_glob(None)) == []
    assert list(Listing.from_glob("")) == []


def test_from_glob_lists_files_under_root(tree):
    listings = {
        listing.display: listing for listing in Listing.from_glob(str(tree / "*"))
    }
    assert set(listings) == {"a.txt", "b.log", "inside_link.txt", "sub"}
    assert listings["sub"].is_dir is True
    assert listings["sub"].size is None
    assert listings["b.log"].is_dir is False
    assert listings["b.log"].size == 2
    assert listings["b.log"].modified is not None
    assert listings["b.log"].on_disk == tree / "b.log"


def test_from_glob_excludes_symlinks_that_escape_the_root(tree):
    names = {listing.display for listing in Listing.from_glob(str(tree / "*.txt"))}
    assert "escape.txt" not in names
    assert names == {"a.txt", "inside_link.txt"}


def test_from_glob_applies_name_filter(tree):
    names = {
        listing.display
        for listing in Listing.from_glob(
            str(tree / "*"), filter=lambda name: name.endswith(".log")
        )
    }
    assert names == {"b.log"}


def test_relative_glob_is_rejected_at_url_build_time():
    with pytest.raises(ImproperlyConfigured):
        FileSystemDirectory(glob="*.txt").urls(Path("/files/pub"))


def test_absolute_glob_builds_listing_and_file_urls(tree):
    urls = FileSystemDirectory(glob=str(tree / "*")).urls(Path("/files/pub"))
    assert [str(url.pattern) for url in urls] == [
        "files/pub/",
        "files/pub/<str:filename>",
    ]


@pytest.mark.parametrize(
    "pattern, regex",
    [
        ("abc*", "abc.*"),
        ("sfo*", "sfo.*"),
        ("ZIMM*", "ZIMM.*"),
        ("a?c", "a.c"),
        ("*Z", ".*Z"),
        ("log[0-9].txt", r"log[0-9]\.txt"),
    ],
)
def test_fnmatch_to_regex(pattern, regex):
    assert fnmatch_to_regex(pattern) == regex


def _get(path, **view_kwargs):
    request = RequestFactory().get(path)
    return FileSystemView.as_view()(request, **view_kwargs)


def _names(response):
    assert response.status_code == 200
    return {entry["name"] for entry in json.loads(response.content)}


def test_view_lists_only_contained_files(tree):
    response = _get("/files/pub/?json", glob=str(tree / "*.txt"), download=False)
    assert _names(response) == {"a.txt", "inside_link.txt"}


def test_view_lists_everything_without_match_filter(tree):
    response = _get("/files/pub/?json", glob=str(tree / "*"), download=False)
    assert _names(response) == {"a.txt", "b.log", "inside_link.txt", "sub"}


def test_view_match_query_filters_names(tree):
    response = _get(
        "/files/pub/?json&match=b*&match=sub", glob=str(tree / "*"), download=False
    )
    assert _names(response) == {"b.log", "sub"}


def test_view_serves_a_listed_file(tree):
    response = _get(
        "/files/pub/a.txt", filename="a.txt", glob=str(tree / "*.txt"), download=False
    )
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"a"
    assert response["Content-Type"].startswith("text/plain")


def test_view_serves_as_attachment_when_download_is_set(tree):
    response = _get(
        "/files/pub/a.txt", filename="a.txt", glob=str(tree / "*.txt"), download=True
    )
    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment")


@pytest.mark.parametrize("filename", ["escape.txt", "secret.txt", "../secret.txt"])
def test_view_refuses_files_outside_the_root(tree, filename):
    with pytest.raises(Http404):
        _get(
            f"/files/pub/{filename}",
            filename=filename,
            glob=str(tree / "*.txt"),
            download=False,
        )


def test_view_refuses_files_not_matched_by_the_glob(tree):
    with pytest.raises(Http404):
        _get(
            "/files/pub/b.log",
            filename="b.log",
            glob=str(tree / "*.txt"),
            download=False,
        )
