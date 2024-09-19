"""
httpx web resource collector module.
"""

# imports
import asyncio
import hashlib
import json
import logging
import urllib.parse
import urllib.robotparser
from functools import cache
from typing import AsyncIterator, List, Optional, Tuple

# packages
import dateutil.parser
import dns.resolver
import httpx
from playwright.async_api import async_playwright

# project imports
from alea_web_survey.config import CONFIG
from alea_web_survey.models.web_resource import WebResource

# Set up logging
LOGGER = logging.getLogger(__name__)

# module default constants
DEFAULT_MAX_CONNECTIONS = CONFIG.http_pool_size
DEFAULT_MAX_KEEPALIVE = CONFIG.http_keep_alive
DEFAULT_NETWORK_TIMEOUT = CONFIG.http_network_timeout
DEFAULT_PLAYWRIGHT_TIMEOUT = CONFIG.playwright_timeout
DEFAULT_USER_AGENT = CONFIG.user_agent
DEFAULT_PATH_LIST = CONFIG.path_list
DEFAULT_MAX_SITEMAPS = 10

# set up default timeout config
DEFAULT_TIMEOUT_CONFIG = httpx.Timeout(
    connect=CONFIG.http_connect_timeout,
    read=CONFIG.http_read_timeout,
    write=CONFIG.http_write_timeout,
    pool=CONFIG.http_connect_timeout,
)


class WebResourceCollector:
    """
    Class to efficiently retrieve web resources from a server.
    """

    def __init__(
        self,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        max_keepalive: int = DEFAULT_MAX_KEEPALIVE,
    ):
        """
        Initialize the WebResourceCollector.

        Args:
            max_connections: The maximum number of connections to open.
            max_keepalive: The maximum number of keepalive connections to maintain.

        Returns:
            None
        """
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive

    @staticmethod
    @cache
    async def check_host(domain: str) -> Optional[Tuple[str, str]]:
        """
        Check if the host is live by attempting to connect to port 443 (HTTPS), then port 80 (HTTP).

        Args:
            domain: The domain to check.

        Returns:
            Tuple with the scheme and IPv4/IPv6 address of the host, or None if the host is not live.
        """
        # Resolve domain to IP address
        try:
            ip_address = dns.resolver.resolve(
                domain, "A", lifetime=DEFAULT_NETWORK_TIMEOUT
            )[0].address
            # LOGGER.debug(f"Resolved {domain} to {ip_address}.")
            LOGGER.debug("Resolved %s to %s.", domain, ip_address)
        except Exception as e:  # pylint: disable=broad-except
            # LOGGER.error(f"Failed to resolve {domain}: {e}")
            LOGGER.error("Failed to resolve %s: %s", domain, e)
            return None

        # Check ports 443 (https) and 80 (http)
        for port, scheme in [(443, "https"), (80, "http")]:
            try:
                # make sure to use a timeout here
                conn_future = asyncio.open_connection(ip_address, port)
                _, writer = await asyncio.wait_for(
                    conn_future, timeout=DEFAULT_NETWORK_TIMEOUT
                )
                writer.close()
                await writer.wait_closed()
                LOGGER.debug(
                    "Host %s (%s) is live on port %d (%s).",
                    domain,
                    ip_address,
                    port,
                    scheme,
                )
                return scheme, str(ip_address)
            except Exception as e:  # pylint: disable=broad-except
                LOGGER.debug(
                    "Host %s (%s) not reachable on port %d: %s",
                    domain,
                    ip_address,
                    port,
                    e,
                )

        LOGGER.error("Host %s (%s) is not live on ports 443 or 80.", domain, ip_address)
        return None

    @staticmethod
    @cache
    def requires_playwright(content: bytes) -> bool:
        """
        Check if the content requires Playwright to render.

        Args:
            content: The content to check.

        Returns:
            True if the content requires Playwright, False otherwise.
        """
        # check for a noscript tag with javascript contained within
        lower_content = content.lower()
        p0 = lower_content.find(b"<noscript>")
        if p0 == -1:
            return False

        # handle case where noscript tag is found or somehow not
        p1 = lower_content.find(b"</noscript>", p0)
        if p1 == -1:
            p1 = min(p0 + 256, len(lower_content))

        return b"javascript" in lower_content[p0:p1]

    @staticmethod
    @cache
    async def fetch_content_playwright(url: str) -> bytes:
        """
        Fetch a resource using Playwright and return a WebResource object.

        Args:
            url: The URL of the resource to fetch.

        Returns:
            A WebResource object or None if the resource could not be fetched.
        """
        # log it
        LOGGER.info("Fetching %s with Playwright...", url)

        # retrieve the page
        async with async_playwright() as p:
            # launch browser and create a new page
            browser = await p.chromium.launch(headless=True)

            # create a new page and wait for it to load
            try:
                page = await browser.new_page()
                LOGGER.info("Fetching page...")
                await page.goto(url, timeout=DEFAULT_PLAYWRIGHT_TIMEOUT)

                # wait for the page to finish rendering
                LOGGER.info("Waiting for page to load...")
                await page.wait_for_load_state(
                    "networkidle", timeout=DEFAULT_PLAYWRIGHT_TIMEOUT
                )

                # get the content
                LOGGER.info("Getting page content...")
                content = await page.content()
            except Exception as e:  # pylint: disable=broad-except
                LOGGER.error("Failed to fetch %s with Playwright: %s", url, e)
                content = ""
            finally:
                await browser.close()

        return content.encode("utf-8")

    @staticmethod
    @cache
    async def fetch_resource(
        client: httpx.AsyncClient, url: str, ip_address: Optional[str] = None
    ) -> Optional[WebResource]:
        """
        Fetch a resource and return a WebResource object.

        Args:
            client: The httpx.AsyncClient object to use for fetching.
            url: The URL of the resource to fetch.
            ip_address: The IP address of the server, if known.

        Returns:
            A WebResource object or None if the resource could not be fetched.
        """
        # check if the resource is available in cache
        cached_resource = WebResource.load_from_cache(url)
        if cached_resource:
            return cached_resource

        try:
            response = await client.get(url, follow_redirects=True)

            # get best IP
            try:
                response_ip, _ = response.extensions["network_stream"].get_extra_info(
                    "server_addr"
                )
            except Exception:  # pylint: disable=broad-except
                response_ip = ip_address or ""

            # get the content
            content = response.content

            # init headers and scan case-insensitively
            content_type = "text/plain"
            last_modified = None
            for key, value in response.headers.items():
                if key.lower() == "content-type":
                    content_type = value
                elif key.lower() == "last-modified":
                    try:
                        last_modified = dateutil.parser.parse(value)
                    except Exception as e:  # pylint: disable=broad-except
                        LOGGER.error("Failed to parse last modified date: %s", e)

            # check if the content requires Playwright and fetch it
            if WebResourceCollector.requires_playwright(
                content
            ) and response.status_code in (200, 301):
                content = await WebResourceCollector.fetch_content_playwright(url)

            # Compute BLAKE2b hash
            hash_value = hashlib.blake2b(content).hexdigest()

            # Create WebResource object
            web_resource = WebResource(
                url=url,
                ip=response_ip,
                status=response.status_code,
                hash=hash_value,
                size=len(content),
                content=content,
                content_type=content_type,
                date_modified=last_modified,
            )

            # save to cache
            web_resource.save_to_cache()

            # return
            return web_resource
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.error("Failed to fetch %s: %s", url, e)
            return None

    @staticmethod
    def save_domain_content(pages: List[WebResource]) -> None:
        """
        Save the local domain content data.

        Args:
            pages: The list of WebResource objects to save.

        Returns:
            None
        """
        # skip if empty
        if len(pages) == 0:
            return

        # get the path, which is the cache path + content.json
        cache_path = WebResource.get_cache_path(pages[0].url).parent
        content_path = cache_path / "content.json"

        # create the list of basic page data, excluding the content and headers
        page_data = [
            {
                "url": page.url,
                "status": page.status,
                "hash": page.hash,
                "size": page.size,
                "content_type": page.content_type,
                "ip_address": page.ip,
                "date_retrieved": page.date_retrieved.isoformat(),
                "date_modified": page.date_modified.isoformat()
                if page.date_modified
                else None,
            }
            for page in pages
        ]

        # save the content
        content_path.write_text(json.dumps(page_data, indent=2))

    async def get_resources(
        self, domain: str, paths: Optional[List[str]] = None
    ) -> AsyncIterator[WebResource]:
        """
        Retrieve a list of resources from a domain.

        Args:
            domain: The domain to retrieve resources from.
            paths: A list of paths to retrieve.

        Returns:
            An async iterator of WebResource objects.
        """
        # set default delay
        domain_delay = CONFIG.http_delay

        # set default paths if none are provided
        if paths is None:
            paths = DEFAULT_PATH_LIST

        # check if host is live
        LOGGER.info("Checking if host %s is live...", domain)
        host_result = await self.check_host(domain)
        if not host_result:
            LOGGER.error("Host %s is not live.", domain)
            return

        # unpack if host is live
        scheme, ip_address = host_result

        # set base URL for client
        base_url = f"{scheme}://{domain}"

        # set up httpx client limits
        limits = httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive,
        )

        # store pages to save content index
        pages = []

        # fetch resources in client context
        async with httpx.AsyncClient(
            http1=True,
            verify=False,
            limits=limits,
            timeout=DEFAULT_TIMEOUT_CONFIG,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        ) as client:
            # push tasks to fetch resources
            LOGGER.info("Fetching resources from %s...", domain)

            # set domain paths
            domain_paths: list[str] = list(paths)

            # always start with robots.txt
            robots_resource = await self.fetch_resource(
                client=client, url=f"{base_url}/robots.txt", ip_address=ip_address
            )
            if robots_resource:
                # parse the robots.txt file
                robots_parser = urllib.robotparser.RobotFileParser()
                robots_parser.parse(
                    robots_resource.content.decode("utf-8").splitlines()
                )

                # get the page delay
                if robots_parser.crawl_delay("*") is not None:
                    domain_delay = robots_parser.crawl_delay("*")
                    LOGGER.info("Crawl delay for %s: %f", domain, domain_delay)

                # get the sitemap list
                site_maps = robots_parser.site_maps()
                if site_maps:
                    for sitemap_url in site_maps[:DEFAULT_MAX_SITEMAPS]:
                        # parse the url
                        parsed_url = urllib.parse.urlparse(sitemap_url)

                        # check if it's a relative path or absolute path
                        if parsed_url.scheme and parsed_url.netloc:
                            domain_paths.append(parsed_url.path)
                        else:
                            domain_paths.append(parsed_url.path)

            # fetch the resources
            tasks = []
            LOGGER.info("Fetching %d paths from %s...", len(domain_paths), domain)
            for path in domain_paths:
                # skip robots.txt since we've already fetched it
                if path == "/robots.txt":
                    continue

                # add delay between requests
                tasks.append(
                    self.fetch_resource(
                        client=client, url=f"{base_url}{path}", ip_address=ip_address
                    )
                )

                # avoid reverse DoS via extreme delays like Crawl-Delay: 999999
                LOGGER.info(
                    "Delaying %f seconds for %s...",
                    min(CONFIG.http_delay_max, domain_delay),
                    domain,
                )
                await asyncio.sleep(min(CONFIG.http_delay_max, domain_delay))

            # wait for all tasks to complete
            for coro in asyncio.as_completed(tasks):
                web_resource = await coro
                if web_resource:
                    # add the page to the list
                    yield web_resource
                    pages.append(web_resource)

        # update the domain index
        self.save_domain_content(pages)
