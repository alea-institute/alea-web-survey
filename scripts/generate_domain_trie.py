"""
Create a marisa_trie from a list of one or more domain lists.

Currently, this relies on the CloudFlare Top 10M list retrieved from the CloudFlare Radar project.
"""

# imports
import gzip
from pathlib import Path
from typing import Generator

# packages
import marisa_trie

# constants
DEFAULT_DATA_PATH = Path().home() / ".alea" / "web-survey"
DOMAIN_LISTS = [
    Path(__file__).parent.parent
    / "resources"
    / "cloudflare-radar_top-1000000-domains_20240909-20240916.csv.gz",
]

if __name__ == "__main__":
    # load the domain lists
    def domain_list_generator() -> Generator[str, None, None]:
        """
        Generate domain names from the domain lists.

        Yields:
            str: The domain name.
        """
        for domain_list in DOMAIN_LISTS:
            with gzip.open(domain_list, "rt", encoding="utf-8") as input_file:
                for line in input_file:
                    yield line.strip()

    # create the marisa trie
    domain_trie = marisa_trie.Trie(domain_list_generator())  # pylint: disable=c-extension-no-member

    # save the trie
    trie_output_path = DEFAULT_DATA_PATH / "domains.trie"
    domain_trie.save(trie_output_path.as_posix())
