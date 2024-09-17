"""
S3 storage utilities for the web-survey collector.
"""

# imports
import concurrent.futures
import logging
import multiprocessing
from pathlib import Path
from typing import Any, Generator, Tuple

# packages
import boto3
import botocore.config

# project
from alea_web_survey.config import CONFIG

# logger set up with file output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("push_data.log"),
        logging.StreamHandler(),
    ],
)
LOGGER = logging.getLogger(__name__)


# path constants
DEFAULT_CACHE_PATH = Path().home() / ".alea" / "web-survey" / "cache"
DEFAULT_S3_BUCKET = CONFIG.s3_bucket

# s3 constants
DEFAULT_S3_THREADS = multiprocessing.cpu_count()
DEFAULT_S3_POOL_SIZE = DEFAULT_S3_THREADS
DEFAULT_S3_CONNECT_TIMEOUT = 30
DEFAULT_S3_READ_TIMEOUT = 30
DEFAULT_S3_MAX_RETRIES = 10


# s3 config
BOTO_S3_CONFIG = botocore.config.Config(
    connect_timeout=DEFAULT_S3_CONNECT_TIMEOUT,
    read_timeout=DEFAULT_S3_READ_TIMEOUT,
    retries={
        "max_attempts": DEFAULT_S3_MAX_RETRIES,
        "mode": "standard",
    },
    max_pool_connections=DEFAULT_S3_POOL_SIZE,
)

# create shared client
S3_CLIENT = boto3.client("s3", config=BOTO_S3_CONFIG)

# create an S3 thread pool
S3_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(DEFAULT_S3_THREADS)


def copy_object(
    source_path: Path,
    s3_client: Any,
    dest_bucket: str,
    dest_key: str,
    remove_after: bool = False,
) -> None:
    """
    Copy a local object to an S3 bucket.

    Args:
        source_path (Path): Path to the local object
        s3_client (Any): S3 client
        dest_bucket (str): Destination S3 bucket
        dest_key (str): Destination S3 key
        remove_after (bool): Whether to remove the local object after copying

    Returns:
        None
    """
    try:
        # get object into memory
        source_data = source_path.read_bytes()

        # put object into new bucket
        s3_client.put_object(
            Bucket=dest_bucket,
            Key=dest_key,
            Body=source_data,
        )

        # remove local object if requested
        if remove_after:
            LOGGER.info(
                "Successfully copy-deleted %s to %s/%s",
                source_path,
                dest_bucket,
                dest_key,
            )
            source_path.unlink()
        else:
            LOGGER.info(
                "Successfully copied %s to %s/%s",
                source_path,
                dest_bucket,
                dest_key,
            )

    except Exception as e:
        # log failure
        LOGGER.error(
            "Failed to copy %s to %s/%s: %s", source_path, dest_bucket, dest_key, e
        )
        raise e


def get_completed_paths() -> Generator[Tuple[Path, ...], None, None]:
    """
    Iterate through the data directory to identify any paths that contain a
    content.json file, which indicates that the collector has completed.

    Returns:
        Generator[Tuple[Path, ...], None, None]: Generator of paths within each completed directory.
    """
    # iterate through the data directory
    for domain_path in DEFAULT_CACHE_PATH.iterdir():
        # check if /content.json exists
        if (domain_path / "content.json").exists():
            yield tuple(domain_path.iterdir())
