"""
Web data collection task.
"""

# imports
import logging
from typing import Optional

# packages
import tqdm

# project
from alea_web_survey.collection.dns.domain_generator import DomainGenerator
from alea_web_survey.collection.http.web_client import WebResourceCollector

# set up logging
LOGGER = logging.getLogger(__name__)


def size_to_str(num_bytes: int) -> str:
    """
    Convert bytes to a human-readable string.

    Args:
        num_bytes: The number of bytes.

    Returns:
        The string.
    """
    # convert to float
    byte_result = float(num_bytes)

    # iterate through units in order of magnitude
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(byte_result) < 1024.0:
            return f"{byte_result:3.1f} {unit}"
        byte_result /= 1024.0
    return f"{byte_result:.1f} YB"


async def collect_sites(max_sites: Optional[int] = None) -> bool:
    """
    Retrieve a number of websites and save them to the filesystem.

    Args:
        max_sites: The max number of sites to retrieve.

    Returns:
        True if successful, False otherwise
    """
    try:
        # create the web resource collector
        web_collector = WebResourceCollector()

        # create the domain generator
        domain_generator = DomainGenerator()

        # get the domain list
        num_sites = 0
        num_pages = 0
        num_bytes = 0
        prog_bar = tqdm.tqdm(total=max_sites, desc="Retrieving sites...")
        while True:
            try:
                # stop when requested
                if max_sites is not None and num_sites >= max_sites:
                    break

                # get a domain
                domain = domain_generator.generate().rstrip(".")
                if domain is None:
                    continue

                # set status
                prog_bar.set_postfix(
                    domain=domain,
                    num_sites=num_sites,
                    num_pages=num_pages,
                    num_bytes=size_to_str(num_bytes),
                )

                # get the web resource
                async for page in web_collector.get_resources(domain):
                    # increment the count
                    num_pages += 1
                    num_bytes += page.size
                    prog_bar.set_postfix(
                        domain=domain,
                        num_sites=num_sites,
                        num_pages=num_pages,
                        num_bytes=size_to_str(num_bytes),
                    )

                # increment the count
                num_sites += 1
                prog_bar.update(1)
            except Exception as e:  # pylint: disable=broad-except
                LOGGER.error("Failed to retrieve site: %s", e)
                continue
        prog_bar.close()
        return True
    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("Failed to collect sites: %s", e)
        return False
