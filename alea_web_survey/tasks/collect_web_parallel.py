"""
Web data collection task with parallel processing using semaphore and concurrent.futures.
"""

import asyncio
import logging
from typing import Optional, Tuple

import tqdm

from alea_web_survey.collection.dns.domain_generator import DomainGenerator
from alea_web_survey.collection.http.web_client import WebResourceCollector
from alea_web_survey.tasks.collect_web import size_to_str

LOGGER = logging.getLogger(__name__)


async def collect_domain(domain: str) -> Tuple[int, int, int]:
    """
    Collect resources for a single domain.

    Args:
        domain: The domain to collect resources from.

    Returns:
        A tuple of (number of pages, number of bytes, 1 if successful else 0).
    """
    # create a new web resource collector locally
    web_collector = WebResourceCollector()

    num_pages = 0
    num_bytes = 0
    try:
        async for page in web_collector.get_resources(domain):
            num_pages += 1
            num_bytes += page.size
        return num_pages, num_bytes, 1
    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("Failed to retrieve site %s: %s", domain, e)
        return 0, 0, 0


def collect_domain_sync(domain: str) -> Tuple[int, int, int]:
    """
    Collect resources for a single domain.

    Args:
        domain: The domain to collect resources from.

    Returns:
        A tuple of (number of pages, number of bytes, 1 if successful else 0).
    """
    return asyncio.run(collect_domain(domain))


async def collect_sites_parallel(
    max_sites: Optional[int] = None, max_workers: int = 8
) -> bool:
    """
    Retrieve a number of websites in parallel and save them to the filesystem.

    Args:
        max_sites: The max number of sites to retrieve.
        max_workers: The maximum number of worker threads.

    Returns:
        True if successful, False otherwise
    """
    try:
        domain_generator = DomainGenerator()

        # if max_sites is None, set it to 1M
        max_sites = max_sites or 1_000_000
        num_sites = 0

        # create the progress bar
        prog_bar = tqdm.tqdm(total=max_sites, desc="Retrieving sites...")

        while True:
            # stop when requested
            if num_sites >= max_sites:
                break

            # get a batch of domains
            domains_to_process = [
                domain_generator.generate().rstrip(".") for _ in range(max_workers * 4)
            ]

            # create the semaphore
            semaphore = asyncio.Semaphore(max_workers)

            # create the tasks
            tasks = [
                asyncio.ensure_future(collect_domain(domain))
                for domain in domains_to_process
            ]

            # run the tasks
            for task in tasks:
                async with semaphore:
                    await task
                    num_pages, num_bytes, success = task.result()
                    if success:
                        num_sites += 1
                        prog_bar.update(1)
                        prog_bar.set_postfix(
                            num_sites=num_sites,
                            num_pages=num_pages,
                            num_bytes=size_to_str(num_bytes),
                        )

        return True
    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("Failed to retrieve sites: %s", e)
        return False
