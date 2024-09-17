"""
Default project logger to file alea_web_survey.log
"""

# imports
import logging
from pathlib import Path

# set up logging to file with timestamps
LOG_PATH = Path(__file__).parent.parent / "alea_web_survey.log"

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_PATH)],
)

# get the logger
LOGGER = logging.getLogger(__name__)

# set the default log level
LOGGER.setLevel(logging.INFO)
