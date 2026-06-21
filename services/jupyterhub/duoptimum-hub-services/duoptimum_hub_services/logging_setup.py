"""One loguru sink for the platform's own hub-side log lines.

JupyterHub (the DuoptimumHub app) formats its OWN logs via traitlets; these are the
PLATFORM's lines - startup, GPU inventory, activity sampler, user-sync events. They
were a mix of bare ``print()`` and ad-hoc ``getLogger()`` names (``JupyterHub`` /
``jupyterhub`` / ``jupyterhub.*``), so they rendered inconsistently and INFO on a
non-app logger could even fail to show. Route them all through one loguru sink instead:
consistent, level-aware, coloured when stderr is a TTY and plain when piped (docker
logs) - "coloured if the terminal permits". Importing ``log`` configures the sink once.

The sink level is INFO by default; set ``JUPYTERHUB_LOG_LEVEL`` (TRACE/DEBUG/INFO/
WARNING/ERROR/CRITICAL) to change it - the Hub's own ``c.JupyterHub.log_level`` does not
reach this independent sink, so this env is how an operator turns our lines up or down.
An unknown value falls back to INFO so a typo never blocks boot.

Scope: RUNTIME hub code only. Build-time, stdlib-only scripts (e.g. event_schema_fix)
keep ``print`` on purpose - their output is the image-build log, not runtime logging.
"""
import os
import sys

from loguru import logger

# colour markup is parsed when colourising (TTY) and stripped when not, so piped
# output stays clean - no literal <tags>
_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "<level>{level: <7}</level> "
    "<cyan>{name}</cyan> - <level>{message}</level>"
)

# loguru's built-in level names; anything else is an operator typo
_VALID_LEVELS = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}


def _resolve_level(raw):
    """Map a raw JUPYTERHUB_LOG_LEVEL value to a valid loguru level name (default INFO).

    Unknown/blank/None -> INFO so an operator typo never crashes the sink at import.
    """
    level = (raw or "").strip().upper()
    return level if level in _VALID_LEVELS else "INFO"


# configure once at import: a single stderr sink, level from JUPYTERHUB_LOG_LEVEL (INFO
# default), colour auto-detected from the TTY (loguru's colorize=None). Re-import returns
# the same configured logger.
logger.remove()
logger.add(
    sys.stderr,
    level=_resolve_level(os.environ.get("JUPYTERHUB_LOG_LEVEL")),
    format=_FORMAT,
    colorize=None,
    backtrace=False,
    diagnose=False,
)

log = logger
