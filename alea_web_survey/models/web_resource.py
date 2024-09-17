"""
Web resource model, designed to handle resources like web pages, robots.txt files, and
any other HTTP(S)-accessible resources.

This model is designed to provide integrated filesystem caching functionality.
"""

# future imports
from __future__ import annotations

# standard library
import base64
import datetime
import hashlib
import json
import lzma
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

# packages
from pydantic import BaseModel, Field

# project
from alea_web_survey.logger import LOGGER

# set default cache path
CACHE_PATH = Path().home() / ".alea" / "web-survey" / "cache"


def utc_now() -> datetime.datetime:
    """
    Get the current UTC time.

    :return: The current UTC time.
    """
    return datetime.datetime.now(tz=datetime.timezone.utc)


class WebResource(BaseModel):
    """
    Web resource model, designed to handle resources like web pages, robots.txt files, and
    any other HTTP(S)-accessible resources.

    This model is designed to provide integrated filesystem caching functionality.
    """

    url: str
    ip: str
    status: int
    hash: str
    size: int
    content: bytes
    content_type: str
    headers: Dict[str, Any] = Field(default_factory=dict)
    date_retrieved: datetime.datetime = Field(default_factory=utc_now)
    date_modified: Optional[datetime.datetime] = None

    @classmethod
    def from_file(cls, path: Path) -> WebResource:
        """
        Load a web resource from a file on disk.

        :param path: The path to the file to load.
        :return: The loaded web resource.
        """
        with path.open("rb") as input_file:
            # load raw data
            file_data = json.load(input_file)

            # decode base64-encoded content
            content = base64.b64decode(file_data["content"])

            # decompress content
            content = lzma.decompress(content)

            # create web resource
            return cls(
                url=file_data["url"],
                ip=file_data["ip"],
                status=file_data["status"],
                hash=file_data["hash"],
                size=file_data["size"],
                content=content,
                content_type=file_data["content_type"],
                headers=file_data["headers"],
                date_retrieved=datetime.datetime.fromisoformat(
                    file_data["date_retrieved"]
                ),
                date_modified=datetime.datetime.fromisoformat(
                    file_data["date_modified"]
                )
                if file_data["date_modified"]
                else None,
            )

    def save(self, path: Path) -> None:
        """
        Save a web resource to a file on disk.

        :param path: The path to the file to save.
        """
        # create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # compress content
        content = lzma.compress(self.content)

        # encode content as base64
        content = base64.b64encode(content)

        # create file data
        # pylint: disable=no-member
        file_data = {
            "url": self.url,
            "ip": self.ip,
            "status": self.status,
            "hash": self.hash,
            "size": self.size,
            "content": content.decode("utf-8"),
            "content_type": self.content_type,
            "headers": self.headers,
            "date_retrieved": self.date_retrieved.isoformat(),
            "date_modified": self.date_modified.isoformat()
            if self.date_modified
            else None,
        }

        # write file data
        with path.open("wt", encoding="utf-8") as output_file:
            output_file.write(json.dumps(file_data))

    @staticmethod
    def get_cache_path(url: str, cache_path: Optional[Path] = None) -> Path:
        """
        Get the cache path based on the URL.

        Args:
            url (str): url for WebResource
            cache_path (Path): base path for fs storage

        Returns:
             Path to cached object if it exists.
        """
        if cache_path is None:
            cache_path = CACHE_PATH

        # Parse the URL components
        parsed_url = urllib.parse.urlparse(url)

        # Extract domain and safely encode it
        domain = parsed_url.netloc

        # Extract path and safely encode it
        path = parsed_url.path
        path_hash = hashlib.blake2b(path.encode("utf-8")).hexdigest()

        # Set the full cache directory and file path
        return cache_path / domain / f"{path_hash}.json"

    def save_to_cache(self, cache_path: Optional[Path] = None):
        """
        Save the document to the cache based on the URL.

        The file will be saved under a directory named after the domain, and a file named
        based on the URL path. If the resource is at the root (e.g. "/"), the file will be
        saved as ".index".

        :param cache_path: Base path to set relative from (optional).
        """
        # Save the resource to the cache
        cache_file = self.get_cache_path(self.url, cache_path)
        self.save(cache_file)
        LOGGER.debug("Saved resource %s to cache at %s", self.url, cache_file)

    @classmethod
    def load_from_cache(
        cls, url: str, cache_path: Optional[Path] = None
    ) -> Optional[WebResource]:
        """
        Load the document from the cache based on the URL.

        :param url: The URL of the web resource to load.
        :param cache_path: Base path to load the cache from (optional).
        :return: The loaded web resource, or None if not found.
        """
        # get cache path
        cache_file = cls.get_cache_path(url, cache_path)

        # Check if the cache file exists
        if not cache_file.exists():
            LOGGER.debug("Cache file not found for URL %s at %s", url, cache_file)
            return None

        # return if it does
        return cls.from_file(cache_file)
