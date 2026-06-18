"""Handlers for the settings page (HTML) and the settings data API (JSON)."""

import logging
import os

from jupyterhub.handlers import BaseHandler
from tornado import web

log = logging.getLogger('jupyterhub.settings')

SETTINGS_DICT_PATH = "/srv/jupyterhub/settings_dictionary.yml"


def load_settings_dict(path=SETTINGS_DICT_PATH):
    """Load the settings dictionary and resolve each entry's live env value.

    Returns a flat list of ``{category, name, value, description}`` in file
    order. Read-only: these are the running env values, never written here.
    """
    import yaml

    settings = []
    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        for category, items in config.items():
            if not isinstance(items, list):
                continue

            for item in items:
                name = item.get('name', '')
                default = str(item.get('default', ''))
                value = os.environ.get(name, default)

                if not value and 'empty_display' in item:
                    value = item['empty_display']

                settings.append({
                    "category": category,
                    "name": name,
                    "value": value,
                    "description": item.get('description', ''),
                })
    except FileNotFoundError:
        log.error(f"[Settings] Settings dictionary not found: {path}")
    except Exception as e:
        log.error(f"[Settings] Error loading settings dictionary: {e}")

    return settings


class SettingsDataHandler(BaseHandler):
    """Read-only JSON of the live platform settings (admin only)."""

    @web.authenticated
    async def get(self):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this endpoint")

        self.finish({"settings": load_settings_dict(SETTINGS_DICT_PATH)})
