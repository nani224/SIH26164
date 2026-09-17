import json
import logging
import os

logger = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    with open(os.path.join(path, "config.json")) as fh:
        return json.load(fh)


def greet(name: str) -> str:
    logger.info("greeting %s", name)
    return f"hello, {name}"
