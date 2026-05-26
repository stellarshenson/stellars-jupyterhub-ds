"""Handler for settings page."""

import os

from jupyterhub.handlers import BaseHandler
from tornado import web


class SettingsPageHandler(BaseHandler):
    """Handler for rendering the settings page (admin only, read-only)."""

    SETTINGS_DICT_PATH = "/srv/jupyterhub/settings_dictionary.yml"

    @web.authenticated
    async def get(self):
        """Render the settings page showing key environment variables."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Settings Page] Admin {current_user.name} accessed settings panel")
        settings = self._load_settings()

        html = self.render_template("settings.html", sync=True, user=current_user, settings=settings)
        self.finish(html)

    def _load_settings(self):
        """Load settings from YAML dictionary file and populate with env values."""
        import yaml

        settings = []
        try:
            with open(self.SETTINGS_DICT_PATH, 'r') as f:
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
            self.log.error(f"[Settings Page] Settings dictionary not found: {self.SETTINGS_DICT_PATH}")
        except Exception as e:
            self.log.error(f"[Settings Page] Error loading settings dictionary: {e}")

        return settings
