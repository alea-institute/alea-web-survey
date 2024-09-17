"""
Configuration module for the alea_web_survey package.
"""

# imports
import dataclasses
import json
from pathlib import Path


def default_weights() -> dict:
    """
    Default weights for the domain generation methods.

    These names must match methods in the DomainGenerator class.

    Returns:
        dict: A dictionary of weights for the domain generation
    """

    return {
        "get_random_known_domain": 90 / 100.0,
        "get_random_known_domain_tld": 2 / 100.0,
        "get_random_words_domain": 2 / 100.0,
        "get_random_chars_domain": 2 / 100.0,
        "get_random_domain_tld_suffix": 2 / 100.0,
        "get_random_ipv4_domain": 2 / 100.0,
    }


def default_path_list() -> list:
    """
    Default list of paths for the domain generation.

    Returns:
        list: A list of paths
    """

    return [
        "/",
        "/robots.txt",
        "/ai.txt",
        "/humans.txt",
        "/security.txt",
        "/sitemap.xml",
    ]


# dataclass for config to load from JSON
@dataclasses.dataclass
class WebSurveyConfig:
    """
    Configuration class for the WebSurvey package.
    """

    # dataclass fields with default values
    s3_bucket: str = "web-survey.aleainstitute.ai"
    domain_path: str = "domains.trie"
    user_agent: str = (
        "ALEA-AI-Web-Survey/0.1.0 (https://aleainstitute.ai; hello@aleainstitute.ai)"
    )
    dns_resolve_timeout: float = 5.0
    http_pool_size: int = 5
    http_keep_alive: int = 10
    http_network_timeout: int = 5
    http_connect_timeout: int = 5
    http_read_timeout: int = 5
    http_write_timeout: int = 5
    playwright_timeout: int = 5
    path_list: list[str] = dataclasses.field(default_factory=default_path_list)
    domain_weights: dict = dataclasses.field(default_factory=default_weights)

    @staticmethod
    def from_json(file_path: Path):
        """
        Load a WebSurveyConfig object from a JSON file.

        Args:
            file_path (Path): Path to the JSON file.

        Returns:
            WebSurveyConfig: A WebSurveyConfig object.
        """
        with file_path.open("rt", encoding="utf-8") as input_file:
            config_data = json.load(input_file)
            return WebSurveyConfig(**config_data)


# load the configuration as a module-level variable
CONFIG = WebSurveyConfig.from_json(Path(__file__).parent.parent / "config.json")

# if you want to output for editing, you can do this:
# print(json.dumps(dataclasses.asdict(CONFIG), default=str, indent=2))
