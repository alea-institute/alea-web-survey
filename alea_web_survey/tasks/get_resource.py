"""
Output a resource, either by checking the local cache or fetching it from S3.
"""

# imports
import base64
import io
import json
import lzma

from alea_web_survey.models.web_resource import WebResource
from alea_web_survey.storage.s3 import DEFAULT_CACHE_PATH, DEFAULT_S3_BUCKET, S3_CLIENT

# packages

# project


def get_resource(url: str) -> bytes:
    """
    Get a resource, either by checking the local cache or fetching it from S3.

    Args:
        url (str): The URL of the resource to fetch.

    Returns:
        bytes: The content of the resource.
    """
    resource_path = WebResource.get_cache_path(url)
    if resource_path.exists():
        # load the resource from the cache
        resource_data = json.loads(resource_path.read_text())
    else:
        # the s3 key is the relative portion of the file path after the cache path
        s3_key = resource_path.relative_to(DEFAULT_CACHE_PATH).as_posix()

        # use boto3 client to fetch the resource from S3
        resource_buffer = io.BytesIO()
        S3_CLIENT.download_fileobj(
            Bucket=DEFAULT_S3_BUCKET,
            Key=s3_key,
            Fileobj=resource_buffer,
        )

        # decompress the resource
        resource_buffer.seek(0)
        resource_data = json.loads(resource_buffer.read())

    return lzma.decompress(base64.b64decode(resource_data["content"]))
