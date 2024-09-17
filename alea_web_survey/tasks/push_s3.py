"""
This module contains the push_cache function, which is responsible for pushing completed work to S3.
"""

# imports
import logging

# packages
import tqdm

# project
from alea_web_survey.storage.s3 import (
    DEFAULT_CACHE_PATH,
    DEFAULT_S3_BUCKET,
    S3_CLIENT,
    copy_object,
    get_completed_paths,
)

# logger set up with file output
LOGGER = logging.getLogger(__name__)


async def push_cache(remove_after: bool = False) -> bool:
    """
    Pushes completed work to S3, optionally removing the local cache after pushing.

    Work is pushed to S3 in the following manner:
    - Each completed target is pushed to S3.
    - If remove_after is True, the local cache is removed after pushing to S3.
    - If remove_after is True, empty parent paths are removed after pushing to S3.

    Args:
        remove_after (bool): Whether to remove the local cache after pushing to S3.

    Returns:
        bool: Whether the operation was successful.
    """
    try:
        prog_bar = tqdm.tqdm(desc="Pushing completed work to S3...")
        num_domains = 0
        num_paths = 0

        # parent paths to remove
        parent_paths = set()

        # iterate over tuples of completed targets
        for path_targets in get_completed_paths():
            # submit each target to the thread pool
            domain_name = path_targets[0].parts[-2]
            prog_bar.set_postfix(
                domain=domain_name,
                domains=num_domains,
                paths=num_paths,
            )

            # iterate over each path target
            for target_path in path_targets:
                copy_object(
                    source_path=target_path,
                    s3_client=S3_CLIENT,
                    dest_bucket=DEFAULT_S3_BUCKET,
                    dest_key=target_path.relative_to(DEFAULT_CACHE_PATH).as_posix(),
                    remove_after=remove_after,
                )
                num_paths += 1
            num_domains += 1
            prog_bar.update(1)

            # add the parent path to the set
            parent_paths.add(path_targets[0].parent)

        # update status to show that all tasks have been submitted
        prog_bar.set_postfix(
            domain="",
            domains=num_domains,
            paths=num_paths,
        )

        # clean up all empty parent paths
        if remove_after:
            prog_bar.set_description("Cleaning up parent paths...")
            for parent_path in parent_paths:
                try:
                    parent_path.rmdir()
                except Exception as e:  # pylint: disable=broad-except
                    LOGGER.error("Failed to remove parent path %s: %s", parent_path, e)

        return True
    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("Failed to push cache to S3: %s", e)
        return False
