# imports
import base64
import datetime
import json
import lzma
from pathlib import Path

# package imports
import pytest

from alea_web_survey.models.web_resource import WebResource, utc_now


@pytest.fixture
def sample_web_resource():
    return WebResource(
        url="https://example.com",
        status=200,
        ip="123.123.123.123",
        hash="123456",
        size=100,
        content=b"Sample content",
        content_type="text/html",
        date_retrieved=utc_now(),
        date_modified=None,
    )


def test_web_resource_creation(sample_web_resource):
    assert isinstance(sample_web_resource, WebResource)
    assert sample_web_resource.url == "https://example.com"
    assert sample_web_resource.hash == "123456"
    assert sample_web_resource.size == 100
    assert sample_web_resource.content == b"Sample content"
    assert sample_web_resource.content_type == "text/html"
    assert isinstance(sample_web_resource.date_retrieved, datetime.datetime)
    assert sample_web_resource.date_modified is None


def test_web_resource_save_and_load(tmp_path, sample_web_resource):
    # Save the web resource
    file_path = tmp_path / "test_resource.json"
    sample_web_resource.save(file_path)

    # Load the web resource
    loaded_resource = WebResource.from_file(file_path)

    # Compare original and loaded resource
    assert loaded_resource.url == sample_web_resource.url
    assert loaded_resource.hash == sample_web_resource.hash
    assert loaded_resource.size == sample_web_resource.size
    assert loaded_resource.content == sample_web_resource.content
    assert loaded_resource.content_type == sample_web_resource.content_type
    assert loaded_resource.date_retrieved == sample_web_resource.date_retrieved
    assert loaded_resource.date_modified == sample_web_resource.date_modified


def test_utc_now():
    now = utc_now()
    assert isinstance(now, datetime.datetime)
    assert now.tzinfo == datetime.timezone.utc


def test_web_resource_with_date_modified(sample_web_resource):
    date_modified = utc_now()
    sample_web_resource.date_modified = date_modified
    assert sample_web_resource.date_modified == date_modified

    # Test saving and loading with date_modified
    file_path = Path("test_resource_with_date.json")
    sample_web_resource.save(file_path)
    loaded_resource = WebResource.from_file(file_path)
    assert loaded_resource.date_modified == date_modified

    # Clean up
    file_path.unlink()


def test_web_resource_content_compression(sample_web_resource, tmp_path):
    file_path = tmp_path / "compressed_resource.json"
    sample_web_resource.save(file_path)

    with file_path.open("rb") as f:
        saved_data = json.load(f)

    # Check if content is base64 encoded
    decoded_content = base64.b64decode(saved_data["content"])
    # Check if content is compressed
    decompressed_content = lzma.decompress(decoded_content)

    assert decompressed_content == sample_web_resource.content
