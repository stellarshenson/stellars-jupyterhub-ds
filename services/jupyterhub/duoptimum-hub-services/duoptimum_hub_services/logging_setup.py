"""One loguru sink for the platform's own hub-side log lines.

JupyterHub (the DuoptimumHub app) formats its OWN logs via traitlets; these are the
PLATFORM's lines - startup, GPU inventory, activity sampler, user-sync events. They
were a mix of bare ``print()`` and ad-hoc ``getLogger()`` names (``JupyterHub`` /
``jupyterhub`` / ``jupyterhub.*``), so they rendered inconsistently and INFO on a
non-app logger could even fail to show. Route them all through one loguru sink instead:
consistent, level-aware, coloured when stderr is a TTY and plain when piped (docker
logs) - "coloured if the terminal permits". Importing ``log`` configures the sink once.

Scope: RUNTIME hub code only. Build-time, stdlib-only scripts (e.g. event_schema_fix)
keep ``print`` on purpose - their output is the image-build log, not runtime logging.
"""
import sys

from loguru import logger

# colour markup is parsed when colourising (TTY) and stripped when not, so piped
# output stays clean - no literal <tags>
_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "<level>{level: <7}</level> "
    "<cyan>{name}</cyan> - <level>{message}</level>"
)

# configure once at import: a single stderr sink, INFO+, colour auto-detected from the
# TTY (loguru's default colorize=None). Re-import returns the same configured logger.
logger.remove()
logger.add(sys.stderr, level="INFO", format=_FORMAT, colorize=None, backtrace=False, diagnose=False)

log = logger
