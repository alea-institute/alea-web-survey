"""
Module to generate domain names using various methods for enumeration and reconnaissance purposes.
"""

# imports
import json
import logging
import random
from pathlib import Path
from typing import Optional

import dns.exception

# packages
import dns.resolver
import httpx
import lxml.html
import marisa_trie

# project import
from alea_web_survey.config import CONFIG

# set up the logger
LOGGER = logging.getLogger(__name__)

# constants
DEFAULT_DATA_PATH = Path().home() / ".alea" / "web-survey"
DEFAULT_DICTIONARY_PATH = Path("resources") / "words"
DEFAULT_DOMAIN_PATH = DEFAULT_DATA_PATH / CONFIG.domain_path


class DomainGenerator:
    """
    A class to generate domain names using various methods.

    Attributes:
        known_domains (list): List of known domain names.
        known_tlds (list): List of known top-level domains (TLDs).
        dictionary_words (list): List of words from the dictionary.
    """

    def __init__(
        self,
        dictionary_file: Optional[Path] = None,
    ):
        """
        Initialize the DomainGenerator with files containing known domains, TLDs, and a dictionary.

        Args:
            dictionary_file (Path): Path to the file containing the dictionary words.
        """
        self.known_domains = self.load_domain_list()
        self.dictionary_words = self.load_dictionary(
            dictionary_file or DEFAULT_DICTIONARY_PATH
        )
        self.known_tlds = self.load_tld_list()

    @staticmethod
    def load_dictionary(file_path: Path) -> list[str]:
        """
        Load a list of words from a dictionary file.

        Args:
            file_path (Path): Path to the dictionary file.

        Returns:
            list[str]: List of words from the dictionary.
        """
        return [
            word.strip()
            for word in file_path.read_text(encoding="utf-8").splitlines()
            if len(word.strip()) > 0
        ]

    @staticmethod
    def load_domain_list():
        """
        Load a list of known domain names from a file.

        Returns:
            list: List of known domain names.
        """
        domain_trie_path = DEFAULT_DATA_PATH / "domains.trie"
        domain_trie = marisa_trie.Trie()  # pylint: disable=c-extension-no-member
        domain_trie.load(domain_trie_path.as_posix())
        return list(domain_trie.keys())

    @staticmethod
    def load_tld_list(force_update: bool = False) -> list[str]:
        """
        Get the list of TLDs from wiki and return them as a list.  Check
        for cached file first.

        Args:
            force_update (bool): Force update of the cached file.

        Returns:
            list[str]: List of TLDs.
        """
        # check if the tld file exists
        tld_file = DEFAULT_DATA_PATH / "tld.json"
        if tld_file.exists() and not force_update:
            return json.loads(tld_file.read_text(encoding="utf-8"))

        try:
            tld_page = httpx.get(
                "https://en.wikipedia.org/wiki/List_of_Internet_top-level_domains"
            ).content
            page = lxml.html.fromstring(tld_page)
            tld_list = [
                tld.text.strip().strip(".")
                for tld in page.xpath(".//td")
                if tld.text and tld.text.startswith(".")
            ]
            tld_file.write_text(json.dumps(tld_list), encoding="utf-8")
            return tld_list
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.error("Failed to retrieve TLD list: %s", e)
            return []

    def enumerate_domain(self, target_domain: str) -> list[str]:
        """
        Enumerate DNS records of various types for a given domain.

        Args:
            target_domain (str): The domain to enumerate DNS records for.

        Returns:
            list: List of DNS records for the domain.
        """
        # DNS record types to query
        record_types = ["A", "AAAA", "CNAME", "MX"]
        resolver = dns.resolver.Resolver()
        dns_records = {}

        # Query each record type
        for record_type in record_types:
            try:
                answers = resolver.resolve(
                    target_domain, record_type, lifetime=CONFIG.dns_resolve_timeout
                )
                dns_records[record_type] = [rdata.to_text() for rdata in answers]
            except (
                dns.resolver.NoAnswer,
                dns.resolver.NXDOMAIN,
                dns.resolver.NoNameservers,
                dns.exception.Timeout,
            ):
                continue

        # filter the DNS records to things that look like a domain name
        subdomain_list = []
        for record_type, records in dns_records.items():
            for record in records:
                if record.endswith("."):
                    subdomain_list.append(record)

        return subdomain_list

    def get_random_known_domain(self) -> str:
        """
        Sample a random known domain.

        Returns:
            str: A random domain from the known domains list.
        """
        return random.choice(self.known_domains)

    def get_random_known_domain_tld(self) -> str:
        """
        Sample a random known domain with an alternate TLD.

        Returns:
            str: The domain with the TLD changed to a random TLD.
        """
        # get the original domain
        domain = self.get_random_known_domain()

        # swap the last part of the domain with a random TLD
        random_tld = random.choice(self.known_tlds)

        # swap the last component
        domain_parts = domain.split(".")
        domain_parts[-1] = random_tld
        return ".".join(domain_parts)

    @staticmethod
    def string_to_domain(input_string: str) -> str:
        """
        Remove any invalid characters for DNS entries.

        Args:
            input_string (str): The input string to convert to a valid domain.

        Returns:
            str: The input string converted to a valid domain.
        """
        return "".join(
            [c.lower() for c in input_string if c.isalnum() or c in ["-", "."]]
        )

    def get_random_words_domain(self, min_words: int = 1, max_words: int = 3) -> str:
        """
        Generate a domain from random word(s) from the dictionary.

        Args:
            min_words (int): Minimum number of words to use.
            max_words (int): Maximum number of words to use.

        Returns:
            str: A domain name generated from random words.
        """
        # sample number of words
        num_words = random.randint(min_words, max_words)

        # get the random words
        words = random.sample(self.dictionary_words, num_words)

        # choose a separate randomly
        separator = random.choice(["", "-", "."])

        # get a random tld
        tld = random.choice(self.known_tlds)

        # combine the words
        return f"{self.string_to_domain(separator.join(words))}.{tld}"

    def get_random_chars_domain(self, min_chars: int = 1, max_chars: int = 10) -> str:
        """
        Generate a domain from random characters.

        Args:
            min_chars (int): Minimum number of characters to use.
            max_chars (int): Maximum number of characters

        Returns:
            str: A domain name generated from random characters.
        """
        # sample number of characters
        num_chars = random.randint(min_chars, max_chars)

        # get the random characters
        characters = random.sample("abcdefghijklmnopqrstuvwxyz", num_chars)

        # get a random tld
        tld = random.choice(self.known_tlds)

        # combine the charachters
        return f"{''.join(characters)}.{tld}"

    def get_random_domain_tld_suffix(self) -> str:
        """
        Generate domains using domain hacks (e.g., using TLD as part of the word).

        Returns:
            str: A domain name using domain hack.
        """
        # pick a random tld
        tld = random.choice(self.known_tlds)

        # find a dictionary word that ends with it
        valid_words = [
            word
            for word in self.dictionary_words
            if word.endswith(tld) and len(word) > len(tld)
        ]
        if len(valid_words) == 0:
            return self.get_random_words_domain()

        # pick a random word
        word = random.choice(valid_words)

        # return the domain hack
        subword = word[: -len(tld)]
        return f"{subword}.{tld}"

    def get_random_ipv4_domain(self) -> str:
        """
        Generate a random IPv4 address.

        Returns:
            str: A random IPv4 address.
        """
        # get a random ipv4 address
        ipv4_address = ".".join([str(random.randint(0, 255)) for _ in range(4)])

        # do reverse lookup
        qname = dns.reversename.from_address(ipv4_address)
        try:
            # resolve the PTR record and try to return from the loop
            answer = dns.resolver.resolve(qname, "PTR")
            for rr in answer:
                return str(rr)
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.error("Error resolving PTR record: %s", e)

        # fall back on this
        return self.get_random_known_domain()

    def generate(self, method_weights: Optional[dict[str, float]] = None) -> str:
        """
        Randomly select and return a domain name generated using one of the methods.
        """
        # get config default if not set
        method_weights = method_weights or CONFIG.domain_weights

        # randomly select a method
        while True:
            method = random.choices(
                list(method_weights.keys()), weights=list(method_weights.values()), k=1
            )[0]
            try:
                if method in method_weights:
                    return getattr(self, method)()
            except Exception as e:  # pylint: disable=broad-except
                LOGGER.error("Error generating domain: %s", e)
                continue
