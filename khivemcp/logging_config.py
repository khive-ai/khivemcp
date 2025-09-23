"""Logging configuration utilities."""

import logging
import logging.config
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def setup_logging(
    level: str = "INFO", quiet: bool = False, config_file: Path | None = None
) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        quiet: If True, suppress all output except errors
        config_file: Optional path to external logging config file (YAML/JSON)
    """
    if config_file and config_file.exists():
        # Load external logging configuration
        try:
            with open(config_file) as f:
                if config_file.suffix.lower() in [".yaml", ".yml"]:
                    config_dict = yaml.safe_load(f)
                else:
                    # Assume JSON
                    import json

                    config_dict = json.load(f)

            logging.config.dictConfig(config_dict)
            # Use a basic logger since external config is now loaded
            logging.getLogger(__name__).info(
                f"Loaded logging config from {config_file}"
            )
            return
        except Exception as e:
            # Use basic logging for error reporting since external config failed
            logging.basicConfig(
                level=logging.WARNING, format="%(levelname)s - %(message)s"
            )
            logging.getLogger(__name__).error(
                f"Failed to load logging config from {config_file}: {e}"
            )
            logging.getLogger(__name__).warning(
                "Falling back to basic logging configuration"
            )

    # Fallback to basic configuration
    if quiet:
        level = "ERROR"

    # Configure the root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Set specific logger levels for common noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("fastmcp").setLevel(logging.INFO)
